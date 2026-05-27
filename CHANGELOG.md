# Changelog

## [1.2.0] - Theme Selector & Authentication Updates

### New Features
- 🎨 **Interactive Theme Chooser** - Change terminal appearance on-the-fly!
  - Type `/theme` during chat to open a visual menu of all available styles.
  - Support direct command switching using `/theme <name>`.
  - Configurations are saved persistently back to `config.json` automatically.
- 🌈 **5 New Premium Color Themes** - Matrix, Sunset, Ocean, Forest, and Dracula.
  - Added support for rich ANSI foreground colors, distinct visual double/wave line separators, and custom theme emojis.
- 🌐 **LM Studio Bearer Token Authentication** - Seamless integration with secure local servers.
  - Support for `LM_API_TOKEN` and `SIGNAL_SHARE_LM_STUDIO_API_TOKEN` in `.env` config.
  - Automatic loopback checking over both `localhost` and `127.0.0.1`.

### Improvements
- 🎨 **Theme Aesthetics Refinement**:
  - Upgraded all 8 themes using 256-color ANSI codes to match their names.
  - Polished the `ocean` theme to use pure, rich deep-blue shades (`\033[38;5;33m`, `\033[38;5;75m`) rather than green/cyan.
  - Adjusted the `light` theme to use bright silver/white colors (`\033[38;5;255m`, `\033[1;38;5;231m`) so that it is not dark on dark terminals.
  - Polished the `forest` theme to use earthy greens (`\033[38;5;107m`, `\033[38;5;34m`) and cedar/wood brown (`\033[38;5;94m`).

## [1.1.0] - Model Selector Update

### New Features
- 🎯 **Interactive Model Selector** - Choose from available models when starting the CLI!
  - Automatically detects LM Studio and shows all available models
  - Interactive numbered menu to select models easily
  - Shows model sizes, status (running/downloading), and details
  - Works seamlessly with GPU acceleration via LM Studio

### Improvements
- **Automatic Model Detection** - No need to specify MODEL_PATH when using LM Studio
- **Skip Selector Option** - Use `--skip-selector` flag to skip the interactive menu
- **Better UX** - Models are displayed with icons showing their status (✅ running, 🔄 downloaded)

### Usage Examples
```bash
# Automatic model selection (recommended)
python ai_cli.py

# Skip model selector
python ai_cli.py --skip-selector

# With specific model path
MODEL_PATH="Qwen/Qwen2.5-0.5B-Instruct" python ai_cli.py --skip-selector
```

## [1.0.0] - Initial Release

### Features

### Features
- 🎨 Beautiful terminal output with 3 themes (dark, light, cyberpunk)
- 💬 Interactive chat mode for continuous conversation
- 🚀 Local AI inference support via Hugging Face transformers
- ⚡ Demo mode for exploring the interface without a model
- 📦 Easy setup with requirements.txt and batch/PowerShell launchers

### Installation
- Install dependencies with `pip install -r requirements.txt`
- Run in demo mode: `python ai_cli.py`
- Run with model: `MODEL_PATH="path/to/model" python ai_cli.py`

### Configuration
- Edit `config.json` to customize model settings, chat prompts, and theme
- Use `.env.example` as template for environment variables

### Documentation
- README.md - Full documentation
- QUICKSTART.md - Quick start guide
- MODELS.md - Model download recommendations
- .gitignore - Git ignore rules

### Files Included
- `ai_cli.py` - Main CLI application
- `config.json` - Default configuration
- `requirements.txt` - Python dependencies
- `run.bat` - Windows batch launcher
- `run.ps1` - PowerShell launcher
- `test_install.py` - Installation test script
- `.env.example` - Environment variables template

### Planned Features
- [ ] Model fine-tuning support
- [ ] Multi-modal input (images, audio)
- [ ] Plugin system for custom models
- [ ] Web interface integration
- [ ] Voice input/output support
