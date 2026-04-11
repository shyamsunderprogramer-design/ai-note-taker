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

    // If token expired, clear it and try re-auth
    if (res.status === 401) {
      this.clearToken();
      throw new Error('Authentication required. Please log in again.');
    }
    return res;
  },

  /** Show a login overlay on the page */
  showLoginOverlay() {
    // Don't create duplicate overlays
    if (document.getElementById('auth-login-overlay')) return;

    const overlay = document.createElement('div');
    overlay.id = 'auth-login-overlay';
    overlay.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.85);z-index:99999;display:flex;align-items:center;justify-content:center;font-family:system-ui,sans-serif;';
    overlay.innerHTML = `
      <div style="background:#1e1e2e;border-radius:12px;padding:32px;width:340px;box-shadow:0 20px 60px rgba(0,0,0,0.5);">
        <h2 style="color:#fff;margin:0 0 6px 0;font-size:20px;">Sign In</h2>
        <p style="color:#888;margin:0 0 20px 0;font-size:13px;">Authentication required to access this feature</p>
        <div style="margin-bottom:14px;">
          <label style="color:#aaa;font-size:12px;display:block;margin-bottom:4px;">Username</label>
          <input id="auth-login-user" type="text" style="width:100%;padding:10px 12px;background:#2a2a3a;border:1px solid #444;border-radius:8px;color:#fff;font-size:14px;outline:none;box-sizing:border-box;" placeholder="Enter username">
        </div>
        <div style="margin-bottom:20px;">
          <label style="color:#aaa;font-size:12px;display:block;margin-bottom:4px;">Password</label>
          <input id="auth-login-pass" type="password" style="width:100%;padding:10px 12px;background:#2a2a3a;border:1px solid #444;border-radius:8px;color:#fff;font-size:14px;outline:none;box-sizing:border-box;" placeholder="Enter password">
        </div>
        <div id="auth-login-error" style="color:#ef4444;font-size:12px;margin-bottom:12px;display:none;"></div>
        <button id="auth-login-btn" style="width:100%;padding:12px;background:linear-gradient(135deg,#3b82f6,#8b5cf6);color:#fff;border:none;border-radius:8px;font-size:15px;font-weight:600;cursor:pointer;">Sign In</button>
      </div>
    `;
    document.body.appendChild(overlay);

    const btn = document.getElementById('auth-login-btn');
    const userInput = document.getElementById('auth-login-user');
    const passInput = document.getElementById('auth-login-pass');
    const errorDiv = document.getElementById('auth-login-error');

    const doLogin = async () => {
      btn.disabled = true;
      btn.textContent = 'Signing in...';
      errorDiv.style.display = 'none';
      try {
        await AuthHelper.login(userInput.value, passInput.value);
        overlay.remove();
        // Dispatch event so pages know auth succeeded
        window.dispatchEvent(new Event('auth-success'));
        // Reload page so all initial API calls retry with auth token
        setTimeout(() => window.location.reload(), 200);
      } catch (e) {
        errorDiv.textContent = 'Invalid username or password';
        errorDiv.style.display = 'block';
        btn.disabled = false;
        btn.textContent = 'Sign In';
      }
    };

    btn.addEventListener('click', doLogin);
    passInput.addEventListener('keydown', (e) => { if (e.key === 'Enter') doLogin(); });
    userInput.addEventListener('keydown', (e) => { if (e.key === 'Enter') passInput.focus(); });
    userInput.focus();
  },

  /** Try auto-login with saved credentials or dev credentials (dev-only) */
  async ensureAuth() {
    if (this.isAuthenticated()) {
      return true;
    }
    // Auto-login with dev credentials only when explicitly enabled
    const devUser = sessionStorage.getItem('ainotetaker_dev_user');
    const devPass = sessionStorage.getItem('ainotetaker_dev_pass');
    if (devUser && devPass) {
      try {
        await this.login(devUser, devPass);
        return true;
      } catch (e) {
        console.error('[AuthHelper] Dev auto-login failed:', e);
        return false;
      }
    }
    // No credentials available — show login overlay
    this.showLoginOverlay();
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

  // Auto-login on load: if no token stored, try dev auto-login or show login form
  document.addEventListener('DOMContentLoaded', () => {
    if (!AuthHelper.isAuthenticated()) {
      AuthHelper.ensureAuth();
    }
  });
}