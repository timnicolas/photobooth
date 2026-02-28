import client from './client'

export const getStreamUrl = (orientation = 'portrait', maskId = null) => {
  const params = new URLSearchParams({ orientation })
  if (maskId != null) params.set('mask_id', maskId)
  return `/api/camera/stream?${params}`
}

export const postCapture = (print = false, orientation = 'portrait') =>
  client.post(`/camera/capture?print=${print}&orientation=${orientation}`, null, { timeout: 30000 }).then((r) => r.data)
