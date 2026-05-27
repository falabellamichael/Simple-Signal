# Installation Guide

## Prerequisites

### 1. Install Python

Download and install Python 3.8 or higher from:
https://www.python.org/downloads/

During installation, check "Add Python to PATH"

### 2. Verify Python Installation

Open Command Prompt or PowerShell and run:
```bash
python --version
# Should show: Python 3.x.x
```

## Step-by-Step Installation

### Option A: Quick Install (Recommended)

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Test installation:**
   ```bash
   python test_install.py
   ```

3. **Run the CLI:**
   ```bash
   python ai_cli.py
   ```

### Option B: Using PowerShell Launcher

1. Install dependencies first (see above)

2. Run with PowerShell:
   ```powershell
   .\run.ps1
   ```

### Option C: Using Batch File

1. Install dependencies first (see above)

2. Run with Command Prompt:
   ```cmd
   run.bat
   ```

## Environment Variables (Optional)

Create a `.env` file in the project directory:

```bash
# Copy from template
copy .env.example .env

# Edit .env and set your model path
MODEL_PATH="Qwen/Qwen2.5-0.5B-Instruct"
```

Then run:
```bash
set MODEL_PATH="your/model/path"
python ai_cli.py
```

## Troubleshooting

### "python is not recognized"
- Make sure Python is installed and added to PATH
- Restart your terminal after installing Python
- Try using `py` instead of `python`: `py ai_cli.py`

### "No module named 'transformers'"
- Run: `pip install -r requirements.txt`
- Or: `pip install transformers torch accelerate`

### GPU not working
- Install PyTorch with CUDA support:
  ```bash
  pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
  ```

## Quick Commands Reference

```bash
# Install dependencies
pip install -r requirements.txt

# Run in demo mode (no model)
python ai_cli.py

# Run with model
MODEL_PATH="Qwen/Qwen2.5-0.5B-Instruct" python ai_cli.py

# Using PowerShell launcher
.\run.ps1

# Using batch file launcher
run.bat

# Test installation
python test_install.py
```

## Next Steps

After installation:
1. Run `python ai_cli.py` to start the CLI
2. Try chatting with the AI in demo mode
3. (Optional) Download a model and load it for real inference
4. Customize settings in `config.json`

See README.md, QUICKSTART.md, and MODELS.md for more details!
