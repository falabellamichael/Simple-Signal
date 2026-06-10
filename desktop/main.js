const { app, BrowserWindow, dialog, ipcMain, Menu } = require('electron');
const path = require('path');
const { spawn, exec } = require('child_process');
const http = require('http');
const fs = require('fs');

let mainWindow = null;
let pyProcess = null;
const PORT = 8000;
const STARTUP_TIMEOUT_MS = 90000;
const SERVER_POLL_INTERVAL_MS = 500;
const SERVER_REQUEST_TIMEOUT_MS = 1000;

function getActiveWindow(fallbackWindow = mainWindow) {
  return BrowserWindow.getFocusedWindow() || fallbackWindow;
}

function toggleDeveloperTools(targetWindow = getActiveWindow()) {
  if (!targetWindow || targetWindow.isDestroyed()) return;
  targetWindow.webContents.toggleDevTools();
}

function attachDeveloperToolsShortcuts(targetWindow) {
  if (!targetWindow) return;

  targetWindow.webContents.on('before-input-event', (event, input) => {
    const isDevToolsShortcut =
      input.type === 'keyDown' &&
      (input.key === 'F12' || (input.control && input.shift && input.key.toLowerCase() === 'i'));

    if (isDevToolsShortcut) {
      toggleDeveloperTools(targetWindow);
      event.preventDefault();
    }
  });
}

function createDeveloperToolsMenuItem(targetWindow) {
  return {
    label: 'Developer Tools',
    accelerator: 'F12',
    click: () => toggleDeveloperTools(getActiveWindow(targetWindow))
  };
}

function openTerminal() {
  exec('start pwsh', (err) => {
    if (err) {
      exec('start powershell');
    }
  });
}

function runMainWindowScript(script) {
  if (!mainWindow || mainWindow.isDestroyed()) return;
  mainWindow.webContents.executeJavaScript(script).catch(() => {});
}

// Determine if app is running in packaged production mode
const isPackaged = app.isPackaged;
const backendDir = isPackaged
  ? path.join(process.resourcesPath, 'app-backend')
  : path.join(__dirname, '..');

const serverPath = path.join(backendDir, 'web_server.py');

function getUninstallerPath() {
  const packagedDir = path.dirname(app.getPath('exe'));
  const candidates = [
    path.join(packagedDir, 'SimpleSignalUninstaller.exe'),
    path.join(__dirname, 'tools', 'SimpleSignalUninstaller.exe'),
    path.join(__dirname, 'dist', 'win-unpacked', 'SimpleSignalUninstaller.exe')
  ];

  return candidates.find((candidate) => fs.existsSync(candidate)) || null;
}

function openSimpleSignalUninstaller() {
  const uninstallerPath = getUninstallerPath();
  if (!uninstallerPath) {
    dialog.showErrorBox(
      'Uninstaller Not Found',
      'Simple Signal could not find SimpleSignalUninstaller.exe.\n\n' +
      'Rebuild or reinstall Simple Signal, then try again.'
    );
    return;
  }

  const child = spawn(uninstallerPath, [], {
    detached: true,
    stdio: 'ignore',
    cwd: path.dirname(uninstallerPath)
  });
  child.unref();
}

/**
 * Checks if a specific command or interpreter path exists and can run
 */
function checkPythonInterpreter(cmd, args = ['--version']) {
  return new Promise((resolve) => {
    try {
      const proc = spawn(cmd, args);
      proc.on('error', () => resolve(false));
      proc.on('close', (code) => resolve(code === 0));
    } catch {
      resolve(false);
    }
  });
}

/**
 * Resolves the best available Python interpreter to use
 */
async function getPythonCommand() {
  // 1. Look for virtualenv interpreters relative to backend root
  const venvPaths = process.platform === 'win32'
    ? [
        path.join(backendDir, 'venv', 'Scripts', 'python.exe'),
        path.join(backendDir, '.venv', 'Scripts', 'python.exe')
      ]
    : [
        path.join(backendDir, 'venv', 'bin', 'python'),
        path.join(backendDir, '.venv', 'bin', 'python')
      ];

  for (const venvPath of venvPaths) {
    if (require('fs').existsSync(venvPath)) {
      if (await checkPythonInterpreter(venvPath)) {
        return { command: venvPath, args: [] };
      }
    }
  }

  const localAppData = process.env.LOCALAPPDATA;
  if (process.platform === 'win32' && localAppData) {
    const localPythonPaths = [
      path.join(localAppData, 'Programs', 'Python', 'Python311', 'python.exe'),
      path.join(localAppData, 'Programs', 'Python', 'Python312', 'python.exe'),
      path.join(localAppData, 'Programs', 'Python', 'Python310', 'python.exe')
    ];

    for (const pythonPath of localPythonPaths) {
      if (fs.existsSync(pythonPath) && await checkPythonInterpreter(pythonPath)) {
        return { command: pythonPath, args: [] };
      }
    }
  }

  // 2. Fallback to system PATH python
  if (await checkPythonInterpreter('python')) {
    return { command: 'python', args: [] };
  }

  // 3. Try python3
  if (await checkPythonInterpreter('python3')) {
    return { command: 'python3', args: [] };
  }

  // 4. Try the Windows Python launcher even if PATH has not refreshed yet
  if (process.platform === 'win32' && await checkPythonInterpreter('py', ['-3', '--version'])) {
    return { command: 'py', args: ['-3'] };
  }

  return null;
}

/**
 * Polls the backend server until it responds on port 8000
 */
function checkServerReady(callback) {
  let completed = false;
  const finish = (ready) => {
    if (completed) return;
    completed = true;
    callback(ready);
  };

  const req = http.request({
    host: '127.0.0.1',
    port: PORT,
    path: '/api/system/status',
    method: 'GET',
    timeout: SERVER_REQUEST_TIMEOUT_MS
  }, (res) => {
    res.resume();
    finish(res.statusCode === 200);
  });

  req.on('error', () => {
    finish(false);
  });

  req.on('timeout', () => {
    req.destroy();
    finish(false);
  });

  req.end();
}

function pollServer(callback, startedAt = Date.now()) {
  if (Date.now() - startedAt >= STARTUP_TIMEOUT_MS) {
    callback(false);
    return;
  }

  checkServerReady((ready) => {
    if (ready) {
      callback(true);
    } else {
      setTimeout(() => pollServer(callback, startedAt), SERVER_POLL_INTERVAL_MS);
    }
  });
}

/**
 * Spawns the background python server process
 */
function spawnServer(pythonRuntime) {
  const pythonArgs = [...pythonRuntime.args, serverPath];
  const commandLine = [pythonRuntime.command, ...pythonRuntime.args].join(' ');
  console.log(`[Electron] Spawning python server at: ${serverPath} using interpreter: ${commandLine}`);
  
  pyProcess = spawn(pythonRuntime.command, pythonArgs, {
    cwd: backendDir,
    env: { ...process.env, PYTHONUNBUFFERED: '1' }
  });

  pyProcess.stdout.on('data', (data) => {
    console.log(`[Python Server] ${data.toString().trim()}`);
  });

  pyProcess.stderr.on('data', (data) => {
    console.error(`[Python Server Error] ${data.toString().trim()}`);
  });

  pyProcess.on('close', (code) => {
    console.log(`[Electron] Python server process exited with code ${code}`);
    pyProcess = null;
  });
}

/**
 * Kills the spawned python process tree cleanly
 */
function killServerProcess(callback) {
  if (!pyProcess) {
    if (callback) callback();
    return;
  }

  const pid = pyProcess.pid;
  console.log(`[Electron] Terminating python process tree with PID: ${pid}`);

  if (process.platform === 'win32') {
    // Windows taskkill terminates the entire child process group (/t) forcibly (/f)
    exec(`taskkill /pid ${pid} /t /f`, (err) => {
      if (err) {
        console.error(`[Electron] Failed to kill python process tree: ${err.message}`);
      }
      pyProcess = null;
      if (callback) callback();
    });
  } else {
    // Unix process group killing
    try {
      process.kill(-pid, 'SIGINT');
    } catch {
      try {
        pyProcess.kill('SIGKILL');
      } catch {}
    }
    pyProcess = null;
    if (callback) callback();
  }
}

/**
 * Creates the primary application window loading the local server
 */
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 850,
    minWidth: 1000,
    minHeight: 700,
    title: 'Simple Signal AI Console',
    backgroundColor: '#0a0b10', // Cyberpunk neon dark background color
    icon: path.join(__dirname, 'icon.png'), // Will fallback gracefully if missing
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      devTools: true,
      preload: path.join(__dirname, 'preload.js')
    }
  });

  attachDeveloperToolsShortcuts(mainWindow);

  // Load backend web URL
  mainWindow.loadURL(`http://127.0.0.1:${PORT}`);

  // Create native menu
  const template = [
    {
      label: 'File',
      submenu: [
        {
          label: 'New Chat',
          accelerator: 'CommandOrControl+N',
          click: () => runMainWindowScript(`
            if (typeof handleNewChat === "function") {
              handleNewChat();
            } else {
              document.getElementById("new-chat-btn")?.click();
            }
          `)
        },
        {
          label: 'Clear Terminal',
          accelerator: 'CommandOrControl+Shift+L',
          click: () => runMainWindowScript(`
            if (typeof clearTerminal === "function") {
              clearTerminal();
            }
          `)
        },
        { type: 'separator' },
        {
          label: 'Manage Extensions...',
          accelerator: 'CommandOrControl+Shift+E',
          click: () => {
            if (mainWindow) {
              mainWindow.webContents.send('open-extensions-modal');
            }
          }
        },
        {
          label: 'Token Authentication...',
          click: () => {
            if (mainWindow) {
              mainWindow.webContents.send('open-token-modal');
            }
          }
        },
        {
          label: 'Open Terminal',
          click: openTerminal
        },
        { type: 'separator' },
        {
          label: 'Uninstall Simple Signal / Extensions...',
          click: openSimpleSignalUninstaller
        },
        { type: 'separator' },
        { role: 'quit' }
      ]
    },
    {
      label: 'Edit',
      submenu: [
        { role: 'undo' },
        { role: 'redo' },
        { type: 'separator' },
        { role: 'cut' },
        { role: 'copy' },
        { role: 'paste' },
        { role: 'delete' },
        { type: 'separator' },
        { role: 'selectAll' }
      ]
    },
    {
      label: 'View',
      submenu: [
        { role: 'reload' },
        { role: 'forceReload' },
        createDeveloperToolsMenuItem(mainWindow),
        {
          label: 'Developer Tools (Ctrl+Shift+I)',
          accelerator: 'CommandOrControl+Shift+I',
          click: () => toggleDeveloperTools(getActiveWindow(mainWindow))
        },
        { type: 'separator' },
        { role: 'resetZoom' },
        { role: 'zoomIn' },
        { role: 'zoomOut' },
        { type: 'separator' },
        { role: 'togglefullscreen' },
        { type: 'separator' },
        {
          label: 'Terminal',
          click: openTerminal
        },
        {
          label: 'Token Authentication',
          click: () => {
            if (mainWindow) {
              mainWindow.webContents.send('open-token-modal');
            }
          }
        }
      ]
    },
    {
      label: 'Window',
      submenu: [
        { role: 'minimize' },
        { role: 'zoom' },
        { role: 'close' }
      ]
    },
    {
      label: 'Extensions',
      submenu: [
        {
          label: 'Manage Extensions...',
          click: () => {
            if (mainWindow) {
              mainWindow.webContents.send('open-extensions-modal');
            }
          }
        },
        {
          label: 'Uninstall Extensions...',
          click: openSimpleSignalUninstaller
        }
      ]
    },
    {
      role: 'help',
      submenu: [
        {
          label: 'Learn More',
          click: async () => {
            const { shell } = require('electron')
            await shell.openExternal('https://github.com/falabellamichael/Simple-Signal')
          }
        }
      ]
    }
  ];

  const menu = Menu.buildFromTemplate(template);
  Menu.setApplicationMenu(menu);

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

ipcMain.on('window-control', (event, action) => {
  if (!mainWindow) return;
  if (action === 'close') mainWindow.close();
  if (action === 'minimize') mainWindow.minimize();
  if (action === 'maximize') {
    if (mainWindow.isMaximized()) {
      mainWindow.unmaximize();
    } else {
      mainWindow.maximize();
    }
  }
});

// IPC Handler to open extensions in new windows
ipcMain.on('open-extension', (event, { url, title, width, height }) => {
  const extWindow = new BrowserWindow({
    width: width || 1024,
    height: height || 768,
    title: title || 'Extension',
    backgroundColor: '#0a0b10', // Consistent dark background
    autoHideMenuBar: false,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      devTools: true,
      preload: path.join(__dirname, 'preload_extension.js')
    }
  });

  attachDeveloperToolsShortcuts(extWindow);

  extWindow.loadURL(url);
});

// Electron lifecycle event handlers
app.on('ready', async () => {
  const pythonCmd = await getPythonCommand();
  
  if (!pythonCmd) {
    dialog.showErrorBox(
      'Python Interpreter Not Found',
      'Simple Signal Desktop requires Python 3 to run the local AI backend server.\n\n' +
      '1. Please install Python 3.8+ on your system.\n' +
      '2. Ensure you check "Add Python to PATH" during installation.\n' +
      '3. Run "pip install -r requirements.txt" to install dependencies.\n\n' +
      'The application will now exit.'
    );
    app.quit();
    return;
  }

  // Start server
  spawnServer(pythonCmd);

  // Wait for server to bind
  pollServer((success) => {
    if (success) {
      createWindow();
    } else {
      dialog.showErrorBox(
        'Backend Startup Timeout',
        'The backend AI server failed to initialize or bind to port 8000 within 90 seconds.\n\n' +
        'Please verify that port 8000 is not already in use by another application, and try restarting.'
      );
      killServerProcess(() => app.quit());
    }
  });
});

app.on('window-all-closed', () => {
  killServerProcess(() => {
    app.quit();
  });
});

app.on('will-quit', () => {
  killServerProcess();
});
