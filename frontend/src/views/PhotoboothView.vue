<template>
  <v-app>
    <!-- Barre de navigation -->
    <v-app-bar color="surface" elevation="1">
      <v-app-bar-title>
        <v-icon color="primary" class="mr-1">mdi-camera-iris</v-icon>
        Photobooth
      </v-app-bar-title>
      <template #append>
        <v-btn icon="mdi-image-multiple" :to="'/gallery'" title="Galerie" />
        <v-btn v-if="auth.isAdmin" icon="mdi-cog" :to="'/admin'" title="Administration" />
        <v-btn icon="mdi-logout" @click="logoutDialog = true" title="Déconnexion" />
      </template>
    </v-app-bar>

    <v-main class="overflow-hidden">
      <v-container fluid class="pa-0 h-100 d-flex flex-column">

        <!-- Flux caméra -->
        <div class="camera-wrapper">
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
            <span class="countdown-number">{{ countdown }}</span>
          </div>
        </div>

        <!-- Sélection masque + capture -->
        <v-sheet color="surface" elevation="4" class="pa-3">

          <!-- Ligne 1 : toggle orientation + sélecteur de masques -->
          <div class="d-flex align-center mb-3 ga-2">
            <!-- Toggle portrait / paysage -->
            <v-btn-toggle
              v-model="orientation"
              mandatory
              density="compact"
              color="primary"
              class="flex-shrink-0"
            >
              <v-btn value="portrait" size="small">
                Portrait
              </v-btn>
              <v-btn value="landscape" size="small">
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
                <v-icon start>mdi-cancel</v-icon>
                Aucun
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

          <!-- Ligne 2 : switch impression + bouton capture -->
          <div class="d-flex align-center justify-center ga-4">
            <v-switch
              v-model="shouldPrint"
              color="primary"
              label="Imprimer"
              hide-details
              density="compact"
            />

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

const auth = useAuthStore()
const masksStore = useMasksStore()
const settingsStore = useSettingsStore()

const capturing = ref(false)
const shouldPrint = ref(false)
const logoutDialog = ref(false)
const cameraError = ref(false)
const countdown = ref(null)
const snackbar = ref({ show: false, color: 'success', icon: 'mdi-check', message: '' })

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

async function handleCapture() {
  if (capturing.value || countdown.value !== null) return
  for (let i = 5; i >= 1; i--) {
    countdown.value = i
    await sleep(1000)
  }
  countdown.value = null
  capturing.value = true
  try {
    const result = await postCapture(shouldPrint.value, masksStore.orientation)
    const printed = result.printed ? ' • Impression lancée' : ''
    const printErr = result.print_error ? ` (impression : ${result.print_error})` : ''
    showSnackbar('success', 'mdi-check-circle', `Photo capturée${printed}${printErr}`)
  } catch {
    showSnackbar('error', 'mdi-alert-circle', 'Erreur lors de la capture')
  } finally {
    capturing.value = false
  }
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
  animation: countdown-pop 0.9s ease-out;
}

@keyframes countdown-pop {
  0% { transform: scale(1.4); opacity: 0.6; }
  40% { transform: scale(1); opacity: 1; }
  100% { transform: scale(0.85); opacity: 0.6; }
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
</style>
