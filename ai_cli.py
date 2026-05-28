#!/usr/bin/env python3
"""
Simple Signal CLI - A stylish local AI inference command-line interface
Provides a terminal-based AI assistant with beautiful output and interactive chat mode.
"""

import json
import os
import random
import re
import sys
import threading
import time
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
        self.force_local = False
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
        
    def _save_config(self):
        """Save configuration to config.json"""
        config_path = os.path.join(os.path.dirname(__file__), 'config.json')
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2)
        except Exception:
            pass
    
    def _check_lm_studio(self) -> Optional[str]:
        """Check if LM Studio is running locally on localhost or 127.0.0.1"""
        import urllib.request
        import urllib.error
        
        # Load API token from environment if available
        api_token = os.environ.get("LM_API_TOKEN") or os.environ.get("SIGNAL_SHARE_LM_STUDIO_API_TOKEN")
        
        for host in ["localhost", "127.0.0.1"]:
            # Query the root port URL (always returns 200 or 401 if running)
            # to avoid triggering the 'Unexpected endpoint' warning logs in LM Studio.
            test_url = f"http://{host}:1234/"
            url = f"http://{host}:1234/v1"
            try:
                req = urllib.request.Request(test_url)
                if api_token:
                    req.add_header("Authorization", f"Bearer {api_token}")
                
                with urllib.request.urlopen(req, timeout=1.5) as response:
                    if response.status in [200, 401]:
                        return url
            except urllib.error.HTTPError as e:
                if e.code in [200, 401]:
                    # 401 means running but requires token
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
        if not self.force_local:
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


from typing import Tuple

def format_latex_math(text: str) -> str:
    """Format LaTeX mathematical expressions in text into pretty Unicode representations."""
    greek_letters = {
        r'\alpha': 'α', r'\beta': 'β', r'\gamma': 'γ', r'\delta': 'δ', r'\epsilon': 'ε',
        r'\zeta': 'ζ', r'\eta': 'η', r'\theta': 'θ', r'\iota': 'ι', r'\kappa': 'κ',
        r'\lambda': 'λ', r'\mu': 'μ', r'\nu': 'ν', r'\xi': 'ξ', r'\pi': 'π',
        r'\rho': 'ρ', r'\sigma': 'σ', r'\tau': 'τ', r'\upsilon': 'υ', r'\phi': 'φ',
        r'\chi': 'χ', r'\psi': 'ψ', r'\omega': 'ω',
        r'\Delta': 'Δ', r'\Sigma': 'Σ', r'\Omega': 'Ω', r'\Theta': 'Θ', r'\Pi': 'Π',
        r'\Phi': 'Φ', r'\Psi': 'Ψ', r'\Gamma': 'Γ', r'\Lambda': 'Λ'
    }
    
    math_symbols = {
        r'\sum': '∑', r'\prod': '∏', r'\int': '∫', r'\sqrt': '√', r'\infty': '∞',
        r'\approx': '≈', r'\neq': '≠', r'\le': '≤', r'\ge': '≥', r'\pm': '±',
        r'\times': '×', r'\div': '÷', r'\cdot': '·', r'\partial': '∂', r'\nabla': '∇',
        r'\in': '∈', r'\notin': '∉', r'\forall': '∀', r'\exists': '∃', r'\to': '→',
        r'\left': '', r'\right': ''
    }
    
    superscripts = {
        '0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴', '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹',
        '+': '⁺', '-': '⁻', '=': '⁼', '(': '⁽', ')': '⁾', 'n': 'ⁿ', 'x': 'ˣ', 'y': 'ʸ', 'z': 'ᶻ', 'i': 'ⁱ',
        'j': 'ʲ', 'r': 'ʳ', 't': 'ᵗ', 'a': 'ᵃ', 'b': 'ᵇ', 'c': 'ᶜ', 'd': 'ᵈ', 'e': 'ᵉ', 'f': 'ᶠ', 'g': 'ᵍ',
        'h': 'ʰ', 'k': 'ᵏ', 'l': 'ˡ', 'm': 'ᵐ', 'o': 'ᵒ', 'p': 'ᵖ', 's': 'ˢ', 'u': 'ᵘ', 'v': 'ᵛ', 'w': 'ʷ'
    }
    
    subscripts = {
        '0': '₀', '1': '₁', '2': '₂', '3': '₃', '4': '₄', '5': '₅', '6': '₆', '7': '₇', '8': '₈', '9': '₉',
        '+': '₊', '-': '₋', '=': '₌', '(': '₍', ')': '₎', 'a': 'ₐ', 'e': 'ₑ', 'h': 'ₕ', 'i': 'ᵢ', 'j': 'ⱼ',
        'k': 'ₖ', 'l': 'ₗ', 'm': 'ₘ', 'n': 'ₙ', 'o': 'ₒ', 'p': 'ₚ', 'r': 'ᵣ', 's': 'ₛ', 't': 'ₜ', 'u': 'ᵤ',
        'v': 'ᵥ', 'x': 'ₓ'
    }
    
    def convert_script(val: str, mapping: dict) -> str:
        return "".join(mapping.get(char, char) for char in val)

    def process_math_block(match) -> str:
        expr = match.group(1)
        
        # 1. Replace Greek letters and math symbols
        for key, val in greek_letters.items():
            expr = expr.replace(key, val)
        for key, val in math_symbols.items():
            expr = expr.replace(key, val)
            
        # 2. Replace superscripts: ^{content}
        expr = re.sub(r'\^\{([^}]+)\}', lambda m: convert_script(m.group(1), superscripts), expr)
        # Replace single character superscripts: ^c
        expr = re.sub(r'\^(\w|\+|-|=)', lambda m: convert_script(m.group(1), superscripts), expr)
        
        # 3. Replace subscripts: _{content}
        expr = re.sub(r'\_\{([^}]+)\}', lambda m: convert_script(m.group(1), subscripts), expr)
        # Replace single character subscripts: _c
        expr = re.sub(r'\_(\w|\+|-|=)', lambda m: convert_script(m.group(1), subscripts), expr)
        
        # 4. Clean up fractions
        expr = re.sub(r'\\frac\{([^}]+)\}\{([^}]+)\}', r'(\1/\2)', expr)
        
        return expr

    # Process double dollar blocks first
    text = re.sub(r'\$\$(.*?)\$\$', process_math_block, text, flags=re.DOTALL)
    # Process single dollar blocks
    text = re.sub(r'\$(.*?)\$', process_math_block, text)
    # Process brackets and parentheses blocks
    text = re.sub(r'\\\\\[(.*?)\\\\\]', process_math_block, text, flags=re.DOTALL)
    text = re.sub(r'\\\[(.*?)\\\]', process_math_block, text, flags=re.DOTALL)
    text = re.sub(r'\\\\\((.*?)\\\\\)', process_math_block, text, flags=re.DOTALL)
    text = re.sub(r'\\\((.*?)\\\)', process_math_block, text, flags=re.DOTALL)
    
    return text

def find_empty(board: List[List[int]]) -> Optional[Tuple[int, int]]:
    """Find an empty cell in the Sudoku board."""
    for r in range(9):
        for c in range(9):
            if board[r][c] == 0:
                return r, c
    return None

def is_valid(board: List[List[int]], row: int, col: int, num: int) -> bool:
    """Check if placing num at board[row][col] is valid."""
    # Check row and column
    for i in range(9):
        if board[row][i] == num or board[i][col] == num:
            return False

    # Check 3x3 box
    start_row = (row // 3) * 3
    start_col = (col // 3) * 3
    for i in range(3):
        for j in range(3):
            if board[start_row + i][start_col + j] == num:
                return False

    return True

def solve_sudoku(board: List[List[int]]) -> bool:
    """Solve the Sudoku board using backtracking."""
    empty = find_empty(board)
    if not empty:
        return True
    row, col = empty
    
    nums = list(range(1, 10))
    random.shuffle(nums)
    for num in nums:
        if is_valid(board, row, col, num):
            board[row][col] = num
            if solve_sudoku(board):
                return True
            board[row][col] = 0
    return False

def generate_sudoku(size: int = 9) -> Tuple[List[List[int]], List[List[int]]]:
    """Generate a valid Sudoku puzzle and its solution."""
    if size != 9:
        raise ValueError("Only 9x9 supported.")

    board = [[0] * size for _ in range(size)]

    # Fill diagonal boxes first (independent of each other)
    def fill_box(r, c):
        nums = list(range(1, 10))
        random.shuffle(nums)
        for i in range(3):
            for j in range(3):
                board[r + i][c + j] = nums[i * 3 + j]

    fill_box(0, 0)
    fill_box(3, 3)
    fill_box(6, 6)

    # Solve the rest of the board
    solve_sudoku(board)
    
    # Save the solution
    solution = [row[:] for row in board]

    # Remove digits to create puzzle (remove ~50% of digits)
    cells_to_remove = random.sample(range(size**2), int(size**2 * 0.50))
    for idx in cells_to_remove:
        r, c = divmod(idx, size)
        board[r][c] = 0

    return board, solution

def is_solution_valid(board: List[List[int]]) -> bool:
    """Check if the completed board is a valid solution."""
    # Check rows
    for row in board:
        if sorted(row) != list(range(1, 10)):
            return False
            
    # Check columns
    for col_idx in range(9):
        col = [board[row_idx][col_idx] for row_idx in range(9)]
        if sorted(col) != list(range(1, 10)):
            return False
            
    # Check 3x3 boxes
    for r in range(0, 9, 3):
        for c in range(0, 9, 3):
            box = []
            for i in range(3):
                for j in range(3):
                    box.append(board[r + i][c + j])
            if sorted(box) != list(range(1, 10)):
                return False
                
    return True

def play_sudoku_curses(stdscr, puzzle: List[List[int]], solution: List[List[int]]):
    """Play Sudoku in curses mode."""
    import curses
    
    curses.curs_set(0)
    curses.start_color()
    curses.init_pair(1, curses.COLOR_CYAN, curses.COLOR_BLACK) # original numbers
    curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_BLACK) # user numbers
    curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLUE) # cursor selection
    curses.init_pair(4, curses.COLOR_GREEN, curses.COLOR_BLACK) # success
    curses.init_pair(5, curses.COLOR_RED, curses.COLOR_BLACK) # error
    
    current_board = [row[:] for row in puzzle]
    is_original = [[puzzle[r][c] != 0 for c in range(9)] for r in range(9)]
    
    row, col = 0, 0
    
    while True:
        stdscr.clear()
        stdscr.addstr(1, 2, "🎮 SUDOKU GAME CLI", curses.color_pair(1) | curses.A_BOLD)
        stdscr.addstr(2, 2, "Use arrow keys to move, 1-9 to fill, Backspace/0 to clear, 'q' to quit.")
        stdscr.addstr(3, 2, "Press 's' to submit and check solution.")
        
        # Draw background grid
        stdscr.addstr(4, 2, "╔═══╤═══╤═══╦═══╤═══╤═══╦═══╤═══╤═══╗")
        for r in range(9):
            stdscr.addstr(5 + r*2, 2, "║   │   │   ║   │   │   ║   │   │   ║")
            if r < 8:
                if (r + 1) % 3 == 0:
                    stdscr.addstr(6 + r*2, 2, "╠═══╪═══╪═══╬═══╪═══╪═══╬═══╪═══╪═══╣")
                else:
                    stdscr.addstr(6 + r*2, 2, "╟───┼───┼───╫───┼───┼───╫───┼───┼───╢")
        stdscr.addstr(22, 2, "╚═══╧═══╧═══╩═══╧═══╧═══╩═══╧═══╧═══╝")
        
        # Draw values
        for r in range(9):
            for c in range(9):
                val = current_board[r][c]
                val_str = str(val) if val != 0 else "."
                
                if r == row and c == col:
                    attr = curses.color_pair(3) | curses.A_BOLD
                else:
                    attr = curses.color_pair(1) if is_original[r][c] else curses.color_pair(2)
                    
                stdscr.addstr(5 + r*2, 4 + c*4, val_str, attr)
                
        stdscr.refresh()
        key = stdscr.getch()
        
        if key == ord('q'):
            break
        elif key == curses.KEY_UP and row > 0:
            row -= 1
        elif key == curses.KEY_DOWN and row < 8:
            row += 1
        elif key == curses.KEY_LEFT and col > 0:
            col -= 1
        elif key == curses.KEY_RIGHT and col < 8:
            col += 1
        elif ord('1') <= key <= ord('9'):
            if not is_original[row][col]:
                current_board[row][col] = int(chr(key))
        elif key in [ord('0'), curses.KEY_BACKSPACE, 127, 8]:
            if not is_original[row][col]:
                current_board[row][col] = 0
        elif key == ord('s'):
            if is_solution_valid(current_board):
                stdscr.addstr(24, 2, "🎉 CONGRATULATIONS! You solved the Sudoku correctly!", curses.color_pair(4) | curses.A_BOLD)
                stdscr.addstr(25, 2, "Press any key to exit.")
                stdscr.refresh()
                stdscr.getch()
                break
            else:
                stdscr.addstr(24, 2, "❌ Not quite correct yet! Keep trying.", curses.color_pair(5) | curses.A_BOLD)
                stdscr.addstr(25, 2, "Press any key to continue.")
                stdscr.refresh()
                stdscr.getch()

def play_sudoku_text(puzzle: List[List[int]], solution: List[List[int]]):
    """Play Sudoku in text mode."""
    current_board = [row[:] for row in puzzle]
    is_original = [[puzzle[r][c] != 0 for c in range(9)] for r in range(9)]
    
    def print_board():
        print("\n  ╔═══╤═══╤═══╦═══╤═══╤═══╦═══╤═══╤═══╗")
        for r in range(9):
            if r > 0:
                if r % 3 == 0:
                    print("  ╠═══╪═══╪═══╬═══╪═══╪═══╬═══╪═══╪═══╣")
                else:
                    print("  ╟───┼───┼───╫───┼───┼───╫───┼───┼───╢")
            row_chars = []
            for c in range(9):
                val = current_board[r][c]
                val_str = str(val) if val != 0 else "."
                if is_original[r][c]:
                    row_chars.append(f"\033[94m{val_str}\033[0m")
                elif val != 0:
                    row_chars.append(f"\033[92m{val_str}\033[0m")
                else:
                    row_chars.append(val_str)
            print(f"  ║ {row_chars[0]} │ {row_chars[1]} │ {row_chars[2]} ║ {row_chars[3]} │ {row_chars[4]} │ {row_chars[5]} ║ {row_chars[6]} │ {row_chars[7]} │ {row_chars[8]} ║")
        print("  ╚═══╧═══╧═══╩═══╧═══╧═══╩═══╧═══╧═══╝")

    while True:
        print_board()
        print("\nCommands:")
        print("  - Fill cell: 'r c v' (row column value, e.g. '1 1 5' for row 1, col 1, value 5)")
        print("  - Clear cell: 'r c 0' (e.g. '1 1 0')")
        print("  - 'submit' to check solution")
        print("  - 'quit' to exit game")
        
        try:
            cmd = input("\nEnter command: ").strip().lower()
            if cmd == 'quit':
                break
            elif cmd == 'submit':
                if is_solution_valid(current_board):
                    print("\n🎉 CONGRATULATIONS! You solved the Sudoku correctly!\n")
                    break
                else:
                    print("\n❌ Not quite correct yet! Keep trying.\n")
            else:
                parts = cmd.split()
                if len(parts) == 3:
                    r, c, v = int(parts[0]) - 1, int(parts[1]) - 1, int(parts[2])
                    if 0 <= r < 9 and 0 <= c < 9 and 0 <= v <= 9:
                        if is_original[r][c]:
                            print("\n⚠️ Cannot modify original puzzle cell!\n")
                        else:
                            current_board[r][c] = v
                    else:
                        print("\n⚠️ Invalid values! Row/Col should be 1-9, Value 0-9.\n")
                else:
                    print("\n⚠️ Invalid command format! Use 'row col value' (e.g. '1 2 5') or 'submit' or 'quit'.\n")
        except KeyboardInterrupt:
            print("\nGame exited.")
            break
        except Exception:
            print("\n⚠️ Error parsing command. Try again.\n")


class ThinkingSpinner:
    """A CLI spinner that runs in a background thread to indicate thinking or loading"""
    def __init__(self, prefix: str = "🤖 ", prompt_color: str = "", text_color: str = "", message: str = "Thinking..."):
        self.prefix = prefix
        self.prompt_color = prompt_color
        self.text_color = text_color
        self.message = message
        self.stop_event = threading.Event()
        self.thread = None

    def _spin(self):
        chars = ["/", "-", "\\", "|"]
        reset = "\033[0m"
        i = 0
        while not self.stop_event.is_set():
            char = chars[i % len(chars)]
            sys.stdout.write(f"\r{self.prompt_color}{self.prefix}AI:{reset} {self.text_color}{self.message} {char}{reset}")
            sys.stdout.flush()
            i += 1
            time.sleep(0.1)
        # Clear the spinner line
        sys.stdout.write("\r\033[K")
        sys.stdout.flush()

    def start(self):
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._spin, daemon=True)
        self.thread.start()

    def stop(self):
        if self.thread:
            self.stop_event.set()
            self.thread.join(timeout=1.0)

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()


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
            "bg_color": "",
            "text_color": "\033[38;5;253m",
            "prompt_color": "\033[1;38;5;111m",
            "user_color": "\033[38;5;244m",
            "accent_color": "\033[38;5;111m"
        },
        "light": {
            "prompt_prefix": "🤖 ",
            "user_prefix": "👤 ",
            "separator": "─" * 60,
            "info": "ℹ️ ",
            "success": "✅ ",
            "error": "❌ ",
            "warning": "⚠️ ",
            "bg_color": "",
            "text_color": "\033[38;5;255m",
            "prompt_color": "\033[1;38;5;231m",
            "user_color": "\033[38;5;252m",
            "accent_color": "\033[38;5;250m"
        },
        "cyberpunk": {
            "prompt_prefix": "🔮 ",
            "user_prefix": "⚡ ",
            "separator": "░▒▓" * 20,
            "info": "⚡ ",
            "success": "✨ ",
            "error": "🚨 ",
            "warning": "⚠️ ",
            "bg_color": "",
            "text_color": "\033[38;5;226m",
            "prompt_color": "\033[1;38;5;201m",
            "user_color": "\033[38;5;51m",
            "accent_color": "\033[38;5;201m"
        },
        "matrix": {
            "prompt_prefix": "📟 ",
            "user_prefix": "💾 ",
            "separator": "═" * 60,
            "info": "[SYS] ",
            "success": "[RUN] ",
            "error": "[ERR] ",
            "warning": "[WRN] ",
            "bg_color": "",
            "text_color": "\033[38;5;47m",
            "prompt_color": "\033[1;38;5;46m",
            "user_color": "\033[38;5;28m",
            "accent_color": "\033[38;5;46m"
        },
        "sunset": {
            "prompt_prefix": "🌅 ",
            "user_prefix": "👤 ",
            "separator": "─" * 60,
            "info": "🌅 ",
            "success": "🍊 ",
            "error": "🔥 ",
            "warning": "⚡ ",
            "bg_color": "",
            "text_color": "\033[38;5;220m",
            "prompt_color": "\033[1;38;5;202m",
            "user_color": "\033[38;5;208m",
            "accent_color": "\033[38;5;202m"
        },
        "ocean": {
            "prompt_prefix": "🌊 ",
            "user_prefix": "⛵ ",
            "separator": "≈" * 60,
            "info": "🐬 ",
            "success": "🌊 ",
            "error": "🚨 ",
            "warning": "⚠️ ",
            "bg_color": "",
            "text_color": "\033[38;5;153m",
            "prompt_color": "\033[1;38;5;33m",
            "user_color": "\033[38;5;75m",
            "accent_color": "\033[38;5;39m"
        },
        "forest": {
            "prompt_prefix": "🌿 ",
            "user_prefix": "🌲 ",
            "separator": "─" * 60,
            "info": "🌿 ",
            "success": "🍃 ",
            "error": "🍂 ",
            "warning": "⚠️ ",
            "bg_color": "",
            "text_color": "\033[38;5;107m",
            "prompt_color": "\033[1;38;5;34m",
            "user_color": "\033[38;5;94m",
            "accent_color": "\033[38;5;71m"
        },
        "dracula": {
            "prompt_prefix": "🧛 ",
            "user_prefix": "🦇 ",
            "separator": "─" * 60,
            "info": "🔮 ",
            "success": "✨ ",
            "error": "🩸 ",
            "warning": "⚠️ ",
            "bg_color": "",
            "text_color": "\033[38;5;231m",
            "prompt_color": "\033[1;38;5;141m",
            "user_color": "\033[38;5;212m",
            "accent_color": "\033[38;5;117m"
        }
    }

    
    def __init__(self, ai: SimpleSignalAI):
        self.ai = ai
        self.theme_name = ai.config["output"]["theme"]
        self.theme = self.THEMES.get(self.theme_name, self.THEMES["dark"])
        
    def print_header(self):
        """Print the application header"""
        accent = self.theme.get("accent_color", "")
        reset = "\033[0m"
        print("\n" + accent + self.theme["separator"] + reset)
        print(f"{self.theme['success']}  " + accent + "Simple Signal CLI v1.0" + reset)
        print(f"{self.theme['info']}   " + accent + "Local AI Inference Interface" + reset)
        print(accent + self.theme["separator"] + reset)
        
    def print_footer(self):
        """Print the application footer"""
        accent = self.theme.get("accent_color", "")
        reset = "\033[0m"
        print(accent + self.theme["separator"] + reset)
        print(f"{self.theme['info']}   Type 'quit' or press Ctrl+C to exit")
        print(accent + self.theme["separator"] + reset + "\n")

    def _show_help(self):
        """Show list of commands and summary of the program"""
        accent = self.theme.get("accent_color", "")
        text_color = self.theme.get("text_color", "")
        reset = "\033[0m"
        
        print("\n" + accent + self.theme["separator"] + reset)
        print(f"{self.theme['success']}  " + accent + "Simple Signal CLI - Help & Summary" + reset)
        print(accent + self.theme["separator"] + reset)
        
        print(f"\n{self.theme['info']}  {accent}SUMMARY:{reset}")
        print(f"       Simple Signal CLI is a local AI inference command-line interface.")
        print(f"       It enables interactive chat with local GGUF/Hugging Face models")
        print(f"       or local API endpoints (like LM Studio) with GPU acceleration.")
        print(f"       Features include LaTeX math rendering, terminal games, and web search.")
        
        print(f"\n{self.theme['info']}  {accent}AVAILABLE COMMANDS:{reset}")
        commands = [
            ("/help", "Show this help menu with a program summary and command descriptions."),
            ("/theme", "Open the interactive theme selector menu to switch themes."),
            ("/theme <name>", "Directly change to a specific theme (e.g., '/theme forest')."),
            ("/search <query>", "Search the web/DuckDuckGo and view formatted results inline."),
            ("/sudoku", "Start an interactive 9x9 Sudoku puzzle game in the terminal."),
            ("quit / exit / q", "Exit the application.")
        ]
        
        for cmd, desc in commands:
            cmd_color = self.theme.get("prompt_color", "")
            print(f"       {cmd_color}{cmd:<18}{reset} {text_color}{desc}{reset}")
            
        print("\n" + accent + self.theme["separator"] + reset + "\n")

    def _show_theme_info(self):
        """Show available themes and current theme"""
        accent = self.theme.get("accent_color", "")
        reset = "\033[0m"
        print(accent + self.theme["separator"] + reset)
        print(f"\n{self.theme['success']}  THEME SELECTOR")
        print(accent + self.theme["separator"] + reset)
        print(f"\nCurrent Theme: {self.theme_name}")
        print("\nAvailable Themes:")
        
        for name, theme_data in self.THEMES.items():
            status = "✅" if name == self.theme_name else "  "
            color = theme_data.get("prompt_color", "")
            print(f"  {status} {color}{name}{reset}")
        
        print(accent + self.theme["separator"] + reset)
        print(f"\n{self.theme['info']}  Use '/theme' to open the interactive theme selector,")
        print(f"       or '/theme <name>' to switch directly.")
        print(accent + self.theme["separator"] + reset + "\n")

    def _select_theme_interactive(self):
        """Interactively select and change the CLI theme"""
        accent = self.theme.get("accent_color", "")
        reset = "\033[0m"
        print(accent + self.theme["separator"] + reset)
        print(f"\n{self.theme['success']}  THEME SELECTOR")
        print(accent + self.theme["separator"] + reset)
        print(f"\nCurrent Theme: {self.theme_name}")
        print("\nAvailable Themes:")
        
        themes_list = list(self.THEMES.keys())
        for i, name in enumerate(themes_list, 1):
            status = "✅" if name == self.theme_name else "  "
            color = self.THEMES[name].get("prompt_color", "")
            print(f"  {i}. {status} {color}{name}{reset}")
        
        print(accent + self.theme["separator"] + reset)
        try:
            choice = input(f"\nSelect a theme [1-{len(themes_list)}] or type the name: ").strip()
            if not choice:
                return
            
            selected_theme = None
            if choice.isdigit() and 1 <= int(choice) <= len(themes_list):
                selected_theme = themes_list[int(choice) - 1]
            else:
                choice_lower = choice.lower()
                if choice_lower in self.THEMES:
                    selected_theme = choice_lower
                
            if selected_theme:
                self.theme_name = selected_theme
                self.theme = self.THEMES[selected_theme]
                self.ai.config["output"]["theme"] = selected_theme
                self.ai._save_config()
                print(f"\n{self.theme['success']} Theme successfully changed to '{selected_theme}'!\n")
            else:
                print(f"\n{self.theme['error']} Invalid selection. Theme unchanged.\n")
        except KeyboardInterrupt:
            print("\n\n⚠️ Theme selection cancelled.")

    def print_message(self, role: str, content: str):
        """Print a message with appropriate prefix and coloring"""
        reset = "\033[0m"
        formatted_content = format_latex_math(content)
        if role == "user":
            prefix = self.theme["user_prefix"]
            color = self.theme.get("user_color", "")
            print(f"{color}{prefix}{formatted_content}{reset}")
        else:
            prefix = self.theme["prompt_prefix"]
            color = self.theme.get("prompt_color", "")
            text_color = self.theme.get("text_color", "")
            print(f"{color}{prefix}AI:{reset} {text_color}{formatted_content}{reset}")
            
        # Add visual separator after long messages
        if len(content) > 50:
            accent = self.theme.get("accent_color", "")
            print(accent + "─" * 60 + reset)
            
    def run_interactive(self):
        """Run interactive chat mode"""
        self.print_header()
        
        conversation = []
        
        while True:
            try:
                user_input = input(f"{self.theme['user_prefix']}You: ").strip()
                
                if not user_input:
                    continue
                
                # Handle help command
                if user_input.lower() in ['/help', 'help']:
                    self._show_help()
                    continue
                
                # Handle theme command
                if user_input.lower().startswith('/theme'):
                    parts = user_input.split(maxsplit=1)
                    if len(parts) > 1:
                        requested = parts[1].lower().strip()
                        if requested in self.THEMES:
                            self.theme_name = requested
                            self.theme = self.THEMES[requested]
                            self.ai.config["output"]["theme"] = requested
                            self.ai._save_config()
                            print(f"\n{self.theme['success']} Theme successfully changed to '{requested}'!\n")
                        else:
                            print(f"\n{self.theme['error']} Theme '{requested}' not found. Available: {', '.join(self.THEMES.keys())}\n")
                    else:
                        self._select_theme_interactive()
                    continue
                
                # Handle Sudoku game
                if user_input.lower() == '/sudoku':
                    print("\n🎲 Generating Sudoku puzzle...")
                    try:
                        puzzle, solution = generate_sudoku()
                        try:
                            import curses
                            curses.wrapper(play_sudoku_curses, puzzle, solution)
                        except Exception:
                            print("\n⚠️ Curses mode failed/not supported. Starting text-only mode...")
                            play_sudoku_text(puzzle, solution)
                    except Exception as e:
                        print(f"\n❌ Error starting game: {e}")
                    continue
                
                # Handle Web Search
                if user_input.lower().startswith('/search'):
                    parts = user_input.split(maxsplit=1)
                    if len(parts) > 1:
                        query = parts[1].strip()
                        try:
                            from web_search import search_ddg, display_results, SearchSpinner
                            with SearchSpinner(f"Searching web for: '{query}'..."):
                                results = search_ddg(query)
                            display_results(results, query)
                        except Exception as e:
                            print(f"\n❌ Error performing search: {e}\n")
                    else:
                        print(f"\n{self.theme['error']} Please provide a search query. Example: /search python news\n")
                    continue
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    self.print_footer()
                    break
                
                # Add user message to conversation history
                conversation.append({"role": "user", "content": user_input})
                
                # Generate response using chat history with a visual thinking spinner
                spinner = ThinkingSpinner(
                    prefix=self.theme["prompt_prefix"],
                    prompt_color=self.theme.get("prompt_color", ""),
                    text_color=self.theme.get("text_color", ""),
                    message="Thinking..."
                )
                with spinner:
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
                
                # Handle help command
                if user_input.lower() in ['/help', 'help']:
                    self._show_help()
                    continue
                
                # Handle theme command
                if user_input.lower().startswith('/theme'):
                    parts = user_input.split(maxsplit=1)
                    if len(parts) > 1:
                        requested = parts[1].lower().strip()
                        if requested in self.THEMES:
                            self.theme_name = requested
                            self.theme = self.THEMES[requested]
                            self.ai.config["output"]["theme"] = requested
                            self.ai._save_config()
                            print(f"\n{self.theme['success']} Theme successfully changed to '{requested}'!\n")
                        else:
                            print(f"\n{self.theme['error']} Theme '{requested}' not found. Available: {', '.join(self.THEMES.keys())}\n")
                    else:
                        self._select_theme_interactive()
                    continue
                
                # Handle Sudoku game
                if user_input.lower() == '/sudoku':
                    print("\n🎲 Generating Sudoku puzzle...")
                    try:
                        puzzle, solution = generate_sudoku()
                        try:
                            import curses
                            curses.wrapper(play_sudoku_curses, puzzle, solution)
                        except Exception:
                            print("\n⚠️ Curses mode failed/not supported. Starting text-only mode...")
                            play_sudoku_text(puzzle, solution)
                    except Exception as e:
                        print(f"\n❌ Error starting game: {e}")
                    continue
                
                # Handle Web Search
                if user_input.lower().startswith('/search'):
                    parts = user_input.split(maxsplit=1)
                    if len(parts) > 1:
                        query = parts[1].strip()
                        try:
                            from web_search import search_ddg, display_results, SearchSpinner
                            with SearchSpinner(f"Searching web for: '{query}'..."):
                                results = search_ddg(query)
                            display_results(results, query)
                        except Exception as e:
                            print(f"\n❌ Error performing search: {e}\n")
                    else:
                        print(f"\n{self.theme['error']} Please provide a search query. Example: /search python news\n")
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
                    "math": "Sure! Here is a LaTeX-rendered formula: $E = mc^2$, and a sum: $\\sum_{i=1}^{n} x_i$. Pretty neat, right?",
                    "default": "This is a demo response. For real AI inference, please set MODEL_PATH environment variable and install transformers."
                }
                
                # Simple keyword matching for demo mode
                lower_input = user_input.lower()
                if any(kw in lower_input for kw in ["hello", "hi", "hey"]):
                    response = demo_responses["hello"]
                elif "help" in lower_input:
                    response = demo_responses["help"]
                elif any(kw in lower_input for kw in ["math", "latex", "formula"]):
                    response = demo_responses["math"]
                else:
                    response = demo_responses["default"]
                
                # Show spinner during demo mode thinking time (simulated delay)
                spinner = ThinkingSpinner(
                    prefix=self.theme["prompt_prefix"],
                    prompt_color=self.theme.get("prompt_color", ""),
                    text_color=self.theme.get("text_color", ""),
                    message="Thinking..."
                )
                with spinner:
                    time.sleep(random.uniform(0.3, 0.6))
                
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


def show_backend_selector(ai):
    """Show interactive backend selector menu"""
    print("\n" + "=" * 60)
    print("🔌 SELECT BACKEND ENGINE")
    print("=" * 60)
    print("  1. 🌐 LM Studio (Local API Server - GPU accelerated via Vulkan/DirectML)")
    print("  2. 🐍 PyTorch (Transformers - Local Hugging Face Models)")
    print("\n💡 Select a backend number, or press Enter to auto-detect.")
    
    try:
        choice = input("Enter your choice [1-2]: ").strip()
        if choice == "1":
            lm_url = ai._check_lm_studio()
            ai.force_local = False
            if lm_url:
                ai.is_api = True
                ai.api_url = f"{lm_url}/chat/completions"
                print(f"\n✅ LM Studio Backend active (URL: {ai.api_url})")
                return "api"
            else:
                print("\n⚠️  LM Studio server not detected running on default ports.")
                print("Make sure LM Studio is running and the local server is started!")
                # Default fallback
                ai.is_api = True
                ai.api_url = "http://127.0.0.1:1234/v1/chat/completions"
                print(f"Fallback LM Studio active at default address (URL: {ai.api_url})")
                return "api"
        elif choice == "2":
            ai.is_api = False
            ai.force_local = True
            print("\n✅ PyTorch Local Transformers Backend active")
            return "local"
        else:
            # Auto-detection
            lm_url = ai._check_lm_studio()
            if lm_url:
                ai.is_api = True
                ai.api_url = f"{lm_url}/chat/completions"
                ai.force_local = False
                print(f"\n🔍 Auto-detected running LM Studio server. Using LM Studio API Backend.")
                return "api"
            else:
                ai.is_api = False
                ai.force_local = True
                print(f"\n🔍 No LM Studio server detected. Defaulting to PyTorch Local Backend.")
                return "local"
    except KeyboardInterrupt:
        print("\n\n⚠️  Backend selection cancelled.")
        return None
    except Exception as e:
        print(f"\n❌ Error selecting backend: {e}")
        return None


def main():
    """Main function with optional backend and model selector"""
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
    
    # Check for --skip-selector flag to skip selection menus
    skip_selector = False
    if len(sys.argv) > 2 and sys.argv[2].lower() in ['--skip-selector', '-s']:
        skip_selector = True
    
    # Initialize AI with model path (if provided)
    ai = SimpleSignalAI(model_path=model_path)
    
    # If no model path specified AND not skipping, show backend selector
    if not model_path and not skip_selector:
        backend_choice = show_backend_selector(ai)
        
        # If LM Studio was selected, show the model selector
        if backend_choice == "api":
            selected_model = show_model_selector(ai)
            if selected_model and ai.is_api:
                ai.selected_model = selected_model
                print(f"\n✅ Model '{selected_model}' is now active.\n")
        elif backend_choice == "local":
            print("\n🔍 Loading local PyTorch model resources...")
            ai.load_model()
    else:
        # Load default/autodetected model
        ai.load_model()
        
    cli = CLIInterface(ai)
    cli.run()


if __name__ == "__main__":
    main()
