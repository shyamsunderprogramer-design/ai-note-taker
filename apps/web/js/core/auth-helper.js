/**
 * Auth Helper - Shared authentication for standalone pages
 * Manages JWT token storage and automatic injection into fetch calls
 * When loaded, patches global fetch to include auth token on API calls
 */
// Use existing API_BASE if defined, otherwise set default
var API_BASE = typeof API_BASE !== 'undefined' ? API_BASE : 'http://127.0.0.1:8000';

const AuthHelper = {
  TOKEN_KEY: 'ainotetaker_auth_token',
  _authRequired: null, // cached auth status

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

  /** Check if the backend requires authentication */
  async isAuthRequired() {
    // Return cached value if known
    if (this._authRequired !== null) return this._authRequired;
    try {
      const resp = await _originalFetch(`${API_BASE}/auth/status`, { signal: AbortSignal.timeout(3000) });
      const data = await resp.json();
      this._authRequired = data.auth_required !== false;
      return this._authRequired;
    } catch (e) {
      // Backend not ready yet — assume auth not required for dev
      console.warn('[AuthHelper] Backend not ready, assuming auth disabled');
      this._authRequired = false;
      return false;
    }
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
  async register(username, email, password, securityQuestion, securityAnswer) {
    const formData = new FormData();
    formData.append('username', username);
    formData.append('email', email);
    formData.append('password', password);
    if (securityQuestion && securityAnswer) {
      formData.append('security_question', securityQuestion);
      formData.append('security_answer', securityAnswer);
    }

    const res = await _originalFetch(`${API_BASE}/auth/register`, { method: 'POST', body: formData });
    if (!res.ok) throw new Error('Registration failed');
    const data = await res.json();
    return data;
  },

  /** Step 1 of forgot password: get security question for username */
  async forgotPassword(username) {
    const formData = new FormData();
    formData.append('username', username);
    const res = await _originalFetch(`${API_BASE}/auth/forgot-password`, { method: 'POST', body: formData });
    if (!res.ok) throw new Error('Failed to process request');
    return await res.json();
  },

  /** Step 2 of forgot password: verify answer and reset password */
  async resetPasswordWithSecurityAnswer(username, securityAnswer, newPassword) {
    const formData = new FormData();
    formData.append('username', username);
    formData.append('security_answer', securityAnswer);
    formData.append('new_password', newPassword);
    const res = await _originalFetch(`${API_BASE}/auth/reset-password`, { method: 'POST', body: formData });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(data.detail || 'Password reset failed');
    }
    return await res.json();
  },

  /** Set or update security question (requires auth) */
  async setSecurityQuestion(securityQuestion, securityAnswer) {
    const formData = new FormData();
    formData.append('security_question', securityQuestion);
    formData.append('security_answer', securityAnswer);
    const res = await _originalFetch(`${API_BASE}/auth/set-security-question`, {
      method: 'POST',
      body: formData,
      headers: { 'Authorization': `Bearer ${this.getToken()}` }
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(data.detail || 'Failed to set security question');
    }
    return await res.json();
  },

  /** Get password strength (0-4) */
  getPasswordStrength(password) {
    let score = 0;
    if (password.length >= 8) score++;
    if (password.length >= 12) score++;
    if (/[A-Z]/.test(password) && /[a-z]/.test(password)) score++;
    if (/[0-9]/.test(password)) score++;
    if (/[^A-Za-z0-9]/.test(password)) score++;
    if (score <= 1) return { level: 'weak', label: 'Weak', score };
    if (score <= 2) return { level: 'fair', label: 'Fair', score };
    if (score <= 3) return { level: 'good', label: 'Good', score };
    return { level: 'strong', label: 'Strong', score };
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

  /** Redirect to dedicated sign-in page or show overlay on standalone pages */
  showLoginOverlay() {
    // If on index.html, redirect to signin.html
    const page = window.location.pathname.split('/').pop() || 'index.html';
    if (page === 'index.html') {
      window.location.href = 'signin.html';
      return;
    }
    // Already on dedicated sign-in page — no overlay needed
    if (page === 'signin.html') {
      return;
    }
    // Don't create duplicate overlays
    if (document.getElementById('auth-login-overlay')) return;

    const overlay = document.createElement('div');
    overlay.id = 'auth-login-overlay';
    overlay.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.85);z-index:99999;display:flex;align-items:center;justify-content:center;font-family:system-ui,sans-serif;';
    overlay.innerHTML = `
      <div style="background:#1e1e2e;border-radius:12px;padding:32px;width:340px;box-shadow:0 20px 60px rgba(0,0,0,0.5);">
        <div style="text-align:center;margin-bottom:20px;">
          <img src="ant-icon-new.png" style="width:60px;height:60px;filter:drop-shadow(0 0 12px rgba(56,189,248,0.5));margin-bottom:12px;" alt="ANT">
          <h2 id="auth-form-title" style="color:#fff;margin:0 0 4px 0;font-size:20px;">Sign In</h2>
          <p id="auth-form-subtitle" style="color:#888;margin:0;font-size:13px;">Welcome back to ANT</p>
        </div>

        <!-- Login form -->
        <div id="auth-login-form">
          <div style="margin-bottom:14px;">
            <label style="color:#aaa;font-size:12px;display:block;margin-bottom:4px;">Username</label>
            <input id="auth-login-user" type="text" style="width:100%;padding:10px 12px;background:#2a2a3a;border:1px solid #444;border-radius:8px;color:#fff;font-size:14px;outline:none;box-sizing:border-box;" placeholder="Enter username">
          </div>
          <div style="margin-bottom:20px;">
            <label style="color:#aaa;font-size:12px;display:block;margin-bottom:4px;">Password</label>
            <input id="auth-login-pass" type="password" style="width:100%;padding:10px 12px;background:#2a2a3a;border:1px solid #444;border-radius:8px;color:#fff;font-size:14px;outline:none;box-sizing:border-box;" placeholder="Enter password">
          </div>
          <div id="auth-login-error" style="color:#ef4444;font-size:12px;margin-bottom:12px;display:none;"></div>
          <button id="auth-login-btn" style="width:100%;padding:12px;background:linear-gradient(135deg,#3b82f6,#8b5cf6);color:#fff;border:none;border-radius:8px;font-size:15px;font-weight:600;cursor:pointer;margin-bottom:8px;">Sign In</button>
          <p style="color:#888;font-size:13px;text-align:center;margin:0 0 4px 0;"><a id="auth-show-forgot" href="#" style="color:#60a5fa;text-decoration:none;font-weight:600;">Forgot password?</a></p>
          <p style="color:#888;font-size:13px;text-align:center;margin:0;">Don't have an account? <a id="auth-show-register" href="#" style="color:#3b82f6;text-decoration:none;font-weight:600;">Register</a></p>
        </div>

        <!-- Register form (hidden by default) -->
        <div id="auth-register-form" style="display:none;">
          <div style="margin-bottom:14px;">
            <label style="color:#aaa;font-size:12px;display:block;margin-bottom:4px;">Username</label>
            <input id="auth-reg-user" type="text" style="width:100%;padding:10px 12px;background:#2a2a3a;border:1px solid #444;border-radius:8px;color:#fff;font-size:14px;outline:none;box-sizing:border-box;" placeholder="Choose a username">
          </div>
          <div style="margin-bottom:14px;">
            <label style="color:#aaa;font-size:12px;display:block;margin-bottom:4px;">Email</label>
            <input id="auth-reg-email" type="email" style="width:100%;padding:10px 12px;background:#2a2a3a;border:1px solid #444;border-radius:8px;color:#fff;font-size:14px;outline:none;box-sizing:border-box;" placeholder="you@example.com">
          </div>
          <div style="margin-bottom:20px;">
            <label style="color:#aaa;font-size:12px;display:block;margin-bottom:4px;">Password</label>
            <input id="auth-reg-pass" type="password" style="width:100%;padding:10px 12px;background:#2a2a3a;border:1px solid #444;border-radius:8px;color:#fff;font-size:14px;outline:none;box-sizing:border-box;" placeholder="Choose a password (8+ chars)">
          </div>
          <div id="auth-reg-error" style="color:#ef4444;font-size:12px;margin-bottom:12px;display:none;"></div>
          <div id="auth-reg-success" style="color:#22c55e;font-size:12px;margin-bottom:12px;display:none;"></div>
          <button id="auth-reg-btn" style="width:100%;padding:12px;background:linear-gradient(135deg,#22c55e,#16a34a);color:#fff;border:none;border-radius:8px;font-size:15px;font-weight:600;cursor:pointer;margin-bottom:12px;">Create Account</button>
          <p style="color:#888;font-size:13px;text-align:center;margin:0;">Already have an account? <a id="auth-show-login" href="#" style="color:#3b82f6;text-decoration:none;font-weight:600;">Sign In</a></p>
        </div>

        <!-- Forgot password form (hidden by default) -->
        <div id="auth-forgot-form" style="display:none;">
          <!-- Step 1: Username -->
          <div id="auth-forgot-step1">
            <div style="margin-bottom:14px;">
              <label style="color:#aaa;font-size:12px;display:block;margin-bottom:4px;">Username</label>
              <input id="auth-forgot-user" type="text" style="width:100%;padding:10px 12px;background:#2a2a3a;border:1px solid #444;border-radius:8px;color:#fff;font-size:14px;outline:none;box-sizing:border-box;" placeholder="Enter your username">
            </div>
            <div id="auth-forgot-error" style="color:#ef4444;font-size:12px;margin-bottom:12px;display:none;"></div>
            <button id="auth-forgot-step1-btn" style="width:100%;padding:12px;background:linear-gradient(135deg,#3b82f6,#8b5cf6);color:#fff;border:none;border-radius:8px;font-size:15px;font-weight:600;cursor:pointer;margin-bottom:12px;">Continue</button>
          </div>
          <!-- Step 2: Security question + answer + new password -->
          <div id="auth-forgot-step2" style="display:none;">
            <div style="margin-bottom:14px;">
              <label style="color:#aaa;font-size:12px;display:block;margin-bottom:4px;">Security Question</label>
              <div id="auth-forgot-question" style="padding:10px 12px;background:rgba(59,130,246,0.1);border:1px solid rgba(59,130,246,0.2);border-radius:8px;color:rgba(255,255,255,0.8);font-size:14px;font-style:italic;"></div>
            </div>
            <div style="margin-bottom:14px;">
              <label style="color:#aaa;font-size:12px;display:block;margin-bottom:4px;">Your Answer</label>
              <input id="auth-forgot-answer" type="text" style="width:100%;padding:10px 12px;background:#2a2a3a;border:1px solid #444;border-radius:8px;color:#fff;font-size:14px;outline:none;box-sizing:border-box;" placeholder="Enter your answer">
            </div>
            <div style="margin-bottom:20px;">
              <label style="color:#aaa;font-size:12px;display:block;margin-bottom:4px;">New Password</label>
              <input id="auth-forgot-newpass" type="password" style="width:100%;padding:10px 12px;background:#2a2a3a;border:1px solid #444;border-radius:8px;color:#fff;font-size:14px;outline:none;box-sizing:border-box;" placeholder="Enter new password (8+ chars)">
            </div>
            <div id="auth-forgot-step2-error" style="color:#ef4444;font-size:12px;margin-bottom:12px;display:none;"></div>
            <div id="auth-forgot-step2-success" style="color:#22c55e;font-size:12px;margin-bottom:12px;display:none;"></div>
            <button id="auth-forgot-step2-btn" style="width:100%;padding:12px;background:linear-gradient(135deg,#3b82f6,#8b5cf6);color:#fff;border:none;border-radius:8px;font-size:15px;font-weight:600;cursor:pointer;margin-bottom:12px;">Reset Password</button>
          </div>
          <!-- No security question set -->
          <div id="auth-forgot-no-question" style="display:none;">
            <div style="padding:16px;background:rgba(234,179,8,0.1);border:1px solid rgba(234,179,8,0.2);border-radius:10px;color:rgba(255,255,255,0.7);font-size:13px;line-height:1.5;margin-bottom:16px;">
              This account has not set up a security question for password recovery. Please contact an administrator or create a new account.
            </div>
            <button id="auth-forgot-back-login" style="width:100%;padding:12px;background:linear-gradient(135deg,#3b82f6,#8b5cf6);color:#fff;border:none;border-radius:8px;font-size:15px;font-weight:600;cursor:pointer;">Back to Sign In</button>
          </div>
          <p style="color:#888;font-size:13px;text-align:center;margin-top:8px;">Remember your password? <a id="auth-show-login-from-forgot" href="#" style="color:#3b82f6;text-decoration:none;font-weight:600;">Sign In</a></p>
        </div>
      </div>
    `;
    document.body.appendChild(overlay);

    // Form switching
    const loginForm = document.getElementById('auth-login-form');
    const registerForm = document.getElementById('auth-register-form');
    const forgotForm = document.getElementById('auth-forgot-form');
    const formTitle = document.getElementById('auth-form-title');
    const formSubtitle = document.getElementById('auth-form-subtitle');

    const showLoginForm = () => {
      loginForm.style.display = 'block';
      registerForm.style.display = 'none';
      forgotForm.style.display = 'none';
      formTitle.textContent = 'Sign In';
      formSubtitle.textContent = 'Welcome back to ANT';
    };

    document.getElementById('auth-show-register').addEventListener('click', (e) => {
      e.preventDefault();
      loginForm.style.display = 'none';
      registerForm.style.display = 'block';
      forgotForm.style.display = 'none';
      formTitle.textContent = 'Create Account';
      formSubtitle.textContent = 'Get started with ANT';
      document.getElementById('auth-reg-user').focus();
    });

    document.getElementById('auth-show-login').addEventListener('click', (e) => {
      e.preventDefault();
      showLoginForm();
      document.getElementById('auth-login-user').focus();
    });

    document.getElementById('auth-show-forgot').addEventListener('click', (e) => {
      e.preventDefault();
      loginForm.style.display = 'none';
      registerForm.style.display = 'none';
      forgotForm.style.display = 'block';
      formTitle.textContent = 'Reset Password';
      formSubtitle.textContent = 'Recover your account';
      document.getElementById('auth-forgot-step1').style.display = 'block';
      document.getElementById('auth-forgot-step2').style.display = 'none';
      document.getElementById('auth-forgot-no-question').style.display = 'none';
      document.getElementById('auth-forgot-user').focus();
    });

    document.getElementById('auth-show-login-from-forgot').addEventListener('click', (e) => {
      e.preventDefault();
      showLoginForm();
      document.getElementById('auth-login-user').focus();
    });

    document.getElementById('auth-forgot-back-login')?.addEventListener('click', (e) => {
      e.preventDefault();
      showLoginForm();
      document.getElementById('auth-login-user').focus();
    });

    // Login
    const loginBtn = document.getElementById('auth-login-btn');
    const userInput = document.getElementById('auth-login-user');
    const passInput = document.getElementById('auth-login-pass');
    const errorDiv = document.getElementById('auth-login-error');

    const doLogin = async () => {
      loginBtn.disabled = true;
      loginBtn.textContent = 'Signing in...';
      errorDiv.style.display = 'none';
      try {
        await AuthHelper.login(userInput.value, passInput.value);
        overlay.remove();
        window.dispatchEvent(new Event('auth-success'));
        setTimeout(() => window.location.reload(), 200);
      } catch (e) {
        errorDiv.textContent = 'Invalid username or password';
        errorDiv.style.display = 'block';
        loginBtn.disabled = false;
        loginBtn.textContent = 'Sign In';
      }
    };
    loginBtn.addEventListener('click', doLogin);
    passInput.addEventListener('keydown', (e) => { if (e.key === 'Enter') doLogin(); });
    userInput.addEventListener('keydown', (e) => { if (e.key === 'Enter') passInput.focus(); });

    // Register
    const regBtn = document.getElementById('auth-reg-btn');
    const regUser = document.getElementById('auth-reg-user');
    const regEmail = document.getElementById('auth-reg-email');
    const regPass = document.getElementById('auth-reg-pass');
    const regError = document.getElementById('auth-reg-error');
    const regSuccess = document.getElementById('auth-reg-success');

    const doRegister = async () => {
      regError.style.display = 'none';
      regSuccess.style.display = 'none';

      if (!regUser.value.trim() || !regEmail.value.trim() || !regPass.value) {
        regError.textContent = 'All fields are required';
        regError.style.display = 'block';
        return;
      }
      if (regPass.value.length < 8) {
        regError.textContent = 'Password must be at least 8 characters';
        regError.style.display = 'block';
        return;
      }

      regBtn.disabled = true;
      regBtn.textContent = 'Creating account...';
      try {
        await AuthHelper.register(regUser.value.trim(), regEmail.value.trim(), regPass.value);
        regSuccess.textContent = 'Account created! Signing you in...';
        regSuccess.style.display = 'block';
        // Auto-login after registration
        try {
          await AuthHelper.login(regUser.value.trim(), regPass.value);
          overlay.remove();
          window.dispatchEvent(new Event('auth-success'));
          setTimeout(() => window.location.reload(), 500);
        } catch (e) {
          // If auto-login fails, switch to login form
          registerForm.style.display = 'none';
          loginForm.style.display = 'block';
          formTitle.textContent = 'Sign In';
          formSubtitle.textContent = 'Welcome back to ANT';
          userInput.value = regUser.value.trim();
          userInput.focus();
        }
      } catch (e) {
        regError.textContent = 'Registration failed. Username may already exist.';
        regError.style.display = 'block';
        regBtn.disabled = false;
        regBtn.textContent = 'Create Account';
      }
    };
    regBtn.addEventListener('click', doRegister);
    regPass.addEventListener('keydown', (e) => { if (e.key === 'Enter') doRegister(); });
    regEmail.addEventListener('keydown', (e) => { if (e.key === 'Enter') regPass.focus(); });
    regUser.addEventListener('keydown', (e) => { if (e.key === 'Enter') regEmail.focus(); });

    // Forgot password - Step 1
    const forgotStep1Btn = document.getElementById('auth-forgot-step1-btn');
    const forgotUser = document.getElementById('auth-forgot-user');
    const forgotError = document.getElementById('auth-forgot-error');

    const doForgotStep1 = async () => {
      const username = forgotUser.value.trim();
      if (!username) {
        forgotError.textContent = 'Username is required';
        forgotError.style.display = 'block';
        return;
      }
      forgotError.style.display = 'none';
      forgotStep1Btn.disabled = true;
      forgotStep1Btn.textContent = 'Looking up...';
      try {
        const result = await AuthHelper.forgotPassword(username);
        if (result.has_security_question) {
          document.getElementById('auth-forgot-question').textContent = result.security_question;
          document.getElementById('auth-forgot-step1').style.display = 'none';
          document.getElementById('auth-forgot-step2').style.display = 'block';
          document.getElementById('auth-forgot-answer').focus();
        } else {
          document.getElementById('auth-forgot-step1').style.display = 'none';
          document.getElementById('auth-forgot-step2').style.display = 'none';
          document.getElementById('auth-forgot-no-question').style.display = 'block';
        }
      } catch (e) {
        forgotError.textContent = 'Failed to process request. Please try again.';
        forgotError.style.display = 'block';
      } finally {
        forgotStep1Btn.disabled = false;
        forgotStep1Btn.textContent = 'Continue';
      }
    };
    forgotStep1Btn.addEventListener('click', doForgotStep1);
    forgotUser.addEventListener('keydown', (e) => { if (e.key === 'Enter') doForgotStep1(); });

    // Forgot password - Step 2
    const forgotStep2Btn = document.getElementById('auth-forgot-step2-btn');
    const forgotAnswer = document.getElementById('auth-forgot-answer');
    const forgotNewPass = document.getElementById('auth-forgot-newpass');
    const forgotStep2Error = document.getElementById('auth-forgot-step2-error');
    const forgotStep2Success = document.getElementById('auth-forgot-step2-success');

    const doForgotStep2 = async () => {
      const answer = forgotAnswer.value.trim();
      const newPass = forgotNewPass.value;
      if (!answer) {
        forgotStep2Error.textContent = 'Security answer is required';
        forgotStep2Error.style.display = 'block';
        return;
      }
      if (newPass.length < 8) {
        forgotStep2Error.textContent = 'Password must be at least 8 characters';
        forgotStep2Error.style.display = 'block';
        return;
      }
      forgotStep2Error.style.display = 'none';
      forgotStep2Btn.disabled = true;
      forgotStep2Btn.textContent = 'Resetting...';
      try {
        await AuthHelper.resetPasswordWithSecurityAnswer(forgotUser.value.trim(), answer, newPass);
        forgotStep2Success.textContent = 'Password reset successfully!';
        forgotStep2Success.style.display = 'block';
        setTimeout(() => {
          showLoginForm();
          document.getElementById('auth-login-user').value = forgotUser.value.trim();
          document.getElementById('auth-login-user').focus();
        }, 1500);
      } catch (e) {
        forgotStep2Error.textContent = e.message || 'Reset failed. Please try again.';
        forgotStep2Error.style.display = 'block';
        forgotStep2Btn.disabled = false;
        forgotStep2Btn.textContent = 'Reset Password';
      }
    };
    forgotStep2Btn.addEventListener('click', doForgotStep2);
    forgotNewPass.addEventListener('keydown', (e) => { if (e.key === 'Enter') doForgotStep2(); });
    forgotAnswer.addEventListener('keydown', (e) => { if (e.key === 'Enter') forgotNewPass.focus(); });

    userInput.focus();
  },

  /** Check auth and show login only if required */
  async ensureAuth() {
    // Already authenticated — done
    if (this.isAuthenticated()) {
      return true;
    }

    // Check if backend requires authentication
    const authRequired = await this.isAuthRequired();
    if (!authRequired) {
      console.log('[AuthHelper] Auth disabled, skipping login');
      window.dispatchEvent(new Event('auth-success'));
      return true;
    }

    // Auth required — auto-login with dev credentials if stored
    const devUser = sessionStorage.getItem('ainotetaker_dev_user');
    const devPass = sessionStorage.getItem('ainotetaker_dev_pass');
    if (devUser && devPass) {
      try {
        await this.login(devUser, devPass);
        return true;
      } catch (e) {
        console.error('[AuthHelper] Dev auto-login failed:', e);
      }
    }

    // Show login overlay
    this.showLoginOverlay();
    return false;
  },
};

// Save original fetch before patching
const _originalFetch = window.fetch.bind(window);

/**
 * Patch global fetch to automatically include auth token on API calls.
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
  // Don't set Content-Type for FormData (browser sets it automatically with boundary)
  if (options.body instanceof FormData && options.headers) {
    delete options.headers['Content-Type'];
  }
  return _originalFetch(url, options).then(response => {
    // Auto-reauth on 401: clear stale token and trigger re-login
    if (response.status === 401 && typeof url === 'string' &&
        (url.includes('127.0.0.1:8000') || url.includes('localhost:8000'))) {
      AuthHelper.clearToken();
      // Check if auth is actually required before showing login
      AuthHelper.isAuthRequired().then(required => {
        if (required) {
          AuthHelper.showLoginOverlay();
        }
      });
    }
    return response;
  });
};

// Make available globally
if (typeof window !== 'undefined') {
  window.AuthHelper = AuthHelper;

  // Auto-check auth on load: skip login if auth disabled
  document.addEventListener('DOMContentLoaded', () => {
    if (!AuthHelper.isAuthenticated()) {
      AuthHelper.ensureAuth();
    }
  });
}