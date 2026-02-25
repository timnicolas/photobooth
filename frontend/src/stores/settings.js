import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getSettings, putSettings } from '../api/settings'

export const useSettingsStore = defineStore('settings', () => {
  const allowNoMask = ref(true)

  async function fetchSettings() {
    const data = await getSettings()
    allowNoMask.value = data.allow_no_mask
  }

  async function setAllowNoMask(value) {
    const data = await putSettings({ allow_no_mask: value })
    allowNoMask.value = data.allow_no_mask
  }

  return { allowNoMask, fetchSettings, setAllowNoMask }
})
