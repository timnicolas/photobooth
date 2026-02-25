import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { getMasks, selectMask as apiSelectMask, deselectMasks as apiDeselectMasks } from '../api/masks'

export const useMasksStore = defineStore('masks', () => {
  const masks = ref([])
  const orientation = ref('portrait')

  const activeMask = computed(() => masks.value.find((m) => m.is_active) ?? null)

  const filteredMasks = computed(() =>
    masks.value.filter((m) => m.orientation === orientation.value || m.orientation === 'both'),
  )

  async function fetchMasks() {
    masks.value = await getMasks()
    // Synchroniser l'orientation avec le masque actif
    if (activeMask.value && activeMask.value.orientation !== 'both') {
      orientation.value = activeMask.value.orientation
    }
    // Auto-sélectionner le premier masque compatible si aucun n'est actif
    if (!activeMask.value && filteredMasks.value.length > 0) {
      await selectMask(filteredMasks.value[0].id)
    }
  }

  async function selectMask(id) {
    await apiSelectMask(id)
    masks.value = masks.value.map((m) => ({ ...m, is_active: m.id === id }))
  }

  async function deselectAll() {
    await apiDeselectMasks()
    masks.value = masks.value.map((m) => ({ ...m, is_active: false }))
  }

  async function setOrientation(value) {
    orientation.value = value
    const active = activeMask.value
    if (active && active.orientation !== 'both' && active.orientation !== value) {
      await deselectAll()
    }
    // Auto-sélectionner le premier masque compatible pour la nouvelle orientation
    if (!activeMask.value && filteredMasks.value.length > 0) {
      await selectMask(filteredMasks.value[0].id)
    }
  }

  return { masks, orientation, activeMask, filteredMasks, fetchMasks, selectMask, deselectAll, setOrientation }
})
