/**
 * Shared Window Controls Header
 * Adds macOS-style min/max/close traffic lights to any page
 * Automatically adjusts page headers and content for the 38px bar
 * Usage: Include this script on any standalone page
 */
(function() {
  // Only add if running in Electron (window.api exists)
  if (!window.api) return;

  const BAR_HEIGHT = 38;

  // Insert styles
  const style = document.createElement('style');
  style.textContent = `
    .win-controls-bar {
      position: fixed; top: 0; left: 0; right: 0; z-index: 9999;
      height: ${BAR_HEIGHT}px; display: flex; align-items: center; justify-content: space-between;
      padding: 0 14px; -webkit-app-region: drag; user-select: none;
      background: rgba(8, 47, 73, 0.45); backdrop-filter: blur(20px);
      -webkit-backdrop-filter: blur(20px);
      border-bottom: 1px solid rgba(56, 189, 248, 0.08);
    }
    .win-controls-bar .win-left { display: flex; align-items: center; gap: 6px; -webkit-app-region: no-drag; }
    .win-controls-bar .win-center {
      position: absolute; left: 50%; transform: translateX(-50%);
      font-size: 12px; font-weight: 600; color: rgba(255,255,255,0.55); letter-spacing: 0.3px;
    }
    .win-controls-bar .win-right { display: flex; align-items: center; gap: 8px; -webkit-app-region: no-drag; }
    .win-traffic { display: flex; align-items: center; gap: 7px; }
    .win-traffic-btn {
      width: 13px; height: 13px; border-radius: 50%; border: none; cursor: pointer;
      display: flex; align-items: center; justify-content: center;
      transition: filter 0.15s; flex-shrink: 0;
    }
    .win-traffic-btn:hover { filter: brightness(1.15); }
    .win-traffic-btn:active { filter: brightness(0.9); }
    .win-traffic-btn .win-traffic-icon {
      font-size: 8px; line-height: 1; opacity: 0; transition: opacity 0.15s;
      color: rgba(0,0,0,0.5); pointer-events: none;
    }
    .win-traffic-btn:hover .win-traffic-icon { opacity: 1; }
    .win-btn-close { background: #ff5f57; box-shadow: inset 0 0 0 0.5px rgba(0,0,0,0.08); }
    .win-btn-close:hover { background: #ff3b30; }
    .win-btn-min { background: #ffcc00; box-shadow: inset 0 0 0 0.5px rgba(0,0,0,0.08); }
    .win-btn-min:hover { background: #e6b800; }
    .win-btn-max { background: #28c840; box-shadow: inset 0 0 0 0.5px rgba(0,0,0,0.08); }
    .win-btn-max:hover { background: #1fb834; }
    .win-back-btn {
      width: 28px; height: 28px; border: 1px solid rgba(56,189,248,0.12);
      border-radius: 7px; background: rgba(56,189,248,0.06); color: rgba(56,189,248,0.6);
      font-size: 14px; cursor: pointer; display: flex; align-items: center; justify-content: center;
      transition: all 0.15s;
    }
    .win-back-btn:hover { background: rgba(56,189,248,0.12); color: #38bdf8; }
  `;
  document.head.appendChild(style);

  // Build the bar
  const title = document.title.replace(' - ANT (AI Note Taker)', '').replace(' - ANT', '') || 'ANT';
  const bar = document.createElement('div');
  bar.className = 'win-controls-bar';
  bar.innerHTML = `
    <div class="win-left">
      <button class="win-back-btn" id="winBackBtn" title="Back to App">&#8592;</button>
      <div class="win-traffic">
        <button class="win-traffic-btn win-btn-close" id="winCloseBtn" title="Close"><span class="win-traffic-icon">&#10005;</span></button>
        <button class="win-traffic-btn win-btn-min" id="winMinBtn" title="Minimize"><span class="win-traffic-icon">&#8722;</span></button>
        <button class="win-traffic-btn win-btn-max" id="winMaxBtn" title="Maximize"><span class="win-traffic-icon">&#43;</span></button>
      </div>
    </div>
    <div class="win-center">${title}</div>
    <div class="win-right"></div>
  `;
  document.body.prepend(bar);

  // Wire up buttons
  document.getElementById('winCloseBtn')?.addEventListener('click', () => window.api.closeWindow());
  document.getElementById('winMinBtn')?.addEventListener('click', () => window.api.minimizeWindow());
  document.getElementById('winMaxBtn')?.addEventListener('click', () => window.api.toggleMaximizeWindow());
  document.getElementById('winBackBtn')?.addEventListener('click', () => {
    window.location.href = 'index.html';
  });

  // ── Fix alignment: push down all fixed/sticky headers and content ──
  // Add body padding for the bar
  document.body.style.paddingTop = BAR_HEIGHT + 'px';

  // Find all fixed/sticky headers at top:0 and offset them
  document.querySelectorAll('*').forEach(el => {
    const cs = getComputedStyle(el);
    const pos = cs.position;
    if ((pos === 'fixed' || pos === 'sticky') && parseInt(cs.top) === 0 && el !== bar) {
      // Skip the controls bar itself
      if (el.closest('.win-controls-bar')) return;
      // Offset the element down by BAR_HEIGHT
      el.style.top = BAR_HEIGHT + 'px';
    }
  });

  // Adjust content padding-top on common content containers
  const contentSelectors = [
    '.study-plan-content', '.interview-content', '.job-content',
    '.resume-content', '.prep-content', '.analytics-content',
    '.cg-body', '.cg-page'
  ];
  contentSelectors.forEach(sel => {
    const el = document.querySelector(sel);
    if (el) {
      const current = parseInt(getComputedStyle(el).paddingTop) || 0;
      el.style.paddingTop = (current + BAR_HEIGHT) + 'px';
    }
  });

  // Fix specific elements known to be at fixed positions near top
  document.querySelectorAll('[style*="position: fixed"], [style*="position:fixed"]').forEach(el => {
    if (el.closest('.win-controls-bar')) return;
    const topMatch = el.style.top?.match(/(\d+)/);
    if (topMatch && parseInt(topMatch[1]) < BAR_HEIGHT) {
      el.style.top = (parseInt(topMatch[1]) + BAR_HEIGHT) + 'px';
    }
  });

  // Remove conflicting -webkit-app-region: drag from page headers
  // (the controls bar is the only drag region now)
  const dragHeaders = document.querySelectorAll(
    '.study-plan-header-fixed, .interview-header-fixed, .job-header-fixed, ' +
    '.resume-header-fixed, .prep-header-fixed, .analytics-header-fixed, .cg-header'
  );
  dragHeaders.forEach(el => {
    el.style.webkitAppRegion = 'no-drag';
  });
})();