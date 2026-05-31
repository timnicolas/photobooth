<template>
  <v-alert
    v-if="printerStore.isError || !printerStore.isConnected"
    color="red"
    :icon="printerStore.isConnected ? 'mdi-printer-alert' : 'mdi-printer-off'"
    variant="elevated"
    density="compact"
    rounded="pill"
    class="printer-error-toast"
  >
    <span class="font-weight-medium">{{ printerStore.bannerMessage }}</span>
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
  () => printerStore.bannerMessage,
  (msg, prev) => {
    if (msg && msg !== prev) playAlert()
  }
)

onMounted(() => {
  unlockAudioOnce()
})
</script>

<style scoped>
/* Small persistent toast floating over the camera image, just below the app bar. */
.printer-error-toast {
  position: fixed;
  top: 72px;
  left: 50%;
  transform: translateX(-50%);
  width: auto;
  max-width: 90vw;
  z-index: 2000;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.35);
}
</style>
