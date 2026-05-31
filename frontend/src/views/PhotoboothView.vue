<template>
  <v-app>
    <!-- Barre de navigation -->
    <v-app-bar color="surface" elevation="1">
      <v-app-bar-title>
        <v-icon color="primary" class="mr-1">mdi-camera-iris</v-icon>
        Photobooth
      </v-app-bar-title>
      <template #append>
        <PrinterMenu />
        <v-btn icon="mdi-refresh" :loading="refreshing" @click="handleRefresh" title="Actualiser" />
        <v-btn icon="mdi-image-multiple" :to="'/gallery'" title="Galerie" />
        <v-btn v-if="auth.isAdmin" icon="mdi-cog" :to="'/admin'" title="Administration" />
      </template>
    </v-app-bar>

    <PrinterErrorBanner />

    <v-main class="overflow-hidden">
      <v-container fluid class="pa-0 h-100 d-flex flex-column">

        <!-- Flux caméra -->
        <div
          class="camera-wrapper"
          @touchstart.passive="onPullStart"
          @touchmove.passive="onPullMove"
          @touchend="onPullEnd"
        >
          <!-- Indicateur pull-to-refresh -->
          <div
            v-if="pullDistance > 0 || refreshing"
            class="pull-indicator"
            :style="{ height: refreshing ? '56px' : `${pullDistance / 2}px` }"
          >
            <v-icon
              color="white"
              size="28"
              :class="refreshing ? 'pull-spinning' : pullDistance >= PULL_THRESHOLD ? 'pull-ready' : ''"
            >mdi-refresh</v-icon>
          </div>

          <!-- Zone croppée au ratio photo (portrait ou paysage) -->
          <div class="camera-crop" :style="{ '--crop-ratio': cropRatio }">
            <canvas
              v-if="!useImgFallback"
              ref="canvasRef"
              class="camera-stream"
            />
            <img
              v-else
              :src="streamImgUrl"
              class="camera-stream"
              style="object-fit: cover;"
              alt="Flux caméra"
              @error="cameraError = true"
              @load="cameraError = false"
            />
            <img
              v-if="maskOverlayUrl"
              :src="maskOverlayUrl"
              class="mask-overlay"
              alt=""
            />
            <div v-if="countdown !== null" class="countdown-overlay d-flex align-center justify-center">
              <span
                :key="countdown"
                class="countdown-number"
                :class="{
                  'countdown-green': countdown === 3,
                  'countdown-orange': countdown === 2,
                  'countdown-red': countdown === 1,
                }"
              >{{ countdown }}</span>
            </div>
            <div v-if="flashVisible" class="camera-flash" />
          </div>

          <div v-if="cameraError" class="camera-placeholder d-flex align-center justify-center">
            <div class="text-center text-medium-emphasis">
              <v-icon size="64">mdi-camera-off</v-icon>
              <div class="mt-2">Caméra indisponible</div>
            </div>
          </div>

          <!-- Panneau de contrôle gauche -->
          <div class="left-controls">
            <v-btn
              icon="mdi-phone-rotate-portrait"
              size="x-large"
              rounded="circle"
              elevation="0"
              color="red"
              variant="elevated"
              @click="toggleOrientation"
            />
            <div style="height: 3rem;"></div>
            <v-btn
              v-if="settingsStore.allowNoMask"
              icon="mdi-image-off-outline"
              size="x-large"
              rounded="circle"
              elevation="0"
              :color="masksStore.activeMask === null ? 'red' : 'black'"
              variant="elevated"
              @click="masksStore.deselectAll()"
            />
            <v-btn
              v-for="mask in masksStore.filteredMasks"
              :key="mask.id"
              icon="mdi-image-outline"
              size="x-large"
              rounded="circle"
              elevation="0"
              :color="masksStore.activeMask?.id === mask.id ? 'red' : 'black'"
              variant="elevated"
              @click="masksStore.selectMask(mask.id)"
            />
          </div>

          <!-- Bouton capture -->
          <div class="capture-overlay">
            <v-btn
              color="primary"
              size="x-large"
              icon="mdi-camera"
              rounded="circle"
              elevation="8"
              :loading="capturing"
              @click="handleCapture"
            />
          </div>
        </div>
      </v-container>
    </v-main>

    <!-- Dialog impression post-capture -->
    <v-dialog v-model="printDialog.show" max-width="500" persistent>
      <v-card>
        <v-card-title class="pt-6 px-6 text-h6 font-weight-bold">
          Votre photo est prête ! 🎉
        </v-card-title>
        <v-card-text class="px-6 pb-4">
          <v-img
            v-if="printDialog.photoId"
            :src="photoFileUrl(printDialog.photoId)"
            max-height="280"
            contain
            rounded="lg"
            class="mb-2 bg-black"
          />
        </v-card-text>
        <v-card-actions class="pa-4 pt-0 d-flex flex-column ga-2">
          <v-btn
            color="primary"
            variant="elevated"
            size="large"
            :min-height="52"
            block
            prepend-icon="mdi-printer"
            :loading="printing"
            @click="handlePrintFromDialog"
          >
            Imprimer
          </v-btn>
          <v-btn
            variant="text"
            size="large"
            :min-height="52"
            block
            @click="printDialog.show = false"
          >
            Non merci
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Snackbar feedback -->
    <v-snackbar v-model="snackbar.show" :color="snackbar.color" :timeout="3000" location="top">
      <v-icon class="mr-2">{{ snackbar.icon }}</v-icon>
      {{ snackbar.message }}
    </v-snackbar>
  </v-app>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useAuthStore } from '../stores/auth'
import { useMasksStore } from '../stores/masks'
import { useSettingsStore } from '../stores/settings'
import { usePrinterStore } from '../stores/printer'
import { getStreamUrl, postCapture } from '../api/camera'
import { printPhoto, photoFileUrl } from '../api/photos'
import PrinterMenu from '../components/PrinterMenu.vue'
import PrinterErrorBanner from '../components/PrinterErrorBanner.vue'
import { initAudio, playBeep, getAudioCtx } from '../composables/useAudio'

const auth = useAuthStore()
const masksStore = useMasksStore()
const settingsStore = useSettingsStore()
const printerStore = usePrinterStore()

const capturing = ref(false)
const printing = ref(false)
const refreshing = ref(false)
const cameraError = ref(false)
const countdown = ref(null)
const flashVisible = ref(false)
const printDialog = ref({ show: false, photoId: null })
const snackbar = ref({ show: false, color: 'success', icon: 'mdi-check', message: '' })
const pullDistance = ref(0)
const PULL_THRESHOLD = 80
let pullStartY = 0

const canvasRef = ref(null)
const useImgFallback = ref(false)
const streamBustKey = ref(0)
let streamAbortController = null
let currentBitmap = null
let resizeObserver = null
// Sérialisation : chaque (re)démarrage incrémente la génération ; les reconnexions
// programmées ne s'exécutent que si elles appartiennent toujours à la génération courante.
let streamGeneration = 0
// Backoff de reconnexion : nombre d'échecs consécutifs depuis la dernière frame reçue.
let streamRetryCount = 0
const MAX_CANVAS_RETRIES = 3
let fallbackHealthTimer = null

function streamApiSupported() {
  return typeof createImageBitmap === 'function' && typeof ReadableStream !== 'undefined'
}

const orientation = computed({
  get: () => masksStore.orientation,
  set: (val) => masksStore.setOrientation(val),
})

const streamUrl = computed(() => getStreamUrl(masksStore.orientation))
const streamImgUrl = computed(() => `${streamUrl.value}&_t=${streamBustKey.value}`)

const cropRatio = computed(() => {
  const w = settingsStore.photoWidthMm
  const h = settingsStore.photoHeightMm
  return orientation.value === 'landscape' ? h / w : w / h
})

const maskOverlayUrl = computed(() =>
  masksStore.activeMask ? `/api/masks/${masksStore.activeMask.id}/file` : null,
)

function drawFrame(bitmap) {
  const canvas = canvasRef.value
  if (!canvas || !bitmap) return
  const ctx = canvas.getContext('2d')
  const cw = canvas.width
  const ch = canvas.height
  if (!cw || !ch) return
  const scale = Math.max(cw / bitmap.width, ch / bitmap.height)
  const sw = bitmap.width * scale
  const sh = bitmap.height * scale
  ctx.drawImage(bitmap, (cw - sw) / 2, (ch - sh) / 2, sw, sh)
}

function stopStream() {
  streamAbortController?.abort()
  streamAbortController = null
  currentBitmap?.close()
  currentBitmap = null
}

// Programme une reconnexion canvas avec backoff exponentiel (2s, 4s, 8s… max 30s).
// Au-delà de MAX_CANVAS_RETRIES échecs consécutifs, bascule sur le fallback <img> ;
// le health-check (setInterval) retentera périodiquement le canvas.
function scheduleReconnect(generation) {
  if (generation !== streamGeneration) return  // une génération plus récente a pris le relais
  if (streamRetryCount >= MAX_CANVAS_RETRIES) {
    useImgFallback.value = true
    return
  }
  const delay = Math.min(2000 * 2 ** streamRetryCount, 30000)
  streamRetryCount++
  setTimeout(() => {
    if (generation === streamGeneration) startStream(true)
  }, delay)
}

async function startStream(isRetry = false) {
  stopStream()
  const generation = ++streamGeneration
  useImgFallback.value = false
  streamBustKey.value = Date.now()
  cameraError.value = false
  if (!isRetry) streamRetryCount = 0

  if (!streamApiSupported()) {
    useImgFallback.value = true
    return
  }

  const controller = new AbortController()
  streamAbortController = controller
  let buf = new Uint8Array(0)
  let rendering = false
  let firstFrameReceived = false

  // Si aucune frame n'arrive dans les 5s (ex. WKWebView PWA qui suspend le réseau à la navigation),
  // on abandonne cette tentative et on programme une reconnexion avec backoff.
  const noFrameTimer = setTimeout(() => {
    if (firstFrameReceived || generation !== streamGeneration) return
    controller.abort()
    scheduleReconnect(generation)
  }, 5000)

  const processFrame = (jpeg) => {
    if (!firstFrameReceived) {
      firstFrameReceived = true
      clearTimeout(noFrameTimer)
      streamRetryCount = 0       // flux rétabli → reset du backoff
      cameraError.value = false  // nettoie l'overlay dès qu'une vraie frame arrive
    }
    if (rendering) return
    rendering = true
    let promise
    try {
      promise = createImageBitmap(new Blob([jpeg], { type: 'image/jpeg' }))
    } catch {
      rendering = false
      return
    }
    promise
      .then(bitmap => {
        if (controller.signal.aborted) { bitmap.close(); return }
        drawFrame(bitmap)
        currentBitmap?.close()
        currentBitmap = bitmap
      })
      .catch(() => {})
      .finally(() => { rendering = false })
  }

  try {
    const res = await fetch(streamUrl.value, { signal: controller.signal })
    if (!res.body) {
      clearTimeout(noFrameTimer)
      useImgFallback.value = true
      return
    }
    const reader = res.body.getReader()
    while (true) {
      const { done, value } = await reader.read()
      if (done) {
        // Le serveur a fermé le flux (redémarrage, etc.) — reconnexion avec backoff
        clearTimeout(noFrameTimer)
        if (!controller.signal.aborted) scheduleReconnect(generation)
        break
      }
      const next = new Uint8Array(buf.length + value.length)
      next.set(buf)
      next.set(value, buf.length)
      buf = next
      if (buf.length > 500_000) buf = buf.slice(-200_000)
      let offset = 0
      while (offset < buf.length - 1) {
        let s = -1
        for (let i = offset; i < buf.length - 1; i++) {
          if (buf[i] === 0xFF && buf[i + 1] === 0xD8) { s = i; break }
        }
        if (s < 0) break
        let e = -1
        for (let i = s + 2; i < buf.length - 1; i++) {
          if (buf[i] === 0xFF && buf[i + 1] === 0xD9) { e = i + 2; break }
        }
        if (e < 0) break
        processFrame(buf.slice(s, e))
        offset = e
      }
      buf = buf.slice(offset)
    }
  } catch (err) {
    clearTimeout(noFrameTimer)
    if (err?.name === 'AbortError') return
    // Erreur réseau / streaming non supporté — reconnexion avec backoff, puis fallback <img>
    scheduleReconnect(generation)
  }
}

watch(streamUrl, () => startStream())

function handleVisibilityChange() {
  if (!document.hidden) startStream()
}

onMounted(async () => {
  await Promise.all([masksStore.fetchMasks(), settingsStore.fetchSettings()])
  printerStore.startPolling()
  startStream()
  resizeObserver = new ResizeObserver(entries => {
    for (const entry of entries) {
      const { inlineSize: w, blockSize: h } = entry.contentBoxSize[0]
      const canvas = canvasRef.value
      if (!canvas || !w || !h) return
      canvas.width = Math.round(w)
      canvas.height = Math.round(h)
      if (currentBitmap) drawFrame(currentBitmap)
    }
  })
  if (canvasRef.value) resizeObserver.observe(canvasRef.value)
  document.addEventListener('visibilitychange', handleVisibilityChange)
  // Health-check : si on est resté coincé sur le fallback <img>, retente le canvas
  // périodiquement (et rafraîchit l'URL <img> au passage via streamBustKey).
  fallbackHealthTimer = setInterval(() => {
    if (useImgFallback.value && !document.hidden) startStream()
  }, 20000)
})

onUnmounted(() => {
  printerStore.stopPolling()
  stopStream()
  clearInterval(fallbackHealthTimer)
  resizeObserver?.disconnect()
  document.removeEventListener('visibilitychange', handleVisibilityChange)
})

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

function playShutter() {
  const audioCtx = getAudioCtx()
  if (!audioCtx) return
  try {
    const sr = audioCtx.sampleRate

    // Couche 1 : claquement mécanique (bruit blanc avec enveloppe percussive)
    const clickLen = Math.floor(sr * 0.06)
    const clickBuf = audioCtx.createBuffer(1, clickLen, sr)
    const clickData = clickBuf.getChannelData(0)
    for (let i = 0; i < clickLen; i++) {
      const env = i < sr * 0.003 ? i / (sr * 0.003) : Math.exp(-i / (sr * 0.015))
      clickData[i] = (Math.random() * 2 - 1) * env * 0.8
    }
    const clickSrc = audioCtx.createBufferSource()
    clickSrc.buffer = clickBuf
    clickSrc.connect(audioCtx.destination)
    clickSrc.start()

    // Couche 2 : "whirr" grave (oscillation basse fréquence rapide)
    const osc = audioCtx.createOscillator()
    const gain = audioCtx.createGain()
    osc.connect(gain)
    gain.connect(audioCtx.destination)
    osc.type = 'square'
    osc.frequency.setValueAtTime(180, audioCtx.currentTime)
    osc.frequency.exponentialRampToValueAtTime(60, audioCtx.currentTime + 0.05)
    gain.gain.setValueAtTime(0.15, audioCtx.currentTime)
    gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.08)
    osc.start()
    osc.stop(audioCtx.currentTime + 0.08)
  } catch {}
}

async function handleCapture() {
  if (capturing.value || countdown.value !== null) return
  initAudio() // doit être appelé avant tout await pour déverrouiller l'audio sur Safari
  for (let i = 5; i >= 1; i--) {
    countdown.value = i
    playBeep(i === 1 ? 1100 : i === 2 ? 990 : 880)
    await sleep(1000)
  }
  countdown.value = null
  playShutter()
  flashVisible.value = true
  setTimeout(() => { flashVisible.value = false }, 350)
  capturing.value = true
  try {
    const result = await postCapture(false, masksStore.orientation)
    if (result?.id) {
      printDialog.value = { show: true, photoId: result.id }
    }
    showSnackbar('success', 'mdi-check-circle', 'Photo capturée !')
  } catch {
    showSnackbar('error', 'mdi-alert-circle', 'Erreur lors de la capture')
  } finally {
    capturing.value = false
  }
}

async function handlePrintFromDialog() {
  if (!printDialog.value.photoId) return
  printing.value = true
  try {
    await printPhoto(printDialog.value.photoId)
    printDialog.value.show = false
    showSnackbar('success', 'mdi-printer-check', 'Demande envoyée')
    setTimeout(async () => {
      await printerStore.refresh()
      if (printerStore.errors.length > 0) {
        showSnackbar('error', 'mdi-printer-alert', printerStore.errors.join(' — '))
      } else {
        showSnackbar('success', 'mdi-printer', 'Impression en cours')
      }
    }, 4000)
  } catch (e) {
    showSnackbar('error', 'mdi-alert-circle', e.response?.data?.error ?? 'Erreur impression')
  } finally {
    printing.value = false
  }
}

async function handleRefresh() {
  if (refreshing.value) return
  refreshing.value = true
  cameraError.value = false
  try {
    await Promise.all([masksStore.fetchMasks(), settingsStore.fetchSettings()])
    startStream()
  } finally {
    refreshing.value = false
    pullDistance.value = 0
  }
}

function onPullStart(e) {
  if (capturing.value || countdown.value !== null || refreshing.value) return
  pullStartY = e.touches[0].clientY
}

function onPullMove(e) {
  if (!pullStartY || refreshing.value) return
  const delta = e.touches[0].clientY - pullStartY
  pullDistance.value = delta > 0 ? Math.min(delta, PULL_THRESHOLD * 2) : 0
}

function onPullEnd() {
  if (pullDistance.value >= PULL_THRESHOLD) {
    handleRefresh()
  } else {
    pullDistance.value = 0
  }
  pullStartY = 0
}

function toggleOrientation() {
  orientation.value = orientation.value === 'portrait' ? 'landscape' : 'portrait'
}

function showSnackbar(color, icon, message) {
  snackbar.value = { show: true, color, icon, message }
}
</script>

<style scoped>
.camera-wrapper {
  position: relative;
  flex: 1 1 0;
  min-height: 0;
  background: #000;
  overflow: hidden;
}

.camera-crop {
  position: absolute;
  top: 0;
  bottom: 0;
  left: 50%;
  transform: translateX(-50%);
  aspect-ratio: var(--crop-ratio);
  overflow: hidden;
}

.camera-stream {
  width: 100%;
  height: 100%;
  display: block;
}

.mask-overlay {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: fill;
  pointer-events: none;
}

.countdown-overlay {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
}

.countdown-number {
  font-size: 20vmin;
  font-weight: 900;
  color: #fff;
  line-height: 1;
  text-shadow: 0 4px 24px rgba(0, 0, 0, 0.6);
  animation: countdown-pop 0.7s cubic-bezier(0.34, 1.56, 0.64, 1) forwards;
}

.countdown-green {
  color: #4caf50;
  text-shadow: 0 0 40px rgba(76, 175, 80, 0.9), 0 4px 24px rgba(0, 0, 0, 0.6);
}

.countdown-orange {
  color: #ff9800;
  text-shadow: 0 0 40px rgba(255, 152, 0, 0.9), 0 4px 24px rgba(0, 0, 0, 0.6);
}

.countdown-red {
  color: #f44336;
  text-shadow: 0 0 40px rgba(244, 67, 54, 0.9), 0 4px 24px rgba(0, 0, 0, 0.6);
}

@keyframes countdown-pop {
  0%   { transform: scale(1.6); opacity: 0; }
  35%  { transform: scale(1.05); opacity: 1; }
  50%  { transform: scale(0.95); opacity: 1; }
  65%  { transform: scale(1.02); opacity: 1; }
  100% { transform: scale(1); opacity: 1; }
}

.camera-flash {
  position: absolute;
  inset: 0;
  background: white;
  pointer-events: none;
  animation: camera-flash 350ms ease-out forwards;
}

@keyframes camera-flash {
  0%   { opacity: 0; }
  20%  { opacity: 1; }
  100% { opacity: 0; }
}

.camera-placeholder {
  position: absolute;
  inset: 0;
}

/* Contrôles gauche et bouton capture */
.left-controls {
  position: absolute;
  left: 6px;
  top: 50%;
  transform: translateY(-50%);
  z-index: 10;
  display: flex;
  flex-direction: column;
  align-items: center;
  max-height: 90%;
  gap: 8px;
  overflow-y: auto;
  scrollbar-width: none;
}

.left-controls::-webkit-scrollbar { display: none; }

.left-controls :deep(.v-btn) {
  overflow: hidden;
}

.capture-overlay {
  position: absolute;
  bottom: calc(16px + env(safe-area-inset-bottom, 0px));
  left: 50%;
  transform: translateX(-50%);
  z-index: 10;
}

/* Pull-to-refresh */
.pull-indicator {
  position: absolute;
  top: 0; left: 0; right: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  z-index: 5;
  transition: height 0.2s ease;
}

.pull-ready { color: #e53935 !important; transform: rotate(180deg); transition: transform 0.2s; }

@keyframes spin { to { transform: rotate(360deg); } }
.pull-spinning { animation: spin 0.7s linear infinite; }

</style>
