// Serialize captures so concurrent requests cannot restore ANT midway through capture.
function createScreenCapture({ BrowserWindow, desktopCapturer, screen, nativeCapture = null, delay = ms => new Promise(r => setTimeout(r, ms)) }) {
  let pending = Promise.resolve();
  return function capture() {
    const work = pending.then(async () => {
      const display = screen.getDisplayNearestPoint(screen.getCursorScreenPoint());
      // Native exclusion keeps every ANT window visible and leaves focus untouched.
      // Do not fall back to hiding windows if native capture fails.
      if (nativeCapture) return nativeCapture(display.id);
      const windows = BrowserWindow.getAllWindows().filter(w => !w.isDestroyed() && w.isVisible());
      const focused = windows.find(w => w.isFocused());
      try {
        for (const window of windows) window.hide();
        await delay(200); // Let the compositor remove our windows before taking the frame.
        const sources = await desktopCapturer.getSources({types: ['screen'], thumbnailSize: {width: 1920, height: 1080}});
        const source = sources.find(s => s.display_id === String(display.id)) || sources[0];
        if (!source?.thumbnail || source.thumbnail.isEmpty()) return null;
        return source.thumbnail.toJPEG(85).toString('base64');
      } finally {
        for (const window of windows) if (!window.isDestroyed()) window.showInactive();
        if (focused && !focused.isDestroyed()) focused.focus();
      }
    });
    pending = work.catch(() => {});
    return work;
  };
}
module.exports = { createScreenCapture };
