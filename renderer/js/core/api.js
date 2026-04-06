/**
 * API - Backend communication layer
 * Wraps Electron IPC and HTTP calls
 */

const API_BASE = 'http://localhost:8000';

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
      const response = await fetch(`${API_BASE}/documents`);
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
      const response = await fetch(`${API_BASE}/analytics/summary`);
      return response.ok ? await response.json() : {};
    } catch {
      return {};
    }
  }
}

// Export singleton
export const API = new APIClient();
