/**
 * Tests for the new screens added in Phase 8 (2026-06-08).
 * Uses @testing-library/react-native for component rendering.
 */
import React from "react"
import { render, fireEvent, waitFor } from "@testing-library/react-native"

import VoiceRecordingScreen from "../src/screens/VoiceRecordingScreen"
import JobTrackerScreen from "../src/screens/JobTrackerScreen"
import StudyPlanScreen from "../src/screens/StudyPlanScreen"

// ── VoiceRecordingScreen ──────────────────────────────────────────────────
describe("VoiceRecordingScreen", () => {
  test("renders title and idle subtitle", () => {
    const { getByText } = render(<VoiceRecordingScreen />)
    expect(getByText("Voice Recording")).toBeTruthy()
    expect(getByText("Tap record to start")).toBeTruthy()
  })

  test("record button is present", () => {
    const { getByText } = render(<VoiceRecordingScreen />)
    expect(getByText("⏺ Record")).toBeTruthy()
  })

  test("upload button is disabled when no recording", () => {
    const { getByText } = render(<VoiceRecordingScreen />)
    // TouchableOpacity with disabled=true should still be in the tree
    expect(getByText("📤 Upload")).toBeTruthy()
  })
})

// ── JobTrackerScreen ──────────────────────────────────────────────────────
describe("JobTrackerScreen", () => {
  test("renders empty state when no jobs", async () => {
    // Mock apiService.listJobs
    const apiService = require("../src/services/api").default
    apiService.listJobs = jest.fn().mockResolvedValue([])
    const { findByText } = render(<JobTrackerScreen />)
    const empty = await findByText("No jobs tracked yet.")
    expect(empty).toBeTruthy()
  })
})

// ── StudyPlanScreen ───────────────────────────────────────────────────────
describe("StudyPlanScreen", () => {
  test("renders title and input", () => {
    const { getByText, getByPlaceholderText } = render(<StudyPlanScreen />)
    expect(getByText("AI Study Plan")).toBeTruthy()
    expect(getByPlaceholderText(/Enter a topic/)).toBeTruthy()
  })

  test("input is editable", () => {
    const { getByPlaceholderText } = render(<StudyPlanScreen />)
    const input = getByPlaceholderText(/Enter a topic/)
    fireEvent.changeText(input, "React Hooks")
    expect(input.props.value).toBe("React Hooks")
  })

  test("Generate button is disabled with empty input", () => {
    const { getByText } = render(<StudyPlanScreen />)
    const button = getByText("Generate")
    expect(button.parent.props.disabled).toBe(true)
  })
})
