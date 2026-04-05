/**
 * ANT API Service
 * Backend communication layer
 */

const BASE_URL = 'http://127.0.0.1:8000';

export const API = {
  // Health check
  async checkHealth() {
    try {
      const response = await fetch(`${BASE_URL}/health`, {
        method: 'GET',
        headers: { 'Accept': 'application/json' }
      });
      return response.ok;
    } catch {
      return false;
    }
  },

  // Get streaming URL for AI response
  getStreamUrl(query, options = {}) {
    const {
      mode = 'adaptive',
      style = 'concise',
      provider = 'ollama',
      context = null
    } = options;

    const params = new URLSearchParams({
      q: query,
      mode,
      style,
      provider
    });

    if (context && Array.isArray(context) && context.length > 0) {
      params.append('context', JSON.stringify(context));
    }

    return `${BASE_URL}/stream?${params}`;
  },

  // Get race mode URL (all providers)
  getRaceUrl(query, options = {}) {
    const {
      mode = 'fast',
      style = 'concise',
      context = null
    } = options;

    const params = new URLSearchParams({
      q: query,
      mode,
      style
    });

    if (context && Array.isArray(context) && context.length > 0) {
      params.append('context', JSON.stringify(context));
    }

    return `${BASE_URL}/stream-race?${params}`;
  },

  // Transcribe audio
  async transcribeAudio(audioBlob, options = {}) {
    const formData = new FormData();
    formData.append('audio', audioBlob, 'recording.webm');

    const response = await fetch(`${BASE_URL}/transcribe`, {
      method: 'POST',
      body: formData
    });

    if (!response.ok) {
      throw new Error(`Transcription failed: ${response.statusText}`);
    }

    return response.json();
  },

  // Upload document
  async uploadDocument(file) {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${BASE_URL}/documents/upload`, {
      method: 'POST',
      body: formData
    });

    if (!response.ok) {
      throw new Error(`Upload failed: ${response.statusText}`);
    }

    return response.json();
  },

  // List documents
  async listDocuments() {
    const response = await fetch(`${BASE_URL}/documents`);
    if (!response.ok) throw new Error('Failed to list documents');
    return response.json();
  },

  // Get providers status
  async getProviders() {
    const response = await fetch(`${BASE_URL}/providers`);
    if (!response.ok) throw new Error('Failed to get providers');
    return response.json();
  },

  // Set mode
  async setMode(mode) {
    const response = await fetch(`${BASE_URL}/set-mode?mode=${encodeURIComponent(mode)}`, {
      method: 'POST'
    });
    if (!response.ok) throw new Error('Failed to set mode');
    return response.json();
  },

  // Cognitive graph: Ingest conversation
  async ingestConversation(conversation) {
    try {
      const response = await fetch(`${BASE_URL}/cognitive-graph/ingest/${conversation.id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: conversation.title || 'Untitled',
          user_id: 'default',
          updatedAt: conversation.updatedAt || Date.now(),
          duration_ms: 0,
          messages: conversation.messages || []
        })
      });
      return response.ok;
    } catch {
      return false;
    }
  },

  // Cognitive graph: Query
  async queryGraph(query) {
    try {
      const response = await fetch(`${BASE_URL}/cognitive-graph/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query })
      });
      if (response.ok) {
        return response.json();
      }
      return null;
    } catch {
      return null;
    }
  },

  // Get suggestions
  async getSuggestions(text) {
    try {
      const response = await fetch(`${BASE_URL}/suggestions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text })
      });
      if (response.ok) {
        return response.json();
      }
      return [];
    } catch {
      return [];
    }
  },

  // Analytics: Get summary
  async getAnalyticsSummary(days = 30) {
    try {
      const response = await fetch(`${BASE_URL}/analytics/summary?days=${days}`);
      if (response.ok) {
        return response.json();
      }
      return null;
    } catch {
      return null;
    }
  },

  // Performance: Get checklist
  async getPerformanceChecklist(userId) {
    try {
      const response = await fetch(`${BASE_URL}/performance/checklist/${userId}`);
      if (response.ok) {
        return response.json();
      }
      return null;
    } catch {
      return null;
    }
  },

  // Study plan: Generate
  async generateStudyPlan(userId, options = {}) {
    try {
      const { days = 30, focus_areas = [] } = options;
      const response = await fetch(`${BASE_URL}/study-plan/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId, days, focus_areas })
      });
      if (response.ok) {
        return response.json();
      }
      return null;
    } catch {
      return null;
    }
  }
};

// Conversation storage via Electron IPC
export const ConversationStore = {
  async save(conversation) {
    if (window.api?.conversationSave) {
      return window.api.conversationSave(conversation);
    }
    throw new Error('Conversation API not available');
  },

  async load(id) {
    if (window.api?.conversationLoad) {
      return window.api.conversationLoad(id);
    }
    return null;
  },

  async list() {
    if (window.api?.conversationList) {
      return window.api.conversationList();
    }
    return [];
  },

  async delete(id) {
    if (window.api?.conversationDelete) {
      return window.api.conversationDelete(id);
    }
    return false;
  }
};
