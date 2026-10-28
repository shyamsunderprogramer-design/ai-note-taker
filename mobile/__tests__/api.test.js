/** API service smoke and backend response contract tests. Native storage is mocked in jest.setup.js. */

import { ApiService } from "../src/services/api"

describe("ApiService", () => {
  let svc

  beforeEach(() => {
    svc = new ApiService()
  })

  test("constructs with no args", () => {
    expect(svc).toBeInstanceOf(ApiService)
  })

  test("default base URL is the Android emulator loopback", () => {
    // 10.0.2.2 is the Android emulator's alias for the host machine's
    // loopback interface. This is the URL the RN debug build hits when
    // it wants to talk to a backend running on the developer's laptop.
    expect(svc.baseUrl).toBe("http://10.0.2.2:8000")
  })

  test("starts with no auth token", () => {
    expect(svc.token).toBeNull()
  })

  test("exposes the public methods we use from screens", () => {
    for (const method of ["request", "init", "login", "logout"]) {
      expect(typeof svc[method]).toBe("function")
    }
  })
})

describe("backend response handling", () => {
  const originalFetch = global.fetch
  afterEach(() => { global.fetch = originalFetch })

  test("recording upload sends multipart audio with auth and a native boundary", async () => {
    global.fetch = jest.fn().mockResolvedValue({ status: 200, ok: true, json: async () => ({ text: "Meeting notes" }) })
    const api = new ApiService()
    api.token = "test-token"
    expect(await api.transcribeAudio("/tmp/voice.m4a")).toEqual({ text: "Meeting notes" })
    const [url, options] = global.fetch.mock.calls[0]
    expect(url).toContain("/transcribe")
    expect(options.headers.Authorization).toBe("Bearer test-token")
    expect(options.headers["Content-Type"]).toBeUndefined()
    expect(options.body.getParts()[0]).toMatchObject({ uri: "file:///tmp/voice.m4a", type: "audio/mp4" })
  })

  test("HTTP failures reject instead of rendering an error object as data", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      status: 503, ok: false, json: async () => ({ detail: "Service unavailable" }),
    })
    await expect(new ApiService().request("/analytics/summary")).rejects.toThrow("Service unavailable")
  })

  test("jobs use the authenticated identity and unwrap the application list", async () => {
    const jobs = [{ id: "job-1", company: "Example" }]
    global.fetch = jest.fn()
      .mockResolvedValueOnce({ status: 200, ok: true, json: async () => ({ id: "user-42" }) })
      .mockResolvedValueOnce({ status: 200, ok: true, json: async () => ({ applications: jobs }) })
    const api = new ApiService()
    api.token = "test-token"
    expect(await api.listJobs()).toEqual(jobs)
    expect(global.fetch.mock.calls[1][0]).toContain("user_id=user-42")
    expect(global.fetch.mock.calls[1][1].headers.Authorization).toBe("Bearer test-token")
  })

  test("study sessions become visible steps", async () => {
    global.fetch = jest.fn()
      .mockResolvedValueOnce({ status: 200, ok: true, json: async () => ({ id: "user-42" }) })
      .mockResolvedValueOnce({ status: 200, ok: true, json: async () => ({
        sessions: [{ date: "2026-09-13", tasks: [{ title: "Practice", description: "Solve a problem" }] }],
      }) })
    expect((await new ApiService().generateStudyPlan("Engineer")).steps)
      .toEqual(["2026-09-13: Practice — Solve a problem"])
  })

  test("analytics is requested for the authenticated user", async () => {
    global.fetch = jest.fn()
      .mockResolvedValueOnce({ status: 200, ok: true, json: async () => ({ id: "user-42" }) })
      .mockResolvedValueOnce({ status: 200, ok: true, json: async () => ({ summary: { total_interviews: 3 } }) })
    expect((await new ApiService().getAnalytics()).summary.total_interviews).toBe(3)
    expect(global.fetch.mock.calls[1][0]).toContain("/analytics/dashboard/user-42")
  })
})
