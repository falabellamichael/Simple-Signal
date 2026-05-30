const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
    windowControl: (action) => ipcRenderer.send('window-control', action),
    openExtension: (url, title, width, height) => ipcRenderer.send('open-extension', { url, title, width, height }),
    onOpenExtensionsModal: (callback) => ipcRenderer.on('open-extensions-modal', callback)
});

// Inject electron-mode class into the body once the DOM is ready
window.addEventListener('DOMContentLoaded', () => {
    document.body.classList.add('electron-mode');
});
