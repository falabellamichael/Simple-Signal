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

# Try to import optional dependencies
try:
    import torch
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

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
    
    def load_model(self):
        """Load the AI model if transformers is available"""
        if not HAS_TRANSFORMERS:
            print("\n⚠️  Transformers library not installed. Running in demo mode.\n")
            return False
        
        if self.model_path is None:
            print("ℹ️  No model path specified. Please set MODEL_PATH environment variable.")
            return False
        
        try:
            print(f"🔄 Loading model from: {self.model_path}")
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_path)
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_path,
                device_map="auto",
                torch_dtype=torch.float16 if HAS_TORCH else torch.float32
            )
            print("✅ Model loaded successfully!\n")
            return True
        except Exception as e:
            print(f"❌ Error loading model: {e}\n")
            return False
    
    def generate(self, prompt: str, max_tokens: Optional[int] = None) -> str:
        """Generate text from the model"""
        if not HAS_TRANSFORMERS or self.model is None:
            # Demo mode - simple response
            demo_responses = [
                "This is a demo response. To use real AI inference, install transformers and set MODEL_PATH.",
                "I'm Simple Signal AI! I can help you with various tasks once properly configured.",
                "Hello! I'm your local AI assistant. Try asking me something!"
            ]
            return demo_responses[0]
        
        try:
            # Format prompt with system message
            messages = [
                {"role": "system", "content": self.config["chat"]["system_prompt"]},
                {"role": "user", "content": prompt}
            ]
            
            # Convert to model input format (simplified)
            full_prompt = f"{messages[0]['content']}\n\n{messages[1]['content']}"
            
            inputs = self.tokenizer(full_prompt, return_tensors="pt")
            
            # Generate
            output = self.model.generate(
                **inputs,
                max_new_tokens=max_tokens or self.config["chat"]["max_tokens"],
                temperature=self.config["model"]["temperature"],
                top_p=self.config["model"]["top_p"]
            )
            
            # Decode and clean output
            generated = self.tokenizer.decode(output[0], skip_special_tokens=True)
            response = generated.split(self.tokenizer.bos_token_id)[1] if hasattr(self.tokenizer, 'bos_token_id') else generated
            
            return response.strip()
        except Exception as e:
            print(f"❌ Generation error: {e}")
            return "Error generating response."
    
    def chat(self, messages: List[Dict[str, str]]) -> str:
        """Process a conversation and generate response"""
        if not HAS_TRANSFORMERS or self.model is None:
            return "Demo mode: Please install transformers and load a model for real inference."
        
        try:
            # Build prompt from conversation history
            prompt_parts = []
            for msg in messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                prefix = {"system": "SYS ", "user": "USR ", "assistant": "ASSISTANT "}.get(role, "USR ")
                prompt_parts.append(f"{prefix}{content}")
            
            full_prompt = "\n\n".join(prompt_parts)
            
            # Add assistant placeholder
            full_prompt += "\n\nASSISTANT: "
            
            inputs = self.tokenizer(full_prompt, return_tensors="pt", truncation=True, max_length=self.config["model"]["max_length"])
            
            output = self.model.generate(
                **inputs,
                max_new_tokens=self.config["chat"]["max_tokens"],
                temperature=self.config["model"]["temperature"],
                top_p=self.config["model"]["top_p"]
            )
            
            generated = self.tokenizer.decode(output[0], skip_special_tokens=True)
            response = generated.split(self.tokenizer.bos_token_id)[1] if hasattr(self.tokenizer, 'bos_token_id') else generated
            
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
    
    def print_message(self, role: str, content: str):
        """Print a message with appropriate prefix"""
        prefix = self.theme["user_prefix"] if role == "user" else self.theme["prompt_prefix"]
        print(f"{prefix}{content}")
        # Add visual separator after long messages
        if len(content) > 50:
            print("─" * (len(content) + 10))
    
    def run_interactive(self):
        """Run interactive chat mode"""
        print_header()
        
        while True:
            try:
                user_input = input(f"{self.theme['user_prefix']}You: ").strip()
                
                if not user_input.lower() in ['quit', 'exit', 'q']:
                    self.print_message("user", user_input)
                    
                    # Generate response
                    response = self.ai.generate(user_input)
                    self.print_message("assistant", response)
                    
            except KeyboardInterrupt:
                print("\n\n" + self.theme["warning"] + "Interrupted by user.")
                break
    
    def run_demo_mode(self):
        """Run in demo mode without model"""
        print_header()
        
        print(f"{self.theme['info']}  Demo Mode - No model loaded")
        print(f"{self.theme['info']}  Install transformers and set MODEL_PATH for real AI\n")
        
        while True:
            try:
                user_input = input(f"{self.theme['user_prefix']}You: ").strip()
                
                if not user_input.lower() in ['quit', 'exit', 'q']:
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
                break
    
    def run(self):
        """Main entry point"""
        if HAS_TRANSFORMERS and self.ai.model_path:
            self.ai.load_model()
        
        if HAS_TRANSFORMERS and self.ai.model is not None:
            self.run_interactive()
        else:
            self.run_demo_mode()


def main():
    """Main function"""
    # Parse arguments
    model_path = os.environ.get("MODEL_PATH")
    
    if len(sys.argv) > 1:
        model_path = sys.argv[1]
    
    ai = SimpleSignalAI(model_path=model_path)
    cli = CLIInterface(ai)
    cli.run()


if __name__ == "__main__":
    main()
