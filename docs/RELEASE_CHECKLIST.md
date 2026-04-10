# Release Checklist

Pre-release checklist for AI Note Taker v1.0.0 (Phase 2 Complete)

---

## Pre-Release Tasks

### 1. Code Quality
- [ ] All tests passing (`python -m pytest backend/tests/ -v`)
- [ ] No critical bugs or security issues
- [ ] Code review completed
- [ ] Documentation updated

### 2. Version Updates
- [ ] Update version in `electron/package.json` (1.0.0)
- [ ] Update version in `backend/main.py` health check
- [ ] Update CHANGELOG.md with release date
- [ ] Update README.md if needed

### 3. Build Preparation
- [ ] Install dependencies: `cd electron && npm install`
- [ ] Ensure Python environment is set up
- [ ] Test local build: `npm run build:win`

### 4. Assets
- [ ] App icon created (`assets/icon.ico` for Windows)
- [ ] App icon created (`assets/icon.icns` for macOS)
- [ ] Screenshots for release notes
- [ ] Demo GIF/video prepared

---

## Build Process

### Windows Build
```bash
cd electron
npm run build:win
```

**Expected Outputs:**
- `dist/AI Note Taker-1.0.0-win-x64.exe` (Installer)
- `dist/AI Note Taker-1.0.0-win-x64-portable.exe` (Portable)

### macOS Build
```bash
cd electron
npm run build:mac
```

**Expected Outputs:**
- `dist/AI Note Taker-1.0.0-mac-x64.dmg`
- `dist/AI Note Taker-1.0.0-mac-arm64.dmg`

### Linux Build
```bash
cd electron
npm run build:linux
```

**Expected Outputs:**
- `dist/AI Note Taker-1.0.0-linux-x64.AppImage`
- `dist/AI Note Taker-1.0.0-linux-x64.deb`

---

## GitHub Release

### Create Release
1. Go to GitHub Releases
2. Click "Draft a new release"
3. Tag version: `v1.0.0`
4. Target: `main` branch

### Release Notes Template

```markdown
## AI Note Taker v1.0.0 - Phase 2 Complete 🎉

### What's New

**Real-Time Interview Assistance**
- Contextual suggestions during live interviews
- Voice commands: "What did I say about React?"
- Confidence-based suggestion filtering

**Enhanced Analytics**
- 4 new dashboard visualizations
- Skill progression tracking
- Company comparison heatmaps
- Topic network graphs

**Performance Insights**
- STAR method analysis
- Code quality scoring
- Speaking pattern feedback
- Personalized recommendations

**Study Plan Generator**
- AI-generated preparation roadmap
- Spaced repetition scheduling
- Resource recommendations (LeetCode, System Design)
- Export to calendar (iCal)

### Downloads

| Platform | Download |
|----------|----------|
| Windows (Installer) | `AI Note Taker-Setup-1.0.0-win-x64.exe` |
| Windows (Portable) | `AI Note Taker-1.0.0-win-x64-portable.exe` |
| macOS (Intel) | `AI Note Taker-1.0.0-mac-x64.dmg` |
| macOS (Apple Silicon) | `AI Note Taker-1.0.0-mac-arm64.dmg` |
| Linux (AppImage) | `AI Note Taker-1.0.0-linux-x64.AppImage` |
| Linux (deb) | `AI Note Taker-1.0.0-linux-x64.deb` |

### Installation

**Windows:**
1. Download installer
2. Run `AI Note Taker-Setup-1.0.0-win-x64.exe`
3. Follow installation wizard

**macOS:**
1. Download .dmg
2. Drag to Applications folder
3. Allow in System Preferences > Security

**Linux:**
```bash
# AppImage
chmod +x "AI Note Taker-1.0.0-linux-x64.AppImage"
./"AI Note Taker-1.0.0-linux-x64.AppImage"

# Debian/Ubuntu
sudo dpkg -i "AI Note Taker-1.0.0-linux-x64.deb"
```

### What's Changed
See [CHANGELOG.md](../CHANGELOG.md) for full details.

### Contributors
- @shyamsunderprogramer-design
- Claude (Anthropic)

### Support
- Report issues: [GitHub Issues](https://github.com/shyamsunderprogramer-design/ai-note-taker/issues)
- Documentation: [README.md](../README.md)
```

### Upload Assets
- [ ] Upload Windows installer
- [ ] Upload Windows portable
- [ ] Upload macOS DMG (x64)
- [ ] Upload macOS DMG (arm64)
- [ ] Upload Linux AppImage
- [ ] Upload Linux deb
- [ ] Mark as pre-release if needed
- [ ] Publish release

---

## Post-Release Tasks

### Verification
- [ ] Download and test installer
- [ ] Verify auto-updater works
- [ ] Check digital signatures (if applicable)

### Communication
- [ ] Post on social media
- [ ] Update website/download page
- [ ] Send notification to users
- [ ] Create demo video

### Monitoring
- [ ] Monitor GitHub issues
- [ ] Track download statistics
- [ ] Collect user feedback

---

## Quick Commands

```bash
# Run tests
python -m pytest backend/tests/ -v

# Build Windows
cd electron && npm run build:win

# Build macOS
cd electron && npm run build:mac

# Build Linux
cd electron && npm run build:linux

# Build all
cd electron && npm run build
```

---

## Rollback Plan

If critical issues found:
1. Mark release as pre-release
2. Add warning to release notes
3. Fix issues in patch branch
4. Release v1.0.1

---

*Last Updated: 2026-04-05*
