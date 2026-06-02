# Simple Signal

Simple Signal is a local AI desktop app and command-line assistant with extension support. The desktop installer ships the base app only, so optional extensions such as PDF RAG can be installed separately.

## Features

- 🎨 Beautiful terminal output with 8 rich themes (dark, light, cyberpunk, matrix, sunset, ocean, forest, dracula) with full ANSI colors
- 💬 Interactive chat mode for continuous conversation
- 📐 **LaTeX Mathematical Formatting** - Automatically converts LaTeX equations into clean, readable Unicode math formatting in your terminal!
- 🚀 Local AI inference with support for various models
- ⚡ Fast and efficient CLI interface
- 🖥️ Desktop installer for Windows
- 📦 Installer bootstrap for Python, pip, PATH, and requirements.txt
- 🧩 Extension-ready base app without bundled third-party extensions
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

### Windows Desktop Installer

Download the latest installer from the GitHub release:

```text
https://github.com/falabellamichael/Simple-Signal/releases/tag/v1.0.5
```

Run:

```text
SimpleSignal.exe
```

The installer is designed to prepare the runtime for a normal Windows user:

- Installs Simple Signal into a `Simple-Signal-Desktop` app folder
- Includes the packaged backend files, including `web_server.py` and `requirements.txt`
- Checks for a supported Python 3 runtime
- Installs Python 3.11 for the current user if Python is missing
- Adds Python and its `Scripts` folder to the user PATH
- Checks for pip
- Runs `ensurepip` if pip is missing
- Falls back to `get-pip.py` if needed
- Installs the packaged `requirements.txt`
- Writes setup details to `simple-signal-bootstrap.log` in the installed app folder

The first install may take a while because the Python packages include large AI dependencies. Internet access is required when Python, pip, or packages need to be downloaded.

### Extensions

Simple Signal supports external extensions, but this base installer does not bundle them. Install optional extensions separately after installing Simple Signal.

For example, the PDF RAG extension has its own installer and should be installed separately from the Simple Signal base app.

### Source / Development Install

Clone or download this repository if you want to edit, rebuild, commit, or publish Simple Signal:

```text
C:\Users\Falab\simple-signal-cli
```

Install Python dependencies manually for development:

```bash
pip install -r requirements.txt
```

Build the Windows desktop installer from the `desktop` folder:

```bash
cd desktop
npm install
npm run dist
```

The built installer is created at:

```text
desktop\dist\SimpleSignal.exe
```

## CLI Usage

The CLI is still available for source/development users and for anyone who wants to run Simple Signal directly from a terminal.

### Start the CLI

```bash
python ai_cli.py
```

When launched without arguments, Simple Signal opens an interactive backend selector:

```text
1. LM Studio local API server
2. llama.cpp local API server
3. PyTorch / Transformers local Hugging Face model
```

If you press Enter, it auto-detects available backends in this order:

```text
LM Studio on localhost or 127.0.0.1, port 1234
llama.cpp on localhost or 127.0.0.1, port 8080
PyTorch / Transformers local model fallback
```

### LM Studio Mode

Start LM Studio, load a model, and start the local server. Then run:

```bash
python ai_cli.py
```

Simple Signal checks:

```text
http://localhost:1234/v1
http://127.0.0.1:1234/v1
```

If LM Studio is running, the CLI lists available models and lets you choose one interactively.

### llama.cpp Mode

Start a llama.cpp-compatible OpenAI API server on port `8080`, then run:

```bash
python ai_cli.py
```

Simple Signal checks:

```text
http://localhost:8080/v1
http://127.0.0.1:8080/v1
```

### Local PyTorch / Transformers Mode

Use this mode when you want to load a Hugging Face model directly through Python:

```bash
python ai_cli.py "path/to/your/model"
```

Or set `MODEL_PATH` first:

```bash
MODEL_PATH="path/to/your/model" python ai_cli.py
```

On Windows PowerShell:

```powershell
$env:MODEL_PATH="C:\path\to\your\model"
python ai_cli.py
```

### Skip Interactive Selectors

Use `--skip-selector` or `-s` when you do not want the backend/model prompts:

```bash
python ai_cli.py --skip-selector
python ai_cli.py "path/to/your/model" --skip-selector
python ai_cli.py "path/to/your/model" -s
```

### Demo Mode

If no model or API backend is available, the CLI falls back to demo mode. Demo mode lets you try the terminal UI, themes, and built-in commands without loading a real model.

### CLI Commands

- Type any message to chat with the AI
- `/theme` - Open the interactive theme selector
- `/theme <name>` - Switch directly to a theme, such as `/theme matrix`
- `/search <query>` - Search DuckDuckGo and show formatted results inline
- `/sudoku` - Start an interactive 9x9 Sudoku game
- `help` - Show available commands in demo mode
- `quit`, `exit`, or `q` - Exit the CLI

### Environment Variables

Simple Signal reads environment variables from your shell and from a local `.env` file when present.

Useful variables:

```text
MODEL_PATH=path/to/local/model
LM_API_TOKEN=your-lm-studio-token
SIGNAL_SHARE_LM_STUDIO_API_TOKEN=your-lm-studio-token
```

`LM_API_TOKEN` and `SIGNAL_SHARE_LM_STUDIO_API_TOKEN` are used for local OpenAI-compatible servers that require a bearer token.

### Configuration

Edit `config.json` to customize:

- Model settings: temperature, max_length, top_p, repetition_penalty
- Chat settings: system prompt and max tokens
- Output settings: saved terminal theme and verbosity

Supported terminal themes include:

```text
dark
light
cyberpunk
matrix
sunset
ocean
forest
dracula
```

### Authentication With LM Studio

If your local LM Studio server requires authentication:

1. Copy `.env.example` to `.env`.
2. Set your token:

```text
LM_API_TOKEN=your-token-here
```

The CLI also checks `SIGNAL_SHARE_LM_STUDIO_API_TOKEN` for compatibility with related local workspaces.

## Supported Models

This CLI supports any Hugging Face model compatible with transformers library. Popular choices:

- `Qwen/Qwen2.5-7B-Instruct`
- `microsoft/Phi-3-mini-4k-instruct`
- `meta-llama/Llama-2-7b-chat-hf`
- Any other causal LM from Hugging Face

## Requirements

For the desktop installer:

- Windows
- Internet access for first-time Python/pip/package setup when missing
- Optional local model server such as LM Studio

For source/development use:

- Python 3.8+
- Node.js/npm for rebuilding the desktop app
- Transformers library
- PyTorch
- Optional CUDA for GPU acceleration

## Demo Mode

If no model is loaded, the CLI runs in demo mode with predefined responses. This allows you to explore the interface before setting up a real model.

## Tips

- Use a smaller model for faster inference on limited hardware
- Adjust temperature in config.json for more creative (higher) or factual (lower) responses
- The cyberpunk theme provides a retro-futuristic aesthetic

## License

MIT License - Feel free to modify and distribute.
