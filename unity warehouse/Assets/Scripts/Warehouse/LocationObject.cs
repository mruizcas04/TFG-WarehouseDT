using UnityEngine;
using WarehouseTwin.Bridge;
using WarehouseTwin.Data;

namespace WarehouseTwin.Warehouse
{
    public class LocationObject : MonoBehaviour
    {
        public string LocationId    { get; private set; }
        public LocationState CurrentState { get; private set; } = LocationState.Free;

        public string LocationLabel { get; set; } = "";
        public string ProductName   { get; private set; } = "";
        public string ProductId     { get; private set; } = "";
        public string Barcode         { get; private set; } = "";
        public string Category        { get; private set; } = "";
        public string CategoryColor   { get; private set; } = "";
        public string TaskInfo      { get; private set; } = "";
        public int    Quantity      { get; private set; }
        public bool   IsBox         { get; private set; }

        private Renderer _renderer;
        private bool     _dimmed;
        private bool     _hoverHighlight;
        private Color    _savedColor;
        private bool     _selectionHighlight;
        private Color    _selectionSavedColor;

        private static readonly Color ColorFree     = new Color(0.6f,  0.6f,  0.6f);
        private static readonly Color ColorProduct  = new Color(0.2f,  0.8f,  0.2f);
        private static readonly Color ColorBox      = new Color(0.2f,  0.8f,  0.2f);
        private static readonly Color ColorTask     = new Color(1.0f,  0.85f, 0.0f);
        private static readonly Color ColorDimmed   = new Color(0.15f, 0.15f, 0.15f, 0.4f);
        private static readonly Color ColorSelected = new Color(0.2f,  0.6f,  1.0f);

        private void Awake()
        {
            _renderer = GetComponent<Renderer>();
        }

        public void Initialize(string locationId, LocationState initialState)
        {
            LocationId = locationId;
            SetState(initialState);
        }

        public void SetMetadata(string productName, int quantity, bool isBox, string taskInfo, string productId = "", string barcode = "", string category = "", string categoryColor = "")
        {
            ProductName   = productName;
            ProductId     = productId;
            Barcode       = barcode;
            Category      = category;
            CategoryColor = categoryColor;
            Quantity      = quantity;
            IsBox         = isBox;
            TaskInfo      = taskInfo;
        }

        public void SetState(LocationState newState)
        {
            Debug.Log($"SetState {LocationId} — {CurrentState} → {newState}");
            CurrentState = newState;
            // Auto-gestión de TaskInfo para eventos WebSocket que no pasan por SetMetadata
            if (newState == LocationState.Task && string.IsNullOrEmpty(TaskInfo))
                TaskInfo = "Tarea activa";
            else if (newState != LocationState.Task)
                TaskInfo = "";
            if (!_dimmed) ApplyColor();
        }

        public void SetFilterDim(bool dimmed)
        {
            _dimmed = dimmed;
            if (dimmed)
            {
                if (_renderer != null) _renderer.material.color = ColorDimmed;
            }
            else
            {
                ApplyColor();
            }
        }

        private void ApplyColor()
        {
            if (_renderer == null) { Debug.LogError($"Renderer null en {LocationId}"); return; }

            Color color = CurrentState switch
            {
                LocationState.Free    => ColorFree,
                LocationState.Product => ColorProduct,
                LocationState.Box     => ColorBox,
                LocationState.Task    => ColorTask,
                _                     => ColorFree
            };

            Debug.Log($"ApplyColor {LocationId} — estado: {CurrentState} — color: {color}");
            _renderer.material.color = color;
        }

        public void SetSelectionHighlight(bool highlighted)
        {
            if (highlighted && !_selectionHighlight && _renderer != null)
            {
                _selectionHighlight = true;
                _hoverHighlight = false;
                _renderer.material.color = ColorSelected;
            }
            else if (!highlighted && _selectionHighlight && _renderer != null)
            {
                _selectionHighlight = false;
                _hoverHighlight = false;
                if (!_dimmed) ApplyColor();
            }
        }

        private void OnMouseDown()
        {
            ReactBridge.NotifyLocationSelected(LocationId, LocationLabel);
        }

        private void OnMouseEnter()
        {
            WarehouseTooltip tooltip = WarehouseTooltip.Instance;
            if (tooltip != null)
                tooltip.Show(LocationLabel, ProductName, Quantity, TaskInfo, CurrentState, Barcode, Category, CategoryColor);

            if (ReactBridge.Instance != null && ReactBridge.Instance.IsInSelectionMode && _renderer != null && !_dimmed)
            {
                _savedColor = _renderer.material.color;
                _hoverHighlight = true;
                Color c = _savedColor;
                _renderer.material.color = new Color(
                    Mathf.Min(c.r + 0.3f, 1f),
                    Mathf.Min(c.g + 0.3f, 1f),
                    Mathf.Min(c.b + 0.3f, 1f),
                    c.a);
            }
        }

        private void OnMouseExit()
        {
            WarehouseTooltip.Instance?.Hide();
            if (_hoverHighlight && _renderer != null)
            {
                _renderer.material.color = _selectionHighlight ? ColorSelected : _savedColor;
                _hoverHighlight = false;
            }
        }

        public static LocationState StateFromInventory(InventoryItemDTO inventory)
        {
            if (inventory == null) return LocationState.Free;
            if (!string.IsNullOrEmpty(inventory.box_id))     return LocationState.Box;
            if (!string.IsNullOrEmpty(inventory.product_id)) return LocationState.Product;
            return LocationState.Free;
        }
    }
}
