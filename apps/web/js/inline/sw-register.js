/**
 * sw-register.js — service-worker registration for PWA install.
 * Skipped in Electron (file:// protocol doesn't support SW).
 *
 * Extracted from index.html's inline <script> so the CSP can drop
 * 'unsafe-inline' (Phase 6 cleanup, 2026-06-08).
 *
 * Run after DOMContentLoaded. Uses the standard navigator.serviceWorker
 * API; no external deps.
 */
(function () {
  if (!('serviceWorker' in navigator)) return;

  // Electron exposes a `window.api` IPC bridge; if present, skip SW.
  if (window.api) {
    console.log('[PWA] Service Worker disabled in Electron app');
    return;
  }

  // Only register under http(s) — file://, blob:, and data: can't host a SW.
  var proto = window.location.protocol;
  if (proto !== 'http:' && proto !== 'https:') return;

  window.addEventListener('load', function () {
    navigator.serviceWorker
      .register('/sw.js')
      .then(function (reg) {
        console.log('[PWA] SW registered:', reg.scope);
      })
      .catch(function (err) {
        console.log('[PWA] SW registration failed:', err);
      });
  });
})();
