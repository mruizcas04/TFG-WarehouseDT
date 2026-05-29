import client from './client'

export const getWarehouses = async () => {
  const response = await client.get('/warehouses')
  return response.data
}

export const createWarehouse = async (data) => {
  const response = await client.post('/warehouses', data)
  return response.data
}

export const getWarehouseFull = async (id) => {
  const response = await client.get(`/warehouses/${id}/full`)
  return response.data
}

export const expandWarehouse = async (id, data) => {
  const response = await client.post(`/warehouses/${id}/expand`, data)
  return response.data
}

export const flattenLocations = (warehouse) => {
  const result = []
  for (const shelf of warehouse?.shelves || []) {
    for (const level of shelf.levels || []) {
      for (const loc of level.locations || []) {
        result.push({
          id: loc.id,
          label: `Fila ${shelf.aisle_number} · Est. ${shelf.shelf_number} · Nivel ${level.level_number} · Pos. ${loc.position_number}`,
          nfc_tag: loc.nfc_tag,
          aisle_number: shelf.aisle_number,
          shelf_number: shelf.shelf_number,
          level_number: level.level_number,
          position_number: loc.position_number,
          inventory: loc.inventory || null,
        })
      }
    }
  }
  return result
}
