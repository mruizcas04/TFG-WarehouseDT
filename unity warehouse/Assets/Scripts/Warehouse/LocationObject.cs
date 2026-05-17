using UnityEngine;
using WarehouseTwin.Data;

namespace WarehouseTwin.Warehouse
{
    // Componente que se añade a cada hueco (Location) del almacén.
    // Guarda el ID del backend y gestiona el color según su estado.
    public class LocationObject : MonoBehaviour
    {
        // ID de la location en el backend, usado para identificarla
        // cuando llega un evento WebSocket con location_id
        public string LocationId { get; private set; }

        // Estado actual del hueco
        public LocationState CurrentState { get; private set; } = LocationState.Free;

        // Referencia al Renderer para cambiar el color
        private Renderer _renderer;

        // Colores según el documento de diseño:
        // gris=libre, verde=producto, azul=caja, amarillo=tarea
        private static readonly Color ColorFree = new Color(0.6f, 0.6f, 0.6f); // gris
        private static readonly Color ColorProduct = new Color(0.2f, 0.8f, 0.2f); // verde
        private static readonly Color ColorBox = new Color(0.2f, 0.4f, 0.9f); // azul
        private static readonly Color ColorTask = new Color(1.0f, 0.85f, 0.0f); // amarillo

        private void Awake()
        {
            _renderer = GetComponent<Renderer>();
        }

        // Inicializa el hueco con su ID y estado inicial
        // Se llama desde WarehouseGenerator al crear cada hueco
        public void Initialize(string locationId, LocationState initialState)
        {
            LocationId = locationId;
            SetState(initialState);
        }

        // Cambia el estado del hueco y actualiza su color visualmente
        public void SetState(LocationState newState)
        {
            Debug.Log($"SetState {LocationId} — {CurrentState} → {newState}");
            CurrentState = newState;
            ApplyColor();
        }

        // Aplica el color correspondiente al estado actual
        private void ApplyColor()
        {
            if (_renderer == null) { Debug.LogError($"Renderer null en {LocationId}"); return; }

            Color color = CurrentState switch
            {
                LocationState.Free => ColorFree,
                LocationState.Product => ColorProduct,
                LocationState.Box => ColorBox,
                LocationState.Task => ColorTask,
                _ => ColorFree
            };

            Debug.Log($"ApplyColor {LocationId} — estado: {CurrentState} — color: {color}");
            _renderer.material.color = color;
        }

        // Calcula el estado a partir de un InventoryItemDTO
        // Se usa al inicializar y al recibir eventos WebSocket
        public static LocationState StateFromInventory(InventoryItemDTO inventory)
        {
            if (inventory == null) return LocationState.Free;
            if (!string.IsNullOrEmpty(inventory.box_id)) return LocationState.Box;
            if (!string.IsNullOrEmpty(inventory.product_id)) return LocationState.Product;
            return LocationState.Free;
        }
    }
}