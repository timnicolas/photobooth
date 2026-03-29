<template>
  <v-app>
    <v-app-bar color="surface" elevation="1">
      <v-btn icon="mdi-arrow-left" @click="$router.back()" />
      <v-app-bar-title>Administration</v-app-bar-title>
    </v-app-bar>

    <v-main>
      <v-container class="py-6" max-width="800">

        <!-- Section Masques -->
        <v-card class="mb-6">
          <v-card-title class="d-flex align-center">
            <v-icon class="mr-2">mdi-image-filter-frames</v-icon>
            Masques
          </v-card-title>

          <v-card-text>
            <!-- Formulaire upload -->
            <v-row class="align-center mb-4">
              <v-col cols="12" sm="4">
                <v-file-input
                  v-model="maskFile"
                  label="Fichier PNG (avec transparence)"
                  accept=".png"
                  prepend-icon="mdi-file-image"
                  variant="outlined"
                  density="compact"
                  hide-details
                  clearable
                />
              </v-col>
              <v-col cols="12" sm="3">
                <v-text-field
                  v-model="maskLabel"
                  label="Nom du masque (optionnel)"
                  variant="outlined"
                  density="compact"
                  hide-details
                />
              </v-col>
              <v-col cols="12" sm="3">
                <v-select
                  v-model="maskOrientation"
                  :items="orientationOptions"
                  label="Orientation"
                  variant="outlined"
                  density="compact"
                  hide-details
                />
              </v-col>
              <v-col cols="12" sm="2">
                <v-btn
                  color="primary"
                  block
                  :loading="uploading"
                  :disabled="!maskFile"
                  prepend-icon="mdi-upload"
                  @click="handleUpload"
                >
                  Uploader
                </v-btn>
              </v-col>
            </v-row>

            <v-divider class="mb-4" />

            <!-- Liste des masques -->
            <div v-if="masksStore.masks.length === 0" class="text-center text-medium-emphasis py-4">
              Aucun masque
            </div>

            <v-row>
              <v-col
                v-for="mask in masksStore.masks"
                :key="mask.id"
                cols="6"
                sm="4"
                md="3"
              >
                <v-card
                  :color="mask.is_active ? 'primary' : 'surface'"
                  variant="tonal"
                  class="pa-2 text-center"
                >
                  <v-img
                    :src="maskFileUrl(mask.id)"
                    height="80"
                    contain
                    class="mb-2 checkerboard rounded"
                  />
                  <div class="text-caption text-truncate mb-1">{{ mask.label }}</div>
                  <v-chip size="x-small" class="mb-1" :color="orientationColor(mask.orientation)">
                    {{ orientationLabel(mask.orientation) }}
                  </v-chip>
                  <div class="d-flex justify-center ga-1">
                    <v-btn
                      size="x-small"
                      :color="mask.is_active ? 'success' : 'default'"
                      :icon="mask.is_active ? 'mdi-check' : 'mdi-cursor-default-click'"
                      :title="mask.is_active ? 'Masque actif' : 'Activer'"
                      @click="masksStore.selectMask(mask.id)"
                    />
                    <v-btn
                      size="x-small"
                      color="error"
                      icon="mdi-trash-can-outline"
                      title="Supprimer"
                      :loading="deletingId === mask.id"
                      @click="handleDeleteMask(mask)"
                    />
                  </div>
                </v-card>
              </v-col>
            </v-row>
          </v-card-text>
        </v-card>

        <!-- Section Paramètres -->
        <v-card class="mb-6">
          <v-card-title class="d-flex align-center">
            <v-icon class="mr-2">mdi-tune</v-icon>
            Paramètres
          </v-card-title>
          <v-card-text>
            <v-switch
              :model-value="settingsStore.allowNoMask"
              color="primary"
              label="Autoriser l'option « Aucun filtre »"
              hide-details
              :loading="settingsLoading"
              @update:model-value="handleAllowNoMask"
            />
            <div class="text-caption text-medium-emphasis mt-1">
              Si désactivé, un filtre est toujours obligatoire avant de prendre une photo.
            </div>
          </v-card-text>
        </v-card>

        <!-- Section Imprimante -->
        <v-card>
          <v-card-title class="d-flex align-center">
            <v-icon class="mr-2">mdi-printer</v-icon>
            Imprimante
            <v-spacer />
            <v-btn
              size="small"
              variant="tonal"
              prepend-icon="mdi-refresh"
              :loading="printerLoading"
              @click="refreshPrinter"
            >
              Actualiser
            </v-btn>
          </v-card-title>

          <v-card-text>
            <div v-if="!printerStatus" class="text-medium-emphasis">
              Cliquez sur Actualiser pour vérifier l'état.
            </div>
            <v-alert
              v-else
              :type="printerStatus.ready ? 'success' : 'error'"
              :icon="printerStatus.ready ? 'mdi-printer-check' : 'mdi-printer-alert'"
              density="compact"
              variant="tonal"
            >
              <strong>{{ printerStatus.printer }}</strong> — {{ printerStatus.message }}
            </v-alert>
          </v-card-text>
        </v-card>

      </v-container>
    </v-main>

    <v-snackbar v-model="snackbar.show" :color="snackbar.color" :timeout="3000" location="top">
      {{ snackbar.message }}
    </v-snackbar>
  </v-app>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useMasksStore } from '../stores/masks'
import { useSettingsStore } from '../stores/settings'
import { postMask, deleteMask, maskFileUrl } from '../api/masks'
import { getPrinterStatus } from '../api/printer'

const masksStore = useMasksStore()
const settingsStore = useSettingsStore()
const settingsLoading = ref(false)

const maskFile = ref(null)
const maskLabel = ref('')
const maskOrientation = ref('both')
const uploading = ref(false)

const orientationOptions = [
  { title: 'Portrait', value: 'portrait' },
  { title: 'Paysage', value: 'landscape' },
  { title: 'Les deux', value: 'both' },
]

function orientationLabel(o) {
  return { portrait: 'Portrait', landscape: 'Paysage', both: 'Les deux' }[o] ?? o
}

function orientationColor(o) {
  return { portrait: 'blue', landscape: 'green', both: 'grey' }[o] ?? 'grey'
}
const deletingId = ref(null)
const printerStatus = ref(null)
const printerLoading = ref(false)
const snackbar = ref({ show: false, color: 'success', message: '' })

onMounted(() => {
  masksStore.fetchMasks()
  settingsStore.fetchSettings()
})

async function handleAllowNoMask(value) {
  settingsLoading.value = true
  try {
    await settingsStore.setAllowNoMask(value)
  } catch {
    showSnackbar('error', 'Erreur lors de la sauvegarde')
  } finally {
    settingsLoading.value = false
  }
}

async function handleUpload() {
  if (!maskFile.value) return
  uploading.value = true
  try {
    await postMask(maskFile.value, maskLabel.value, maskOrientation.value)
    await masksStore.fetchMasks()
    maskFile.value = null
    maskLabel.value = ''
    maskOrientation.value = 'both'
    showSnackbar('success', 'Masque uploadé')
  } catch (e) {
    showSnackbar('error', e.response?.data?.error ?? 'Erreur upload')
  } finally {
    uploading.value = false
  }
}

async function handleDeleteMask(mask) {
  deletingId.value = mask.id
  try {
    await deleteMask(mask.id)
    await masksStore.fetchMasks()
    showSnackbar('success', 'Masque supprimé')
  } catch {
    showSnackbar('error', 'Erreur lors de la suppression')
  } finally {
    deletingId.value = null
  }
}

async function refreshPrinter() {
  printerLoading.value = true
  try {
    printerStatus.value = await getPrinterStatus()
  } catch (e) {
    printerStatus.value = { ready: false, printer: '—', message: e.response?.data?.error ?? 'Inaccessible' }
  } finally {
    printerLoading.value = false
  }
}

function showSnackbar(color, message) {
  snackbar.value = { show: true, color, message }
}
</script>

<style scoped>
.checkerboard {
  background-image:
    linear-gradient(45deg, #ccc 25%, transparent 25%),
    linear-gradient(-45deg, #ccc 25%, transparent 25%),
    linear-gradient(45deg, transparent 75%, #ccc 75%),
    linear-gradient(-45deg, transparent 75%, #ccc 75%);
  background-size: 16px 16px;
  background-position: 0 0, 0 8px, 8px -8px, -8px 0px;
}
</style>
