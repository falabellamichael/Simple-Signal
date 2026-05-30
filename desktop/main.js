const { app, BrowserWindow, dialog, ipcMain, Menu } = require('electron');
const path = require('path');
const { spawn, exec } = require('child_process');
const http = require('http');

let mainWindow = null;
let pyProcess = null;
const PORT = 8000;

// Determine if app is running in packaged production mode
const isPackaged = app.isPackaged;
const backendDir = isPackaged
  ? path.join(process.resourcesPath, 'app-backend')
  : path.join(__dirname, '..');

const serverPath = path.join(backendDir, 'web_server.py');

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
        return venvPath;
      }
    }
  }

  // 2. Fallback to system PATH python
  if (await checkPythonInterpreter('python')) {
    return 'python';
  }

  // 3. Try python3
  if (await checkPythonInterpreter('python3')) {
    return 'python3';
  }

  return null;
}

/**
 * Polls the backend server until it responds on port 8000
 */
function checkServerReady(callback) {
  const req = http.request({
    host: '127.0.0.1',
    port: PORT,
    path: '/api/system/status',
    method: 'GET',
    timeout: 1000
  }, (res) => {
    if (res.statusCode === 200) {
      callback(true);
    } else {
      callback(false);
    }
  });

  req.on('error', () => {
    callback(false);
  });

  req.end();
}

function pollServer(callback, attempts = 0) {
  // Max 40 attempts (20 seconds total)
  if (attempts > 40) {
    callback(false);
    return;
  }
  checkServerReady((ready) => {
    if (ready) {
      callback(true);
    } else {
      setTimeout(() => pollServer(callback, attempts + 1), 500);
    }
  });
}

/**
 * Spawns the background python server process
 */
function spawnServer(pythonCmd) {
  console.log(`[Electron] Spawning python server at: ${serverPath} using interpreter: ${pythonCmd}`);
  
  pyProcess = spawn(pythonCmd, [serverPath], {
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
      preload: path.join(__dirname, 'preload.js')
    }
  });

  // Load backend web URL
  mainWindow.loadURL(`http://127.0.0.1:${PORT}`);

  // Create native menu
  const template = [
    {
      label: 'File',
      submenu: [
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
        { role: 'toggleDevTools' },
        { type: 'separator' },
        { role: 'resetZoom' },
        { role: 'zoomIn' },
        { role: 'zoomOut' },
        { type: 'separator' },
        { role: 'togglefullscreen' },
        { type: 'separator' },
        {
          label: 'Terminal',
          click: () => {
            const { exec } = require('child_process');
            // Try to open PowerShell Core (pwsh) first, fallback to Windows PowerShell
            exec('start pwsh', (err) => {
              if (err) {
                exec('start powershell');
              }
            });
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
    autoHideMenuBar: true,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload_extension.js')
    }
  });

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
        'The backend AI server failed to initialize or bind to port 8000 within 20 seconds.\n\n' +
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
