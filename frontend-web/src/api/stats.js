import client from './client'

export const getRecommendation = () =>
  client.get('/tasks/recommendation').then((r) => r.data)

export const getStats = () =>
  client.get('/tasks/stats').then((r) => r.data)
