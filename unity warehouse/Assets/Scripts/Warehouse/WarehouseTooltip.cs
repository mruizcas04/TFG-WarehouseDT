using UnityEngine;
using UnityEngine.UI;
using WarehouseTwin.Data;

namespace WarehouseTwin.Warehouse
{
    public class WarehouseTooltip : MonoBehaviour
    {
        private static WarehouseTooltip _instance;

        public static WarehouseTooltip Instance
        {
            get
            {
                if (_instance == null)
                {
                    GameObject go = new GameObject("WarehouseTooltip");
                    DontDestroyOnLoad(go);
                    _instance = go.AddComponent<WarehouseTooltip>();
                }
                return _instance;
            }
        }

        private RectTransform _borderRect;
        private Text          _text;
        private bool          _visible;

        private static readonly Color BorderColor = new Color(0.85f, 0.85f, 0.85f, 1f);
        private static readonly Color TextColor   = new Color(0.11f, 0.11f, 0.10f, 1f);

        // Rich-text hex strings
        private const string HexText  = "#1C1C1A";
        private const string HexGray  = "#888780";
        private const string HexAmber = "#D9800D";  // new Color(0.85f, 0.50f, 0.05f)

        private const float PanelWidth = 220f;
        private const float PaddingH   = 10f;
        private const float PaddingV   = 8f;
        private const float LineH      = 18f;

        private void Awake()
        {
            if (_instance != null && _instance != this) { Destroy(gameObject); return; }
            _instance = this;
            BuildUI();
        }

        private void BuildUI()
        {
            GameObject canvasGO = new GameObject("TooltipCanvas");
            canvasGO.transform.SetParent(transform);
            Canvas canvas = canvasGO.AddComponent<Canvas>();
            canvas.renderMode   = RenderMode.ScreenSpaceOverlay;
            canvas.sortingOrder = 100;
            canvasGO.AddComponent<CanvasScaler>();
            canvasGO.AddComponent<GraphicRaycaster>();

            // Outer border panel (gray)
            GameObject borderGO = new GameObject("TooltipBorder");
            borderGO.transform.SetParent(canvasGO.transform, false);
            Image borderImg      = borderGO.AddComponent<Image>();
            borderImg.color      = BorderColor;
            _borderRect          = borderGO.GetComponent<RectTransform>();
            _borderRect.anchorMin = Vector2.zero;
            _borderRect.anchorMax = Vector2.zero;
            _borderRect.pivot     = new Vector2(0f, 1f);
            _borderRect.sizeDelta = new Vector2(PanelWidth, 60f);

            // Inner white panel
            GameObject panelGO = new GameObject("TooltipPanel");
            panelGO.transform.SetParent(borderGO.transform, false);
            Image panelImg    = panelGO.AddComponent<Image>();
            panelImg.color    = Color.white;
            RectTransform pr  = panelGO.GetComponent<RectTransform>();
            pr.anchorMin      = Vector2.zero;
            pr.anchorMax      = Vector2.one;
            pr.offsetMin      = new Vector2(1f, 1f);
            pr.offsetMax      = new Vector2(-1f, -1f);

            // Text (rich text enabled)
            GameObject textGO = new GameObject("TooltipText");
            textGO.transform.SetParent(panelGO.transform, false);
            _text                  = textGO.AddComponent<Text>();
            _text.supportRichText  = true;
            _text.fontSize         = 13;
            _text.color            = TextColor;
            _text.alignment        = TextAnchor.UpperLeft;
            _text.font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
            if (_text.font == null)
                _text.font = Resources.GetBuiltinResource<Font>("Arial.ttf");

            RectTransform textRect = textGO.GetComponent<RectTransform>();
            textRect.anchorMin = Vector2.zero;
            textRect.anchorMax = Vector2.one;
            textRect.offsetMin = new Vector2(PaddingH, PaddingV);
            textRect.offsetMax = new Vector2(-PaddingH, -PaddingV);

            _borderRect.gameObject.SetActive(false);
        }

        private void Update()
        {
            if (_visible && _borderRect != null)
            {
                _borderRect.position = new Vector3(
                    Input.mousePosition.x + 18f,
                    Input.mousePosition.y - 10f,
                    0f
                );
            }
        }

        public void Show(string locationLabel, string productName, int quantity, string taskInfo, LocationState state, bool isBox = false, string barcode = "", string category = "", string categoryColor = "")
        {
            if (_borderRect == null) return;

            // Line 1 — location (15px, uppercase, dark)
            string label = string.IsNullOrEmpty(locationLabel) ? "—" : locationLabel.ToUpper();
            string content = $"<size=15><color={HexText}>{label}</color></size>";

            // Line 2 — product name · barcode / state (14px, dark)
            // isBox cubre cajas cuando su estado ya ha pasado a Task y state==Box ya no es cierto.
            bool hasInventory = !string.IsNullOrEmpty(productName)
                             || quantity > 0
                             || isBox
                             || state == LocationState.Box
                             || state == LocationState.Product;
            string namePart;
            if (!string.IsNullOrEmpty(productName))
                namePart = productName;
            else if (hasInventory)
                namePart = "Ocupado";
            else
                namePart = "Libre";

            string line2 = !string.IsNullOrEmpty(barcode) && !string.IsNullOrEmpty(productName)
                ? $"{namePart} · {barcode}"
                : namePart;
            content += $"\n<size=14><color={HexText}>{line2}</color></size>";

            int lineCount = 2;

            // Line 3 — category with its color (13px)
            if (!string.IsNullOrEmpty(category))
            {
                string hexColor = !string.IsNullOrEmpty(categoryColor) ? categoryColor : HexGray;
                content += $"\n<size=13><color={hexColor}>{category}</color></size>";
                lineCount++;
            }

            // Line 4 — quantity (13px, gray) — always visible for occupied locations
            if (hasInventory)
            {
                string qtyText = quantity > 0 ? $"{quantity} unidades" : "Cantidad no disponible";
                content += $"\n<size=13><color={HexGray}>{qtyText}</color></size>";
                lineCount++;
            }

            // Line 5 — active task (13px, amber)
            if (!string.IsNullOrEmpty(taskInfo))
            {
                content += $"\n<size=13><color={HexAmber}>⚑ {taskInfo}</color></size>";
                lineCount++;
            }

            _text.text = content;
            _borderRect.sizeDelta = new Vector2(PanelWidth, PaddingV * 2f + lineCount * LineH);
            _borderRect.gameObject.SetActive(true);
            _visible = true;
        }

        public void Hide()
        {
            if (_borderRect != null) _borderRect.gameObject.SetActive(false);
            _visible = false;
        }
    }
}
