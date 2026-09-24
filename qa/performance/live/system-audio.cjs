// Capture only our synthetic playback process through ANT's production helper.
const { spawn } = require('node:child_process')
const fs = require('node:fs')
const path = require('node:path')
const { SystemAudioCapture } = require('../../../electron/lib/system-audio')

const directory = process.argv[2] || '/tmp/ant-product-benchmark'
const playback = path.join(directory, 'playback.wav')
if (!fs.existsSync(playback)) throw new Error(`Missing fixture: ${playback}`)
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms))

function wav(pcm) {
  const header = Buffer.alloc(44)
  header.write('RIFF'); header.writeUInt32LE(pcm.length + 36, 4); header.write('WAVE', 8)
  header.write('fmt ', 12); header.writeUInt32LE(16, 16); header.writeUInt16LE(1, 20)
  header.writeUInt16LE(1, 22); header.writeUInt32LE(16000, 24); header.writeUInt32LE(32000, 28)
  header.writeUInt16LE(2, 32); header.writeUInt16LE(16, 34)
  header.write('data', 36); header.writeUInt32LE(pcm.length, 40)
  return Buffer.concat([header, pcm])
}

async function main() {
  const errors = [], chunks = []
  let silent = false, playerCode, capture
  const started = Date.now()
  const player = spawn('/usr/bin/afplay', [playback], { stdio: ['ignore', 'ignore', 'pipe'] })
  player.on('error', error => errors.push(error.message))
  player.stderr.on('data', data => errors.push(data.toString()))
  const done = new Promise(resolve => player.once('close', code => { playerCode = code; resolve() }))
  const timeout = setTimeout(() => { player.kill(); capture?.stop() }, 15000)
  try {
    // afplay is already rendering the fixture's silent lead-in when the tap attaches.
    await sleep(700)
    if (!player.pid || player.exitCode !== null) throw new Error('Synthetic player exited before capture')
    capture = new SystemAudioCapture({ includeProcesses: [player.pid], probeMs: 4500 })
    capture.on('data', chunk => chunks.push(chunk))
    capture.on('silent', () => { silent = true })
    capture.on('error', error => errors.push(error.message))
    if (!capture.start()) throw new Error('Capture could not start')
    await done
    await sleep(300)
  } catch (error) {
    errors.push(error.message)
  } finally {
    clearTimeout(timeout)
    capture?.stop()
    if (player.exitCode === null) player.kill()
  }
  const pcm = Buffer.concat(chunks)
  let peak = 0, nonzero = 0
  for (let i = 0; i + 1 < pcm.length; i += 2) {
    const value = Math.abs(pcm.readInt16LE(i))
    peak = Math.max(peak, value)
    if (value) nonzero++
  }
  if (pcm.length) fs.writeFileSync(path.join(directory, 'captured-system-audio.wav'), wav(pcm))
  const report = {
    test: 'ANT system-audio capture of isolated synthetic afplay process',
    elapsedSeconds: (Date.now() - started) / 1000,
    capturedSeconds: pcm.length / 32000, chunks: chunks.length, peak, nonzeroSamples: nonzero,
    silent, playerExitCode: playerCode, errors,
    passed: playerCode === 0 && peak > 0 && pcm.length >= 32000 * 5 && errors.length === 0,
    limits: 'OS loopback test, not a Meet/Zoom call. No microphone or unrelated processes captured.',
  }
  fs.writeFileSync(path.join(directory, 'system-audio-report.json'), JSON.stringify(report, null, 2) + '\n')
  console.log(JSON.stringify(report, null, 2))
  if (!report.passed) process.exitCode = 1
}
main().catch(error => { console.error(error); process.exitCode = 1 })
