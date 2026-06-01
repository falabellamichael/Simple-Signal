$ErrorActionPreference = "Stop"

python -m PyInstaller `
  --clean `
  --noconfirm `
  --onefile `
  --windowed `
  --name SimpleSignalUninstaller `
  --distpath tools `
  --workpath build-uninstaller `
  simple_signal_uninstaller.py
