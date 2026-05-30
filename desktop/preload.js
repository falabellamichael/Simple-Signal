const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
    windowControl: (action) => ipcRenderer.send('window-control', action)
});

// Inject electron-mode class into the body once the DOM is ready
window.addEventListener('DOMContentLoaded', () => {
    document.body.classList.add('electron-mode');
});
