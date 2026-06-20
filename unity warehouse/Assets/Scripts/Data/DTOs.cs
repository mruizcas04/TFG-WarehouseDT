using System;
using System.Collections.Generic;

namespace WarehouseTwin.Data
{
    [Serializable]
    public class InventoryItemDTO
    {
        public string id;
        public string product_id;
        public string product_name;
        public string product_barcode;
        public string product_category;
        public string product_category_color;
        public string box_id;
        public int quantity;
    }

    [Serializable]
    public class LocationDTO
    {
        public string id;
        public int position_number;
        public string nfc_tag;
        public InventoryItemDTO inventory;
    }

    [Serializable]
    public class LevelDTO
    {
        public string id;
        public int level_number;
        public List<LocationDTO> locations;
    }

    [Serializable]
    public class ShelfDTO
    {
        public string id;
        public int aisle_number;
        public int shelf_number;
        public bool is_double;
        public List<LevelDTO> levels;
    }

    [Serializable]
    public class WarehouseDTO
    {
        public string id;
        public string name;
        public int num_shelves;
        public int? num_levels;
        public int? num_locations;
        public List<ShelfDTO> shelves;
        public List<string> active_task_locations;
        public Dictionary<string, string> active_task_info;
    }

    [Serializable]
    public class WebSocketEventData
    {
        public string location_id;
        public string destination_location_id;
        public string origin_location_id;
        public string destination_state;        // "free" | "product" | "box"
        public string origin_state;             // "free" | "product" | "box"
        public string movement_id;
        public string task_id;
        public string assigned_to;
        public string status;
        public InventoryItemDTO inventory;
        public InventoryItemDTO destination_inventory;
        public InventoryItemDTO origin_inventory;
    }

    [Serializable]
    public class WebSocketEventDTO
    {
        public string @event;
        public WebSocketEventData data;
    }

    public enum LocationState
    {
        Free,
        Product,
        Box,
        Task
    }
}