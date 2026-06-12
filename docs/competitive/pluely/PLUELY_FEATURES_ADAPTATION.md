# Pluely Features Adaptation Plan for AI Note Taker

**Analysis Date:** April 18, 2026  
**Source:** https://github.com/shyamsunderprogramer-design/pluely  
**Goal:** Adapt Pluely's best features into ANT (AI Note Taker)

---

## Executive Summary

Pluely is a ~10MB Tauri-based AI assistant focused on "invisibility" during meetings/interviews. While our ANT application already has many similar features, we can adopt several enhancements from Pluely to improve stealth, UX, and performance.

---

## Feature Comparison Matrix

| Feature | Pluely | ANT Current | Adaptation Priority |
|---------|--------|-------------|---------------------|
| **Translucent Overlay** | ✅ Yes | ⚠️ Basic | **HIGH** |
| **Global Hotkeys** | ✅ Cmd+Shift+M/A/S | ⚠️ Limited | **HIGH** |
| **System Audio Capture** | ✅ Hotkey | ✅ Yes | Already Have |
| **Voice Input** | ✅ Hotkey | ⚠️ WebSocket | **MEDIUM** |
| **Screenshot OCR** | ✅ Hotkey | ✅ Yes | Already Have |
| **File Drag-Drop** | ✅ Yes | ❌ No | **MEDIUM** |
| **Chat History by Date** | ✅ Yes | ✅ Yes | Already Have |
| **Always-on-Top** | ✅ Yes | ✅ Yes | Already Have |
| **Theme Toggle** | ✅ Light/Dark/System | ⚠️ Basic | **MEDIUM** |
| **Autostart** | ✅ Yes | ⚠️ Manual | **LOW** |
| **Hide Dock Icon** | ✅ Yes | ✅ Yes | Already Have |
| **Zero Server** | ✅ Local LLM | ⚠️ Hybrid | **MEDIUM** |
| **SQLite Storage** | ✅ Yes | ✅ Yes | Already Have |
| **Custom Providers** | ✅ Curl commands | ✅ 8+ Providers | Already Better |
| **Cross-Platform** | ✅ Mac/Win/Linux | ✅ Yes | Already Have |
| **Size** | ~10MB | ~200MB | **Optimization** |

---

## HIGH PRIORITY Adaptations

### 1. Translucent Overlay Window (Feature: `translucent-overlay`)

**Pluely Implementation:**
- Translucent window with adjustable opacity
- Undetectable in screen shares
- Content "bleed-through" (see-through to underlying windows)

**ANT Adaptation Plan:**

```javascript
// electron/main.js - Window creation enhancements
function createTranslucentWindow() {
  const overlay = new BrowserWindow({
    width: 400,
    height: 600,
    transparent: true,        // Enable transparency
    frame: false,              // No window frame
    alwaysOnTop: true,
    opacity: 0.85,             // Default 85% opacity (adjustable)
    backgroundColor: '#00000000', // Fully transparent background
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false
    }
  })
  
  // Enable click-through when holding specific key
  overlay.setIgnoreMouseEvents(false)
  
  return overlay
}
```

**UI Changes Required:**
- [ ] Add opacity slider (50% - 100%)
- [ ] Add "click-through" toggle (Alt+Click to pass through)
- [ ] Add border glow effect for visibility
- [ ] Add minimize-to-translucent-mode button

**Files to Modify:**
- `electron/main.js` - Window creation
- `apps/web/style.css` - Translucent styling
- `electron/stealth.js` - Integration with stealth mode

---

### 2. Global Hotkey System (Feature: `global-hotkeys`)

**Pluely Implementation:**
- `Cmd/Ctrl+Shift+M` - Toggle microphone/system audio
- `Cmd/Ctrl+Shift+A` - Voice input
- `Cmd/Ctrl+Shift+S` - Screenshot
- `Cmd/Ctrl+Shift+H` - Show/hide overlay

**ANT Adaptation Plan:**

```javascript
// electron/main.js - Global shortcuts
function registerGlobalHotkeys() {
  // Toggle transcription (system audio)
  globalShortcut.register('CommandOrControl+Shift+M', () => {
    toggleTranscription()
  })
  
  // Voice input (push-to-talk)
  globalShortcut.register('CommandOrControl+Shift+A', () => {
    startVoiceInput()
  })
  
  // Screenshot + OCR
  globalShortcut.register('CommandOrControl+Shift+S', () => {
    captureScreenshot()
  })
  
  // Toggle overlay visibility
  globalShortcut.register('CommandOrControl+Shift+H', () => {
    toggleOverlayVisibility()
  })
  
  // Quick AI response (new)
  globalShortcut.register('CommandOrControl+Shift+Space', () => {
    showQuickResponse()
  })
}
```

**New Features:**
- [ ] Push-to-talk voice input (hold for recording)
- [ ] Quick screenshot without UI interaction
- [ ] One-key stealth toggle
- [ ] Customizable hotkeys in settings

**Files to Modify:**
- `electron/main.js` - Hotkey registration
- `apps/web/app.js` - Frontend hotkey handling

---

## MEDIUM PRIORITY Adaptations

### 3. Enhanced Theme System (Feature: `theme-system`)

**Pluely Implementation:**
- Light theme
- Dark theme
- System theme (auto-detect)

**ANT Adaptation Plan:**

```css
/* apps/web/style.css - Theme system */
:root {
  /* Light theme */
  --bg-light: #ffffff;
  --text-light: #1a1a1a;
  --accent-light: #3b82f6;
  
  /* Dark theme */
  --bg-dark: #0f172a;
  --text-dark: #e2e8f0;
  --accent-dark: #60a5fa;
  
  /* Glass/translucent */
  --bg-translucent: rgba(15, 23, 42, 0.75);
  --glass-border: rgba(255, 255, 255, 0.1);
}

/* System preference detection */
@media (prefers-color-scheme: light) {
  [data-theme="system"] { ... }
}
```

**UI Changes:**
- [ ] Add theme toggle (Light/Dark/System/Translucent)
- [ ] Add glassmorphism effects
- [ ] Add accent color picker
- [ ] Theme-aware icons

---

### 4. File Drag & Drop Support (Feature: `drag-drop`)

**Pluely Implementation:**
- Drag files onto window
- Automatic file processing
- Support for images, PDFs, text files

**ANT Adaptation Plan:**

```javascript
// electron/preload.js - Drag and drop API
const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('electronAPI', {
  // ... existing APIs
  
  // Drag and drop
  onFileDrop: (callback) => ipcRenderer.on('file-dropped', callback),
  processFile: (filePath) => ipcRenderer.invoke('process-file', filePath)
})

// electron/main.js - Handle drag events
ipcMain.handle('process-file', async (event, filePath) => {
  const ext = path.extname(filePath).toLowerCase()
  
  if (['.png', '.jpg', '.jpeg'].includes(ext)) {
    return await processImage(filePath)
  } else if (ext === '.pdf') {
    return await processPDF(filePath)
  } else if (['.txt', '.md'].includes(ext)) {
    return await processText(filePath)
  }
})
```

**Features:**
- [ ] Drag image → OCR + analyze
- [ ] Drag PDF → Extract text + RAG
- [ ] Drag text file → Add to context
- [ ] Visual feedback during drag (border highlight)

---

### 5. Local LLM Support Enhancement (Feature: `zero-server`)

**Pluely Implementation:**
- 100% local with Ollama
- No cloud dependency
- SQLite vector storage

**ANT Enhancement Plan:**

```python
# backend/modules/ai/local_llm_manager.py
import ollama
from typing import Optional, Iterator

class LocalLLMManager:
    """Manage local LLM via Ollama integration"""
    
    def __init__(self):
        self.available_models = []
        self.default_model = "llama3.2"
        
    async def list_models(self) -> list:
        """List available local models"""
        try:
            models = ollama.list()
            return [m['name'] for m in models['models']]
        except:
            return []
    
    async def generate(self, prompt: str, model: str = None) -> Iterator[str]:
        """Stream response from local model"""
        model = model or self.default_model
        
        stream = ollama.generate(
            model=model,
            prompt=prompt,
            stream=True
        )
        
        for chunk in stream:
            yield chunk['response']
    
    async def is_available(self) -> bool:
        """Check if Ollama is running"""
        try:
            ollama.list()
            return True
        except:
            return False
```

**Features:**
- [ ] Auto-detect Ollama installation
- [ ] Download model recommendations
- [ ] Fallback to cloud if local unavailable
- [ ] Local embeddings for RAG
- [ ] Complete offline mode toggle

---

## LOW PRIORITY Adaptations

### 6. Autostart Configuration (Feature: `autostart`)

```javascript
// electron/main.js
const { app } = require('electron')

function configureAutostart(enabled) {
  app.setLoginItemSettings({
    openAtLogin: enabled,
    openAsHidden: true,      // Start in tray/stealth
    path: app.getPath('exe')
  })
}
```

---

### 7. Window Size & Position Memory

```javascript
// electron/main.js - Store window state
const windowState = store.get('windowState', {
  width: 1200,
  height: 800,
  x: undefined,
  y: undefined,
  opacity: 0.95,
  alwaysOnTop: true
})

function saveWindowState() {
  if (win && !win.isDestroyed()) {
    const bounds = win.getBounds()
    store.set('windowState', {
      ...bounds,
      opacity: win.getOpacity(),
      alwaysOnTop: win.isAlwaysOnTop()
    })
  }
}
```

---

## Implementation Roadmap

### Phase 1: Core UI Enhancements (Week 1-2)
1. **Translucent Overlay**
   - [ ] Implement transparent window
   - [ ] Add opacity controls
   - [ ] Test screen share detection

2. **Global Hotkeys**
   - [ ] Register all hotkeys
   - [ ] Add settings UI for customization
   - [ ] Document hotkey cheatsheet

### Phase 2: UX Improvements (Week 3-4)
3. **Theme System**
   - [ ] Implement CSS variables
   - [ ] Add theme toggle
   - [ ] Glassmorphism effects

4. **Drag & Drop**
   - [ ] Implement IPC handlers
   - [ ] Add visual feedback
   - [ ] Support multiple file types

### Phase 3: Advanced Features (Week 5-6)
5. **Local LLM Enhancement**
   - [ ] Ollama integration
   - [ ] Model management UI
   - [ ] Offline mode toggle

6. **Polish**
   - [ ] Autostart
   - [ ] Window state persistence
   - [ ] Performance optimization

---

## Code Implementation Guide

### File: `electron/features/pluely-adaptations.js`

```javascript
/**
 * Pluely-inspired features for ANT
 * Module: pluely-adaptations.js
 */

const { BrowserWindow, globalShortcut, ipcMain } = require('electron')
const path = require('path')

class PluelyAdapter {
  constructor(mainWindow) {
    this.mainWindow = mainWindow
    this.overlayWindow = null
    this.opacity = 0.95
    this.isClickThrough = false
  }
  
  // Create translucent overlay window
  createOverlay() {
    this.overlayWindow = new BrowserWindow({
      width: 400,
      height: 700,
      transparent: true,
      frame: false,
      alwaysOnTop: true,
      opacity: this.opacity,
      backgroundColor: '#00000000',
      webPreferences: {
        nodeIntegration: true,
        contextIsolation: false,
        preload: path.join(__dirname, '..', 'preload.js')
      }
    })
    
    this.overlayWindow.loadFile('apps/web/overlay.html')
    
    // Enable drag
    this.overlayWindow.setMovable(true)
    
    return this.overlayWindow
  }
  
  // Toggle click-through mode
  toggleClickThrough() {
    this.isClickThrough = !this.isClickThrough
    if (this.overlayWindow) {
      this.overlayWindow.setIgnoreMouseEvents(this.isClickThrough)
    }
    return this.isClickThrough
  }
  
  // Set opacity (0.5 - 1.0)
  setOpacity(value) {
    this.opacity = Math.max(0.5, Math.min(1.0, value))
    if (this.overlayWindow) {
      this.overlayWindow.setOpacity(this.opacity)
    }
  }
  
  // Register Pluely-style hotkeys
  registerHotkeys() {
    // Screenshot
    globalShortcut.register('CmdOrCtrl+Shift+S', () => {
      this.captureScreenshot()
    })
    
    // Toggle overlay
    globalShortcut.register('CmdOrCtrl+Shift+H', () => {
      this.toggleOverlay()
    })
    
    // Quick voice
    globalShortcut.register('CmdOrCtrl+Shift+A', () => {
      this.startQuickVoice()
    })
    
    // Decrease opacity
    globalShortcut.register('CmdOrCtrl+Shift+-', () => {
      this.setOpacity(this.opacity - 0.05)
    })
    
    // Increase opacity
    globalShortcut.register('CmdOrCtrl+Shift+=', () => {
      this.setOpacity(this.opacity + 0.05)
    })
  }
  
  captureScreenshot() {
    // Trigger screenshot capture
    this.mainWindow.webContents.send('trigger-screenshot')
  }
  
  toggleOverlay() {
    if (this.overlayWindow) {
      if (this.overlayWindow.isVisible()) {
        this.overlayWindow.hide()
      } else {
        this.overlayWindow.show()
      }
    }
  }
  
  startQuickVoice() {
    // Start voice recording
    this.mainWindow.webContents.send('start-voice-input')
  }
  
  // Cleanup
  destroy() {
    globalShortcut.unregisterAll()
    if (this.overlayWindow) {
      this.overlayWindow.destroy()
    }
  }
}

module.exports = { PluelyAdapter }
```

---

## UI Mockup: Translucent Overlay

```
+----------------------------------+
|  ANT Overlay (85% opacity)      |
|  +----------------------------+  |
|  |  🎤 Live Transcription     |  |
|  |  "Tell me about yourself"  |  |
  |                             |  |
|  |  🤖 AI Suggestion:          |  |
|  |  "I have 5 years..."       |  |
|  +----------------------------+  |
|                                  |
|  [🔊] [📷] [🎤] [👁️] [⚙️]      |
|  Audio  SS  Voice Click  Settings|
+----------------------------------+

Controls:
- 🔊: Toggle system audio capture
- 📷: Screenshot + OCR
- 🎤: Push-to-talk voice input
- 👁️: Toggle click-through mode
- ⚙️: Opacity slider (50-100%)
```

---

## Testing Checklist

- [ ] Overlay appears above all windows
- [ ] Opacity changes reflect immediately
- [ ] Click-through mode works (Alt+Click)
- [ ] Screen share detection (test with Zoom)
- [ ] All hotkeys work when app is not focused
- [ ] File drag-drop shows visual feedback
- [ ] Theme changes apply instantly
- [ ] Window position/size persists
- [ ] Autostart works after reboot
- [ ] Local LLM fallback works

---

## Summary

**Already Superior to Pluely:**
- ✅ Multi-provider AI (8+ vs custom curl)
- ✅ Meeting transcription (not in Pluely)
- ✅ Job tracking pipeline
- ✅ Knowledge graph (Neo4j)
- ✅ Chrome extension
- ✅ 10,000+ curated questions

**Features to Adapt from Pluely:**
- 🔧 Translucent overlay (higher stealth)
- 🔧 Global hotkey system
- 🔧 Enhanced theming
- 🔧 File drag-drop
- 🔧 Local LLM emphasis

**Pluely Advantages to Match:**
- ⚠️ Size (10MB vs 200MB) - Consider Tauri migration long-term
- ⚠️ Linux support (we have Electron, add Linux build)
- ⚠️ Click-through mode

---

*Adaptation plan ready for implementation*
