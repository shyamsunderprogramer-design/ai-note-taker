/**
 * API service for ANT Mobile — connects to the backend server.
 */
import AsyncStorage from "@react-native-async-storage/async-storage"

const DEFAULT_BASE_URL = "http://10.0.2.2:8000" // Android emulator localhost

class ApiService {
  constructor() {
    this.baseUrl = DEFAULT_BASE_URL
    this.token = null
  }

  async init() {
    this.token = await AsyncStorage.getItem("auth_token")
    this.baseUrl = (await AsyncStorage.getItem("api_url")) || DEFAULT_BASE_URL
  }

  async request(endpoint, options = {}) {
    const headers = {
      "Content-Type": "application/json",
      ...(this.token ? { Authorization: `Bearer ${this.token}` } : {}),
      ...options.headers,
    }

    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      ...options,
      headers,
    })

    if (response.status === 401) {
      this.token = null
      await AsyncStorage.removeItem("auth_token")
      throw new Error("Authentication required")
    }

    return response.json()
  }

  // ── Auth ──────────────────────────────────────────────────────────────────

  async login(username, password) {
    const formData = new FormData()
    formData.append("username", username)
    formData.append("password", password)

    const response = await fetch(`${this.baseUrl}/auth/login`, {
      method: "POST",
      body: formData,
    })
    const data = await response.json()

    if (data.access_token) {
      this.token = data.access_token
      await AsyncStorage.setItem("auth_token", this.token)
      return data
    }
    throw new Error(data.detail || "Login failed")
  }

  async register(username, email, password) {
    const formData = new FormData()
    formData.append("username", username)
    formData.append("email", email)
    formData.append("password", password)

    const response = await fetch(`${this.baseUrl}/auth/register`, {
      method: "POST",
      body: formData,
    })
    return response.json()
  }

  async logout() {
    this.token = null
    await AsyncStorage.removeItem("auth_token")
  }

  // ── Conversations ─────────────────────────────────────────────────────────

  async getConversations(limit = 20, offset = 0) {
    return this.request(`/conversations?limit=${limit}&offset=${offset}`)
  }

  async getConversation(id) {
    return this.request(`/conversations/${id}`)
  }

  async deleteConversation(id) {
    return this.request(`/conversations/${id}`, { method: "DELETE" })
  }

  // ── Transcription ─────────────────────────────────────────────────────────

  async startTranscription() {
    return this.request("/transcription/start", { method: "POST" })
  }

  async stopTranscription() {
    return this.request("/transcription/stop", { method: "POST" })
  }

  // ── AI Summary ────────────────────────────────────────────────────────────

  async generateSummary(conversationId) {
    return this.request("/ai/summarize", {
      method: "POST",
      body: JSON.stringify({ conversation_id: conversationId }),
    })
  }

  async generateActionItems(conversationId) {
    return this.request("/ai/action-items", {
      method: "POST",
      body: JSON.stringify({ conversation_id: conversationId }),
    })
  }

  // ── Interview ──────────────────────────────────────────────────────────────

  async getInterviewQuestions(category = "behavioral", limit = 10) {
    return this.request(`/questions/v2/enhanced?category=${category}&limit=${limit}`)
  }

  async startInterviewSession(role, difficulty = "medium") {
    return this.request("/interview-simulator/create", {
      method: "POST",
      body: JSON.stringify({ role, difficulty }),
    })
  }

  // ── Career ──────────────────────────────────────────────────────────────────

  async generateCoverLetter(data) {
    return this.request("/career/cover-letter", {
      method: "POST",
      body: JSON.stringify(data),
    })
  }

  async getInterviewPrep(company) {
    return this.request(`/career/interview-prep/${company}`)
  }

  async getSalaryInsights(data) {
    return this.request("/career/salary-insights", {
      method: "POST",
      body: JSON.stringify(data),
    })
  }

  // ── Video / Clips ──────────────────────────────────────────────────────────

  async createClip(data) {
    return this.request("/video/clips", {
      method: "POST",
      body: JSON.stringify(data),
    })
  }

  async getClips(conversationId) {
    return this.request(`/video/clips/${conversationId}`)
  }

  // ── Health ─────────────────────────────────────────────────────────────────

  async checkHealth() {
    return this.request("/health")
  }

  // ── Settings ────────────────────────────────────────────────────────────────

  async setApiUrl(url) {
    this.baseUrl = url
    await AsyncStorage.setItem("api_url", url)
  }
}

export default new ApiService()