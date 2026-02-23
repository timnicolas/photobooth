import client from './client'

export const streamUrl = '/api/camera/stream'

export const postCapture = (print = false) =>
  client.post(`/camera/capture?print=${print}`).then((r) => r.data)
