/**
 * platform-class.js — runs in <head> of every page that needs
 * platform-specific CSS (e.g. hiding duplicate traffic lights on macOS).
 *
 * Extracted from index.html's inline <script> so the CSP can drop
 * 'unsafe-inline' (Phase 6 cleanup, 2026-06-08).
 *
 * Loaded synchronously in <head> so the class is set before the
 * first paint — no FOUC.
 */
(function () {
  if (
    navigator.userAgent.includes('Mac') ||
    navigator.platform === 'MacIntel' ||
    navigator.platform === 'MacPPC'
  ) {
    document.body.classList.add('platform-darwin');
  } else {
    document.body.classList.add('platform-other');
  }
})();
