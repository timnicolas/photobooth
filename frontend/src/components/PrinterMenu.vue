<template>
  <v-menu :close-on-content-click="false">
    <template #activator="{ props }">
      <v-btn
        v-bind="props"
        :icon="printerStore.isError ? 'mdi-printer-alert' : 'mdi-printer'"
        :color="printerStore.isError ? 'error' : undefined"
        title="État imprimante"
      />
    </template>

    <v-card min-width="300" class="pa-1">
      <!-- Statut -->
      <v-card-text v-if="!printerStore.status" class="text-medium-emphasis text-center py-3">
        Chargement...
      </v-card-text>
      <template v-else>
        <v-alert
          v-if="printerStore.isPrinting"
          type="info"
          icon="mdi-printer"
          density="compact"
          variant="tonal"
          class="ma-2 mb-1"
        >
          Impression en cours...
        </v-alert>
        <v-alert
          v-for="err in printerStore.errors"
          :key="err"
          type="error"
          icon="mdi-alert-circle-outline"
          density="compact"
          variant="tonal"
          class="ma-2 mb-1"
        >
          {{ err }}
        </v-alert>
        <v-alert
          v-if="!printerStore.isPrinting && printerStore.errors.length === 0"
          type="success"
          icon="mdi-printer-check"
          density="compact"
          variant="tonal"
          class="ma-2 mb-1"
        >
          Prête
        </v-alert>

        <!-- File d'attente -->
        <template v-if="printerStore.jobs.length > 0">
          <v-divider class="my-1" />
          <div class="d-flex align-center px-3 pt-2 pb-1">
            <span class="text-caption text-medium-emphasis flex-grow-1">
              File d'attente ({{ printerStore.jobs.length }})
            </span>
            <v-btn
              size="x-small"
              variant="text"
              color="error"
              :loading="cancellingAll"
              @click.stop="handleCancelAll"
            >
              Tout annuler
            </v-btn>
          </div>
          <v-list density="compact" class="pa-0">
            <v-list-item
              v-for="job in printerStore.jobs"
              :key="job.id"
              class="px-2"
            >
              <template #prepend>
                <v-icon :color="jobIconColor(job.state)" size="16" class="mr-1">
                  {{ jobIcon(job.state) }}
                </v-icon>
              </template>
              <v-list-item-title class="text-body-2">
                Job #{{ job.id }}
                <span class="text-caption text-medium-emphasis ml-1">{{ job.state_label }}</span>
                <span v-if="job.elapsed_seconds !== null" class="text-caption text-medium-emphasis ml-1">
                  ({{ formatElapsed(job.elapsed_seconds) }})
                </span>
              </v-list-item-title>
              <template #append>
                <v-btn
                  icon="mdi-close"
                  size="x-small"
                  variant="text"
                  color="error"
                  :loading="cancelling === job.id"
                  title="Annuler"
                  @click.stop="handleCancel(job.id)"
                />
              </template>
            </v-list-item>
          </v-list>
        </template>
        <div v-else class="text-caption text-medium-emphasis text-center pb-2 pt-1">
          Aucun job en attente
        </div>
      </template>
    </v-card>
  </v-menu>
</template>

<script setup>
import { ref } from 'vue'
import { usePrinterStore } from '../stores/printer'

const printerStore = usePrinterStore()
const cancelling = ref(null)
const cancellingAll = ref(false)

function jobIcon(state) {
  if (state === 5) return 'mdi-printer'
  if (state === 6) return 'mdi-alert-circle-outline'
  return 'mdi-clock-outline'
}

function jobIconColor(state) {
  if (state === 5) return 'info'
  if (state === 6) return 'error'
  return undefined
}

function formatElapsed(seconds) {
  if (seconds < 60) return `${seconds}s`
  return `${Math.floor(seconds / 60)}min ${seconds % 60}s`
}

async function handleCancel(id) {
  cancelling.value = id
  await printerStore.cancelJob(id)
  cancelling.value = null
}

async function handleCancelAll() {
  cancellingAll.value = true
  await printerStore.cancelAllJobs()
  cancellingAll.value = false
}
</script>
