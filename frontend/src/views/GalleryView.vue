<template>
  <v-app>
    <v-app-bar color="surface" elevation="1">
      <v-btn icon="mdi-arrow-left" @click="$router.back()" />
      <v-app-bar-title>Galerie</v-app-bar-title>
      <template #append>
        <v-btn icon="mdi-refresh" :loading="loading" @click="load" title="Actualiser" />
      </template>
    </v-app-bar>

    <v-main>
      <v-container class="py-4">

        <!-- État vide -->
        <div v-if="!loading && photos.length === 0" class="text-center text-medium-emphasis py-16">
          <v-icon size="64">mdi-image-off</v-icon>
          <div class="mt-3 text-h6">Aucune photo pour l'instant</div>
        </div>

        <!-- Grille de photos -->
        <v-row v-else>
          <v-col
            v-for="photo in photos"
            :key="photo.id"
            cols="6"
            sm="4"
            md="3"
          >
            <v-card
              class="photo-card"
              @click="openDialog(photo)"
              :ripple="true"
            >
              <v-img
                :src="photoFileUrl(photo.id)"
                aspect-ratio="1"
                cover
              >
                <template #placeholder>
                  <v-skeleton-loader type="image" />
                </template>
              </v-img>

              <v-card-text class="pa-2">
                <div class="text-caption text-truncate text-medium-emphasis">
                  {{ formatDate(photo.captured_at) }}
                </div>
                <v-chip v-if="photo.printed" size="x-small" color="success" class="mt-1">
                  <v-icon start size="10">mdi-printer-check</v-icon>
                  Imprimée
                </v-chip>
              </v-card-text>
            </v-card>
          </v-col>
        </v-row>
      </v-container>
    </v-main>

    <!-- Dialog photo plein écran -->
    <v-dialog v-model="dialog" fullscreen>
      <v-card v-if="selected" class="d-flex flex-column" color="black">
        <v-toolbar color="black" density="compact">
          <v-btn icon="mdi-close" @click="dialog = false" />
          <v-toolbar-title class="text-caption text-medium-emphasis">
            {{ formatDate(selected.captured_at) }}
            <v-chip v-if="selected.printed" size="x-small" color="success" class="ml-2">Imprimée</v-chip>
          </v-toolbar-title>
          <template #append>
            <v-btn
              v-if="auth.isAdmin"
              icon="mdi-trash-can-outline"
              color="error"
              :loading="deleting"
              @click="handleDelete"
            />
          </template>
        </v-toolbar>

        <div class="flex-grow-1 d-flex align-center justify-center">
          <v-img
            :src="photoFileUrl(selected.id)"
            max-height="100%"
            contain
          />
        </div>
      </v-card>
    </v-dialog>

    <v-snackbar v-model="snackbar.show" :color="snackbar.color" :timeout="3000" location="top">
      {{ snackbar.message }}
    </v-snackbar>
  </v-app>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useAuthStore } from '../stores/auth'
import { getPhotos, deletePhoto, photoFileUrl } from '../api/photos'

const auth = useAuthStore()
const photos = ref([])
const loading = ref(false)
const dialog = ref(false)
const selected = ref(null)
const deleting = ref(false)
const snackbar = ref({ show: false, color: 'success', message: '' })

onMounted(load)

async function load() {
  loading.value = true
  try {
    photos.value = await getPhotos()
  } finally {
    loading.value = false
  }
}

function openDialog(photo) {
  selected.value = photo
  dialog.value = true
}

async function handleDelete() {
  if (!selected.value) return
  deleting.value = true
  try {
    await deletePhoto(selected.value.id)
    photos.value = photos.value.filter((p) => p.id !== selected.value.id)
    dialog.value = false
    snackbar.value = { show: true, color: 'success', message: 'Photo supprimée' }
  } catch {
    snackbar.value = { show: true, color: 'error', message: 'Erreur lors de la suppression' }
  } finally {
    deleting.value = false
  }
}

function formatDate(iso) {
  return new Date(iso).toLocaleString('fr-FR', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}
</script>

<style scoped>
.photo-card { cursor: pointer; transition: transform 0.15s; }
.photo-card:hover { transform: scale(1.02); }
</style>
