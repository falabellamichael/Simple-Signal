#!/usr/bin/env python3
"""
Simple Signal Web CLI - FastAPI Server
Bridges the Simple Signal AI engine with a web-based terminal client.
"""

import os
import json
import asyncio
import threading
import time
import subprocess
import psutil
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Import existing SimpleSignalAI capabilities
from ai_cli import SimpleSignalAI, HAS_TRANSFORMERS
from telemetry import get_gpu_info_data_sync, get_system_status as fetch_system_telemetry

app = FastAPI(title="Simple Signal Web CLI")

# Enable CORS for local testing/development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Logging middleware to debug and track all incoming requests
@app.middleware("http")
async def log_requests(request: Request, call_next):
    response = await call_next(request)
    print(f"📥 Web Request: {request.method} {request.url.path} -> {response.status_code}")
    return response

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

@app.on_event("startup")
def startup_event():
    # Trigger model detection/loading asynchronously or in background to prevent blocking
    import threading
    def load():
        global model_loaded
        model_loaded = ai.load_model()
    threading.Thread(target=load, daemon=True).start()

class ChatPayload(BaseModel):
    messages: List[Dict[str, str]]

class ConfigUpdate(BaseModel):
    theme: Optional[str] = None
    system_prompt: Optional[str] = None

class ModelSelect(BaseModel):
    model: str

class BackendSelect(BaseModel):
    backend: str

class MetricsTogglePayload(BaseModel):
    enabled: bool



# Global cache and control for system metrics to prevent blocking FastAPI request threads
system_metrics_enabled = True
system_status_cache = {
    "cpu": {"percentage": 0.0},
    "memory": {"used": 0.0, "total": 0.0, "percentage": 0.0},
    "disk": {"used": 0.0, "total": 0.0, "percentage": 0.0},
    "gpu": {"percentage": 0.0, "name": "N/A"}
}
system_status_lock = threading.Lock()

def update_system_status_loop():
    """Background worker that periodically polls system metrics to avoid blocking request threads"""
    # Wait a moment for server startup
    time.sleep(1.0)
    while True:
        try:
            if not system_metrics_enabled:
                time.sleep(1.0)
                continue
            
            # Fetch status via high-performance telemetry wrapper
            status = fetch_system_telemetry()
            
            # Write safely to global cache
            with system_status_lock:
                system_status_cache.update(status)
        except Exception:
            pass
        time.sleep(0.5)

# Start background metric monitoring thread
threading.Thread(target=update_system_status_loop, daemon=True).start()

def stream_gpu_table():
    """Format and stream GPU detection as an aligned ASCII text table"""
    yield "🔌 Querying system for graphics hardware details...\n\n"
    time.sleep(0.3)
    
    gpus = get_gpu_info_data_sync()
    
    # Column configuration widths (total characters to fit inside 80cols cleanly)
    col_widths = {
        "name": 32,
        "backend": 24,
        "id": 14,
        "status": 10
    }
    
    # Build ASCII dividers
    separator = "+" + "-"*(col_widths["name"]+2) + "+" + "-"*(col_widths["backend"]+2) + "+" + "-"*(col_widths["id"]+2) + "+" + "-"*(col_widths["status"]+2) + "+\n"
    header = f"| {'GPU Device Name'.ljust(col_widths['name'])} | {'Backend Support'.ljust(col_widths['backend'])} | {'Device ID'.ljust(col_widths['id'])} | {'Status'.ljust(col_widths['status'])} |\n"
    
    yield separator
    yield header
    yield separator
    time.sleep(0.1)
    
    for gpu in gpus:
        name = gpu["name"]
        if len(name) > col_widths["name"]:
            name = name[:col_widths["name"]-3] + "..."
            
        backend = gpu["backend"]
        if len(backend) > col_widths["backend"]:
            backend = backend[:col_widths["backend"]-3] + "..."
            
        dev_id = gpu["identifier"]
        if len(dev_id) > col_widths["id"]:
            dev_id = dev_id[:col_widths["id"]-3] + "..."
            
        status = gpu["status"]
        if len(status) > col_widths["status"]:
            status = status[:col_widths["status"]-3] + "..."
            
        row = f"| {name.ljust(col_widths['name'])} | {backend.ljust(col_widths['backend'])} | {dev_id.ljust(col_widths['id'])} | {status.ljust(col_widths['status'])} |\n"
        yield row
        yield separator
        time.sleep(0.04)

def stream_search_results(query: str):
    """Perform a web search via DuckDuckGo and stream findings chunk-by-chunk"""
    yield "🔍 Searching the web for: " + query + "...\n\n"
    time.sleep(0.3)
    try:
        from web_search import search_ddg
        # Note: We don't need loop.run_in_executor here because this generator runs in a thread pool already!
        results = search_ddg(query)
        
        if not results:
            yield "❌ No search results found or web request failed."
            return
            
        yield f"✅ Found {len(results)} web results:\n\n"
        time.sleep(0.2)
        
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
                time.sleep(0.002)
    except Exception as e:
        yield f"❌ Error during web search: {str(e)}"

def generate_chat_stream(messages: List[Dict[str, str]]):
    """Stream response in real-time depending on active backend mode"""
    # 1. API Mode (e.g. LM Studio running)
    if ai.is_api:
        import requests
        # Refresh API URL dynamically in case LM Studio was started after server launch
        lm_url = ai._check_lm_studio()
        if lm_url:
            ai.api_url = f"{lm_url}/chat/completions"
            
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
            
        try:
            response = requests.post(url, json=payload, headers=headers, stream=True, timeout=30.0)
            if response.status_code != 200:
                yield f"❌ API Error: Received status code {response.status_code}\n{response.text}"
                return
                
            for line in response.iter_lines(chunk_size=1):
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
                                yield content
                        except Exception:
                            pass
        except Exception as e:
            yield f"❌ API Connection Error: {str(e)}"

    # 2. Local Transformers Mode
    elif HAS_TRANSFORMERS and ai.model is not None and ai.tokenizer is not None:
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
            
            # Run in a side thread to let TextIteratorStreamer work
            t = Thread(target=ai.model.generate, kwargs=generation_kwargs)
            t.start()
            
            # Yield from streamer directly (synchronous iterator)
            for chunk in streamer:
                yield chunk
        except Exception as e:
            yield f"❌ Generation error: {str(e)}"

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
            time.sleep(0.04)

@app.post("/api/chat")
def chat_endpoint(payload: ChatPayload):
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
    
    # Check for custom GPU command
    if last_user_message.strip().lower() == "/gpu":
        return StreamingResponse(
            stream_gpu_table(),
            media_type="text/plain; charset=utf-8"
        )
        
    return StreamingResponse(
        generate_chat_stream(messages),
        media_type="text/plain; charset=utf-8"
    )

@app.get("/api/config")
def get_config():
    """Retrieve settings and backend state"""
    backend_val = "local"
    if ai.is_api:
        backend_val = "llamacpp" if ai.api_url and "8080" in ai.api_url else "api"
    return {
        "theme": ai.config.get("output", {}).get("theme", "dark"),
        "system_prompt": ai.config.get("chat", {}).get("system_prompt", "You are Simple Signal AI, a helpful local assistant."),
        "is_api": ai.is_api,
        "backend": backend_val,
        "model_path": ai.model_path,
        "selected_model": ai.selected_model
    }

@app.post("/api/config")
def update_config(data: ConfigUpdate):
    """Persist settings to configuration file"""
    if data.theme:
        ai.config["output"]["theme"] = data.theme
    if data.system_prompt:
        ai.config["chat"]["system_prompt"] = data.system_prompt
    ai._save_config()
    return {"status": "success", "config": ai.config}

@app.get("/api/models")
def get_models():
    """Find models in local LM Studio or llama.cpp"""
    # 1. Determine which URL to query based on active api_url
    url_to_check = None
    if ai.api_url:
        parts = ai.api_url.split("/chat/completions")
        if parts:
            url_to_check = parts[0]
            
    # 2. Fallback to auto-detecting either if not set
    if not url_to_check:
        url_to_check = ai._check_lm_studio() or ai._check_llama_cpp()
        
    if url_to_check:
        try:
            import urllib.request
            models_url = f"{url_to_check}/models" if url_to_check.endswith("/v1") else f"{url_to_check}/v1/models"
            req = urllib.request.Request(models_url)
            
            # Add API token if checking LM Studio (1234)
            api_token = os.environ.get("LM_API_TOKEN") or os.environ.get("SIGNAL_SHARE_LM_STUDIO_API_TOKEN")
            if api_token and "1234" in url_to_check:
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
            
    return {"connected": False, "models": [], "info": "No active API server detected running locally."}

@app.get("/api/system/gpu")
def get_gpu_info():
    """Endpoint exposing the raw GPU hardware list as JSON"""
    gpus = get_gpu_info_data_sync()
    return {"gpus": gpus}

@app.get("/api/system/status")
def get_system_status():
    """Retrieve current system metrics from the background-populated cache"""
    with system_status_lock:
        return system_status_cache

@app.post("/api/system/toggle")
def toggle_system_metrics(payload: MetricsTogglePayload):
    global system_metrics_enabled
    system_metrics_enabled = payload.enabled
    
    # If disabled, zero out metrics to show they are inactive
    if not system_metrics_enabled:
        with system_status_lock:
            system_status_cache["cpu"] = {"percentage": 0.0}
            system_status_cache["memory"] = {"used": 0.0, "total": 0.0, "percentage": 0.0}
            system_status_cache["disk"] = {"used": 0.0, "total": 0.0, "percentage": 0.0}
            system_status_cache["gpu"] = {"percentage": 0.0, "name": "Disabled"}
            
    print(f"⚙️ System metrics tracking {'ENABLED' if system_metrics_enabled else 'DISABLED'}")
    return {"status": "success", "system_metrics_enabled": system_metrics_enabled}


@app.post("/api/model")
def select_model(data: ModelSelect):
    """Switch models or force API mode"""
    ai.selected_model = data.model
    if not ai.is_api:
        lm_url = ai._check_lm_studio()
        if lm_url:
            ai.is_api = True
            ai.api_url = f"{lm_url}/chat/completions"
    return {"status": "success", "selected": ai.selected_model}

@app.post("/api/backend")
def select_backend(data: BackendSelect):
    """Switch between LM Studio (API), llama.cpp (API), and PyTorch (Local) backend modes"""
    active_backend = data.backend
    if data.backend == "api":
        lm_url = ai._check_lm_studio()
        ai.is_api = True
        ai.force_local = False
        if lm_url:
            ai.api_url = f"{lm_url}/chat/completions"
        else:
            ai.api_url = "http://127.0.0.1:1234/v1/chat/completions"
    elif data.backend == "llamacpp":
        llama_url = ai._check_llama_cpp()
        ai.is_api = True
        ai.force_local = False
        if llama_url:
            ai.api_url = f"{llama_url}/chat/completions"
        else:
            ai.api_url = "http://127.0.0.1:8080/v1/chat/completions"
    elif data.backend == "local":
        ai.is_api = False
        ai.force_local = True
        if ai.model is None and HAS_TRANSFORMERS:
            # Load local model path/resources if configured
            ai.load_model()
    else:
        raise HTTPException(status_code=400, detail="Invalid backend mode")
        
    return {
        "status": "success",
        "backend": active_backend,
        "is_api": ai.is_api,
        "force_local": ai.force_local,
        "has_local_model": ai.model is not None
    }

# Mount static files directory
app.mount("/static", StaticFiles(directory="static"), name="static")

# Root endpoint serves index.html
@app.get("/")
def get_index():
    return FileResponse("static/index.html")

if __name__ == "__main__":
    import uvicorn
    print("\n" + "=" * 60)
    print("🚀 Simple Signal Web CLI is starting up...")
    print("👉 Open your browser at: http://localhost:8000")
    print("=" * 60 + "\n")
    uvicorn.run("web_server:app", host="127.0.0.1", port=8000, reload=False)
