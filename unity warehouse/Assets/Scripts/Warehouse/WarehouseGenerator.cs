using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using WarehouseTwin.Data;
using WarehouseTwin.Network;

namespace WarehouseTwin.Warehouse
{
    public class WarehouseGenerator : MonoBehaviour
    {
        [Header("Configuración del almacén")]
        [SerializeField] private string warehouseId;

        [Header("Dimensiones de los elementos (metros)")]
        [Tooltip("Ancho de cada ubicación (eje del pasillo). 1.2m = ancho de un palet europeo.")]
        [SerializeField] private float shelfWidth = 1.2f;
        [Tooltip("Altura de cada balda. 1.5m permite encajar cajas/palets de tamaño realista.")]
        [SerializeField] private float shelfHeight = 1.5f;
        [Tooltip("Profundidad de la estantería (eje transversal al pasillo). 1.0m = profundidad palet europeo.")]
        [SerializeField] private float shelfDepth = 1.0f;
        [Tooltip("Distancia entre pasillos (centro a centro). 3.5m permite paso de carretilla.")]
        [SerializeField] private float aisleSpacing = 3.5f;
        [SerializeField] private float locationPadding = 0.05f;

        [Header("Prefabs")]
        [SerializeField] private GameObject locationPrefab;
        [Tooltip("Poste vertical del rack (ej: stand_vertical del pack). Opcional — si está vacío no se renderiza estructura.")]
        [SerializeField] private GameObject rackPostPrefab;
        [Tooltip("Rotación euler en grados que se aplica a cada poste al instanciarlo. Por defecto (0,90,0) igual que la viga, para que el frame del poste quede perpendicular a la dirección del pasillo.")]
        [SerializeField] private Vector3 rackPostRotationEuler = new Vector3(0, 90, 0);
        [Tooltip("Si está activo, escala el poste en Y para que coincida con la altura del almacén. Si está desactivado, usa la altura nativa del FBX (el poste sobresale por arriba, más realista).")]
        [SerializeField] private bool scalePostToWarehouseHeight = false;
        [Tooltip("Altura nativa del poste vertical (en metros). Solo se usa si scalePostToWarehouseHeight está activado.")]
        [SerializeField] private float rackPostNativeHeight = 7.778f;
        [Tooltip("Viga horizontal del rack (ej: stand_horizontal_long). Se escala en eje Z para cubrir el largo de la estantería.")]
        [SerializeField] private GameObject rackBeamPrefab;
        [Tooltip("Rotación euler en grados que se aplica a cada viga al instanciarla. Por defecto (0,90,0) porque los FBX del pack suelen tener su eje largo en X — esta rotación lo alinea con Z, donde mi código espera el largo.")]
        [SerializeField] private Vector3 rackBeamRotationEuler = new Vector3(0, 90, 0);
        [Tooltip("Longitud nativa de la viga horizontal (en metros). Se usa para calcular la escala. Mide el prefab original en Unity y rellena aquí.")]
        [SerializeField] private float rackBeamNativeLength = 5.5f;

        [Header("Espacio libre alrededor (metros)")]
        [SerializeField] private float margin = 8.0f;
        [SerializeField] private float wallExtraHeight = 5.0f;
        [SerializeField] private float shelfGap = 1.0f;

        [Header("Materiales (opcional)")]
        [SerializeField] private Material floorMaterial;
        [SerializeField] private Material wallMaterial;

        private Dictionary<string, LocationObject> _locationObjects = new();

        private void Start()
        {
            WebSocketClient.Instance.OnInventoryUpdated += HandleInventoryUpdated;
            WebSocketClient.Instance.OnMovementCreated += HandleMovementCreated;
            WebSocketClient.Instance.OnTaskAssigned += HandleTaskAssigned;
            WebSocketClient.Instance.OnTaskStatusChanged += HandleTaskStatusChanged;
        }

        private void OnDestroy()
        {
            if (WebSocketClient.Instance != null)
            {
                WebSocketClient.Instance.OnInventoryUpdated -= HandleInventoryUpdated;
                WebSocketClient.Instance.OnMovementCreated -= HandleMovementCreated;
                WebSocketClient.Instance.OnTaskAssigned -= HandleTaskAssigned;
                WebSocketClient.Instance.OnTaskStatusChanged -= HandleTaskStatusChanged;
            }
        }

        public void ApplyFilter(string filterType)
        {
            foreach (var kvp in _locationObjects)
            {
                LocationObject loc = kvp.Value;
                bool dimmed = filterType switch
                {
                    "all"     => false,
                    "free"    => loc.CurrentState != LocationState.Free,
                    "product" => loc.CurrentState != LocationState.Product,
                    "box"     => loc.CurrentState != LocationState.Box,
                    "task"    => loc.CurrentState != LocationState.Task,
                    _         => false
                };
                loc.SetFilterDim(dimmed);
            }
        }

        public void GenerateFromDTO(WarehouseDTO warehouse)
        {
            Debug.Log($"Generando almacén: {warehouse.name}");

            _locationObjects.Clear();
            foreach (Transform child in transform)
                Destroy(child.gameObject);

            // Precomputar ubicaciones con tarea activa
            var activeTaskSet = new HashSet<string>();
            if (warehouse.active_task_locations != null)
            {
                foreach (string id in warehouse.active_task_locations)
                    activeTaskSet.Add(id);
            }

            // --- Pre-pasada: posición X por pasillo (dobles pegados, normales con aisleSpacing) ---
            var aislesWithDouble = new HashSet<int>();
            var sortedAisleNums  = new SortedSet<int>();
            foreach (ShelfDTO s in warehouse.shelves)
            {
                sortedAisleNums.Add(s.aisle_number);
                if (s.is_double) aislesWithDouble.Add(s.aisle_number);
            }
            var aisleXPos = new Dictionary<int, float>();
            float xCursor = 0f;
            int prevA = -1;
            foreach (int a in sortedAisleNums)
            {
                if (prevA < 0)
                    aisleXPos[a] = 0f;
                else if (aislesWithDouble.Contains(prevA))
                    aisleXPos[a] = xCursor + shelfDepth + locationPadding;
                else
                    aisleXPos[a] = xCursor + aisleSpacing;
                xCursor = aisleXPos[a];
                prevA = a;
            }

            // --- Primera pasada: calcular dimensiones totales ---
            int maxAisle = 0;
            int maxLevels = 0;
            Dictionary<int, float> aisleLengths = new();

            foreach (ShelfDTO shelf in warehouse.shelves)
            {
                maxAisle = Mathf.Max(maxAisle, shelf.aisle_number);
                maxLevels = Mathf.Max(maxLevels, shelf.levels.Count);

                if (!aisleLengths.ContainsKey(shelf.aisle_number))
                    aisleLengths[shelf.aisle_number] = 0f;

                int numLocs = shelf.levels.Count > 0 ? shelf.levels[0].locations.Count : 0;
                aisleLengths[shelf.aisle_number] += numLocs * (shelfWidth + locationPadding) + 0.3f;
            }

            float maxLength = 0f;
            foreach (float l in aisleLengths.Values)
                maxLength = Mathf.Max(maxLength, l - 0.3f);

            // Límites reales de las estanterías (los cubos tienen pivot en el centro)
            float halfDepth = shelfDepth / 2f;
            float halfWidth = (shelfWidth - locationPadding) / 2f;
            float boundsMinX = -halfDepth;
            float boundsMaxX = (maxAisle - 1) * aisleSpacing + halfDepth;
            float boundsMinZ = -halfWidth;
            float boundsMaxZ = maxLength + halfWidth;


            float wallThickness = 0.3f;
            float wallHeight = maxLevels * shelfHeight + wallExtraHeight;
            float floorThickness = 0.2f;

            float fMinX = boundsMinX - margin;
            float fMaxX = boundsMaxX + margin;
            float fMinZ = boundsMinZ - margin;
            float fMaxZ = boundsMaxZ + margin;
            float fW = fMaxX - fMinX;
            float fL = fMaxZ - fMinZ;
            float fCX = (fMinX + fMaxX) / 2f;
            float fCZ = (fMinZ + fMaxZ) / 2f;

            // --- Suelo ---
            GameObject floor = GameObject.CreatePrimitive(PrimitiveType.Cube);
            floor.name = "Floor";
            floor.transform.SetParent(transform);
            floor.transform.localScale = new Vector3(fW, floorThickness, fL);
            floor.transform.localPosition = new Vector3(fCX, -floorThickness / 2f, fCZ);
            if (floorMaterial != null)
                floor.GetComponent<Renderer>().material = floorMaterial;

            // --- Paredes ---
            CreateWall("Wall_Front", fCX, wallHeight / 2f, fMinZ - wallThickness / 2f,
                new Vector3(fW + wallThickness * 2f, wallHeight, wallThickness));
            CreateWall("Wall_Back", fCX, wallHeight / 2f, fMaxZ + wallThickness / 2f,
                new Vector3(fW + wallThickness * 2f, wallHeight, wallThickness));
            CreateWall("Wall_Left", fMinX - wallThickness / 2f, wallHeight / 2f, fCZ,
                new Vector3(wallThickness, wallHeight, fL));
            CreateWall("Wall_Right", fMaxX + wallThickness / 2f, wallHeight / 2f, fCZ,
                new Vector3(wallThickness, wallHeight, fL));

            // --- Segunda pasada: generar estanterías ---
            // Offset Y para que el nivel 1 apoye en el suelo (pivot de los cubos en centro)
            float groundOffset = (shelfHeight - locationPadding) / 2f;
            Dictionary<int, float> aisleZOffset = new();
            // Almacena las Z de las estanterías dobles del pasillo frontal para sincronizar la trasera
            var frontDoubleZ = new Dictionary<int, List<float>>();
            var backShelfIdx = new Dictionary<int, int>();

            foreach (ShelfDTO shelf in warehouse.shelves)
            {
                int aisle = shelf.aisle_number;

                if (!aisleZOffset.ContainsKey(aisle))
                    aisleZOffset[aisle] = 0f;

                bool isDoubleBack = aislesWithDouble.Contains(aisle - 1);

                float placedX = aisleXPos[aisle];
                float placedZ;
                if (isDoubleBack)
                {
                    if (!backShelfIdx.ContainsKey(aisle)) backShelfIdx[aisle] = 0;
                    placedZ = frontDoubleZ[aisle - 1][backShelfIdx[aisle]];
                    backShelfIdx[aisle]++;
                }
                else
                {
                    placedZ = aisleZOffset[aisle];
                }

                int numLocations = shelf.levels.Count > 0 ? shelf.levels[0].locations.Count : 0;
                float shelfLength = numLocations * (shelfWidth + locationPadding);

                GameObject shelfGO = new GameObject($"Shelf_Aisle{aisle}_Shelf{shelf.shelf_number}");
                shelfGO.transform.SetParent(transform);
                shelfGO.transform.localPosition = new Vector3(placedX, groundOffset, placedZ);
                if (isDoubleBack)
                    shelfGO.transform.localRotation = Quaternion.Euler(0, 180f, 0);

                foreach (LevelDTO level in shelf.levels)
                {
                    float levelY = (level.level_number - 1) * shelfHeight;

                    GameObject levelGO = new GameObject($"Level_{level.level_number}");
                    levelGO.transform.SetParent(shelfGO.transform);
                    levelGO.transform.localPosition = new Vector3(0, levelY, 0);

                    foreach (LocationDTO location in level.locations)
                    {
                        float locationZ = (location.position_number - 1) * (shelfWidth + locationPadding);

                        GameObject locationGO = Instantiate(locationPrefab, levelGO.transform);
                        locationGO.name = $"Location_{location.position_number}";
                        locationGO.transform.localPosition = new Vector3(0, 0, locationZ);

                        LocationObject locObj = locationGO.GetComponent<LocationObject>();
                        locObj.Initialize(location.id, LocationObject.StateFromInventory(location.inventory));
                        locObj.SetCellSize(new Vector3(
                            shelfDepth - locationPadding,
                            shelfHeight - locationPadding,
                            shelfWidth - locationPadding
                        ));

                        bool   hasTask  = activeTaskSet.Contains(location.id);
                        bool   isBox    = !string.IsNullOrEmpty(location.inventory?.box_id);
                        int    qty      = location.inventory?.quantity ?? 0;
                        string prodId   = location.inventory?.product_id ?? "";
                        string prodName = location.inventory?.product_name ?? "";
                        string barcode       = location.inventory?.product_barcode ?? "";
                        string category      = location.inventory?.product_category ?? "";
                        string categoryColor = location.inventory?.product_category_color ?? "";
                        string taskInfo = "";
                        if (hasTask)
                        {
                            string taskType = null;
                            warehouse.active_task_info?.TryGetValue(location.id, out taskType);
                            taskInfo = taskType != null ? $"Tarea activa: {taskType}" : "Tarea activa";
                        }
                        locObj.SetMetadata(prodName, qty, isBox, taskInfo, prodId, barcode, category, categoryColor);
                        locObj.LocationLabel = $"F{aisle} · E{shelf.shelf_number} · B{level.level_number} · H{location.position_number}";

                        _locationObjects[location.id] = locObj;
                    }
                }

                BuildRackStructure(shelfGO, shelf.levels.Count, shelfLength);

                if (!isDoubleBack)
                {
                    // Guardar Z de estanterías dobles frontales para sincronizar la trasera
                    if (shelf.is_double)
                    {
                        if (!frontDoubleZ.ContainsKey(aisle)) frontDoubleZ[aisle] = new List<float>();
                        frontDoubleZ[aisle].Add(placedZ);
                    }
                    aisleZOffset[aisle] += shelfLength + shelfGap;
                }
            }

            // Pintar en amarillo las ubicaciones con tareas activas
            foreach (string locationId in activeTaskSet)
            {
                if (_locationObjects.TryGetValue(locationId, out LocationObject locObj))
                    locObj.SetState(LocationState.Task);
            }

            // Ajustar cámara al almacén generado
            float centerX = (boundsMinX + boundsMaxX) / 2f;
            float centerZ = (boundsMinZ + boundsMaxZ) / 2f;
            float size    = Mathf.Max(boundsMaxX - boundsMinX, boundsMaxZ - boundsMinZ);
            OrbitCamera cam = Camera.main != null ? Camera.main.GetComponent<OrbitCamera>() : null;
            if (cam != null) cam.FitToWarehouse(new Vector3(centerX, 0f, centerZ), size);

            Debug.Log($"Almacén generado: {_locationObjects.Count} ubicaciones.");
        }

        private void CreateWall(string wallName, float x, float y, float z, Vector3 scale)
        {
            GameObject wall = GameObject.CreatePrimitive(PrimitiveType.Cube);
            wall.name = wallName;
            wall.transform.SetParent(transform);
            wall.transform.localPosition = new Vector3(x, y, z);
            wall.transform.localScale = scale;
            if (wallMaterial != null)
                wall.GetComponent<Renderer>().material = wallMaterial;
        }

        /// <summary>
        /// Instancia postes verticales en los extremos de la estantería y vigas horizontales en
        /// la base de cada nivel. No-op si rackPostPrefab no está asignado (modo legacy).
        /// </summary>
        private void BuildRackStructure(GameObject shelfGO, int numLevels, float shelfLength)
        {
            if (rackPostPrefab == null) return;

            // En el espacio local del shelfGO: Y=0 es el centro del nivel 1 (por el groundOffset que
            // se aplica al posicionar el shelfGO). El suelo del nivel 1 está en Y = -groundOffset.
            float groundY = -((shelfHeight - locationPadding) / 2f);

            // Las ubicaciones se colocan a lo largo de Z. La primera tiene su centro en Z=0,
            // así que el borde frontal de la estantería está en Z = -shelfWidth/2.
            float startZ = -(shelfWidth - locationPadding) / 2f;
            float endZ   = startZ + shelfLength;

            // Escalado vertical del poste: solo si el usuario lo activa explícitamente
            float postYScale = 1f;
            if (scalePostToWarehouseHeight && rackPostNativeHeight > 0.01f)
            {
                float postTargetHeight = numLevels * shelfHeight;
                postYScale = postTargetHeight / rackPostNativeHeight;
            }

            // Postes en los extremos
            InstantiatePost(shelfGO, "Post_Start", new Vector3(0, groundY, startZ), postYScale);
            InstantiatePost(shelfGO, "Post_End",   new Vector3(0, groundY, endZ),   postYScale);

            // Vigas: una por nivel, en la base. Rotadas para alinear su eje largo nativo con Z, y escaladas en Z para cubrir shelfLength.
            if (rackBeamPrefab != null && rackBeamNativeLength > 0.01f)
            {
                float beamScale = shelfLength / rackBeamNativeLength;
                Quaternion beamRotation = Quaternion.Euler(rackBeamRotationEuler);
                for (int lv = 0; lv < numLevels; lv++)
                {
                    float levelBottomY = lv * shelfHeight + groundY;
                    GameObject beam = Instantiate(rackBeamPrefab, shelfGO.transform);
                    beam.name = $"Beam_Level{lv + 1}";
                    beam.transform.localPosition = new Vector3(0, levelBottomY, startZ);
                    beam.transform.localRotation = beamRotation;
                    Vector3 s = beam.transform.localScale;
                    beam.transform.localScale = new Vector3(s.x, s.y, s.z * beamScale);
                }
            }
        }

        private void InstantiatePost(GameObject parent, string name, Vector3 localPosition, float yScale)
        {
            GameObject post = Instantiate(rackPostPrefab, parent.transform);
            post.name = name;
            post.transform.localPosition = localPosition;
            post.transform.localRotation = Quaternion.Euler(rackPostRotationEuler);
            Vector3 s = post.transform.localScale;
            post.transform.localScale = new Vector3(s.x, s.y * yScale, s.z);
        }

        private void HandleInventoryUpdated(WebSocketEventDTO evt)
        {
            if (!string.IsNullOrEmpty(evt.data?.destination_location_id))
            {
                if (_locationObjects.TryGetValue(evt.data.destination_location_id, out LocationObject dest))
                    dest.SetState(ParseLocationState(evt.data.destination_state));
            }
            if (!string.IsNullOrEmpty(evt.data?.origin_location_id))
            {
                if (_locationObjects.TryGetValue(evt.data.origin_location_id, out LocationObject origin))
                    origin.SetState(ParseLocationState(evt.data.origin_state));
            }
        }

        private void HandleMovementCreated(WebSocketEventDTO evt)
        {
            HandleInventoryUpdated(evt);
            UpdateLocationMetadata(evt.data?.destination_location_id, evt.data?.destination_inventory);
            UpdateLocationMetadata(evt.data?.origin_location_id, evt.data?.origin_inventory);
        }

        private void UpdateLocationMetadata(string locationId, InventoryItemDTO inv)
        {
            if (string.IsNullOrEmpty(locationId)) return;
            if (!_locationObjects.TryGetValue(locationId, out LocationObject locObj)) return;

            if (inv == null)
            {
                locObj.SetMetadata("", 0, false, locObj.TaskInfo, "");
                return;
            }

            bool isBox = !string.IsNullOrEmpty(inv.box_id);
            int qty = inv.quantity ?? 0;
            locObj.SetMetadata(inv.product_name ?? "", qty, isBox, locObj.TaskInfo, inv.product_id ?? "", inv.product_barcode ?? "", inv.product_category ?? "", inv.product_category_color ?? "");
        }

        private static LocationState ParseLocationState(string state) => state switch
        {
            "box" => LocationState.Box,
            "product" => LocationState.Product,
            _ => LocationState.Free,
        };

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

        private void HandleTaskAssigned(WebSocketEventDTO evt)
        {
            Debug.Log($"HandleTaskAssigned llamado — dest: {evt.data?.destination_location_id} — origin: {evt.data?.origin_location_id}");
            HighlightLocation(evt.data?.destination_location_id, LocationState.Task);
            HighlightLocation(evt.data?.origin_location_id, LocationState.Task);
        }

        private void HandleTaskStatusChanged(WebSocketEventDTO evt)
        {
            // Si la tarea se completa o cancela, quitar el amarillo
            string status = evt.data?.status;
            if (status == "completada" || status == "cancelada")
            {
                // Restaurar al color real consultando el estado actual
                RestoreLocation(evt.data?.destination_location_id);
                RestoreLocation(evt.data?.origin_location_id);
                Debug.Log($"Tarea {status} — restaurando colores");
            }
            else if (status == "en_curso")
            {
                // Mantener amarillo mientras está en curso
                HighlightLocation(evt.data?.destination_location_id, LocationState.Task);
                HighlightLocation(evt.data?.origin_location_id, LocationState.Task);
            }
        }

        private void HighlightLocation(string locationId, LocationState state)
        {
            if (string.IsNullOrEmpty(locationId)) return;
            Debug.Log($"HighlightLocation — buscando: {locationId} — encontrado: {_locationObjects.ContainsKey(locationId)}");
            if (_locationObjects.TryGetValue(locationId, out LocationObject locObj))
                locObj.SetState(state);
        }

        private void RestoreLocation(string locationId)
        {
            if (string.IsNullOrEmpty(locationId)) return;
            if (_locationObjects.TryGetValue(locationId, out LocationObject locObj))
                locObj.SetState(LocationState.Free); // simplificación — podría consultarse el inventario real
        }
    }
}
