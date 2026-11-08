import client from './client'

export const getPhotos = (page = 1) => client.get(`/photos?page=${page}`).then((r) => r.data)

export const deletePhoto = (id) => client.delete(`/photos/${id}`).then((r) => r.data)

export const photoFileUrl = (id, raw = false) =>
  raw ? `/api/photos/${id}/file?raw=true` : `/api/photos/${id}/file`

export const printPhoto = (id, raw = false) =>
  client.post(`/photos/${id}/print${raw ? '?raw=true' : ''}`).then((r) => r.data)

export const downloadPhoto = (id, raw = false) =>
  client.get(`/photos/${id}/file${raw ? '?raw=true' : ''}`, { responseType: 'blob', timeout: 60000 }).then((r) => {
    const url = URL.createObjectURL(r.data)
    const a = document.createElement('a')
    a.href = url
    a.download = `photo_${id}${raw ? '_brute' : ''}.jpg`
    a.click()
    URL.revokeObjectURL(url)
  })

// Native download link (token passed as ?jwt=): the browser streams the ZIP straight to
// disk. Fetching it through axios would keep the whole archive (often >1 GB) in memory.
export const exportPhotos = (raw = false) => {
  const params = new URLSearchParams({ jwt: localStorage.getItem('token') ?? '' })
  if (raw) params.set('raw', 'true')
  const a = document.createElement('a')
  a.href = `/api/photos/export?${params}`
  a.download = raw ? 'photos_brutes.zip' : 'photos.zip'
  document.body.appendChild(a)
  a.click()
  a.remove()
}

export const downloadSelection = (ids, raw = false) =>
  client.post('/photos/download-selection', { ids, raw }, { responseType: 'blob', timeout: 0 }).then((r) => {
    const url = URL.createObjectURL(r.data)
    const a = document.createElement('a')
    a.href = url
    a.download = 'selection.zip'
    a.click()
    URL.revokeObjectURL(url)
  })

export const deleteSelection = (ids) =>
  client.post('/photos/delete-selection', { ids }).then((r) => r.data)

