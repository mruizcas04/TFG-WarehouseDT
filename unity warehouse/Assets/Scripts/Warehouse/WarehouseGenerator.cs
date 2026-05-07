using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using WarehouseTwin.Data;
using WarehouseTwin.Network;

namespace WarehouseTwin.Warehouse
{
    // Script principal del gemelo digital.
    // Al inicializarse llama al backend para obtener la configuración
    // del almacén y genera proceduralmente la geometría 3D.
    // También se suscribe a los eventos WebSocket para actualizar
    // el estado visual en tiempo real.
    public class WarehouseGenerator : MonoBehaviour
    {
        [Header("Configuración del almacén")]
        [SerializeField] private string warehouseId;

        [Header("Dimensiones de los elementos (metros)")]
        [SerializeField] private float shelfWidth      = 1.0f;
        [SerializeField] private float shelfHeight     = 0.4f;
        [SerializeField] private float shelfDepth      = 0.6f;
        [SerializeField] private float aisleSpacing    = 2.5f;
        [SerializeField] private float locationPadding = 0.05f;

        [Header("Prefabs")]
        [SerializeField] private GameObject locationPrefab;
        [SerializeField] private GameObject shelfFramePrefab;

        // Diccionario para acceder a cada LocationObject por su ID del backend
        private Dictionary<string, LocationObject> _locationObjects
            = new Dictionary<string, LocationObject>();

        private void Start()
        {
            WebSocketClient.Instance.OnInventoryUpdated += HandleInventoryUpdated;
            WebSocketClient.Instance.OnMovementCreated  += HandleMovementCreated;

            StartCoroutine(ApiClient.Instance.GetWarehouseFull(
                warehouseId,
                warehouse => GenerateFromDTO(warehouse),
                error => Debug.LogError($"No se pudo cargar el almacén: {error}")
            ));
        }

        private void OnDestroy()
        {
            if (WebSocketClient.Instance != null)
            {
                WebSocketClient.Instance.OnInventoryUpdated -= HandleInventoryUpdated;
                WebSocketClient.Instance.OnMovementCreated  -= HandleMovementCreated;
            }
        }

        // Genera toda la geometría 3D a partir del WarehouseDTO.
        // Es público para que ReactBridge pueda llamarlo también.
        public void GenerateFromDTO(WarehouseDTO warehouse)
        {
            Debug.Log($"Generando almacén: {warehouse.name}");

            _locationObjects.Clear();
            foreach (Transform child in transform)
                Destroy(child.gameObject);

            foreach (ShelfDTO shelf in warehouse.shelves)
            {
                float shelfX = (shelf.aisle_number - 1) * aisleSpacing;

                GameObject shelfGO = new GameObject($"Shelf_Aisle{shelf.aisle_number}");
                shelfGO.transform.SetParent(transform);
                shelfGO.transform.localPosition = new Vector3(shelfX, 0, 0);

                foreach (LevelDTO level in shelf.levels)
                {
                    float levelY = (level.level_number - 1) * shelfHeight;

                    GameObject levelGO = new GameObject($"Level_{level.level_number}");
                    levelGO.transform.SetParent(shelfGO.transform);
                    levelGO.transform.localPosition = new Vector3(0, levelY, 0);

                    foreach (LocationDTO location in level.locations)
                    {
                        float locationZ = (location.position_number - 1)
                            * (shelfWidth + locationPadding);

                        GameObject locationGO = Instantiate(
                            locationPrefab,
                            levelGO.transform
                        );
                        locationGO.name = $"Location_{location.position_number}";
                        locationGO.transform.localPosition = new Vector3(0, 0, locationZ);
                        locationGO.transform.localScale = new Vector3(
                            shelfDepth,
                            shelfHeight - locationPadding,
                            shelfWidth - locationPadding
                        );

                        LocationObject locObj = locationGO.GetComponent<LocationObject>();
                        LocationState initialState =
                            LocationObject.StateFromInventory(location.inventory);
                        locObj.Initialize(location.id, initialState);

                        _locationObjects[location.id] = locObj;
                    }
                }
            }

            Debug.Log($"Almacén generado: {_locationObjects.Count} ubicaciones.");
        }

        private void HandleInventoryUpdated(WebSocketEventDTO evt)
        {
            if (!_locationObjects.TryGetValue(evt.location_id, out LocationObject locObj))
            {
                Debug.LogWarning($"Location no encontrada: {evt.location_id}");
                return;
            }

            LocationState newState = LocationObject.StateFromInventory(evt.inventory);
            locObj.SetState(newState);

            Debug.Log($"Location {evt.location_id} actualizada a estado: {newState}");
        }

        private void HandleMovementCreated(WebSocketEventDTO evt)
        {
            HandleInventoryUpdated(evt);
        }

        public void HighlightTaskLocation(string locationId)
        {
            if (_locationObjects.TryGetValue(locationId, out LocationObject locObj))
                locObj.SetState(LocationState.Task);
        }

        public void ClearTaskHighlight(string locationId)
        {
            if (_locationObjects.TryGetValue(locationId, out LocationObject locObj))
                locObj.SetState(LocationState.Free);
        }
    }
}