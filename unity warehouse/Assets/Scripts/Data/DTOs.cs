using System;
using System.Collections.Generic;

namespace WarehouseTwin.Data
{
    // --- Inventory ---

    [Serializable]
    public class InventoryItemDTO
    {
        public string id;
        public string product_id;   // null si es caja
        public string box_id;       // null si es producto suelto
        public int? quantity;       // null si es caja
    }

    // --- Location ---

    [Serializable]
    public class LocationDTO
    {
        public string id;
        public int position_number;
        public string nfc_tag;              // puede ser null
        public InventoryItemDTO inventory;  // null si está vacía
    }

    // --- Level ---

    [Serializable]
    public class LevelDTO
    {
        public string id;
        public int level_number;
        public List<LocationDTO> locations;
    }

    // --- Shelf ---

    [Serializable]
    public class ShelfDTO
    {
        public string id;
        public int aisle_number;
        public int shelf_number;
        public List<LevelDTO> levels;
    }

    // --- Warehouse ---

    [Serializable]
    public class WarehouseDTO
    {
        public string id;
        public string name;
        public int num_shelves;
        public int num_levels;
        public int num_locations;
        public List<ShelfDTO> shelves;
    }

    // --- WebSocket Events ---

    [Serializable]
    public class WebSocketEventDTO
    {
        public string type;     // "inventory_updated" | "movement_created"
        public string location_id;
        public string task_id;
        public InventoryItemDTO inventory;  // null si la ubicación quedó vacía
    }

    // --- Estado de una ubicación (para colores) ---

    public enum LocationState
    {
        Free,       // gris   — sin inventario
        Product,    // verde  — producto suelto
        Box,        // azul   — caja
        Task        // amarillo — implicada en tarea activa
    }
}