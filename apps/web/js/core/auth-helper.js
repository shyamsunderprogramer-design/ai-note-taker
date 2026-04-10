/**
 * Auth Helper - Shared authentication for standalone pages
 * Manages JWT token storage and automatic injection into fetch calls
 * When loaded, patches global fetch to include auth token on API calls
 */
// Use existing API_BASE if defined, otherwise set default
var API_BASE = typeof API_BASE !== 'undefined' ? API_BASE : 'http://127.0.0.1:8000';

const AuthHelper = {
  TOKEN_KEY: 'ainotetaker_auth_token',

  /** Get the stored auth token */
  getToken() {
    return localStorage.getItem(this.TOKEN_KEY);
  },

  /** Store auth token */
  setToken(token) {
    localStorage.setItem(this.TOKEN_KEY, token);
  },

  /** Clear auth token */
  clearToken() {
    localStorage.removeItem(this.TOKEN_KEY);
  },

  /** Check if user is authenticated */
  isAuthenticated() {
    return !!this.getToken();
  },

  /** Login and store token */
  async login(username, password) {
    const formData = new FormData();
    formData.append('username', username);
    formData.append('password', password);

    const res = await _originalFetch(`${API_BASE}/auth/login`, { method: 'POST', body: formData });
    if (!res.ok) throw new Error('Login failed');
    const data = await res.json();
    if (data.access_token) {
      this.setToken(data.access_token);
    }
    return data;
  },

  /** Register and store token */
  async register(username, email, password) {
    const formData = new FormData();
    formData.append('username', username);
    formData.append('email', email);
    formData.append('password', password);

    const res = await _originalFetch(`${API_BASE}/auth/register`, { method: 'POST', body: formData });
    if (!res.ok) throw new Error('Registration failed');
    const data = await res.json();
    return data;
  },

  /** Get auth headers for fetch calls */
  getAuthHeaders() {
    const token = this.getToken();
    const headers = { 'Content-Type': 'application/json' };
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    return headers;
  },

  /** Authenticated fetch wrapper - includes token and handles 401 */
  async authFetch(url, options = {}) {
    const token = this.getToken();
    if (token) {
      options.headers = {
        ...(options.headers || {}),
        'Authorization': `Bearer ${token}`,
      };
    } else {
      console.warn('[AuthHelper] authFetch called with no token for:', url);
    }
    const res = await _originalFetch(url, options);

    // If token expired, clear it and redirect to login
    if (res.status === 401) {
      this.clearToken();
      throw new Error('Authentication required. Please log in again.');
    }
    return res;
  },

  /** Try auto-login with saved credentials or dev credentials (dev-only) */
  async ensureAuth() {
    if (this.isAuthenticated()) {
      console.log('[AuthHelper] Already authenticated, token exists');
      return true;
    }
    // Auto-login with dev credentials only when explicitly enabled
    const devUser = sessionStorage.getItem('ainotetaker_dev_user');
    const devPass = sessionStorage.getItem('ainotetaker_dev_pass');
    if (devUser && devPass) {
      try {
        console.log('[AuthHelper] Attempting dev auto-login...');
        const result = await this.login(devUser, devPass);
        console.log('[AuthHelper] Dev auto-login successful, token stored:', !!this.getToken());
        return true;
      } catch (e) {
        console.error('[AuthHelper] Dev auto-login failed:', e);
        return false;
      }
    }
    console.warn('[AuthHelper] No stored token and no dev credentials. Please log in manually.');
    return false;
  },
};

// Save original fetch before patching
const _originalFetch = window.fetch.bind(window);

/**
 * Patch global fetch to automatically include auth token on API calls.
 * This ensures ALL fetch calls to the backend include the Authorization header
 * without needing to modify each individual call.
 */
window.fetch = function patchedFetch(url, options = {}) {
  // Only inject auth header for our API calls
  if (typeof url === 'string' && (url.includes('127.0.0.1:8000') || url.includes('localhost:8000') || url.startsWith('/'))) {
    const token = localStorage.getItem(AuthHelper.TOKEN_KEY);
    if (token) {
      options.headers = {
        ...(options.headers || {}),
        'Authorization': `Bearer ${token}`,
      };
    }
  }
  return _originalFetch(url, options);
};

// Make available globally
if (typeof window !== 'undefined') {
  window.AuthHelper = AuthHelper;

  // Auto-login on load: if no token stored, try dev auto-login
  // This ensures standalone pages work seamlessly in development
  document.addEventListener('DOMContentLoaded', () => {
    if (!AuthHelper.isAuthenticated()) {
      AuthHelper.ensureAuth().then(ok => {
        if (!ok) {
          console.warn('[AuthHelper] Auto-login failed. You may need to log in manually.');
        }
      });
    }
  });
}