# Installation Guide

Complete installation guide for ANT (AI Note Taker).

---

## System Requirements

### Windows
- **OS:** Windows 10 (64-bit) or Windows 11
- **RAM:** 4 GB minimum, 8 GB recommended
- **Disk:** 2 GB free space
- **Microphone:** Required for voice input
- **Internet:** Required for cloud AI features (optional for local mode)

### macOS
- **OS:** macOS 11 (Big Sur) or later
- **RAM:** 4 GB minimum, 8 GB recommended
- **Disk:** 2 GB free space
- **Microphone:** Required for voice input

### Linux
- **OS:** Ubuntu 20.04+, Fedora 34+, or similar
- **RAM:** 4 GB minimum, 8 GB recommended
- **Disk:** 2 GB free space
- **Microphone:** Required for voice input

---

## Download

Download the latest release from [GitHub Releases](https://github.com/shyamsunderprogramer-design/ai-note-taker/releases).

### Choose Your Version

| Version | Best For |
|---------|----------|
| **Installer** (Setup.exe) | Most users - Installs to Program Files |
| **Portable** (.exe) | USB drive or no-install use |
| **macOS DMG** | Mac users |
| **Linux AppImage** | Universal Linux distribution |
| **Linux DEB** | Debian/Ubuntu users |

---

## Windows Installation

### Installer (Recommended)

1. Download `AI Note Taker-Setup-X.X.X-win-x64.exe`
2. Double-click to run
3. Follow the installation wizard:
   - Choose installation directory
   - Create desktop shortcut (optional)
   - Install
4. Launch from Start Menu or Desktop

### Portable

1. Download `AI Note Taker-X.X.X-win-x64-portable.exe`
2. Copy to desired location (USB drive, Desktop, etc.)
3. Double-click to run

### First Run

On first launch, the app will:
1. Check for Python environment
2. Verify microphone access
3. Download required models (one-time, ~500MB)

---

## macOS Installation

1. Download `AI Note Taker-X.X.X-mac-x64.dmg` (Intel) or `AI Note Taker-X.X.X-mac-arm64.dmg` (M1/M2)
2. Open the DMG file
3. Drag "AI Note Taker" to Applications folder
4. Open from Applications

### Security Notice

If you see "AI Note Taker can't be opened":
1. Go to System Preferences > Security & Privacy
2. Click "Open Anyway"
3. Confirm with your password

---

## Linux Installation

### AppImage (Universal)

1. Download `AI Note Taker-X.X.X-linux-x64.AppImage`
2. Make executable:
   ```bash
   chmod +x "AI Note Taker-X.X.X-linux-x64.AppImage"
   ```
3. Run:
   ```bash
   ./"AI Note Taker-X.X.X-linux-x64.AppImage"
   ```

### Debian/Ubuntu (DEB)

1. Download `AI Note Taker-X.X.X-linux-x64.deb`
2. Install:
   ```bash
   sudo dpkg -i "AI Note Taker-X.X.X-linux-x64.deb"
   sudo apt-get install -f  # Fix dependencies if needed
   ```
3. Launch from applications menu or:
   ```bash
   ai-note-taker
   ```

---

## Post-Installation Setup

### 1. Configure Microphone

- Ensure microphone is connected and working
- Test in app's onboarding screen
- Adjust input volume in system settings

### 2. Install Ollama (Optional - for local AI)

```bash
# macOS/Linux
curl -fsSL https://ollama.com/install.sh | sh

# Windows
# Download from https://ollama.com
```

Pull a model:
```bash
ollama pull qwen2.5:1.5b
```

### 3. Configure API Keys (Optional - for cloud AI)

1. Open app menu (☰) → Settings
2. Add API keys for desired providers:
   - OpenAI
   - Anthropic
   - Google
   - etc.

### 4. Setup Cognitive Graph (Optional)

1. Install Neo4j or use embedded
2. Follow [SETUP_COGNITIVE_GRAPH.md](SETUP_COGNITIVE_GRAPH.md)

---

## Troubleshooting

### App Won't Start

**Windows:**
- Install [Visual C++ Redistributable](https://aka.ms/vs/17/release/vc_redist.x64.exe)
- Run as Administrator
- Check Windows Defender exclusions

**macOS:**
- Allow in Security & Privacy
- Update to latest macOS

**Linux:**
- Install dependencies:
  ```bash
  sudo apt-get install libgtk-3-0 libnotify4 libnss3 libxss1 libxtst6
  ```

### Microphone Not Working

1. Check system permissions
2. Test in another app
3. Restart AI Note Taker
4. Check input device selection

### High CPU/Memory Usage

- Close other applications
- Reduce AI model size in settings
- Disable real-time suggestions if not needed

### Transcription Not Working

1. Check microphone permissions
2. Verify Whisper model downloaded
3. Check logs: `%APPDATA%/AI Note Taker/logs` (Windows)

---

## Updating

### Automatic Updates

The app checks for updates automatically (if enabled in settings).

### Manual Update

1. Download new version
2. Install over existing (settings preserved)
3. Or uninstall old version first

---

## Uninstallation

### Windows

**Installer version:**
- Settings → Apps → AI Note Taker → Uninstall
- Or use Control Panel

**Portable version:**
- Simply delete the file

### macOS

1. Drag from Applications to Trash
2. Remove config:
   ```bash
   rm -rf ~/Library/Application\ Support/ai-note-taker
   ```

### Linux

**AppImage:**
- Simply delete the file

**DEB:**
```bash
sudo apt-get remove ai-note-taker
```

---

## Support

- **Issues:** [GitHub Issues](https://github.com/shyamsunderprogramer-design/ai-note-taker/issues)
- **Documentation:** [README.md](../README.md)
- **Changelog:** [CHANGELOG.md](../../../CHANGELOG.md)

---

*Last Updated: 2026-04-05*
