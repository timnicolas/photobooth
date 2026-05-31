<template>
  <v-alert
    v-if="printerStore.isError"
    type="error"
    icon="mdi-printer-alert"
    variant="elevated"
    prominent
    rounded="0"
    class="printer-error-banner"
  >
    <div class="text-h6 font-weight-bold">Erreur imprimante</div>
    <div class="text-body-1">{{ printerStore.errorMessage }}</div>
  </v-alert>
</template>

<script setup>
import { watch, onMounted } from 'vue'
import { usePrinterStore } from '../stores/printer'
import { playBeep, unlockAudioOnce } from '../composables/useAudio'

const printerStore = usePrinterStore()

// Two low beeps to grab attention.
function playAlert() {
  playBeep(440, 200)
  setTimeout(() => playBeep(440, 200), 280)
}

// Play the alert only when the error message changes (new/different error),
// not on every polling cycle.
watch(
  () => printerStore.errorMessage,
  (msg, prev) => {
    if (msg && msg !== prev) playAlert()
  }
)

onMounted(() => {
  unlockAudioOnce()
})
</script>

<style scoped>
.printer-error-banner {
  position: sticky;
  top: 0;
  z-index: 5;
}
</style>
