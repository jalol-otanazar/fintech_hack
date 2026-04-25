// apps/overlay/electron/preload.js — typed IPC bridge
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  onBrainMessage:  (cb) => ipcRenderer.on('brain-message', (_, msg) => cb(msg)),
  sendCardUsed:    (cardId) => ipcRenderer.send('card-used', cardId),
  sendCallStarted: (callId) => ipcRenderer.send('call-started', callId),
  sendHeartbeat:   () => ipcRenderer.send('heartbeat'),
});
