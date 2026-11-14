/** Desktop backend endpoint; explicit injection supports isolated renderer tests. */
(function () {
  if (typeof window.__API_URL__ !== 'undefined') {
    window.API_BASE = window.__API_URL__;
  } else if (typeof window.API_BASE === 'undefined') {
    window.API_BASE = 'http://127.0.0.1:8000';
  }
})();
