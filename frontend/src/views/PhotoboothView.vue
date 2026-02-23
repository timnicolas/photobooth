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
        <v-btn icon="mdi-logout" @click="auth.logout()" title="Déconnexion" />
      </template>
    </v-app-bar>

    <v-main>
      <v-container fluid class="pa-0 fill-height d-flex flex-column">

        <!-- Flux caméra -->
        <div class="camera-wrapper flex-grow-1">
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
        </div>

        <!-- Sélection masque + capture -->
        <v-sheet color="surface" elevation="4" class="pa-3">

          <!-- Sélecteur de masques -->
          <div class="d-flex align-center mb-3 px-1 mask-scroll">
            <!-- Chip "Aucun masque" -->
            <v-chip
              :variant="masksStore.activeMask === null ? 'elevated' : 'outlined'"
              color="primary"
              class="mr-2 flex-shrink-0"
              @click="masksStore.deselectAll()"
            >
              <v-icon start>mdi-cancel</v-icon>
              Aucun
            </v-chip>

            <v-chip
              v-for="mask in masksStore.masks"
              :key="mask.id"
              :variant="masksStore.activeMask?.id === mask.id ? 'elevated' : 'outlined'"
              color="primary"
              class="mr-2 flex-shrink-0"
              @click="masksStore.selectMask(mask.id)"
            >
              {{ mask.label }}
            </v-chip>
          </div>

          <!-- Bouton capture + switch impression -->
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

    <!-- Snackbar feedback -->
    <v-snackbar v-model="snackbar.show" :color="snackbar.color" :timeout="3000" location="top">
      <v-icon class="mr-2">{{ snackbar.icon }}</v-icon>
      {{ snackbar.message }}
    </v-snackbar>
  </v-app>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useAuthStore } from '../stores/auth'
import { useMasksStore } from '../stores/masks'
import { streamUrl, postCapture } from '../api/camera'

const auth = useAuthStore()
const masksStore = useMasksStore()

const capturing = ref(false)
const shouldPrint = ref(false)
const cameraError = ref(false)
const snackbar = ref({ show: false, color: 'success', icon: 'mdi-check', message: '' })

onMounted(() => masksStore.fetchMasks())

async function handleCapture() {
  capturing.value = true
  try {
    const result = await postCapture(shouldPrint.value)
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
  width: 100%;
  background: #000;
  min-height: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.camera-stream {
  width: 100%;
  height: 100%;
  object-fit: contain;
  display: block;
}

.camera-placeholder {
  position: absolute;
  inset: 0;
}

.mask-scroll {
  overflow-x: auto;
  scrollbar-width: none;
}
.mask-scroll::-webkit-scrollbar {
  display: none;
}
</style>
