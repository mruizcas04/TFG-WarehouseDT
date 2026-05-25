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

        [Header("Visuales en capas (opcional — vacíos = modo legacy single-cube)")]
        [Tooltip("Hijo mostrado cuando la ubicación está ocupada (caja/producto). Oculto si Free o si filtro la oculta.")]
        [SerializeField] private GameObject _contentVisual;
        [Tooltip("Renderer del cubo translúcido superpuesto. Se muestra y cambia color con hover / task / selected.")]
        [SerializeField] private Renderer _slotOverlay;

        private Renderer _legacyRenderer;
        private bool     _dimmed;
        private bool     _hover;
        private bool     _selected;

        private static readonly Color ColorFree     = new Color(0.6f,  0.6f,  0.6f);
        private static readonly Color ColorProduct  = new Color(0.2f,  0.8f,  0.2f);
        private static readonly Color ColorBox      = new Color(0.2f,  0.8f,  0.2f);
        private static readonly Color ColorTask     = new Color(1.0f,  0.85f, 0.0f);
        private static readonly Color ColorDimmed   = new Color(0.15f, 0.15f, 0.15f, 0.4f);
        private static readonly Color ColorSelected = new Color(0.2f,  0.6f,  1.0f);

        // Tintes translúcidos para el SlotOverlay (modo layered)
        private static readonly Color OverlayHover    = new Color(0.4f, 0.8f, 1.0f, 0.30f);
        private static readonly Color OverlaySelected = new Color(0.2f, 0.6f, 1.0f, 0.55f);
        private static readonly Color OverlayTask     = new Color(1.0f, 0.85f, 0.0f, 0.45f);

        private bool UseLayered => _contentVisual != null || _slotOverlay != null;
        private bool HasContent => !string.IsNullOrEmpty(ProductId) || IsBox;

        private void Awake()
        {
            _legacyRenderer = GetComponent<Renderer>();
            if (_slotOverlay != null) _slotOverlay.gameObject.SetActive(false);
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
            RefreshVisual();
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
            RefreshVisual();
        }

        public void SetFilterDim(bool dimmed)
        {
            _dimmed = dimmed;
            RefreshVisual();
        }

        public void SetSelectionHighlight(bool highlighted)
        {
            _selected = highlighted;
            if (highlighted) _hover = false;
            RefreshVisual();
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

            _hover = true;
            RefreshVisual();
        }

        private void OnMouseExit()
        {
            WarehouseTooltip.Instance?.Hide();
            _hover = false;
            RefreshVisual();
        }

        private void RefreshVisual()
        {
            if (UseLayered) RefreshLayered();
            else            RefreshLegacy();
        }

        private void RefreshLegacy()
        {
            if (_legacyRenderer == null)
            {
                Debug.LogError($"Renderer null en {LocationId}");
                return;
            }

            // Prioridad: selected > dimmed > estado base. Hover brillo solo en modo selección.
            Color color;
            if (_selected)
            {
                color = ColorSelected;
            }
            else if (_dimmed)
            {
                color = ColorDimmed;
            }
            else
            {
                color = CurrentState switch
                {
                    LocationState.Free    => ColorFree,
                    LocationState.Product => ColorProduct,
                    LocationState.Box     => ColorBox,
                    LocationState.Task    => ColorTask,
                    _                     => ColorFree
                };
            }

            bool selectionMode = ReactBridge.Instance != null && ReactBridge.Instance.IsInSelectionMode;
            if (_hover && selectionMode && !_dimmed && !_selected)
            {
                color = new Color(
                    Mathf.Min(color.r + 0.3f, 1f),
                    Mathf.Min(color.g + 0.3f, 1f),
                    Mathf.Min(color.b + 0.3f, 1f),
                    color.a);
            }

            _legacyRenderer.material.color = color;
        }

        private void RefreshLayered()
        {
            // Content: visible si ocupada (metadata o estado) y el filtro no la oculta.
            // Si está seleccionada, también la mostramos aunque el filtro la "tape" — la selección manda.
            if (_contentVisual != null)
            {
                bool occupied = HasContent
                                || CurrentState == LocationState.Product
                                || CurrentState == LocationState.Box;
                _contentVisual.SetActive(occupied && (!_dimmed || _selected));
            }

            // SlotOverlay: prioridad Selected > Task > Hover. Oculto si solo Dim.
            if (_slotOverlay != null)
            {
                Color? overlay = null;
                if (_selected)                                   overlay = OverlaySelected;
                else if (!_dimmed && CurrentState == LocationState.Task) overlay = OverlayTask;
                else if (!_dimmed && _hover)                     overlay = OverlayHover;

                _slotOverlay.gameObject.SetActive(overlay.HasValue);
                if (overlay.HasValue)
                    _slotOverlay.material.color = overlay.Value;
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
