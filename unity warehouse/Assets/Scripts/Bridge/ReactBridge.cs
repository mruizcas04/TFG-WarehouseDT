using System.Collections;
using UnityEngine;
using WarehouseTwin.Network;
using WarehouseTwin.Warehouse;

namespace WarehouseTwin.Bridge
{
    // Puente de comunicación entre React y Unity WebGL.
    // React llama a los métodos de este script usando SendMessage() de Unity WebGL.
    // Formato: unityInstance.SendMessage('ReactBridge', 'Initialize', JSON)
    //
    // Flujo de inicialización:
    // 1. React carga el WebGL y espera a que Unity esté listo
    // 2. React llama a Initialize() con el token JWT y el warehouse ID
    // 3. Unity conecta el WebSocket y genera el almacén 3D
    public class ReactBridge : MonoBehaviour
    {
        [SerializeField] private WarehouseGenerator warehouseGenerator;

        // Singleton
        public static ReactBridge Instance { get; private set; }

        private bool _selectionMode = false;
        public bool IsInSelectionMode => _selectionMode;

        private void Awake()
        {
            if (Instance != null && Instance != this)
            {
                Destroy(gameObject);
                return;
            }
            Instance = this;
            DontDestroyOnLoad(gameObject);
        }

        // React llama a este método al cargar el gemelo digital.
        // Recibe un JSON con el token JWT y el warehouse ID.
        // Ejemplo: { "token": "eyJ...", "warehouseId": "712c785a-..." }
        public void Initialize(string json)
        {
            InitPayload payload = JsonUtility.FromJson<InitPayload>(json);

            if (string.IsNullOrEmpty(payload.token) ||
                string.IsNullOrEmpty(payload.warehouseId))
            {
                Debug.LogError("Initialize: token o warehouseId vacíos.");
                return;
            }

            Debug.Log($"ReactBridge.Initialize — warehouseId: {payload.warehouseId}");

            // Pasar el token al ApiClient y al WebSocketClient
            ApiClient.Instance.SetAuthToken(payload.token);

            // Conectar el WebSocket
            StartCoroutine(ConnectWebSocket(payload.token));

            // Arrancar la generación del almacén
            StartCoroutine(InitWarehouse(payload.warehouseId));
        }

        private IEnumerator ConnectWebSocket(string token)
        {
            Debug.Log($"Intentando conectar WebSocket con token: {token.Substring(0, 20)}...");
            WebSocketClient.Instance.ConnectAsync(token);
            yield break;
        }

        private IEnumerator InitWarehouse(string warehouseId)
        {
            // Pequeña espera para asegurar que el WebSocket está conectado
            yield return new WaitForSeconds(0.5f);

            yield return ApiClient.Instance.GetWarehouseFull(
                warehouseId,
                warehouse => warehouseGenerator.GenerateFromDTO(warehouse),
                error => Debug.LogError($"Error cargando almacén: {error}")
            );
        }

        // React llama a este método cuando el administrador selecciona una tarea.
        // Recibe un JSON con los location IDs implicados en la tarea.
        // Ejemplo: { "locationIds": ["uuid1", "uuid2"] }
        public void HighlightTask(string json)
        {
            TaskHighlightPayload payload =
                JsonUtility.FromJson<TaskHighlightPayload>(json);

            if (payload.locationIds == null) return;

            foreach (string locationId in payload.locationIds)
                warehouseGenerator.HighlightTaskLocation(locationId);
        }

        // React llama a este método para quitar el resaltado de tarea.
        public void ClearHighlight(string json)
        {
            TaskHighlightPayload payload =
                JsonUtility.FromJson<TaskHighlightPayload>(json);

            if (payload.locationIds == null) return;

            foreach (string locationId in payload.locationIds)
                warehouseGenerator.ClearTaskHighlight(locationId);
        }

        public void EnterLocationSelectionMode(string filterJson)
        {
            _selectionMode = true;
            SetFilter(filterJson);
        }

        public void ExitLocationSelectionMode(string _)
        {
            _selectionMode = false;
            warehouseGenerator.ApplyFilter("all");
        }

        public static void NotifyLocationSelected(string locationId, string locationLabel)
        {
            if (Instance == null || !Instance._selectionMode) return;
            string payload = (locationId + "|" + locationLabel).Replace("'", "\\'");
#pragma warning disable CS0618
            Application.ExternalEval($"if(window.onUnityLocationSelected){{window.onUnityLocationSelected('{payload}');}}");
#pragma warning restore CS0618
        }

        public void SetSelectionHighlight(string locationId)
        {
            LocationObject loc = FindLocationObject(locationId);
            if (loc != null) loc.SetSelectionHighlight(true);
        }

        public void ClearSelectionHighlight(string locationId)
        {
            LocationObject loc = FindLocationObject(locationId);
            if (loc != null) loc.SetSelectionHighlight(false);
        }

        private LocationObject FindLocationObject(string locationId)
        {
            foreach (LocationObject loc in FindObjectsOfType<LocationObject>())
                if (loc.LocationId == locationId) return loc;
            return null;
        }

        // React llama a este método para aplicar un filtro visual.
        // Formato: {"type": "all"|"free"|"product"|"box"|"task"}
        //          {"type": "product_id", "value": "uuid"}
        public void SetFilter(string filterJson)
        {
            FilterPayload payload = JsonUtility.FromJson<FilterPayload>(filterJson);
            if (payload == null || string.IsNullOrEmpty(payload.type)) return;

            if (payload.type == "product_id")
            {
                LocationObject[] locs = FindObjectsOfType<LocationObject>();
                foreach (LocationObject loc in locs)
                {
                    bool dimmed = string.IsNullOrEmpty(payload.value) || loc.ProductId != payload.value;
                    loc.SetFilterDim(dimmed);
                }
                return;
            }

            warehouseGenerator.ApplyFilter(payload.type);
        }

        // Clases auxiliares para deserializar los JSON que manda React
        [System.Serializable]
        private class InitPayload
        {
            public string token;
            public string warehouseId;
        }

        [System.Serializable]
        private class TaskHighlightPayload
        {
            public string[] locationIds;
        }

        [System.Serializable]
        private class FilterPayload
        {
            public string type;
            public string value;
        }
    }
}