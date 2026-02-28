<template>
  <v-app>
    <!-- Barre de navigation -->
    <v-app-bar color="surface" elevation="1">
      <v-app-bar-title>
        <v-icon color="primary" class="mr-1">mdi-camera-iris</v-icon>
        Photobooth
      </v-app-bar-title>
      <template #append>
        <v-btn icon="mdi-refresh" :loading="refreshing" @click="handleRefresh" title="Actualiser" />
        <v-btn icon="mdi-image-multiple" :to="'/gallery'" title="Galerie" />
        <v-btn v-if="auth.isAdmin" icon="mdi-cog" :to="'/admin'" title="Administration" />
        <v-btn icon="mdi-logout" @click="logoutDialog = true" title="Déconnexion" />
      </template>
    </v-app-bar>

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

          <img
            :src="streamUrl"
            class="camera-stream"
            alt="Flux caméra"
            @error="cameraError = true"
          />

          <div v-if="cameraError" class="camera-placeholder d-flex align-center justify-center">
            <div class="text-center text-medium-emphasis">
              <v-icon size="64">mdi-camera-off</v-icon>
              <div class="mt-2">Caméra indisponible</div>
            </div>
          </div>
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

        <!-- Sélection masque + capture -->
        <v-sheet color="surface" elevation="4" class="pa-3" style="padding-bottom: max(12px, env(safe-area-inset-bottom))">

          <!-- Ligne 1 : bouton capture -->
          <div class="d-flex align-center justify-center mb-3">
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

          <!-- Ligne 2 : toggle orientation + sélecteur de masques -->
          <div class="d-flex align-center ga-3">
            <!-- Toggle portrait / paysage -->
            <v-btn-toggle
              v-model="orientation"
              mandatory
              color="primary"
              class="flex-shrink-0 orientation-toggle"
            >
              <v-btn value="portrait">
                Portrait
              </v-btn>
              <v-btn value="landscape">
                Paysage
              </v-btn>
            </v-btn-toggle>

            <!-- Sélecteur de masques (filtré par orientation) -->
            <div class="mask-scroll d-flex align-center flex-grow-1">
              <v-chip
                v-if="settingsStore.allowNoMask"
                :variant="masksStore.activeMask === null ? 'elevated' : 'outlined'"
                color="primary"
                class="mr-2 flex-shrink-0"
                @click="masksStore.deselectAll()"
              >
                <v-icon start>mdi-image-filter-none</v-icon>
                Sans filtre
              </v-chip>

              <v-chip
                v-for="mask in masksStore.filteredMasks"
                :key="mask.id"
                :variant="masksStore.activeMask?.id === mask.id ? 'elevated' : 'outlined'"
                color="primary"
                class="mr-2 flex-shrink-0"
                @click="masksStore.selectMask(mask.id)"
              >
                {{ mask.label }}
              </v-chip>
            </div>
          </div>
        </v-sheet>
      </v-container>
    </v-main>

    <!-- Dialog déconnexion -->
    <v-dialog v-model="logoutDialog" max-width="320">
      <v-card>
        <v-card-title class="text-body-1 font-weight-bold pt-5 px-5">Déconnexion</v-card-title>
        <v-card-text class="px-5 pb-2 text-medium-emphasis">Se déconnecter de la session ?</v-card-text>
        <v-card-actions class="pa-4 pt-2">
          <v-spacer />
          <v-btn variant="text" @click="logoutDialog = false">Annuler</v-btn>
          <v-btn color="primary" variant="tonal" @click="auth.logout()">Déconnexion</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

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
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '../stores/auth'
import { useMasksStore } from '../stores/masks'
import { useSettingsStore } from '../stores/settings'
import { getStreamUrl, postCapture } from '../api/camera'
import { printPhoto, photoFileUrl } from '../api/photos'

const auth = useAuthStore()
const masksStore = useMasksStore()
const settingsStore = useSettingsStore()

const capturing = ref(false)
const printing = ref(false)
const refreshing = ref(false)
const logoutDialog = ref(false)
const cameraError = ref(false)
const countdown = ref(null)
const flashVisible = ref(false)
const printDialog = ref({ show: false, photoId: null })
const snackbar = ref({ show: false, color: 'success', icon: 'mdi-check', message: '' })
const pullDistance = ref(0)
const PULL_THRESHOLD = 80
let pullStartY = 0

const orientation = computed({
  get: () => masksStore.orientation,
  set: (val) => masksStore.setOrientation(val),
})

const streamUrl = computed(() =>
  getStreamUrl(masksStore.orientation, masksStore.activeMask?.id ?? null),
)

onMounted(async () => {
  await Promise.all([masksStore.fetchMasks(), settingsStore.fetchSettings()])
})

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

// AudioContext unique réutilisé — doit être créé pendant un geste utilisateur (avant tout await)
let audioCtx = null

function initAudio() {
  try {
    if (!audioCtx || audioCtx.state === 'closed') {
      audioCtx = new AudioContext()
    } else if (audioCtx.state === 'suspended') {
      audioCtx.resume()
    }
  } catch {}
}

function playBeep(freq = 880, duration = 120, volume = 0.25) {
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

function playShutter() {
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
    showSnackbar('success', 'mdi-printer', 'Impression lancée')
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

.camera-stream {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  max-height: 100%;
  max-width: 100%;
  width: auto;
  height: auto;
  display: block;
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

.mask-scroll {
  overflow-x: auto;
  scrollbar-width: none;
  min-width: 0;
}
.mask-scroll::-webkit-scrollbar {
  display: none;
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

/* Touch targets */
.orientation-toggle { min-height: 48px; }
.orientation-toggle :deep(.v-btn) { min-height: 48px; font-size: 15px; padding: 0 20px; touch-action: manipulation; }
.mask-scroll :deep(.v-chip) { min-height: 40px; font-size: 15px; cursor: pointer; touch-action: manipulation; -webkit-tap-highlight-color: transparent; }
</style>
