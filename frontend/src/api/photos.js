import client from './client'

export const getPhotos = () => client.get('/photos').then((r) => r.data)

export const deletePhoto = (id) => client.delete(`/photos/${id}`).then((r) => r.data)

export const photoFileUrl = (id) => `/api/photos/${id}/file`

export const getPrinterStatus = () => client.get('/printer/status').then((r) => r.data)
