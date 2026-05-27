# 🚀 Start Simple Signal CLI - Easy Commands

## First Time Setup (Run Once)

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Test Installation (Optional)
```bash
python test_install.py
```

---

## Quick Start Commands

### Option 1: Run in Demo Mode (No Model Required)
```bash
python ai_cli.py
```
*Starts the CLI with a demo interface - no AI model needed!*

### Option 2: Run with a Pre-installed Model
```bash
MODEL_PATH="Qwen/Qwen2.5-0.5B-Instruct" python ai_cli.py
```
*Loads a real AI model for actual inference.*

### Option 3: Use the Windows Launcher (Batch File)
```cmd
run.bat
```
*Automatically detects if you have a MODEL_PATH set and starts accordingly.*

### Option 4: Use PowerShell Launcher
```powershell
.\run.ps1
```

---

## Using Environment Variables

### Set Model Path in Command Prompt
```cmd
set MODEL_PATH="Qwen/Qwen2.5-0.5B-Instruct"
python ai_cli.py "%MODEL_PATH%"
```

### Create .env File (Optional)
```bash
copy .env.example .env
notepad .env
```
*Edit `.env` to set your preferred MODEL_PATH permanently.*

---

## Quick Chat Commands (Inside the CLI)

Once running, try these messages:
- `Hello!` - Greet the AI
- `What can you do?` - See capabilities
- `Tell me a joke` - Get entertainment
- `Help me write code` - Get coding assistance
- `quit`, `exit`, or `q` - Exit the application

---

## Troubleshooting

### "python is not recognized"
```bash
# Try using py instead
py ai_cli.py
```

### "No module named 'transformers'"
```bash
pip install -r requirements.txt
```

### GPU Acceleration (Optional)
```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

---

## Summary of All Start Commands

| Command | Description |
|---------|-------------|
| `python ai_cli.py` | Start demo mode (no model) |
| `MODEL_PATH="..." python ai_cli.py` | Start with specific model |
| `run.bat` | Windows batch launcher |
| `.\run.ps1` | PowerShell launcher |

---

**Enjoy your local AI assistant!** 🎉
