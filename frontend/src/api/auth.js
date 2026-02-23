import client from './client'

export const postLogin = (mail, password) =>
  client.post('/login', { mail, password }).then((r) => r.data)
