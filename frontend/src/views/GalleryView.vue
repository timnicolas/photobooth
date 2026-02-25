<template>
  <v-app>
    <v-app-bar color="surface" elevation="1">
      <v-btn
        :icon="selectionMode ? 'mdi-close' : 'mdi-arrow-left'"
        @click="selectionMode ? exitSelection() : $router.back()"
      />
      <v-app-bar-title>
        {{ selectionMode ? `${selectedIds.size} sélectionnée(s)` : 'Galerie' }}
      </v-app-bar-title>
      <template #append>
        <!-- Mode sélection actif -->
        <template v-if="selectionMode">
          <v-btn
            icon="mdi-download"
            :disabled="selectedIds.size === 0"
            :loading="downloading"
            title="Télécharger la sélection"
            @click="handleDownloadSelection"
          />
          <v-btn
            v-if="auth.isAdmin"
            icon="mdi-trash-can-outline"
            color="error"
            :disabled="selectedIds.size === 0"
            :loading="deleting"
            title="Supprimer la sélection"
            @click="handleDeleteSelection"
          />
        </template>

        <!-- Mode normal -->
        <template v-else>
          <v-btn
            v-if="photos.length > 0"
            icon="mdi-checkbox-multiple-marked-outline"
            title="Sélectionner"
            @click="selectionMode = true"
          />
          <v-menu v-if="auth.isAdmin">
            <template #activator="{ props }">
              <v-btn v-bind="props" icon="mdi-folder-zip-outline" title="Exporter tout" />
            </template>
            <v-list density="compact">
              <v-list-item
                prepend-icon="mdi-image-auto-adjust"
                title="Avec filtres"
                :disabled="exporting"
                @click="handleExport(false)"
              />
              <v-list-item
                prepend-icon="mdi-image"
                title="Sans filtres (brutes)"
                :disabled="exporting"
                @click="handleExport(true)"
              />
            </v-list>
          </v-menu>
          <v-btn icon="mdi-refresh" :loading="loading" @click="load" title="Actualiser" />
        </template>
      </template>
    </v-app-bar>

    <v-main>
      <v-container class="py-4">

        <!-- État vide -->
        <div v-if="!loading && photos.length === 0" class="text-center text-medium-emphasis py-16">
          <v-icon size="64">mdi-image-off</v-icon>
          <div class="mt-3 text-h6">Aucune photo pour l'instant</div>
        </div>

        <template v-else>
          <!-- Pagination -->
          <div v-if="totalPages > 1" class="d-flex align-center justify-center mb-4 ga-1">
            <v-btn icon="mdi-chevron-left" variant="text" density="compact" :disabled="page === 1" @click="goToPage(page - 1)" />
            <span class="text-body-2 text-medium-emphasis px-2">{{ page }} / {{ totalPages }}</span>
            <v-btn icon="mdi-chevron-right" variant="text" density="compact" :disabled="page === totalPages" @click="goToPage(page + 1)" />
          </div>

          <!-- Grille de photos -->
          <v-row>
          <v-col
            v-for="photo in photos"
            :key="photo.id"
            cols="6"
            sm="4"
            md="3"
          >
            <v-card
              class="photo-card"
              :class="{ 'photo-selected': selectionMode && selectedIds.has(photo.id) }"
              :ripple="true"
              @click="onCardClick(photo)"
            >
              <div class="card-img-wrapper">
                <v-img :src="photoFileUrl(photo.id)" aspect-ratio="1" cover>
                  <template #placeholder>
                    <v-skeleton-loader type="image" />
                  </template>
                </v-img>
                <div v-if="selectionMode" class="selection-overlay">
                  <v-icon
                    :color="selectedIds.has(photo.id) ? 'primary' : 'white'"
                    size="28"
                  >
                    {{ selectedIds.has(photo.id) ? 'mdi-checkbox-marked-circle' : 'mdi-checkbox-blank-circle-outline' }}
                  </v-icon>
                </div>
              </div>
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
        </template>
      </v-container>
    </v-main>

    <!-- Dialog photo plein écran -->
    <v-dialog v-model="dialog" fullscreen>
      <v-card v-if="selected" class="d-flex flex-column" color="black" style="height: 100vh;">
        <!-- Toolbar -->
        <v-toolbar color="black" density="compact">
          <v-btn icon="mdi-close" @click="dialog = false" />
          <v-toolbar-title class="text-caption text-medium-emphasis">
            {{ formatDate(selected.captured_at) }}
            <v-chip v-if="selected.printed" size="x-small" color="success" class="ml-2">
              Imprimée
            </v-chip>
          </v-toolbar-title>
          <template #append>
            <!-- Toggle avec/sans filtre -->
            <v-btn
              size="small"
              variant="tonal"
              :color="showRaw ? 'orange' : 'primary'"
              class="mr-1"
              @click="showRaw = !showRaw"
            >
              <v-icon start>{{ showRaw ? 'mdi-image' : 'mdi-image-auto-adjust' }}</v-icon>
              {{ showRaw ? 'Brut' : 'Filtré' }}
            </v-btn>

            <!-- Imprimer -->
            <v-btn
              icon="mdi-printer"
              :loading="printing"
              title="Imprimer"
              @click="handlePrint"
            />

            <!-- Télécharger (admin) -->
            <v-btn
              v-if="auth.isAdmin"
              icon="mdi-download"
              :loading="downloading"
              title="Télécharger"
              @click="handleDownload"
            />

            <!-- Supprimer (admin) -->
            <v-btn
              v-if="auth.isAdmin"
              icon="mdi-trash-can-outline"
              color="error"
              :loading="deleting"
              title="Supprimer"
              @click="handleDelete"
            />
          </template>
        </v-toolbar>

        <!-- Image -->
        <div class="flex-grow-1 d-flex align-center justify-center" style="min-height: 0; overflow: hidden; padding: 8px;">
          <img
            :src="dialogPhotoUrl"
            style="max-height: 100%; max-width: 100%; object-fit: contain; display: block;"
            alt="Photo"
          />
        </div>
      </v-card>
    </v-dialog>

    <!-- Dialog de confirmation -->
    <v-dialog v-model="confirmDialog.show" max-width="360" persistent>
      <v-card>
        <v-card-title class="text-body-1 font-weight-bold pt-5 px-5">
          {{ confirmDialog.title }}
        </v-card-title>
        <v-card-text class="px-5 pb-2 text-medium-emphasis">
          {{ confirmDialog.message }}
        </v-card-text>
        <v-card-actions class="pa-4 pt-2">
          <v-spacer />
          <v-btn variant="text" @click="confirmDialog.resolve(false)">Annuler</v-btn>
          <v-btn color="error" variant="tonal" @click="confirmDialog.resolve(true)">Supprimer</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-snackbar v-model="snackbar.show" :color="snackbar.color" :timeout="3000" location="top">
      {{ snackbar.message }}
    </v-snackbar>
  </v-app>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '../stores/auth'
import {
  getPhotos, deletePhoto, printPhoto, downloadPhoto, exportPhotos, photoFileUrl,
  downloadSelection, deleteSelection,
} from '../api/photos'

const auth = useAuthStore()
const photos = ref([])
const loading = ref(false)
const dialog = ref(false)
const selected = ref(null)
const showRaw = ref(false)
const deleting = ref(false)
const printing = ref(false)
const downloading = ref(false)
const exporting = ref(false)
const snackbar = ref({ show: false, color: 'success', message: '' })

const selectionMode = ref(false)
const selectedIds = ref(new Set())

const page = ref(1)
const totalPages = ref(1)
const total = ref(0)

const confirmDialog = ref({ show: false, title: '', message: '', resolve: null })

function confirm(title, message) {
  return new Promise((resolve) => {
    confirmDialog.value = { show: true, title, message, resolve: (val) => {
      confirmDialog.value.show = false
      resolve(val)
    }}
  })
}

const dialogPhotoUrl = computed(() =>
  selected.value ? photoFileUrl(selected.value.id, showRaw.value) : '',
)

onMounted(load)

async function load(p = page.value) {
  loading.value = true
  try {
    const data = await getPhotos(p)
    photos.value = data.photos
    page.value = data.page
    totalPages.value = data.pages
    total.value = data.total
  } finally {
    loading.value = false
  }
}

async function goToPage(p) {
  if (p < 1 || p > totalPages.value || p === page.value) return
  exitSelection()
  await load(p)
}

function exitSelection() {
  selectionMode.value = false
  selectedIds.value = new Set()
}

function toggleSelect(photo) {
  const next = new Set(selectedIds.value)
  if (next.has(photo.id)) {
    next.delete(photo.id)
  } else {
    next.add(photo.id)
  }
  selectedIds.value = next
}

function onCardClick(photo) {
  if (selectionMode.value) {
    toggleSelect(photo)
  } else {
    openDialog(photo)
  }
}

function openDialog(photo) {
  selected.value = photo
  showRaw.value = false
  dialog.value = true
}

async function handleDeleteSelection() {
  const n = selectedIds.value.size
  const ok = await confirm('Supprimer la sélection', `Supprimer ${n} photo(s) définitivement ?`)
  if (!ok) return
  deleting.value = true
  try {
    const ids = [...selectedIds.value]
    await deleteSelection(ids)
    showSnackbar('success', `${ids.length} photo(s) supprimée(s)`)
    exitSelection()
    const remaining = photos.value.filter((p) => !ids.includes(p.id)).length
    const targetPage = remaining === 0 && page.value > 1 ? page.value - 1 : page.value
    await load(targetPage)
  } catch {
    showSnackbar('error', 'Erreur lors de la suppression')
  } finally {
    deleting.value = false
  }
}

async function handleDownloadSelection() {
  downloading.value = true
  try {
    await downloadSelection([...selectedIds.value])
    exitSelection()
  } catch {
    showSnackbar('error', 'Erreur lors du téléchargement')
  } finally {
    downloading.value = false
  }
}

async function handleDelete() {
  if (!selected.value) return
  const ok = await confirm('Supprimer la photo', 'Supprimer cette photo définitivement ?')
  if (!ok) return
  deleting.value = true
  try {
    await deletePhoto(selected.value.id)
    dialog.value = false
    showSnackbar('success', 'Photo supprimée')
    const targetPage = photos.value.length === 1 && page.value > 1 ? page.value - 1 : page.value
    await load(targetPage)
  } catch {
    showSnackbar('error', 'Erreur lors de la suppression')
  } finally {
    deleting.value = false
  }
}

async function handlePrint() {
  if (!selected.value) return
  printing.value = true
  try {
    await printPhoto(selected.value.id, showRaw.value)
    selected.value = { ...selected.value, printed: true }
    photos.value = photos.value.map((p) =>
      p.id === selected.value.id ? { ...p, printed: true } : p,
    )
    showSnackbar('success', 'Impression lancée')
  } catch (e) {
    showSnackbar('error', e.response?.data?.error ?? 'Erreur impression')
  } finally {
    printing.value = false
  }
}

async function handleDownload() {
  if (!selected.value) return
  downloading.value = true
  try {
    await downloadPhoto(selected.value.id, showRaw.value)
  } catch {
    showSnackbar('error', 'Erreur lors du téléchargement')
  } finally {
    downloading.value = false
  }
}

async function handleExport(raw) {
  exporting.value = true
  try {
    await exportPhotos(raw)
  } catch {
    showSnackbar('error', 'Erreur lors de l\'export')
  } finally {
    exporting.value = false
  }
}

function showSnackbar(color, message) {
  snackbar.value = { show: true, color, message }
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
