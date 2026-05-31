import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { getPrinterStatus, getPrinterJobs, cancelPrinterJob, cancelAllPrinterJobs } from '../api/printer'

export const usePrinterStore = defineStore('printer', () => {
  const status = ref(null)
  const jobs = ref([])
  const reachable = ref(true)
  let _timeoutId = null
  let _polling = false

  const isError = computed(() => (status.value?.errors ?? []).length > 0)
  const isPrinting = computed(() => status.value?.printing ?? false)
  const errors = computed(() => status.value?.errors ?? [])
  const errorMessage = computed(() => errors.value.join(' — ') || null)

  // Connected = last fetch succeeded, printer present in CUPS, and not reported offline.
  const isConnected = computed(
    () =>
      reachable.value &&
      status.value?.available !== false &&
      !errors.value.some((e) => e.toLowerCase().includes('déconnect'))
  )

  // Message shown in the error banner: explicit errors, or a disconnection fallback
  // when the printer is simply unreachable (no error string available).
  const bannerMessage = computed(() => errorMessage.value || (isConnected.value ? null : 'Imprimante déconnectée'))

  async function refresh() {
    try {
      const [s, j] = await Promise.all([getPrinterStatus(), getPrinterJobs()])
      status.value = s
      jobs.value = j.jobs ?? []
      reachable.value = true
    } catch {
      reachable.value = false
    }
  }

  async function _poll() {
    await refresh()
    if (_polling) {
      // 3s en impression, 10s sinon
      const delay = isPrinting.value ? 1000 : 10000
      _timeoutId = setTimeout(_poll, delay)
    }
  }

  function startPolling() {
    stopPolling()
    _polling = true
    _poll()
  }

  function stopPolling() {
    _polling = false
    if (_timeoutId) {
      clearTimeout(_timeoutId)
      _timeoutId = null
    }
  }

  async function cancelJob(id) {
    try {
      await cancelPrinterJob(id)
      await refresh()
    } catch {}
  }

  async function cancelAllJobs() {
    try {
      await cancelAllPrinterJobs()
      await refresh()
    } catch {}
  }

  return { status, jobs, reachable, isError, isPrinting, errors, errorMessage, isConnected, bannerMessage, refresh, startPolling, stopPolling, cancelJob, cancelAllJobs }
})
