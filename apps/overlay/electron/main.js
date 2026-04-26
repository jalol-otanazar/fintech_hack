// apps/overlay/electron/main.js — Electron main process
const { app, BrowserWindow, ipcMain, globalShortcut } = require('electron');
const path = require('path');
const WebSocket = require('ws');

const BRAIN_WS_URL = process.env.BRAIN_WS_URL || 'ws://localhost:8001/ws';
const IS_DEV = process.env.NODE_ENV === 'development' || !app.isPackaged;

let mainWindow = null;
let brainWs = null;
let callId = null;

// ── Window ──────────────────────────────────────────────────────────────────
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200, height: 220,
    x: 0, y: 0,
    frame: false,
    transparent: true,
    alwaysOnTop: true,
    skipTaskbar: true,
    resizable: true,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js'),
    },
  });

  mainWindow.setIgnoreMouseEvents(false);
  if (IS_DEV) {
    mainWindow.loadURL('http://localhost:5173');
  } else {
    mainWindow.loadFile(path.join(__dirname, '../build/index.html'));
  }
}

// ── Brain WebSocket ──────────────────────────────────────────────────────────
function connectBrain(cid) {
  const url = `${BRAIN_WS_URL}/${cid}`;
  brainWs = new WebSocket(url);

  brainWs.on('open', () => console.log('[Brain WS] connected', url));
  brainWs.on('message', (data) => {
    try {
      const msg = JSON.parse(data.toString());
      if (mainWindow) mainWindow.webContents.send('brain-message', msg);
    } catch (e) { console.error('[Brain WS] parse error', e); }
  });

  let delay = 1000;
  brainWs.on('close', () => {
    console.log(`[Brain WS] closed, reconnect in ${delay}ms`);
    setTimeout(() => connectBrain(cid), delay);
    delay = Math.min(delay * 2, 16000);
  });
  brainWs.on('error', (e) => console.error('[Brain WS] error', e.message));
}

// ── IPC ──────────────────────────────────────────────────────────────────────
ipcMain.on('call-started', (_, cid) => {
  callId = cid;
  connectBrain(cid);
});

ipcMain.on('card-used', (_, cardId) => {
  console.log('[Audit] card used:', cardId);
  // TODO: POST to brain audit endpoint
});

ipcMain.on('heartbeat', () => {
  if (brainWs && brainWs.readyState === WebSocket.OPEN) {
    brainWs.send(JSON.stringify({ type: 'heartbeat', ts: Date.now() }));
  }
});

// ── App lifecycle ────────────────────────────────────────────────────────────
app.whenReady().then(() => {
  createWindow();
  // Demo: auto-connect with a fake call ID after 1s
  setTimeout(() => {
    callId = 'demo-call-001';
    connectBrain(callId);
    if (mainWindow) mainWindow.webContents.send('brain-message',
      { type: 'call_start', payload: { call_id: callId } });
  }, 1000);
});

app.on('window-all-closed', () => app.quit());
