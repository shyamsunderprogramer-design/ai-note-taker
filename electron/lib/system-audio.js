/**
 * system-audio.js — interviewer-channel capture.
 *
 * Why a helper binary rather than getDisplayMedia: Electron's loopback audio
 * is Windows-only (electron.d.ts, Streams.audio: "Specifying a loopback device
 * will capture system audio, and is currently only supported on Windows"). On
 * macOS the call returns a stream with zero audio tracks, so the interviewer
 * is simply inaudible — fatal when the candidate wears headphones, because
 * then their voice never reaches the microphone either.
 *
 * audiotee (MIT) wraps Core Audio process taps, available since macOS 14.2, in
 * a small universal binary: raw PCM on stdout, JSON logs on stderr.
 *
 * The permission trap: when "System Audio Recording" has not been granted,
 * macOS does not raise an error — it delivers perfectly-formed SILENCE. Left
 * undetected that reads to the user as "no hints, no reason given", which is
 * exactly the failure this project spent a day chasing. SilenceProbe below
 * turns it into an explicit, actionable signal.
 */

const { EventEmitter } = require("events")
const { spawn } = require("child_process")
const fs = require("fs")
const path = require("path")

/** Decides whether a capture stream is carrying real audio or pure silence. */
class SilenceProbe {
  constructor({ sampleRate = 16000, probeMs = 4000 } = {}) {
    this.bytesNeeded = Math.max(1, Math.floor((sampleRate * 2 * probeMs) / 1000))
    this.bytesSeen = 0
    this.peak = 0
    this.settled = false
  }

  /**
   * Feed a PCM chunk. Returns "silent" once enough audio has arrived with no
   * signal at all, "ok" once real signal is seen, otherwise null (undecided).
   */
  push(buf) {
    if (this.settled) return null
    for (let i = 0; i + 1 < buf.length; i += 2) {
      const v = Math.abs(buf.readInt16LE(i))
      if (v > this.peak) this.peak = v
    }
    this.bytesSeen += buf.length
    if (this.peak > 0) {
      this.settled = true
      return "ok"
    }
    if (this.bytesSeen >= this.bytesNeeded) {
      this.settled = true
      return "silent"
    }
    return null
  }
}

/** Locates the audiotee binary in dev, in a workspace, or inside a build. */
function resolveBinary() {
  const candidates = []
  if (process.resourcesPath) {
    candidates.push(path.join(process.resourcesPath, "audiotee"))
  }
  try {
    const pkg = require.resolve("audiotee/package.json")
    candidates.push(path.join(path.dirname(pkg), "bin", "audiotee"))
  } catch {
    /* not resolvable from here — fall through to explicit paths */
  }
  candidates.push(
    path.join(__dirname, "..", "node_modules", "audiotee", "bin", "audiotee"),
    path.join(__dirname, "..", "..", "node_modules", "audiotee", "bin", "audiotee")
  )
  return (
    candidates.find((p) => {
      try {
        fs.accessSync(p, fs.constants.X_OK)
        return true
      } catch {
        return false
      }
    }) || null
  )
}

class SystemAudioCapture extends EventEmitter {
  constructor({ sampleRate = 16000, chunkDuration = 0.1, probeMs = 4000, includeProcesses = [] } = {}) {
    super()
    this.sampleRate = sampleRate
    this.chunkDuration = chunkDuration
    this.probeMs = probeMs
    if (!Array.isArray(includeProcesses) || includeProcesses.some(pid => !Number.isSafeInteger(pid) || pid <= 0)) {
      throw new TypeError("includeProcesses must contain positive integer process IDs")
    }
    this.includeProcesses = [...includeProcesses]
    this.proc = null
    this.probe = null
  }

  isActive() {
    return this.proc !== null
  }

  start() {
    if (this.proc) return true
    if (process.platform !== "darwin") {
      this.emit("error", new Error("system audio capture is macOS-only here"))
      return false
    }
    const bin = resolveBinary()
    if (!bin) {
      this.emit("error", new Error("audiotee binary not found"))
      return false
    }

    this.probe = new SilenceProbe({ sampleRate: this.sampleRate, probeMs: this.probeMs })
    const args = [
      "--sample-rate", String(this.sampleRate),
      "--chunk-duration", String(this.chunkDuration),
    ]
    if (this.includeProcesses.length) args.push("--include-processes", ...this.includeProcesses.map(String))
    this.proc = spawn(bin, args, { stdio: ["ignore", "pipe", "pipe"] })

    this.proc.stdout.on("data", (chunk) => {
      const verdict = this.probe && this.probe.push(chunk)
      if (verdict === "silent") {
        // Not an error state to the OS, but always an error state to the user.
        this.emit("silent")
      }
      this.emit("data", chunk)
    })

    this.proc.stderr.on("data", (buf) => {
      for (const line of buf.toString().split("\n")) {
        if (!line.trim()) continue
        try {
          const msg = JSON.parse(line)
          if (msg.message_type === "error") {
            this.emit("error", new Error(msg.data && msg.data.message))
          }
        } catch {
          /* non-JSON diagnostics from the binary — ignore */
        }
      }
    })

    this.proc.on("error", (err) => {
      this.proc = null
      this.emit("error", err)
    })
    this.proc.on("close", () => {
      this.proc = null
      this.emit("stop")
    })
    return true
  }

  stop() {
    if (!this.proc) return
    try {
      this.proc.kill("SIGTERM")
    } catch {
      /* already gone */
    }
    this.proc = null
    this.probe = null
  }
}

module.exports = { SystemAudioCapture, SilenceProbe, resolveBinary }
