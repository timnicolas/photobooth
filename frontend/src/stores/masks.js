import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { getMasks, selectMask as apiSelectMask } from '../api/masks'

export const useMasksStore = defineStore('masks', () => {
  const masks = ref([])

  const activeMask = computed(() => masks.value.find((m) => m.is_active) ?? null)

  async function fetchMasks() {
    masks.value = await getMasks()
  }

  async function selectMask(id) {
    await apiSelectMask(id)
    masks.value = masks.value.map((m) => ({ ...m, is_active: m.id === id }))
  }

  async function deselectAll() {
    // On sélectionne null en appelant select sur l'actif courant pour toggle — pas de route API
    // Pour désélectionner, l'UI n'appelle simplement pas selectMask
    masks.value = masks.value.map((m) => ({ ...m, is_active: false }))
  }

  return { masks, activeMask, fetchMasks, selectMask, deselectAll }
})
