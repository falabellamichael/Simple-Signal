#!/usr/bin/env python3
"""
Simple Signal CLI - A stylish local AI inference command-line interface
Provides a terminal-based AI assistant with beautiful output and interactive chat mode.
"""

import json
import os
import sys
from datetime import datetime
from typing import Optional, List, Dict, Any

def load_env_file():
    """Load environment variables from .env file if it exists"""
    # 1. Try local/script directory
    for path in [os.getcwd(), os.path.dirname(__file__)]:
        env_path = os.path.join(path, '.env')
        if os.path.exists(env_path):
            try:
                with open(env_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            parts = line.split('=', 1)
                            if len(parts) == 2:
                                key = parts[0].strip()
                                val = parts[1].strip().strip('"\'')
                                if key not in os.environ:
                                    os.environ[key] = val
            except Exception:
                pass
    
    # 2. Try specific fallback path for Website Project backend
    fallback_path = r"C:\Users\Falab\OneDrive\Documents\Website Project\backend\.env"
    if os.path.exists(fallback_path):
        try:
            with open(fallback_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        parts = line.split('=', 1)
                        if len(parts) == 2:
                            key = parts[0].strip()
                            val = parts[1].strip().strip('"\'')
                            if key not in os.environ:
                                os.environ[key] = val
        except Exception:
            pass

# Load environment variables on startup
load_env_file()

# Try to import optional dependencies
try:
    import torch
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

try:
    import torch_directml
    HAS_DML = torch_directml.is_available()
except ImportError:
    HAS_DML = False

try:
    from transformers import AutoTokenizer, AutoModelForCausalLM
    HAS_TRANSFORMERS = True
except ImportError:
    HAS_TRANSFORMERS = False


class SimpleSignalAI:
    """Main AI inference engine with CLI interface"""
    
    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path
        self.tokenizer = None
        self.model = None
        self.config = self._load_config()
        # Set up compute device: CUDA (NVIDIA GPU) -> CPU
        # Note: DirectML (AMD GPU) is disabled for local PyTorch loading because the DirectML compiler
        # has known bugs with Qwen/Llama architectures, resulting in random gibberish.
        # AMD users should run the LM Studio local server (Vulkan/DirectML backend) which runs flawlessly.
        if HAS_TORCH and torch.cuda.is_available():
            self.device = "cuda"
        else:
            self.device = "cpu"
            
        self.is_api = False
        self.api_url = None
        self.selected_model = None
        if self.model_path:
            cleaned = self.model_path.strip('"\'')
            if cleaned.startswith("http://") or cleaned.startswith("https://"):
                self.is_api = True
                self.api_url = cleaned
        
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from config.json or use defaults"""
        config_path = os.path.join(os.path.dirname(__file__), 'config.json')
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        
        # Default configuration
        return {
            "model": {
                "path": None,  # Set to actual model path if available
                "max_length": 2048,
                "temperature": 0.7,
                "top_p": 0.9,
                "repetition_penalty": 1.0
            },
            "chat": {
                "system_prompt": "You are Simple Signal AI, a helpful local assistant.",
                "max_tokens": 512
            },
            "output": {
                "theme": "dark",  # dark, light, cyberpunk
                "verbose": True
            }
        }
    
    def _check_lm_studio(self) -> Optional[str]:
        """Check if LM Studio is running locally on localhost or 127.0.0.1"""
        import urllib.request
        import urllib.error
        
        # Load API token from environment if available
        api_token = os.environ.get("LM_API_TOKEN") or os.environ.get("SIGNAL_SHARE_LM_STUDIO_API_TOKEN")
        
        for host in ["localhost", "127.0.0.1"]:
            url = f"http://{host}:1234/v1"
            try:
                # Ping LM Studio models endpoint with a 1.5s timeout
                req = urllib.request.Request(f"{url}/models")
                if api_token:
                    req.add_header("Authorization", f"Bearer {api_token}")
                
                with urllib.request.urlopen(req, timeout=1.5) as response:
                    if response.status == 200:
                        return url
            except urllib.error.HTTPError as e:
                if e.code == 401:
                    # 401 means the server is running and active, but requires token
                    return url
            except Exception:
                pass
        return None

    def _call_api(self, messages: List[Dict[str, str]], max_tokens: Optional[int] = None) -> str:
        """Call the OpenAI-compatible API endpoint"""
        import urllib.request
        import json
        
        # Normalize url
        if self.api_url.endswith("/chat/completions"):
            url = self.api_url
        else:
            url = f"{self.api_url}/chat/completions"
            
        headers = {"Content-Type": "application/json"}
        
        # Load API token from environment if available
        api_token = os.environ.get("LM_API_TOKEN") or os.environ.get("SIGNAL_SHARE_LM_STUDIO_API_TOKEN")
        if api_token:
            headers["Authorization"] = f"Bearer {api_token}"
        
        payload = {
            "messages": messages,
            "temperature": self.config["model"].get("temperature", 0.7),
            "max_tokens": max_tokens or self.config["chat"]["max_tokens"],
            "top_p": self.config["model"].get("top_p", 0.9)
        }
        
        if getattr(self, "selected_model", None):
            payload["model"] = self.selected_model
            
        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=30.0) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                return res_data["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"\n❌ API Error: {e}")
            return "Error: Could not retrieve response from API."

    def load_model(self):
        """Load the AI model (API or local HF/GGUF format)"""
        # 1. Check if we already detected API from model_path
        if self.is_api:
            print(f"🌐 Connected to remote API: {self.api_url}\n")
            return True

        # 2. Check if local LM Studio is running
        lm_url = self._check_lm_studio()
        if lm_url:
            self.is_api = True
            self.api_url = lm_url
            print(f"🌐 Connected via GPU acceleration to LM Studio: {self.api_url}\n")
            return True

        # 3. Fallback to local model loading via transformers
        if not HAS_TRANSFORMERS:
            print("\n⚠️  Transformers library not installed. Running in demo mode.\n")
            return False
        
        if self.model_path is None:
            print("ℹ️  No model path specified. Please set MODEL_PATH environment variable.")
            return False
        
        try:
            model_dir = self.model_path
            gguf_file = None

            # Clean path quotes if any
            model_dir = model_dir.strip('"\'')

            # Detect if pointing to a GGUF file or a directory containing a GGUF file
            if os.path.isfile(model_dir) and model_dir.endswith('.gguf'):
                gguf_file = os.path.basename(model_dir)
                model_dir = os.path.dirname(model_dir)
            elif os.path.isdir(model_dir):
                files = os.listdir(model_dir)
                gguf_files = [f for f in files if f.endswith('.gguf')]
                if gguf_files:
                    gguf_file = gguf_files[0]

            device_map = "auto" if str(self.device) in ["cuda", "cpu"] else None
            
            if gguf_file:
                # Check for gguf package dependency
                try:
                    import gguf
                except ImportError:
                    print("\n⚠️  GGUF models require the 'gguf' package. Installing it now...\n")
                    import subprocess
                    import sys
                    subprocess.run([sys.executable, "-m", "pip", "install", "gguf"], check=True)
                
                print(f"🔄 Loading GGUF model: {gguf_file} from {model_dir}")
                self.tokenizer = AutoTokenizer.from_pretrained(model_dir, gguf_file=gguf_file)
                self.model = AutoModelForCausalLM.from_pretrained(
                    model_dir,
                    gguf_file=gguf_file,
                    device_map=device_map,
                    torch_dtype=torch.float16 if (HAS_TORCH and torch.cuda.is_available()) else torch.float32
                )
            else:
                print(f"🔄 Loading model from: {model_dir}")
                self.tokenizer = AutoTokenizer.from_pretrained(model_dir)
                self.model = AutoModelForCausalLM.from_pretrained(
                    model_dir,
                    device_map=device_map,
                    torch_dtype=torch.float16 if (HAS_TORCH and torch.cuda.is_available()) else torch.float32
                )
            
            # Move model to custom device (e.g. DirectML) if not handled by device_map="auto"
            if str(self.device) not in ["cpu", "cuda"] and self.device is not None:
                print(f"📦 Moving model to acceleration device: {self.device}...")
                self.model = self.model.to(self.device)
            
            print("✅ Model loaded successfully!\n")
            return True
        except Exception as e:
            print(f"❌ Error loading model: {e}\n")
            return False

    
    def generate(self, prompt: str, max_tokens: Optional[int] = None) -> str:
        """Generate text from the model"""
        if self.is_api:
            messages = [
                {"role": "system", "content": self.config["chat"]["system_prompt"]},
                {"role": "user", "content": prompt}
            ]
            return self._call_api(messages, max_tokens)
            
        if not HAS_TRANSFORMERS or self.model is None:
            # Demo mode - simple response
            demo_responses = [
                "This is a demo response. To use real AI inference, install transformers and set MODEL_PATH.",
                "I'm Simple Signal AI! I can help you with various tasks once properly configured.",
                "Hello! I'm your local AI assistant. Try asking me something!"
            ]
            return demo_responses[0]
        
        try:
            messages = [
                {"role": "system", "content": self.config["chat"]["system_prompt"]},
                {"role": "user", "content": prompt}
            ]
            
            # Apply chat template if available, fallback to simple format
            try:
                full_prompt = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            except Exception:
                full_prompt = f"{messages[0]['content']}\n\n{messages[1]['content']}"
            
            inputs = self.tokenizer(full_prompt, return_tensors="pt")
            
            # Move inputs to device (e.g. DirectML) if accelerating
            if str(self.device) != "cpu" and self.device is not None:
                inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # Generate
            temp = self.config["model"].get("temperature", 0.7)
            top_p = self.config["model"].get("top_p", 0.9)
            do_sample = temp > 0.0
            
            output = self.model.generate(
                **inputs,
                max_new_tokens=max_tokens or self.config["chat"]["max_tokens"],
                do_sample=do_sample,
                temperature=temp,
                top_p=top_p
            )
            
            # Decode only the generated tokens
            input_length = inputs["input_ids"].shape[-1]
            new_tokens = output[0][input_length:]
            response = self.tokenizer.decode(new_tokens, skip_special_tokens=True)
            
            return response.strip()
        except Exception as e:
            print(f"❌ Generation error: {e}")
            return "Error generating response."
    
    def chat(self, messages: List[Dict[str, str]]) -> str:
        """Process a conversation and generate response"""
        if self.is_api:
            chat_messages = []
            has_system = any(msg.get("role") == "system" for msg in messages)
            if not has_system:
                chat_messages.append({"role": "system", "content": self.config["chat"]["system_prompt"]})
            chat_messages.extend(messages)
            return self._call_api(chat_messages, self.config["chat"]["max_tokens"])

        if not HAS_TRANSFORMERS or self.model is None:
            return "Demo mode: Please install transformers and load a model for real inference."
        
        try:
            # Apply chat template if available, fallback to simple format
            try:
                chat_messages = []
                has_system = any(msg.get("role") == "system" for msg in messages)
                if not has_system:
                    chat_messages.append({"role": "system", "content": self.config["chat"]["system_prompt"]})
                chat_messages.extend(messages)
                full_prompt = self.tokenizer.apply_chat_template(chat_messages, tokenize=False, add_generation_prompt=True)
            except Exception:
                prompt_parts = []
                for msg in messages:
                    role = msg.get("role", "user")
                    content = msg.get("content", "")
                    prefix = {"system": "SYS ", "user": "USR ", "assistant": "ASSISTANT "}.get(role, "USR ")
                    prompt_parts.append(f"{prefix}{content}")
                
                full_prompt = "\n\n".join(prompt_parts)
                full_prompt += "\n\nASSISTANT: "
            
            inputs = self.tokenizer(full_prompt, return_tensors="pt", truncation=True, max_length=self.config["model"]["max_length"])
            
            # Move inputs to device (e.g. DirectML) if accelerating
            if str(self.device) != "cpu" and self.device is not None:
                inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            temp = self.config["model"].get("temperature", 0.7)
            top_p = self.config["model"].get("top_p", 0.9)
            do_sample = temp > 0.0
            
            output = self.model.generate(
                **inputs,
                max_new_tokens=self.config["chat"]["max_tokens"],
                do_sample=do_sample,
                temperature=temp,
                top_p=top_p
            )
            
            # Decode only the generated tokens
            input_length = inputs["input_ids"].shape[-1]
            new_tokens = output[0][input_length:]
            response = self.tokenizer.decode(new_tokens, skip_special_tokens=True)
            
            return response.strip()
        except Exception as e:
            print(f"❌ Chat error: {e}")
            return "Error processing conversation."


class CLIInterface:
    """Command-line interface with styling"""
    
    THEMES = {
        "dark": {
            "prompt_prefix": "🤖 ",
            "user_prefix": "👤 ",
            "separator": "─" * 60,
            "info": "ℹ️ ",
            "success": "✅ ",
            "error": "❌ ",
            "warning": "⚠️ ",
            "bg_color": "\033[40m",
            "text_color": "\033[0m"
        },
        "light": {
            "prompt_prefix": "🤖 ",
            "user_prefix": "👤 ",
            "separator": "─" * 60,
            "info": "ℹ️ ",
            "success": "✅ ",
            "error": "❌ ",
            "warning": "⚠️ ",
            "bg_color": "\033[47m",
            "text_color": "\033[0m"
        },
        "cyberpunk": {
            "prompt_prefix": "🔮 ",
            "user_prefix": "💬 ",
            "separator": "▓" * 60,
            "info": "[INFO]",
            "success": "[OK]",
            "error": "[ERR]",
            "warning": "[WARN]",
            "bg_color": "",
            "text_color": "\033[91m"
        }
    }
    
    def __init__(self, ai: SimpleSignalAI):
        self.ai = ai
        self.theme_name = ai.config["output"]["theme"]
        self.theme = self.THEMES.get(self.theme_name, self.THEMES["dark"])
        
    def print_header(self):
        """Print the application header"""
        print("\n" + self.theme["separator"])
        print(f"{self.theme['success']}  Simple Signal CLI v1.0")
        print(f"{self.theme['info']}   Local AI Inference Interface")
        print(f"{self.theme['separator']}")
        
    def print_footer(self):
        """Print the application footer"""
        print(self.theme["separator"])
        print(f"{self.theme['info']}   Type 'quit' or press Ctrl+C to exit")
        print(self.theme["separator"] + "\n")

    def _show_theme_info(self):
        """Show available themes and current theme"""
        print(self.theme["separator"])
        print(f"\n{self.theme['success']}  THEME SELECTOR")
        print(self.theme["separator"])
        print(f"\nCurrent Theme: {self.theme_name}")
        print("\nAvailable Themes:")
        
        for name, theme_data in self.THEMES.items():
            status = "✅" if name == self.theme_name else "  "
            print(f"  {status} {name}")
        
        print(self.theme["separator"])
        print(f"\n{self.theme['info']}  Use '/theme' to view this menu at any time")
        print(self.theme["separator"] + "\n")
    
    def print_message(self, role: str, content: str):
        """Print a message with appropriate prefix"""
        prefix = self.theme["user_prefix"] if role == "user" else self.theme["prompt_prefix"]
        print(f"{prefix}{content}")
        # Add visual separator after long messages
        if len(content) > 50:
            print("─" * (len(content) + 10))
    
    def run_interactive(self):
        """Run interactive chat mode"""
        self.print_header()
        
        conversation = []
        
        while True:
            try:
                user_input = input(f"{self.theme['user_prefix']}You: ").strip()
                
                if not user_input:
                    continue
                
                # Handle theme command
                if user_input.lower() == '/theme':
                    self._show_theme_info()
                    continue
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    self.print_footer()
                    break
                
                # Add user message to conversation history
                conversation.append({"role": "user", "content": user_input})
                
                # Generate response using chat history
                response = self.ai.chat(conversation)
                self.print_message("assistant", response)
                
                # Add assistant response to conversation history
                conversation.append({"role": "assistant", "content": response})
                    
            except KeyboardInterrupt:
                print("\n\n" + self.theme["warning"] + "Interrupted by user.")
                self.print_footer()
                break
    
    def run_demo_mode(self):
        """Run in demo mode without model"""
        self.print_header()
        
        print(f"{self.theme['info']}  Demo Mode - No model loaded")
        print(f"{self.theme['info']}  Install transformers and set MODEL_PATH for real AI\n")
        
        while True:
            try:
                user_input = input(f"{self.theme['user_prefix']}You: ").strip()
                
                if not user_input:
                    continue
                
                # Handle theme command
                if user_input.lower() == '/theme':
                    self._show_theme_info()
                    continue
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    self.print_footer()
                    break
                    
                self.print_message("user", user_input)
                
                # Demo responses
                demo_responses = {
                    "hello": "Hello! I'm Simple Signal AI. To use real inference, install transformers and load a model.",
                    "hi": "Hi there! I can help you with various tasks once properly configured.",
                    "help": "Available commands: quit/exit - Exit the application",
                    "default": "This is a demo response. For real AI inference, please set MODEL_PATH environment variable and install transformers."
                }
                
                # Simple keyword matching for demo mode
                lower_input = user_input.lower()
                if any(kw in lower_input for kw in ["hello", "hi", "hey"]):
                    response = demo_responses["hello"]
                elif "help" in lower_input:
                    response = demo_responses["help"]
                else:
                    response = demo_responses["default"]
                
                self.print_message("assistant", response)
                    
            except KeyboardInterrupt:
                print("\n\n" + self.theme["warning"] + "Interrupted by user.")
                self.print_footer()
                break
    
    def run(self):
        """Main entry point"""
        # Try loading model (API or local)
        model_loaded = self.ai.load_model()
        
        if model_loaded:
            self.run_interactive()
        else:
            self.run_demo_mode()


def show_model_selector(ai):
    """Show interactive model selector menu"""
    print("\n" + "=" * 60)
    print("📦 MODEL SELECTOR")
    print("=" * 60)
    
    # Check for API connection first
    lm_url = ai._check_lm_studio()
    
    if lm_url:
        print(f"\n🌐 Connected to LM Studio at: {lm_url}")
        
        try:
            import urllib.request
            import json
            
            # Normalize url
            models_url = f"{lm_url}/models" if lm_url.endswith("/v1") else f"{lm_url}/v1/models"
            req = urllib.request.Request(models_url)
            
            # Add API token if available
            api_token = os.environ.get("LM_API_TOKEN") or os.environ.get("SIGNAL_SHARE_LM_STUDIO_API_TOKEN")
            if api_token:
                req.add_header("Authorization", f"Bearer {api_token}")
                
            with urllib.request.urlopen(req, timeout=5.0) as response:
                models_data = json.loads(response.read().decode("utf-8"))
                
                if isinstance(models_data, list):
                    models = models_data
                elif isinstance(models_data, dict) and "data" in models_data:
                    models = models_data.get("data", [])
                else:
                    models = []
                
                print(f"\n📋 Available Models ({len(models)} found):\n")
                for i, model in enumerate(models, 1):
                    id = model.get("id", "Unknown")
                    details = model.get("details", {})
                    size = details.get("size", details.get("size_in_bytes", "N/A"))
                    if isinstance(size, int):
                        size_str = f"{size / (1024**3):.1f} GB"
                    else:
                        size_str = str(size)
                    
                    status = model.get("status", "unknown").lower()
                    status_icon = "✅" if status == "running" else "🔄"
                    
                    print(f"  {i}. {status_icon} {id}")
                    if size_str != "N/A":
                        print(f"     Size: {size_str}")
                
                print("\n💡 Select a model number to load, or press Enter to use default.")
                
                try:
                    choice = input("Enter your choice [1-{}]: ".format(len(models))).strip()
                    
                    if choice.isdigit() and 1 <= int(choice) <= len(models):
                        selected_model = models[int(choice) - 1]
                        model_id = selected_model.get("id", "")
                        print(f"\n🎯 Loading model: {model_id}")
                        
                        # Update AI with selected model URL (append /v1/chat/completions for API)
                        ai.api_url = f"{lm_url}/chat/completions"
                        ai.is_api = True
                        return model_id
                    else:
                        print("\nℹ️  No model selected. Using default configuration.")
                        return None
                except KeyboardInterrupt:
                    print("\n\n⚠️  Model selection cancelled.")
                    return None
                except Exception as e:
                    print(f"\n❌ Error reading models: {e}")
                    return None
                    
        except Exception as e:
            print(f"\n⚠️  Could not list models: {e}")
            print("Using default configuration.\n")
            return None
    else:
        print("\nℹ️  No API connection detected.")
        print("If you have LM Studio running, start it first to see available models.")
        print("Or specify a model path via MODEL_PATH environment variable or command line argument.\n")
        return None


def main():
    """Main function with optional model selector"""
    # Fix Windows console UTF-8 issues
    if sys.platform == 'win32':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
            sys.stderr.reconfigure(encoding='utf-8')
        except Exception:
            pass

    # Parse arguments
    model_path = os.environ.get("MODEL_PATH")
    
    if len(sys.argv) > 1:
        model_path = sys.argv[1]
    
    # Check for --skip-selector flag to skip the model selector
    skip_selector = False
    if len(sys.argv) > 2 and sys.argv[2].lower() in ['--skip-selector', '-s']:
        skip_selector = True
    
    # Initialize AI with model path (if provided)
    ai = SimpleSignalAI(model_path=model_path)
    
    # Check if we're connected to an API (LM Studio)
    lm_url = ai._check_lm_studio()
    
    # If no model path specified AND connected to API AND not skipping, show model selector by default
    if not model_path and lm_url and not skip_selector:
        print("\n🔍 Detecting available models...")
        selected_model = show_model_selector(ai)
        
        # If a model was selected, reload with that model
        if selected_model and ai.is_api:
            ai.selected_model = selected_model
            print(f"\n✅ Model '{selected_model}' is now active.\n")
    
    cli = CLIInterface(ai)
    cli.run()


if __name__ == "__main__":
    main()
