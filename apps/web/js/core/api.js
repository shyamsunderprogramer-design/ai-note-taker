/**
 * API - Backend communication layer
 * Wraps Electron IPC and HTTP calls
 */

const API_BASE = typeof window.API_BASE !== 'undefined' ? window.API_BASE : 'http://127.0.0.1:8000';

class APIClient {
  constructor() {
    this.connected = false;
    this.checkInterval = null;
  }

  /**
   * Check if backend is healthy
   * @returns {Promise<boolean>}
   */
  async checkHealth() {
    try {
      const response = await fetch(`${API_BASE}/health`, {
        method: 'GET',
        signal: AbortSignal.timeout(5000)
      });
      this.connected = response.ok;
      return response.ok;
    } catch {
      this.connected = false;
      return false;
    }
  }

  /**
   * Start health checking
   * @param {function} onStatusChange - Callback when status changes
   * @param {number} interval - Check interval in ms
   */
  startHealthCheck(onStatusChange, interval = 5000) {
    if (this.checkInterval) return;

    const check = async () => {
      const wasConnected = this.connected;
      const isConnected = await this.checkHealth();

      if (wasConnected !== isConnected) {
        onStatusChange(isConnected ? 'ready' : 'error');
      }
    };

    this.checkInterval = setInterval(check, interval);
    check(); // Initial check
  }

  /**
   * Stop health checking
   */
  stopHealthCheck() {
    if (this.checkInterval) {
      clearInterval(this.checkInterval);
      this.checkInterval = null;
    }
  }

  /**
   * Send a message to the backend
   * @param {Object} params - Message parameters
   * @returns {Promise<Response>}
   */
  async sendMessage(params) {
    const response = await fetch(`${API_BASE}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params)
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    return response;
  }

  /**
   * Get conversation list
   * @returns {Promise<Array>}
   */
  async getConversations() {
    try {
      const response = await fetch(`${API_BASE}/conversations`);
      return response.ok ? await response.json() : [];
    } catch {
      return [];
    }
  }

  /**
   * Load a specific conversation
   * @param {string} id - Conversation ID
   * @returns {Promise<Object|null>}
   */
  async loadConversation(id) {
    try {
      const response = await fetch(`${API_BASE}/conversations/${id}`);
      return response.ok ? await response.json() : null;
    } catch {
      return null;
    }
  }

  /**
   * Save conversation
   * @param {Object} conversation - Conversation data
   * @returns {Promise<boolean>}
   */
  async saveConversation(conversation) {
    try {
      const response = await fetch(`${API_BASE}/conversations`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(conversation)
      });
      return response.ok;
    } catch {
      return false;
    }
  }

  /**
   * Get documents list
   * @returns {Promise<Array>}
   */
  async getDocuments() {
    try {
      const headers = this._authHeaders();
      const response = await fetch(`${API_BASE}/documents`, { headers });
      return response.ok ? await response.json() : [];
    } catch {
      return [];
    }
  }

  /**
   * Get analytics data
   * @returns {Promise<Object>}
   */
  async getAnalytics() {
    try {
      const headers = this._authHeaders();
      const response = await fetch(`${API_BASE}/analytics/summary`, { headers });
      return response.ok ? await response.json() : {};
    } catch {
      return {};
    }
  }

  // ── Integration API Methods ──────────────────────────────────────────

  /**
   * Authenticated fetch helper — adds auth headers, JSON body, error handling
   */
  async _authFetch(url, options = {}) {
    const headers = { ...this._authHeaders(), ...(options.headers || {}) };
    if (options.body && typeof options.body === 'object' && !(options.body instanceof FormData)) {
      headers['Content-Type'] = 'application/json';
      options.body = JSON.stringify(options.body);
    }
    options.headers = headers;
    const response = await fetch(url, options);
    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(err.detail || `HTTP ${response.status}`);
    }
    return response.json();
  }

  /** Get integration status */
  async getIntegrationStatus(type) {
    try {
      return await this._authFetch(`${API_BASE}/${type}/status`);
    } catch { return { connected: false }; }
  }

  /** Configure an integration */
  async configureIntegration(type, config) {
    if (type === 'slack') {
      const params = new URLSearchParams({
        webhook_url: config.webhook_url || '',
        default_channel: config.default_channel || '',
        auto_post: String(config.auto_post || false),
      });
      return await this._authFetch(`${API_BASE}/slack/configure?${params}`, { method: 'POST' });
    }
    if (type === 'calendar') {
      const params = new URLSearchParams({
        provider: config.provider || 'google',
        auto_join: String(config.auto_join || false),
      });
      return await this._authFetch(`${API_BASE}/calendar/configure?${params}`, { method: 'POST' });
    }
    if (type === 'phone') {
      return await this._authFetch(`${API_BASE}/phone/connect`, { method: 'POST', body: config });
    }
    // Notion, Jira, etc. — JSON body to /{type}/connect
    return await this._authFetch(`${API_BASE}/${type}/connect`, { method: 'POST', body: config });
  }

  /** Disconnect an integration */
  async disconnectIntegration(type) {
    return await this._authFetch(`${API_BASE}/${type}/disconnect`, { method: 'DELETE' });
  }

  /** Post a message to Slack */
  async postToSlack(body) {
    return await this._authFetch(`${API_BASE}/slack/post`, { method: 'POST', body });
  }

  /** List Notion pages */
  async listNotionPages(pageSize = 50) {
    return await this._authFetch(`${API_BASE}/notion/pages?page_size=${pageSize}`);
  }

  /** List Jira projects */
  async listJiraProjects() {
    return await this._authFetch(`${API_BASE}/jira/projects`);
  }

  /** Get upcoming calendar meetings */
  async getCalendarUpcoming(hours = 24) {
    return await this._authFetch(`${API_BASE}/calendar/upcoming?hours=${hours}`);
  }

  /** Get SSO status */
  async getSSOStatus() {
    try {
      const resp = await fetch(`${API_BASE}/sso/status`);
      return await resp.json();
    } catch { return { google: { configured: false }, microsoft: { configured: false } }; }
  }

  /** Initiate SSO login */
  async initiateSSO(provider) {
    return await this._authFetch(`${API_BASE}/sso/${provider}`);
  }

  /** Create a team */
  async createTeam(name, description = '') {
    return await this._authFetch(`${API_BASE}/teams`, { method: 'POST', body: { name, description } });
  }

  /** List teams */
  async listTeams() {
    return await this._authFetch(`${API_BASE}/teams`);
  }

  /** Build auth headers from stored token */
  _authHeaders() {
    const token = localStorage.getItem('ainotetaker_auth_token');
    return token ? { 'Authorization': `Bearer ${token}` } : {};
  }
}

// Export singleton
export const API = new APIClient();
