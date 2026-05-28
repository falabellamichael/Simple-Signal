# Changelog

All notable changes to this project will be documented in this file.

## [1.0.0] - 2026-05-28

This is the first official release of the **Simple Signal CLI & Web Interface**.

### Core AI & CLI Features
- 🎨 **Beautiful ANSI Themes** - 8 premium terminal themes (dark, light, cyberpunk, matrix, sunset, ocean, forest, dracula) with on-the-fly switching via `/theme` commands.
- 💬 **Interactive Terminal Chat** - Continuous AI conversation mode with prompt memory.
- 📐 **LaTeX Math Rendering** - Automatic inline and block math equation formatting into clean Unicode characters.
- 🌐 **Web Search Integration** - Query DuckDuckGo directly with `/search <query>` inside the chat interface.
- 🎮 **Interactive Sudoku** - Fully playable terminal Sudoku mini-game with curses rendering and text fallback.

### Web Interface & System Telemetry
- 🚀 **FastAPI Web Server** - High-performance backend routing local AI inference to a modern web client terminal.
- 📊 **Collapsible Neon System Monitor** - Right sidebar charts displaying real-time CPU, Memory, Disk, and GPU stats with a customizable polling rate and a "Disable System Monitor" switch.
- ⚡ **High-Performance Telemetry Wrapper** - Custom Windows `ctypes` wrapper for the native Performance Data Helper (`pdh.dll`) API, retrieving real-time GPU engine utilization in under 10ms with zero subprocess spawning overhead.
- 🔌 **Multiple Local API Backends** - Integrated support for LM Studio (port 1234) and llama.cpp (port 8080) with automatic model list retrieval, plus local PyTorch fallback loading.
