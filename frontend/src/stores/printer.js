import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { getPrinterStatus, getPrinterJobs, cancelPrinterJob, cancelAllPrinterJobs } from '../api/printer'

export const usePrinterStore = defineStore('printer', () => {
  const status = ref(null)
  const jobs = ref([])
  let _timeoutId = null
  let _polling = false

  const isError = computed(() => (status.value?.errors ?? []).length > 0)
  const isPrinting = computed(() => status.value?.printing ?? false)
  const errors = computed(() => status.value?.errors ?? [])
  const errorMessage = computed(() => errors.value.join(' — ') || null)

  async function refresh() {
    try {
      const [s, j] = await Promise.all([getPrinterStatus(), getPrinterJobs()])
      status.value = s
      jobs.value = j.jobs ?? []
    } catch {}
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

  return { status, jobs, isError, isPrinting, errors, errorMessage, refresh, startPolling, stopPolling, cancelJob, cancelAllJobs }
})
