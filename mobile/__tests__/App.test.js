/**
 * App-level smoke test.
 *
 * Verifies the App component (and the navigation stack it owns) renders
 * without throwing under the @testing-library/react-native renderer.
 *
 * This is the standard RN 0.73 jest preset's default test — moved here
 * from the project root that the audit reported as missing. It uses the
 * testing-library's render() which fakes the native bridge via the
 * jest-react-native preset (registered via package.json's "jest" field).
 */

import "react-native"
import React from "react"
import { render } from "@testing-library/react-native"

import App from "../src/App"

describe("App", () => {
  test("renders without crashing", () => {
    // The App component is async-aware (it calls apiService.init() and
    // notificationService.requestPermissions() in effects). We just need
    // the initial render to succeed and the navigator to mount.
    const { UNSAFE_root } = render(<App />)
    expect(UNSAFE_root).toBeTruthy()
  })
})
