import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getSettings, putSettings } from '../api/settings'

export const useSettingsStore = defineStore('settings', () => {
  const allowNoMask = ref(true)
  const photoWidthMm = ref(89)
  const photoHeightMm = ref(119)

  async function fetchSettings() {
    const data = await getSettings()
    allowNoMask.value = data.allow_no_mask
    photoWidthMm.value = data.photo_width_mm ?? 89
    photoHeightMm.value = data.photo_height_mm ?? 119
  }

  async function setAllowNoMask(value) {
    const data = await putSettings({ allow_no_mask: value })
    allowNoMask.value = data.allow_no_mask
  }

  return { allowNoMask, photoWidthMm, photoHeightMm, fetchSettings, setAllowNoMask }
})
