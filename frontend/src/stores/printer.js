import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { getPrinterStatus, getPrinterJobs, cancelPrinterJob, cancelAllPrinterJobs } from '../api/printer'

export const usePrinterStore = defineStore('printer', () => {
  const status = ref(null)
  const jobs = ref([])
  let _intervalId = null

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

  function startPolling(interval = 20000) {
    stopPolling()
    refresh()
    _intervalId = setInterval(refresh, interval)
  }

  function stopPolling() {
    if (_intervalId) {
      clearInterval(_intervalId)
      _intervalId = null
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
