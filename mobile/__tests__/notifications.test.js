/**
 * Smoke test for the NotificationService.
 *
 * Why this exists (Fix #27): see __tests__/api.test.js for the broader
 * rationale. The notifications service is currently a stub (logs to
 * console, returns a fake id) so the test just exercises the stub and
 * ensures the public API surface stays stable.
 */

import NotificationService from "../src/services/notifications"

describe("NotificationService", () => {
  let svc

  beforeEach(() => {
    svc = new NotificationService()
  })

  test("constructs with no args", () => {
    expect(svc).toBeInstanceOf(NotificationService)
  })

  test("requestPermissions resolves to a truthy value", async () => {
    const result = await svc.requestPermissions()
    expect(result).toBeTruthy()
  })

  test("scheduleInterviewReminder returns a stub id", async () => {
    const result = await svc.scheduleInterviewReminder(
      "Senior SWE @ Google",
      new Date("2026-07-01T10:00:00Z"),
    )
    expect(result).toHaveProperty("id")
  })

  test("cancelAll is callable and resolves", async () => {
    await expect(svc.cancelAll()).resolves.toBeUndefined()
  })
})
