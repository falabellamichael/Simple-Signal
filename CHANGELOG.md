# Changelog

## [1.0.0] - Initial Release

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
