# Quick Start Guide

## Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

## Step 2: Run in Demo Mode (No Model Required)

```bash
python ai_cli.py
```

Type messages and chat with the AI! Try:
- "Hello!"
- "What can you do?"
- "Tell me a joke"
- "Help me write code"

## Step 3: Load a Real Model (Optional)

### Option A: Using Environment Variable
```bash
MODEL_PATH="Qwen/Qwen2.5-0.5B-Instruct" python ai_cli.py
```

### Option B: Using Command Line Argument
```bash
python ai_cli.py "Qwen/Qwen2.5-0.5B-Instruct"
```

### Option C: Download Model First
1. Visit https://huggingface.co/models
2. Find a small model (e.g., Qwen2.5-0.5B, Phi-3-mini)
3. Download it to your preferred location
4. Run with the path:
   ```bash
   python ai_cli.py "path/to/your/downloaded/model"
   ```

## Step 4: Customize (Optional)

Edit `config.json` to change:
- Theme: `"theme": "cyberpunk"` for retro-futuristic look
- Temperature: Higher = more creative, Lower = more factual
- Max tokens: How long responses can be

## Quick Commands

```bash
# Start demo mode
python ai_cli.py

# Start with model
MODEL_PATH="Qwen/Qwen2.5-0.5B-Instruct" python ai_cli.py

# Change theme to cyberpunk
# Edit config.json and set "theme": "cyberpunk"

# Exit application
Type: quit, exit, or q
```

## First Time Setup

1. Install dependencies: `pip install -r requirements.txt`
2. Run demo mode: `python ai_cli.py`
3. Explore the interface!
4. (Optional) Download a model and load it for real AI inference

Enjoy your local AI assistant! 🚀
