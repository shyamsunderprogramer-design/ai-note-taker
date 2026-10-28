/**
 * API service for ANT Mobile — connects to the backend server.
 */
import AsyncStorage from "@react-native-async-storage/async-storage"

const DEFAULT_BASE_URL = "http://10.0.2.2:8000" // Android emulator localhost

export class ApiService {
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
    // Native fetch adds the multipart boundary for file uploads.
    if (options.body instanceof FormData) {
      for (const key of Object.keys(headers)) {
        if (key.toLowerCase() === "content-type") delete headers[key]
      }
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

    const data = await response.json()
    if (!response.ok || data?.status === "error") {
      throw new Error(data?.detail || data?.error?.message || data?.message || `Request failed (${response.status})`)
    }
    return data
  }

  async transcribeAudio(path) {
    if (!path) throw new Error("No recording to upload")
    const uri = /^(file|content):\/\//.test(path) ? path : `file://${path}`
    const extension = path.split(/[?#]/)[0].split(".").pop().toLowerCase()
    const types = { m4a: "audio/mp4", mp4: "audio/mp4", aac: "audio/aac", wav: "audio/wav", mp3: "audio/mpeg", webm: "audio/webm" }
    const form = new FormData()
    form.append("file", {
      uri,
      name: `recording.${types[extension] ? extension : "m4a"}`,
      type: types[extension] || "audio/mp4",
    })
    return this.request("/transcribe", { method: "POST", body: form })
  }

  async listJobs() {
    const user = await this.request("/auth/me")
    const data = await this.request(`/job-tracker/applications?user_id=${encodeURIComponent(user.id)}`)
    return data.applications
  }

  async generateStudyPlan(topic) {
    const user = await this.request("/auth/me")
    const data = await this.request("/study-plan/generate-personalized", {
      method: "POST",
      body: JSON.stringify({ user_id: String(user.id), target_role: topic }),
    })
    return {
      ...data,
      steps: (data.sessions || []).flatMap(session =>
        (session.tasks || []).map(task => `${session.date}: ${task.title} — ${task.description}`)),
    }
  }

  async getAnalytics() {
    const user = await this.request("/auth/me")
    return this.request(`/analytics/dashboard/${encodeURIComponent(user.id)}`)
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
