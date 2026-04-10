# DIY Testing Guide - Verify All New Features

## Step 1: Restart Backend (Required)

The backend needs to restart to load the 50+ new endpoints.

### Option A: If backend is running in terminal
Press `Ctrl+C` to stop, then:
```bash
cd D:/Rep/ai-note-taker/backend
python main.py
```

### Option B: Fresh start
```bash
cd D:/Rep/ai-note-taker/backend
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

Wait for: `[INFO] Application startup complete.`

---

## Step 2: Run Automated Test Suite

In a **new terminal**:
```bash
cd D:/Rep/ai-note-taker
python test_all_features.py
```

Expected: **22 tests, all passing**

---

## Step 3: Manual Testing (Optional but Recommended)

### Test 1: Mock Interview Library
```bash
curl http://localhost:8000/mock-interview/stats
```
Expected: `{"total_questions": 1000+, ...}`

### Test 2: Web Search Status
```bash
curl http://localhost:8000/search/status
```
Expected: `{"configured": false, "message": "Add PERPLEXITY_API_KEY..."}`

### Test 3: Voice Clone
```bash
curl -X POST "http://localhost:8000/voice-clone/create?name=MyVoice"
```
Expected: `{"model_id": "voice_...", "status": "training"}`

### Test 4: Shadow Agent
```bash
curl -X POST "http://localhost:8000/shadow/start?company=Google&role=software_engineer"
```
Expected: `{"status": "started", ...}`

### Test 5: Collaboration Mode
```bash
curl -X POST "http://localhost:8000/collaboration/create?host_name=TestUser"
```
Expected: `{"session_id": "...", "join_code": "ABC123"}`

---

## Step 4: Frontend Testing

Open `renderer/index.html` in browser or Electron app.

### Test Complexity Badge:
1. Ask AI: "What's the time complexity of bubble sort?"
2. Look for badge: `🟡 O(n²)` in the AI response

### Test Chrome Extension:
1. Open Chrome → Extensions → Developer Mode ON
2. Load Unpacked → Select `chrome-extension/` folder
3. Visit LinkedIn job page
4. Look for "🐜 Save Job" button

### Test VSCode Extension:
1. Open VSCode
2. Extensions → Install from VSIX (or F5 to debug)
3. Select `vscode-extension/` folder
4. Press `Ctrl+Shift+A` → Should open ANT sidebar

---

## Troubleshooting

### Backend won't start:
```bash
# Check for errors
python -c "import mock_interview_library; print('OK')"
python -c "import voice_clone_agent; print('OK')"
python -c "import shadow_agent; print('OK')"
python -c "import collaboration_mode; print('OK')"
```

### Port 8000 in use:
```bash
# Kill process using port 8000
# Windows:
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

### Import errors:
All new modules should auto-import. If errors:
```bash
pip install requests  # For web search
# (Other modules have no external deps)
```

---

## Expected Final Results

After restart + tests:

| Feature | Status |
|---------|--------|
| Complexity Badge | ✅ Auto-detects O(n), O(n²), etc. |
| Web Search | ✅ Endpoints ready (needs API key for live search) |
| Mock Interview | ✅ 1000+ questions available |
| Voice Clone | ✅ Framework ready (MVP simulation) |
| Shadow Agent | ✅ Background suggestions working |
| Collaboration | ✅ Duo alternative with join codes |
| Chrome Extension | ✅ Save jobs from LinkedIn/Indeed |
| VSCode Extension | ✅ Sidebar + hotkeys working |

---

## Quick Status Check

Run this one-liner after restart:
```bash
curl -s http://localhost:8000/health && echo " ✓ Backend OK"
curl -s http://localhost:8000/mock-interview/stats | python -c "import sys,json; d=json.load(sys.stdin); print(f'✓ Mock Library: {d.get(\"total_questions\", 0)} questions')"
curl -s http://localhost:8000/voice-clone/models && echo " ✓ Voice Clone OK"
curl -s http://localhost:8000/shadow/stats && echo " ✓ Shadow Agent OK"
```

**All checks should pass!**
