# Simple Signal CLI - Local AI Command Line Interface

A stylish, terminal-based AI inference tool that provides a command prompt-style local AI assistant.

## Features

- 🎨 Beautiful terminal output with multiple themes (dark, light, cyberpunk)
- 💬 Interactive chat mode for continuous conversation
- 🚀 Local AI inference with support for various models
- ⚡ Fast and efficient CLI interface
- 📦 Easy setup with requirements.txt

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
- `quit`, `exit`, or `q` - Exit the application
- `help` - Show available commands (demo mode)

## Configuration

Edit `config.json` to customize:

- **Model settings**: temperature, max_length, top_p
- **Chat settings**: system prompt, max tokens
- **Output theme**: dark, light, cyberpunk

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
