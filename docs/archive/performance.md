# Performance and measurement — historical source records

These are dated source records preserved during documentation consolidation. Their prices, legal statements, feature completion claims, paths, and benchmark numbers have not been revalidated. They are not current setup instructions or release acceptance results.

Current guide: [Performance and measurement](../business/PERFORMANCE.md).

## Source index
- [SPEED_OPTIMIZATION_PLAN.md](#source-speed-optimization-plan)
- [SPEED_OPTIMIZATIONS_IMPLEMENTED.md](#source-speed-optimizations-implemented)
- [SPEED_IMPROVEMENT_SUMMARY.md](#source-speed-improvement-summary)

<a id="source-speed-optimization-plan"></a>

## Source: SPEED_OPTIMIZATION_PLAN.md

<details>
<summary>Read the original source record</summary>

# ANT Speed Optimization Plan

**Goal:** Match Pluely's speed while keeping Electron + Python architecture
**Target:**
- Startup: 3-5s → <2s
- Memory: 300MB → <150MB
- UI: 60fps, instant response

---

## Phase 1: Electron Optimizations (Critical)

### 1.1 Fast Startup Sequence
- [ ] Splash screen for perceived speed
- [ ] Delay non-critical backend init
- [ ] Lazy load UI components
- [ ] Preload critical resources

### 1.2 Renderer Optimizations
- [ ] Disable unused Chromium features
- [ ] Enable hardware acceleration
- [ ] Optimize CSS paint/render
- [ ] Virtual scrolling for chat

### 1.3 Memory Reduction
- [ ] Single shared context
- [ ] Unload unused modules
- [ ] Clear caches periodically
- [ ] Optimize image handling

---

## Phase 2: Python Backend Optimizations (Critical)

### 2.1 Import Optimization
- [ ] Lazy import heavy modules
- [ ] Conditional imports
- [ ] Remove unused dependencies

### 2.2 Startup Optimization
- [ ] Delay AI model loading
- [ ] Async initialization
- [ ] Preload on idle

### 2.3 Response Optimization
- [ ] Connection pooling
- [ ] Response caching
- [ ] Optimize JSON serialization

---

## Phase 3: Process Architecture (High Impact)

### 3.1 Process Consolidation
- [ ] Shared memory for data
- [ ] Reduce IPC overhead
- [ ] Optimize message passing

### 3.2 Resource Management
- [ ] Automatic cleanup
- [ ] Memory limits
- [ ] CPU throttling

---

## Quick Wins (Implement Now)
1. Splash screen
2. Lazy backend start
3. Disable unused Electron APIs
4. Optimize CSS
5. Lazy imports in Python

</details>

<a id="source-speed-optimizations-implemented"></a>

## Source: SPEED_OPTIMIZATIONS_IMPLEMENTED.md

<details>
<summary>Read the original source record</summary>

# Speed Optimizations Implemented

**Date:** April 18, 2026  
**Goal:** Match Pluely's speed while keeping Electron + Python

---

## ✅ Optimizations Implemented

### 1. Electron Main Process Optimizations

#### Disabled Unused Chromium Features
**File:** `electron/main.js`

```javascript
// Disabled features for speed:
- MediaRouter
- TabHoverCardImages
- ReadAnything
- AccessibilityPerformanceMonitoring
- PaymentMethodQuery
- WebPayments
- Background networking
- Component extensions with background pages
- Renderer backgrounding
- Background timer throttling
```

**Impact:**
- Reduced memory footprint by ~50MB
- Faster startup (less to initialize)
- Fewer background processes

#### Optimized Command Line Switches
```javascript
app.commandLine.appendSwitch("disk-cache-size", "104857600")      // 100MB limit
app.commandLine.appendSwitch("media-cache-size", "52428800")      // 50MB limit
app.commandLine.appendSwitch("js-flags", "--max-old-space-size=4096")
```

### 2. Splash Screen (Perceived Speed)

**File:** `apps/web/splash.html`

Features:
- Shows immediately on app launch
- Animated loading indicator
- Status messages ("Initializing...", "Loading backend...")
- Fade-out transition to main window
- -webkit-app-region: drag (movable)

**Impact:**
- User sees feedback in <100ms
- Perceived startup time reduced by ~3s

### 3. Parallel Initialization

**File:** `electron/main.js`

Before:
```javascript
await startBackend()
createWindow()
```

After:
```javascript
const backendPromise = startBackend()
const windowPromise = new Promise((resolve) => createWindow())
await Promise.all([backendPromise, windowPromise])
```

**Impact:**
- Backend and window load in parallel
- ~1s faster startup

### 4. Lazy Feature Loading

**File:** `electron/main.js`

```javascript
// Delay non-critical initialization
setTimeout(() => {
  // Initialize Pluely adapter
  // Register hotkeys
}, 1000) // Delay 1s for UI responsiveness
```

**Impact:**
- Main window shows faster
- Non-critical features load in background
- Better perceived performance

### 5. Renderer Process Optimizations

**File:** `apps/web/app.js`

Added utilities:
```javascript
// Debounce for input handling
function debounce(fn, wait) { ... }

// Throttle for scroll/resize
function throttle(fn, limit) { ... }

// Lazy module loading
async function lazyLoad(moduleName, importFn) { ... }

// Intersection Observer for lazy rendering
const lazyObserver = new IntersectionObserver(...)
```

**Impact:**
- Smoother UI interactions
- Reduced CPU usage
- Better scroll performance

### 6. Python Backend Optimizations

**File:** `backend/core/fast_startup.py`

#### Lazy Module Loading
```python
class LazyModule:
    """Imports only on first access"""
    def __getattr__(self, item):
        if self._module is None:
            self._module = __import__(self.name)
        return getattr(self._module, item)
```

#### Background Initialization
```python
async def background_init():
    # Initialize heavy modules in parallel
    tasks = [
        _init_unified_db(),
        _init_whisper(),
        _init_database()
    ]
    await asyncio.gather(*tasks)
```

#### Fast Health Endpoint
```python
@fast_router.get("/health")
async def health_check():
    return {"status": "ok"}  # No imports needed
```

**Impact:**
- Backend starts in ~500ms (vs ~3s)
- Heavy modules load in background
- Health check responds immediately

---

## 📊 Performance Improvements

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| **Startup (cold)** | 4-5s | ~2s | **2x faster** ✅ |
| **Startup (perceived)** | 4-5s | ~0.5s | **With splash** ✅ |
| **Memory (idle)** | 300MB | ~200MB | **-100MB** ✅ |
| **Memory (active)** | 500MB | ~350MB | **-150MB** ✅ |
| **Backend Start** | 3s | 0.5s | **6x faster** ✅ |
| **UI Responsiveness** | Good | Excellent | **Smoother** ✅ |

---

## 🔧 Files Modified

1. **electron/main.js**
   - Chromium feature flags
   - Splash screen integration
   - Parallel initialization
   - Lazy loading

2. **electron/preload.js**
   - No changes needed

3. **apps/web/app.js**
   - Debounce/throttle utilities
   - Lazy module loading
   - Intersection Observer

4. **apps/web/splash.html** (NEW)
   - Splash screen UI
   - Loading animations

5. **backend/core/fast_startup.py** (NEW)
   - Lazy imports
   - Background initialization
   - Optimized health endpoint

---

## 🎯 How to Use Optimized Backend

### Quick Start (Development)
```bash
cd backend/core
python fast_startup.py
```

### Production Integration
Update `electron/main.js` to use `fast_startup.py`:
```javascript
// Change uvicorn module path
const uvicornModule = isCoreMainPy ? "core.fast_startup:app" : "fast_startup:app"
```

---

## 📈 Monitoring Performance

### Electron DevTools
1. Press `Ctrl+Shift+I` in app
2. Performance tab > Record
3. Check startup time

### Memory Profiling
```javascript
// In console
console.log(process.memoryUsage())
// Check heapUsed, external
```

### Backend Profiling
```python
# In fast_startup.py, add timing
import time
start = time.time()
# ... operation ...
print(f"Time: {time.time() - start:.3f}s")
```

---

## 🚀 Next Steps (Optional)

### Ultra-Optimizations
1. **V8 Snapshots** - Pre-compile JS for faster parsing
2. **Code Splitting** - Load features on demand
3. **Service Workers** - Cache assets locally
4. **Web Workers** - Offload heavy computation
5. **Wasm Modules** - Replace heavy JS with Rust/Wasm

### Memory Optimizations
1. **SharedArrayBuffer** - Share data between processes
2. **Process Consolidation** - Single renderer process
3. **Aggressive GC** - Force garbage collection on idle

---

## ✅ Success Criteria

- [x] Startup < 2 seconds
- [x] Memory < 250MB idle
- [x] 60fps UI interactions
- [x] Backend responds in <100ms
- [x] Splash screen for perceived speed
- [x] Lazy loading for heavy features

**All targets achieved!** 🎉

</details>

<a id="source-speed-improvement-summary"></a>

## Source: SPEED_IMPROVEMENT_SUMMARY.md

<details>
<summary>Read the original source record</summary>

# ANT Speed Improvements - Final Report

**Date:** April 18, 2026  
**Status:** All speed optimizations implemented ✅

---

## 📊 Before vs After Comparison

| Metric | Before | After | Pluely | Status |
|--------|--------|-------|--------|--------|
| **Cold Startup** | 4-5s | ~2s | ~0.5s | ✅ Good |
| **Perceived Startup** | 4-5s | ~0.5s (w/ splash) | ~0.5s | ✅ **Equal** |
| **Memory (idle)** | 300MB | ~200MB | ~50MB | ✅ Improved |
| **Memory (active)** | 500MB | ~350MB | ~100MB | ✅ Improved |
| **Backend Start** | 3s | 0.5s | N/A | ✅ **Excellent** |
| **UI Responsiveness** | Good | 60fps | 60fps | ✅ **Equal** |
| **Bundle Size** | ~200MB | ~200MB | ~10MB | ⚠️ Architecture |

---

## 🎯 What We Achieved

### ✅ Perceived Speed = Pluely
With the splash screen, users see feedback in <100ms, matching Pluely's instant response.

### ✅ Backend Speed > Pluely
Optimized Python backend starts in 0.5s with lazy loading, responding immediately to health checks.

### ✅ UI Performance = Pluely
60fps interactions with debouncing, throttling, and lazy rendering.

### ⚠️ Bundle Size Still Different
Due to Electron vs Tauri architecture. Cannot match 10MB without complete rewrite.

### ⚠️ Memory Still Higher
Due to Chromium runtime. Reduced by 100MB+ but cannot match 50MB without Tauri.

---

## 🔍 Detailed Analysis

### Why Bundle Size Can't Match
```
Pluely:  Tauri + System WebView = ~10MB
ANT:      Electron (Chromium + Node) + Python = ~200MB
```
**Verdict:** Acceptable trade-off for Python ML ecosystem

### Why Memory Can't Match
```
Pluely:  Rust native = ~50MB
ANT:     Chromium (~150MB) + Node (~50MB) + Python (~50MB) = ~250MB
```
**Verdict:** Reduced from 300MB to 200MB, 33% improvement

### Where We Won
```
Backend Speed:     0.5s  (6x improvement)
UI Responsiveness: 60fps (matches Pluely)
Perceived Speed:   0.5s  (matches Pluely)
Features:          100+  (vs Pluely's ~20)
```

---

## 🏆 Final Verdict

### Speed: ✅ Competitive
- Perceived speed matches Pluely
- Backend faster than Pluely
- UI as smooth as Pluely

### Size: ⚠️ Acceptable Trade-off
- 20x larger but 100x more features
- Python ML ecosystem worth the cost
- Optimized to ~200MB (was ~250MB)

### Features: ✅ Far Superior
- Interview prep (10,000+ questions)
- AI providers (8+ vs 2)
- Voice cloning (RVC)
- Knowledge graph (Neo4j)
- Chrome extension
- CRM integration
- And much more...

---

## 💡 Recommendation

**Keep Electron + Python.** The trade-offs are worth it:

1. **Speed is competitive** with optimizations
2. **Features unmatched** by any competitor
3. **Development velocity** 5x faster than Rust
4. **Ecosystem access** to 1000s of Python ML libraries

---

**Speed optimization complete!** 🚀

</details>
