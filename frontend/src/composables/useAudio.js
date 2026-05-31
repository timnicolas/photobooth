// Shared single AudioContext for the whole app.
// Must be created/resumed during a user gesture (browser autoplay policy).
let audioCtx = null
let unlockBound = false

export function initAudio() {
  try {
    if (!audioCtx || audioCtx.state === 'closed') {
      audioCtx = new AudioContext()
    } else if (audioCtx.state === 'suspended') {
      audioCtx.resume()
    }
  } catch {}
}

// Returns the shared AudioContext (or null if not yet unlocked).
export function getAudioCtx() {
  return audioCtx
}

// Attaches a one-shot listener that unlocks audio on the first user interaction.
// Useful on views without an explicit gesture (e.g. the gallery).
export function unlockAudioOnce() {
  if (unlockBound) return
  unlockBound = true
  const unlock = () => {
    initAudio()
    document.removeEventListener('pointerdown', unlock)
    document.removeEventListener('touchstart', unlock)
  }
  document.addEventListener('pointerdown', unlock, { once: true })
  document.addEventListener('touchstart', unlock, { once: true })
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
