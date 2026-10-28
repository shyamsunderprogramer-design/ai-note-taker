/**
 * VoiceRecordingScreen — record audio via the device mic and
 * upload the file to the backend for transcription.
 *
 * Uses react-native-audio-recorder-player (cross-platform, well
 * maintained). On Android, the app must request RECORD_AUDIO
 * permission first — see android/app/src/main/AndroidManifest.xml.
 */
import React, { useState, useRef, useEffect } from "react"
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ActivityIndicator,
  Alert,
  PermissionsAndroid,
  Platform,
} from "react-native"
import AudioRecorderPlayer from "react-native-audio-recorder-player"
import apiService from "../services/api"

const audioRecorderPlayer = new AudioRecorderPlayer()

export default function VoiceRecordingScreen() {
  const [isRecording, setIsRecording] = useState(false)
  const [isUploading, setIsUploading] = useState(false)
  const [durationMs, setDurationMs] = useState(0)
  const [audioPath, setAudioPath] = useState(null)
  const [error, setError] = useState(null)
  const [transcript, setTranscript] = useState(null)
  const [isTransitioning, setIsTransitioning] = useState(false)
  const activeRef = useRef(false)
  const busyRef = useRef(false)
  const mountedRef = useRef(true)

  useEffect(() => {
    mountedRef.current = true
    return () => {
      mountedRef.current = false
      audioRecorderPlayer.removeRecordBackListener()
      if (activeRef.current) {
        activeRef.current = false
        audioRecorderPlayer.stopRecorder().catch(() => {})
      }
    }
  }, [])

  const requestMicPermission = async () => {
    if (Platform.OS !== "android") return true
    try {
      const granted = await PermissionsAndroid.request(
        PermissionsAndroid.PERMISSIONS.RECORD_AUDIO,
        {
          title: "Microphone Permission",
          message: "ANT needs microphone access to record audio.",
          buttonPositive: "OK",
        }
      )
      return granted === PermissionsAndroid.RESULTS.GRANTED
    } catch (err) {
      return false
    }
  }

  const handleStart = async () => {
    if (busyRef.current || activeRef.current) return
    busyRef.current = true
    setIsTransitioning(true)
    setError(null)
    try {
      const ok = await requestMicPermission()
      if (!mountedRef.current) return
      if (!ok) {
        setError("Microphone permission denied")
        return
      }
      const path = await audioRecorderPlayer.startRecorder()
      if (!mountedRef.current) {
        await audioRecorderPlayer.stopRecorder()
        return
      }
      activeRef.current = true
      setAudioPath(path)
      setDurationMs(0)
      setTranscript(null)
      setIsRecording(true)
      audioRecorderPlayer.addRecordBackListener((e) => {
        setDurationMs(e.currentPosition)
      })
    } catch (err) {
      if (mountedRef.current) setError(`Failed to start recording: ${err.message}`)
    } finally {
      busyRef.current = false
      if (mountedRef.current) setIsTransitioning(false)
    }
  }

  const handleStop = async () => {
    if (!activeRef.current || busyRef.current) return
    busyRef.current = true
    setIsTransitioning(true)
    try {
      const result = await audioRecorderPlayer.stopRecorder()
      activeRef.current = false
      audioRecorderPlayer.removeRecordBackListener()
      if (!mountedRef.current) return
      setIsRecording(false)
      setAudioPath(result)
    } catch (err) {
      if (mountedRef.current) setError(`Failed to stop recording: ${err.message}`)
    } finally {
      busyRef.current = false
      if (mountedRef.current) setIsTransitioning(false)
    }
  }

  const handleUpload = async () => {
    if (!audioPath) {
      Alert.alert("No recording", "Record audio first before uploading.")
      return
    }
    setIsUploading(true)
    setError(null)
    try {
      const result = await apiService.transcribeAudio(audioPath)
      if (mountedRef.current) setTranscript(result.text || "No speech detected. Try recording again.")
    } catch (err) {
      if (mountedRef.current) setError(`Upload failed: ${err.message}`)
    } finally {
      if (mountedRef.current) setIsUploading(false)
    }
  }

  const formatDuration = (ms) => {
    const totalSec = Math.floor(ms / 1000)
    const m = Math.floor(totalSec / 60)
    const s = totalSec % 60
    return `${m}:${s.toString().padStart(2, "0")}`
  }

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Voice Recording</Text>
      <Text style={styles.subtitle}>
        {isRecording
          ? `Recording... ${formatDuration(durationMs)}`
          : audioPath
            ? `Stopped at ${formatDuration(durationMs)}`
            : "Tap record to start"}
      </Text>

      {error && <Text style={styles.error}>{error}</Text>}
      {transcript !== null && <Text selectable style={styles.transcript}>{transcript}</Text>}

      <View style={styles.controls}>
        <TouchableOpacity
          style={[styles.button, isRecording && styles.buttonRecording]}
          onPress={isRecording ? handleStop : handleStart}
          disabled={isUploading || isTransitioning}
        >
          <Text style={styles.buttonText}>
            {isRecording ? "⏹ Stop" : "⏺ Record"}
          </Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.button, styles.uploadButton]}
          onPress={handleUpload}
          disabled={!audioPath || isRecording || isUploading || isTransitioning}
        >
          {isUploading ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text style={styles.buttonText}>📤 Upload</Text>
          )}
        </TouchableOpacity>
      </View>

      <Text style={styles.hint}>
        Recorded audio is stored locally until uploaded. Files are
        deleted after a successful upload.
      </Text>
    </View>
  )
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 24,
    backgroundColor: "#0f172a",
  },
  title: {
    fontSize: 24,
    fontWeight: "700",
    color: "#fff",
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 16,
    color: "#94a3b8",
    marginBottom: 24,
  },
  error: {
    color: "#f87171",
    marginBottom: 16,
  },
  transcript: { color: "#fff", marginBottom: 16 },
  controls: {
    flexDirection: "row",
    gap: 12,
    marginBottom: 24,
  },
  button: {
    backgroundColor: "#3b82f6",
    padding: 16,
    borderRadius: 8,
    flex: 1,
    alignItems: "center",
  },
  buttonRecording: {
    backgroundColor: "#ef4444",
  },
  uploadButton: {
    backgroundColor: "#10b981",
  },
  buttonText: {
    color: "#fff",
    fontSize: 16,
    fontWeight: "600",
  },
  hint: {
    color: "#64748b",
    fontSize: 12,
    marginTop: 16,
  },
})
