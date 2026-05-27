# Model Download Guide

## Recommended Models for Local AI

### Small & Fast (Good for beginners)
- **Qwen2.5-0.5B-Instruct** - Very small, fast, good for basic tasks
  ```bash
  MODEL_PATH="Qwen/Qwen2.5-0.5B-Instruct" python ai_cli.py
  ```

- **Phi-3-mini-4k-instruct** - Microsoft's small but powerful model
  ```bash
  MODEL_PATH="microsoft/Phi-3-mini-4k-instruct" python ai_cli.py
  ```

### Medium (Good balance)
- **Qwen2.5-1.5B-Instruct** - Better quality, still fast
  ```bash
  MODEL_PATH="Qwen/Qwen2.5-1.5B-Instruct" python ai_cli.py
  ```

- **Phi-3-small-8k-instruct** - More capable than mini
  ```bash
  MODEL_PATH="microsoft/Phi-3-small-8k-instruct" python ai_cli.py
  ```

### Large (Best quality, needs more resources)
- **Qwen2.5-7B-Instruct** - Excellent quality, ~16GB VRAM recommended
  ```bash
  MODEL_PATH="Qwen/Qwen2.5-7B-Instruct" python ai_cli.py
  ```

- **Llama-3.2-3B-Instruct** - Meta's Llama model
  ```bash
  MODEL_PATH="meta-llama/Llama-3.2-3B-Instruct" python ai_cli.py
  ```

## How to Download Models

### Option 1: Using Hugging Face CLI (Recommended)
```bash
pip install huggingface_hub
huggingface-cli download Qwen/Qwen2.5-0.5B-Instruct --local-dir ./models/qwen-0.5b
python ai_cli.py "./models/qwen-0.5b"
```

### Option 2: Using Git Clone
```bash
git clone https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct ./models/qwen-0.5b
python ai_cli.py "./models/qwen-0.5b"
```

### Option 3: Download from Hugging Face Website
1. Go to https://huggingface.co/models
2. Search for a model (e.g., "Qwen2.5-0.5B-Instruct")
3. Click "Files and Versions" tab
4. Download the `config.json`, `model.safetensors`, and `tokenizer` files
5. Place them in your preferred directory
6. Run with the path to that directory

## Model Requirements

| Model | VRAM Required | RAM Required | Speed | Quality |
|-------|--------------|--------------|-------|---------|
| 0.5B  | ~1GB         | ~2GB         | Very Fast | Basic   |
| 1.5B  | ~3GB         | ~4GB         | Fast   | Good    |
| 3B    | ~6GB         | ~8GB         | Fast   | Very Good |
| 7B    | ~14GB        | ~16GB        | Medium | Excellent |

## Tips

- Use smaller models for faster response times
- Adjust temperature in config.json for different response styles
- The CLI works with any Hugging Face model that supports causal language modeling
- For best performance, use GPU if available (set `device_map="auto"` automatically handles this)

## Alternative: Using Ollama

If you prefer Ollama, you can run models directly:
```bash
# Install Ollama first from https://ollama.ai
ollama pull qwen2.5:0.5b
ollama run qwen2.5:0.5b "Your question here"
```

## Troubleshooting

- **Out of memory**: Use a smaller model or close other applications
- **Slow loading**: Models take time to load on first run (cached afterwards)
- **GPU not detected**: Ensure CUDA is installed and PyTorch supports your GPU

## 🎯 New Model Selector Feature

Starting from this update, you can now select a model interactively when launching the CLI!

### How It Works

When you run `python ai_cli.py` without specifying a model path, the application will:

1. **Auto-detect LM Studio** - If LM Studio is running locally, it will automatically connect to it
2. **Show Available Models** - Display all available models with their sizes and status
3. **Interactive Selection** - Choose from a numbered list of models using your keyboard

### Usage Examples

#### Automatic Model Selection (Recommended)
```bash
python ai_cli.py
# Will show model selector if LM Studio is running
# Or prompt for MODEL_PATH if no API detected
```

#### Skip Model Selector
If you want to skip the interactive selector and use a specific model:
```bash
# Using environment variable
MODEL_PATH="Qwen/Qwen2.5-0.5B-Instruct" python ai_cli.py --skip-selector

# Or using command line argument
python ai_cli.py "path/to/model" --skip-selector
```

#### With LM Studio API
If you have LM Studio running, just run:
```bash
python ai_cli.py
# Automatically connects to LM Studio and shows model selector
```

### Benefits

- ✅ No need to remember model paths
- ✅ See all available models at a glance
- ✅ Easy switching between different models
- ✅ Works seamlessly with LM Studio's GPU acceleration
- ✅ Shows model sizes and status (running/downloading)

### Model Selector Display

When the selector appears, you'll see:
```
📦 MODEL SELECTOR
============================================================

🌐 Connected to LM Studio at: http://localhost:1234/v1

📋 Available Models (3 found):

  1. ✅ Qwen/Qwen2.5-0.5B-Instruct
     Size: 0.3 GB
  2. ✅ Qwen/Qwen2.5-1.5B-Instruct
     Size: 1.2 GB
  3. ✅ Qwen/Qwen2.5-7B-Instruct
     Size: 9.8 GB

💡 Select a model number to load, or press Enter to use default.
Enter your choice [1-3]: 
```

### Tips

- **LM Studio must be running** - Start LM Studio before launching the CLI for automatic detection
- **Models show as "running"** - Only models that are currently loaded will show with a ✅ icon
- **Downloaded but not running** - Models that are downloaded but not active will show with 🔄
- **Press Enter** - If you press Enter without selecting, it uses the default configuration
