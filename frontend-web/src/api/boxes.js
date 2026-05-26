import client from './client'

export const getBoxes = async () => {
  const response = await client.get('/boxes')
  return response.data
}
