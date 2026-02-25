import client from './client'

export const getMasks = () => client.get('/masks').then((r) => r.data)

export const postMask = (file, label, orientation = 'both') => {
  const form = new FormData()
  form.append('file', file)
  if (label) form.append('label', label)
  form.append('orientation', orientation)
  return client.post('/masks', form).then((r) => r.data)
}

export const deleteMask = (id) => client.delete(`/masks/${id}`).then((r) => r.data)

export const selectMask = (id) => client.put(`/masks/${id}/select`).then((r) => r.data)

export const deselectMasks = () => client.put('/masks/deselect').then((r) => r.data)

export const maskFileUrl = (id) => `/api/masks/${id}/file`
