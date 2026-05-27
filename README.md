# Simple Signal CLI - Local AI Command Line Interface

A stylish, terminal-based AI inference tool that provides a command prompt-style local AI assistant.

## Features

- 🎨 Beautiful terminal output with 8 rich themes (dark, light, cyberpunk, matrix, sunset, ocean, forest, dracula) with full ANSI colors
- 💬 Interactive chat mode for continuous conversation
- 📐 **LaTeX Mathematical Formatting** - Automatically converts LaTeX equations into clean, readable Unicode math formatting in your terminal!
- 🚀 Local AI inference with support for various models
- ⚡ Fast and efficient CLI interface
- 📦 Easy setup with requirements.txt
- 🎯 **Interactive Model Selector** - Choose from available models when starting!

## New: Automatic Model Selection

Starting from this update, you can now select a model interactively when launching the CLI! Simply run:

```bash
python ai_cli.py
```

If LM Studio is running locally, it will automatically detect it and show you a list of available models to choose from. No need to remember model paths or set environment variables!

### How It Works

1. **Auto-detects LM Studio** - Automatically connects to your local LM Studio instance
2. **Shows Available Models** - Displays all models with their sizes and status
3. **Interactive Selection** - Choose from a numbered list using your keyboard
4. **GPU Acceleration** - Seamlessly uses LM Studio's GPU acceleration

### Usage Examples

#### Automatic Model Selection (Recommended)
```bash
python ai_cli.py
# Shows model selector if LM Studio is running
# Or prompts for MODEL_PATH if no API detected
```

#### Skip Model Selector
If you want to skip the interactive selector:
```bash
python ai_cli.py --skip-selector
# or
MODEL_PATH="path/to/model" python ai_cli.py --skip-selector
```

#### With Specific Model Path
```bash
python ai_cli.py "path/to/your/model" --skip-selector
```

## Installation

1. Clone or download this repository to your desired location:
   ```
   C:\Users\Falab\simple-signal-cli
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. (Optional) Download a model and set the MODEL_PATH environment variable, or pass it as an argument.

## Usage

### Basic Run (Demo Mode)
```bash
python ai_cli.py
```

### With Model Path
```bash
MODEL_PATH="path/to/your/model" python ai_cli.py
# Or:
python ai_cli.py "path/to/your/model"
```

### Interactive Chat
```bash
python ai_cli.py
# Then type your messages and press Enter
```

## Available Commands
 
 - Type any message to chat with the AI
 - `/theme` - Open the interactive theme selector to switch themes
 - `/theme <name>` - Directly switch to a specific theme (e.g., `/theme matrix`)
 - `/search <query>` - Perform a web search on DuckDuckGo and view formatted results inline
 - `/sudoku` - Play an interactive Sudoku game in the terminal (with `curses` and text fallbacks!)
 - `quit`, `exit`, or `q` - Exit the application
 - `help` - Show available commands (demo mode)
 
 ## Configuration
 
 Edit `config.json` to customize:
 
 - **Model settings**: temperature, max_length, top_p
 - **Chat settings**: system prompt, max tokens
 - **Output theme**: dark, light, cyberpunk, matrix, sunset, ocean, forest, dracula (saved persistently when changed!)
 
 ## Authentication (LM Studio Token)
 
 If your local LM Studio server requires authentication:
 
 1. Copy `.env.example` to `.env`:
    ```bash
    cp .env.example .env
    ```
 2. Set your token in the `.env` file:
    ```
    LM_API_TOKEN=your-token-here
    ```
 
 *Note: The CLI also automatically scans your workspace and detects tokens defined as `SIGNAL_SHARE_LM_STUDIO_API_TOKEN` in the parent projects for a seamless experience.*

## Supported Models

This CLI supports any Hugging Face model compatible with transformers library. Popular choices:

- `Qwen/Qwen2.5-7B-Instruct`
- `microsoft/Phi-3-mini-4k-instruct`
- `meta-llama/Llama-2-7b-chat-hf`
- Any other causal LM from Hugging Face

## Requirements

- Python 3.8+
- Transformers library
- PyTorch
- (Optional) CUDA for GPU acceleration

## Demo Mode

If no model is loaded, the CLI runs in demo mode with predefined responses. This allows you to explore the interface before setting up a real model.

## Tips

- Use a smaller model for faster inference on limited hardware
- Adjust temperature in config.json for more creative (higher) or factual (lower) responses
- The cyberpunk theme provides a retro-futuristic aesthetic

## License

MIT License - Feel free to modify and distribute.
