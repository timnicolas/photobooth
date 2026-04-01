import client from './client'

export const getStreamUrl = (orientation = 'portrait') => {
  return `/api/camera/stream?orientation=${orientation}`
}

export const postCapture = (print = false, orientation = 'portrait') =>
  client.post(`/camera/capture?print=${print}&orientation=${orientation}`, null, { timeout: 30000 }).then((r) => r.data)
