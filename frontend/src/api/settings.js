import client from './client'

export const getSettings = () => client.get('/settings').then((r) => r.data)

export const putSettings = (data) => client.put('/settings', data).then((r) => r.data)
