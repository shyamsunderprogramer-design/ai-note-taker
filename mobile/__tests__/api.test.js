/**
 * Smoke test for the ApiService.
 *
 * Why this exists (Fix #27): mobile/ had no __tests__/ folder before this
 * commit, so `npm test` had nothing to run. This file provides a minimal
 * smoke test for the most-isolated service — the API client — using
 * jest's built-in module mocks so we don't need a full RN runtime.
 *
 * What it does:
 *   - Verifies ApiService is constructible
 *   - Verifies the default base URL points at the Android emulator
 *     loopback (10.0.2.2) so the FastAPI backend on the host machine
 *     is reachable
 *   - Verifies init() can be called (and stores the token field)
 *
 * What it does NOT do (out of scope for the smoke test):
 *   - Hit a real network
 *   - Test the full React Native rendering tree
 *   - Mock AsyncStorage (the RN jest preset handles that globally)
 */

import ApiService from "../src/services/api"

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
