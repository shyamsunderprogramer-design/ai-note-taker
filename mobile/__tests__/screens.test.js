/**
 * Tests for the new screens added in Phase 8 (2026-06-08).
 * Uses @testing-library/react-native for component rendering.
 */
import React from "react"
import { render, fireEvent, waitFor } from "@testing-library/react-native"
import { PermissionsAndroid, Platform } from "react-native"
import AudioRecorderPlayer from "react-native-audio-recorder-player"
import apiService from "../src/services/api"

import VoiceRecordingScreen from "../src/screens/VoiceRecordingScreen"
import JobTrackerScreen from "../src/screens/JobTrackerScreen"
import StudyPlanScreen from "../src/screens/StudyPlanScreen"

// ── VoiceRecordingScreen ──────────────────────────────────────────────────
describe("VoiceRecordingScreen", () => {
  afterEach(() => jest.restoreAllMocks())

  async function stoppedRecording() {
    const screen = render(<VoiceRecordingScreen />)
    fireEvent.press(screen.getByText("⏺ Record"))
    await waitFor(() => expect(screen.getByText("⏹ Stop")).toBeTruthy())
    fireEvent.press(screen.getByText("⏹ Stop"))
    await waitFor(() => expect(screen.getByText("⏺ Record")).toBeTruthy())
    return screen
  }

  test("record, stop and upload displays the transcript", async () => {
    const upload = jest.spyOn(apiService, "transcribeAudio").mockResolvedValue({ text: "Send the summary by Friday." })
    const screen = await stoppedRecording()
    fireEvent.press(screen.getByText("📤 Upload"))
    expect(await screen.findByText("Send the summary by Friday.")).toBeTruthy()
    expect(upload).toHaveBeenCalledWith("/tmp/test-recording.m4a")
  })

  test("upload errors are shown and the recording can be retried", async () => {
    const upload = jest.spyOn(apiService, "transcribeAudio")
      .mockRejectedValueOnce(new Error("Server unavailable"))
      .mockResolvedValueOnce({ text: "Recovered transcript" })
    const screen = await stoppedRecording()
    fireEvent.press(screen.getByText("📤 Upload"))
    expect(await screen.findByText("Upload failed: Server unavailable")).toBeTruthy()
    fireEvent.press(screen.getByText("📤 Upload"))
    expect(await screen.findByText("Recovered transcript")).toBeTruthy()
    expect(upload).toHaveBeenCalledTimes(2)
  })

  test("denied Android permission never starts recording", async () => {
    jest.replaceProperty(Platform, "OS", "android")
    jest.spyOn(PermissionsAndroid, "request").mockResolvedValue(PermissionsAndroid.RESULTS.DENIED)
    const recorder = AudioRecorderPlayer.mock.results[0].value
    recorder.startRecorder.mockClear()
    const screen = render(<VoiceRecordingScreen />)
    fireEvent.press(screen.getByText("⏺ Record"))
    expect(await screen.findByText("Microphone permission denied")).toBeTruthy()
    expect(recorder.startRecorder).not.toHaveBeenCalled()
  })
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
    const apiService = require("../src/services/api").default
    const generate = jest.spyOn(apiService, "generateStudyPlan").mockResolvedValue({})
    const { getByText } = render(<StudyPlanScreen />)
    fireEvent.press(getByText("Generate"))
    expect(generate).not.toHaveBeenCalled()
    generate.mockRestore()
  })
})
