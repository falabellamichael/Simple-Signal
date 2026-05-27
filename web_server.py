#!/usr/bin/env python3
"""
Simple Signal Web CLI - FastAPI Server
Bridges the Simple Signal AI engine with a web-based terminal client.
"""

import os
import json
import asyncio
import threading
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Import existing SimpleSignalAI capabilities
from ai_cli import SimpleSignalAI, HAS_TRANSFORMERS

app = FastAPI(title="Simple Signal Web CLI")

# Enable CORS for local testing/development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Fix Windows console UTF-8 issues
import sys
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Initialize SimpleSignalAI instance
ai = SimpleSignalAI()
# Trigger model detection/loading
model_loaded = ai.load_model()

class ChatPayload(BaseModel):
    messages: List[Dict[str, str]]

class ConfigUpdate(BaseModel):
    theme: Optional[str] = None
    system_prompt: Optional[str] = None

class ModelSelect(BaseModel):
    model: str

async def stream_search_results(query: str):
    """Perform a web search via DuckDuckGo and stream findings chunk-by-chunk"""
    yield "🔍 Searching the web for: " + query + "...\n\n"
    await asyncio.sleep(0.3)
    try:
        from web_search import search_ddg
        loop = asyncio.get_running_loop()
        results = await loop.run_in_executor(None, search_ddg, query)
        
        if not results:
            yield "❌ No search results found or web request failed."
            return
            
        yield f"✅ Found {len(results)} web results:\n\n"
        await asyncio.sleep(0.2)
        
        for idx, r in enumerate(results, 1):
            title = r["title"]
            url = r["url"]
            snippet = r["snippet"]
            
            result_block = f"**{idx}. {title}**\n"
            result_block += f"Link: [{url}]({url})\n"
            if snippet:
                result_block += f"{snippet}\n"
            result_block += "---\n\n"
            
            # Stream out the block in typewriter effect
            for char in result_block:
                yield char
                await asyncio.sleep(0.002)
    except Exception as e:
        yield f"❌ Error during web search: {str(e)}"

async def generate_chat_stream(messages: List[Dict[str, str]]):
    """Stream response in real-time depending on active backend mode"""
    loop = asyncio.get_running_loop()
    
    # 1. API Mode (e.g. LM Studio running)
    if ai.is_api:
        queue = asyncio.Queue()
        
        def make_request():
            try:
                import requests
                url = ai.api_url
                if not url.endswith("/chat/completions"):
                    url = f"{url}/chat/completions"
                    
                headers = {"Content-Type": "application/json"}
                api_token = os.environ.get("LM_API_TOKEN") or os.environ.get("SIGNAL_SHARE_LM_STUDIO_API_TOKEN")
                if api_token:
                    headers["Authorization"] = f"Bearer {api_token}"
                    
                payload = {
                    "messages": messages,
                    "temperature": ai.config["model"].get("temperature", 0.7),
                    "max_tokens": ai.config["chat"]["max_tokens"],
                    "top_p": ai.config["model"].get("top_p", 0.9),
                    "stream": True
                }
                if ai.selected_model:
                    payload["model"] = ai.selected_model
                    
                response = requests.post(url, json=payload, headers=headers, stream=True, timeout=30.0)
                
                if response.status_code != 200:
                    loop.call_soon_threadsafe(queue.put_nowait, f"❌ API Error: Received status code {response.status_code}")
                    loop.call_soon_threadsafe(queue.put_nowait, None)
                    return
                    
                for line in response.iter_lines():
                    if line:
                        decoded_line = line.decode('utf-8')
                        if decoded_line.startswith("data: "):
                            data_str = decoded_line[6:]
                            if data_str.strip() == "[DONE]":
                                break
                            try:
                                data_json = json.loads(data_str)
                                content = data_json["choices"][0]["delta"].get("content", "")
                                if content:
                                    loop.call_soon_threadsafe(queue.put_nowait, content)
                            except Exception:
                                pass
            except Exception as e:
                loop.call_soon_threadsafe(queue.put_nowait, f"❌ API Connection Error: {str(e)}")
            finally:
                loop.call_soon_threadsafe(queue.put_nowait, None)
                
        thread = threading.Thread(target=make_request, daemon=True)
        thread.start()
        
        while True:
            chunk = await queue.get()
            if chunk is None:
                break
            yield chunk

    # 2. Local Transformers Mode
    elif HAS_TRANSFORMERS and ai.model is not None and ai.tokenizer is not None:
        queue = asyncio.Queue()
        
        def run_generation():
            try:
                from transformers import TextIteratorStreamer
                from threading import Thread
                
                # Apply chat template
                try:
                    chat_messages = []
                    has_system = any(msg.get("role") == "system" for msg in messages)
                    if not has_system:
                        chat_messages.append({"role": "system", "content": ai.config["chat"]["system_prompt"]})
                    chat_messages.extend(messages)
                    full_prompt = ai.tokenizer.apply_chat_template(chat_messages, tokenize=False, add_generation_prompt=True)
                except Exception:
                    prompt_parts = []
                    for msg in messages:
                        role = msg.get("role", "user")
                        content = msg.get("content", "")
                        prefix = {"system": "SYS ", "user": "USR ", "assistant": "ASSISTANT "}.get(role, "USR ")
                        prompt_parts.append(f"{prefix}{content}")
                    full_prompt = "\n\n".join(prompt_parts) + "\n\nASSISTANT: "
                    
                inputs = ai.tokenizer(full_prompt, return_tensors="pt", truncation=True, max_length=ai.config["model"]["max_length"])
                
                if str(ai.device) != "cpu" and ai.device is not None:
                    inputs = {k: v.to(ai.device) for k, v in inputs.items()}
                    
                streamer = TextIteratorStreamer(ai.tokenizer, skip_prompt=True, skip_special_tokens=True)
                
                generation_kwargs = dict(
                    **inputs,
                    streamer=streamer,
                    max_new_tokens=ai.config["chat"]["max_tokens"],
                    do_sample=ai.config["model"].get("temperature", 0.7) > 0.0,
                    temperature=ai.config["model"].get("temperature", 0.7),
                    top_p=ai.config["model"].get("top_p", 0.9)
                )
                
                t = Thread(target=ai.model.generate, kwargs=generation_kwargs)
                t.start()
                
                for chunk in streamer:
                    loop.call_soon_threadsafe(queue.put_nowait, chunk)
            except Exception as e:
                loop.call_soon_threadsafe(queue.put_nowait, f"❌ Generation error: {str(e)}")
            finally:
                loop.call_soon_threadsafe(queue.put_nowait, None)
                
        thread = threading.Thread(target=run_generation, daemon=True)
        thread.start()
        
        while True:
            chunk = await queue.get()
            if chunk is None:
                break
            yield chunk

    # 3. Demo Mode (simulated streaming)
    else:
        last_msg = messages[-1]["content"].lower()
        
        demo_responses = {
            "hello": "Hello! I'm Simple Signal AI. This is the web-based CLI client running in **Demo Mode**.\n\nTo use real AI inference, please connect LM Studio locally or specify a `MODEL_PATH` in your terminal.\n\nType `/search <query>` to try the DuckDuckGo search integration!",
            "hi": "Hi there! I can help you with various tasks once properly configured.",
            "help": "Available web commands:\n  - `/search <query>`: Search DuckDuckGo\n  - `/clear`: Clear the console screen\n  - Select different themes from the header dropdown",
            "math": "Sure! Here is some LaTeX-rendered math. Here is an inline equation: $E = mc^2$, and here is a block equation:\n\n$$f(x) = \\int_{-\\infty}^{\\infty} e^{-x^2} dx = \\sqrt{\\pi}$$\n\nAlso, here is a sum expression:\n\n$$\\sum_{i=1}^{n} i = \\frac{n(n+1)}{2}$$\n\nThey should render beautifully on this screen! Try typing another LaTeX formula.",
            "default": "This is a demo response from Simple Signal AI.\n\nFor real AI inference, make sure LM Studio is running on your system (port 1234), or set the `MODEL_PATH` environment variable and install transformers.\n\nIf you want to search the web, type `/search <your query>`!"
        }
        
        if any(kw in last_msg for kw in ["hello", "hi", "hey"]):
            response = demo_responses["hello"]
        elif "help" in last_msg:
            response = demo_responses["help"]
        elif any(kw in last_msg for kw in ["math", "latex", "formula", "equation"]):
            response = demo_responses["math"]
        else:
            response = demo_responses["default"]
            
        # Stream word by word
        words = response.split(" ")
        for i, word in enumerate(words):
            yield word + (" " if i < len(words) - 1 else "")
            await asyncio.sleep(0.04)

@app.post("/api/chat")
async def chat_endpoint(payload: ChatPayload):
    """Receive messages, parsing for custom commands or forwarding to AI generator"""
    messages = payload.messages
    if not messages:
        raise HTTPException(status_code=400, detail="Empty messages")

    # Get user prompt
    last_user_message = next((msg["content"] for msg in reversed(messages) if msg["role"] == "user"), "")
    
    # Check for custom search command
    if last_user_message.strip().startswith("/search "):
        query = last_user_message.strip()[8:].strip()
        return StreamingResponse(
            stream_search_results(query),
            media_type="text/plain; charset=utf-8"
        )
        
    return StreamingResponse(
        generate_chat_stream(messages),
        media_type="text/plain; charset=utf-8"
    )

@app.get("/api/config")
async def get_config():
    """Retrieve settings and backend state"""
    return {
        "theme": ai.config.get("output", {}).get("theme", "dark"),
        "system_prompt": ai.config.get("chat", {}).get("system_prompt", "You are Simple Signal AI, a helpful local assistant."),
        "is_api": ai.is_api,
        "model_path": ai.model_path,
        "selected_model": ai.selected_model
    }

@app.post("/api/config")
async def update_config(data: ConfigUpdate):
    """Persist settings to configuration file"""
    if data.theme:
        ai.config["output"]["theme"] = data.theme
    if data.system_prompt:
        ai.config["chat"]["system_prompt"] = data.system_prompt
    ai._save_config()
    return {"status": "success", "config": ai.config}

@app.get("/api/models")
async def get_models():
    """Find models in local LM Studio"""
    lm_url = ai._check_lm_studio()
    if lm_url:
        try:
            import urllib.request
            models_url = f"{lm_url}/models" if lm_url.endswith("/v1") else f"{lm_url}/v1/models"
            req = urllib.request.Request(models_url)
            
            api_token = os.environ.get("LM_API_TOKEN") or os.environ.get("SIGNAL_SHARE_LM_STUDIO_API_TOKEN")
            if api_token:
                req.add_header("Authorization", f"Bearer {api_token}")
                
            with urllib.request.urlopen(req, timeout=3.0) as response:
                models_data = json.loads(response.read().decode("utf-8"))
                
                models_list = []
                if isinstance(models_data, dict) and "data" in models_data:
                    models_list = [m.get("id") for m in models_data["data"]]
                elif isinstance(models_data, list):
                    models_list = [m.get("id") for m in models_data]
                    
                return {"connected": True, "models": models_list, "selected": ai.selected_model}
        except Exception as e:
            return {"connected": False, "models": [], "error": str(e)}
            
    return {"connected": False, "models": [], "info": "LM Studio API not detected running locally."}

@app.post("/api/model")
async def select_model(data: ModelSelect):
    """Switch models or force API mode"""
    ai.selected_model = data.model
    if not ai.is_api:
        lm_url = ai._check_lm_studio()
        if lm_url:
            ai.is_api = True
            ai.api_url = f"{lm_url}/chat/completions"
    return {"status": "success", "selected": ai.selected_model}

# Mount static files directory
app.mount("/static", StaticFiles(directory="static"), name="static")

# Root endpoint serves index.html
@app.get("/")
async def get_index():
    return FileResponse("static/index.html")

if __name__ == "__main__":
    import uvicorn
    print("\n" + "=" * 60)
    print("🚀 Simple Signal Web CLI is starting up...")
    print("👉 Open your browser at: http://localhost:8000")
    print("=" * 60 + "\n")
    uvicorn.run("web_server:app", host="127.0.0.1", port=8000, reload=True)
