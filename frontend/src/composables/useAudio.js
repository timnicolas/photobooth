// Shared single AudioContext for the whole app.
// Must be created/resumed during a user gesture (browser autoplay policy).
//
// iOS / iPadOS specifics:
// - Web Audio plays in the "ambient" audio session by default, which is muted when the
//   iPad is in silent mode (Control Center bell / side switch). We switch the page to
//   the "playback" session so the beeps play regardless.
// - The context can become "interrupted" (screen lock, app switch, Siri…) and must be
//   resumed from a later user gesture.
// - Only touchend / click count as a user activation for audio, not touchstart / pointerdown.
let audioCtx = null
let keepAliveEl = null
let unlockBound = false

// 50 ms of silence, looped on older iOS to keep the page in the "playback" session
const SILENT_WAV = 'data:audio/wav;base64,UklGRrQBAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YZABAACAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICA'

function usePlaybackAudioSession() {
  // Audio Session API (Safari 17+): the clean way
  if (navigator.audioSession) {
    try {
      navigator.audioSession.type = 'playback'
    } catch {}
    return
  }
  // Older iOS: a playing <audio> element switches the page to the "playback" session
  if (!/iPad|iPhone|iPod/.test(navigator.userAgent) &&
      !(navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1)) return
  if (!keepAliveEl) {
    keepAliveEl = new Audio(SILENT_WAV)
    keepAliveEl.loop = true
    keepAliveEl.setAttribute('playsinline', '')
  }
  if (keepAliveEl.paused) keepAliveEl.play().catch(() => {})
}

// Call synchronously from a user gesture handler (click / touchend), before any await.
export function initAudio() {
  try {
    usePlaybackAudioSession()
    if (!audioCtx || audioCtx.state === 'closed') {
      const Ctx = window.AudioContext || window.webkitAudioContext
      if (!Ctx) return
      audioCtx = new Ctx()
    }
    // "suspended" (autoplay policy) or "interrupted" (iOS): both need a resume
    if (audioCtx.state !== 'running') audioCtx.resume().catch(() => {})
    // A 1-sample silent buffer started inside the gesture unlocks output on some iOS versions
    const src = audioCtx.createBufferSource()
    src.buffer = audioCtx.createBuffer(1, 1, audioCtx.sampleRate)
    src.connect(audioCtx.destination)
    src.start(0)
  } catch {}
}

// Returns the shared AudioContext (or null if not yet unlocked).
export function getAudioCtx() {
  return audioCtx
}

// Unlocks / resumes audio on every user interaction where it is not running yet.
// Not one-shot: on iOS the context can be interrupted again at any time.
// Useful on views without an explicit gesture (e.g. the printer error banner).
export function bindAudioUnlock() {
  if (unlockBound) return
  unlockBound = true
  const unlock = () => {
    if (!audioCtx || audioCtx.state !== 'running') initAudio()
  }
  for (const ev of ['touchend', 'click', 'keydown']) {
    document.addEventListener(ev, unlock, { capture: true, passive: true })
  }
}

export function playBeep(freq = 880, duration = 120, volume = 0.25) {
  if (!audioCtx) return
  try {
    const osc = audioCtx.createOscillator()
    const gain = audioCtx.createGain()
    osc.connect(gain)
    gain.connect(audioCtx.destination)
    osc.type = 'sine'
    osc.frequency.value = freq
    gain.gain.setValueAtTime(volume, audioCtx.currentTime)
    gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + duration / 1000)
    osc.start()
    osc.stop(audioCtx.currentTime + duration / 1000)
  } catch {}
}
