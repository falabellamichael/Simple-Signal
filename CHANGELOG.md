## [1.0.3] - 2026-05-30
- 🧩 **Extension Apps SDK** - Simple Signal now acts as a host platform for external extensions, injecting a `window.SimpleSignal` SDK for direct access to AI chat, hardware telemetry, and web search.
- 📦 **External Installer Support** - Simplified setup allowing external `setup.exe` applications to register natively into Simple Signal via the `extensions/` directory.
- 🪟 **Isolated Window Management** - Extensions launch in secure, independent Electron windows with their own custom UI while seamlessly sharing Simple Signal
'
s backend engine.

# Changelog

All notable changes to this project will be documented in this file.

## [1.0.0] - 2026-05-28

This is the first official release of the **Simple Signal CLI & Web Interface**.

### Core AI & CLI Features
- ðŸŽ¨ **Beautiful ANSI Themes** - 8 premium terminal themes (dark, light, cyberpunk, matrix, sunset, ocean, forest, dracula) with on-the-fly switching via `/theme` commands.
- ðŸ’¬ **Interactive Terminal Chat** - Continuous AI conversation mode with prompt memory.
- ðŸ“ **LaTeX Math Rendering** - Automatic inline and block math equation formatting into clean Unicode characters.
- ðŸŒ **Web Search Integration** - Query DuckDuckGo directly with `/search <query>` inside the chat interface.
- ðŸŽ® **Interactive Sudoku** - Fully playable terminal Sudoku mini-game with curses rendering and text fallback.

### Web Interface & System Telemetry
- ðŸš€ **FastAPI Web Server** - High-performance backend routing local AI inference to a modern web client terminal.
- ðŸ“Š **Collapsible Neon System Monitor** - Right sidebar charts displaying real-time CPU, Memory, Disk, and GPU stats with a customizable polling rate and a "Disable System Monitor" switch.
- âš¡ **High-Performance Telemetry Wrapper** - Custom Windows `ctypes` wrapper for the native Performance Data Helper (`pdh.dll`) API, retrieving real-time GPU engine utilization in under 10ms with zero subprocess spawning overhead.
- ðŸ”Œ **Multiple Local API Backends** - Integrated support for LM Studio (port 1234) and llama.cpp (port 8080) with automatic model list retrieval, plus local PyTorch fallback loading.
## [1.0.4] - 2026-06-01
- Keep Simple Signal as a clean base installer with no bundled extensions.
- Preserve the extension platform while loading packaged-app extensions from the user-writable `%LOCALAPPDATA%\SimpleSignal\extensions` folder.
- Add a generated extension uninstaller helper for removing user-installed extensions without touching the base app.
- Keep installer/build artifacts out of the Git repository and publish the installer through GitHub Releases.
