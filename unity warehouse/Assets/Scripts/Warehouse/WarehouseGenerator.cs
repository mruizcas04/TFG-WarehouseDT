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
        [Tooltip("Hueco extra (en metros) entre la estantería frontal y trasera de un shelf doble. En realidad las dos comparten postes centrales, pero como mi código instancia estructuras separadas, necesitan separación visual. 0.5m suele bastar.")]
        [SerializeField] private float doubleShelfExtraGap = 0.5f;
        [Tooltip("Margen entre el suelo y la primera balda (en metros). Realista — los racks de verdad tienen 15-30cm de hueco abajo. Con este margen activo, en un poste de altura X caben menos niveles (lógico).")]
        [SerializeField] private float levelBaseClearance = 0.2f;

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
        [Tooltip("Extensión extra de la viga en cada extremo (metros). Útil para cerrar el hueco visible entre el final de la viga y el poste cuando el pivot del FBX no cae exacto. Empieza con 0.1 y ajusta.")]
        [SerializeField] private float rackBeamExtraLength = 0.1f;

        [Header("Espacio libre alrededor (metros)")]
        [Tooltip("Margen entre el rack y las paredes. Súbelo si la cámara choca con las paredes.")]
        [SerializeField] private float margin = 15.0f;
        [SerializeField] private float wallExtraHeight = 5.0f;
        [SerializeField] private float shelfGap = 1.0f;

        [Header("Materiales fallback (solo si no asignas prefabs)")]
        [SerializeField] private Material floorMaterial;
        [SerializeField] private Material wallMaterial;

        [Header("Entorno — prefabs del pack (opcional)")]
        [Tooltip("Prefab del suelo (ej. floor_5x5). Si está asignado se tilea para cubrir el almacén. Si está vacío, usa un cubo primitivo con floorMaterial.")]
        [SerializeField] private GameObject floorPrefab;
        [Tooltip("Tamaño nativo del prefab de suelo (lado del cuadrado, en metros). 5 para floor_5x5, 2.5 para floor_2.5x2.5.")]
        [SerializeField] private float floorTileSize = 5f;
        [Tooltip("Prefab de pared (ej. wall_1_neat). Se tilea horizontalmente y se escala vertical para cubrir la altura del almacén.")]
        [SerializeField] private GameObject wallPrefab;
        [Tooltip("Ancho nativo del prefab de pared (en metros). Mide con el truco del Box Collider.")]
        [SerializeField] private float wallTileWidth = 5f;
        [Tooltip("Altura nativa del prefab de pared (en metros). Se escala en Y para cubrir wallHeight.")]
        [SerializeField] private float wallTileHeight = 5f;
        [Tooltip("Rotación euler base aplicada a los prefabs de pared. Ajusta si las paredes salen mirando hacia fuera del almacén — prueba (0,180,0).")]
        [SerializeField] private Vector3 wallRotationOffset = Vector3.zero;
        [Tooltip("Offset vertical (en metros) sumado a la posición Y de las paredes. Útil si el pivot del FBX no está en la base — sube/baja hasta que las paredes lleguen al suelo y al techo.")]
        [SerializeField] private float wallYOffset = 0f;
        [Tooltip("Cuánto se extienden las paredes por encima de la altura del almacén (en metros). Sirve para que tapen cualquier hueco con el techo sin importar el pivot del FBX. 0.5-1m suele bastar.")]
        [SerializeField] private float wallTopOverlap = 0.3f;

        [Header("Techo (plano lados + curvo centro)")]
        [Tooltip("Prefab del techo plano (ej. roof_flat). Se usa en los lados del almacén.")]
        [SerializeField] private GameObject roofFlatPrefab;
        [Tooltip("Prefab del techo curvo (ej. roof_round). Se usa en el strip central del almacén.")]
        [SerializeField] private GameObject roofRoundPrefab;
        [Tooltip("Prefab de claraboya (ej. roof_window). Se intercala en el strip central.")]
        [SerializeField] private GameObject roofWindowPrefab;
        [Tooltip("Tamaño nativo de cada tile del techo (cuadrado, en metros).")]
        [SerializeField] private float roofTileSize = 5f;
        [Tooltip("Ancho del strip central curvo (en metros). El resto a cada lado se cubre con roof plano.")]
        [SerializeField] private float roofRoundStripWidth = 5f;
        [Tooltip("Si está activo, el strip curvo va a lo largo del eje X. Si no, a lo largo del eje Z.")]
        [SerializeField] private bool roofRoundStripAlongX = true;
        [Tooltip("Cada cuántos tiles del strip curvo se pone una claraboya. 0 = sin claraboyas.")]
        [SerializeField] private int roofWindowEvery = 3;
        [Tooltip("Offset vertical de TODO el techo (en metros). Sube/baja si no encaja con las paredes.")]
        [SerializeField] private float roofYOffset = 0f;
        [Tooltip("Offset Y EXTRA solo para los tiles del techo curvo. Útil si el pivot del roof_round está a distinta altura que el del roof_flat. Positivo para subirlo, negativo para bajarlo.")]
        [SerializeField] private float roofRoundExtraY = 0f;
        [Tooltip("Offset horizontal X de TODO el techo (en metros). Para nudgear si los tiles no cuadran con las paredes.")]
        [SerializeField] private float roofXOffset = 0f;
        [Tooltip("Offset horizontal Z de TODO el techo (en metros). Para nudgear si los tiles no cuadran con las paredes.")]
        [SerializeField] private float roofZOffset = 0f;
        [Tooltip("Rotación euler de los tiles del techo plano.")]
        [SerializeField] private Vector3 roofFlatRotation = Vector3.zero;
        [Tooltip("Rotación euler de los tiles del techo curvo (y claraboyas).")]
        [SerializeField] private Vector3 roofRoundRotation = Vector3.zero;
        [Tooltip("Prefab de lámpara (ej. lamp_1). Si está vacío no se colocan lámparas.")]
        [SerializeField] private GameObject lampPrefab;
        [Tooltip("Distancia entre lámparas (en metros, ambas direcciones).")]
        [SerializeField] private float lampSpacing = 10f;
        [Tooltip("Cuánto bajan las lámparas (en metros). 0 = pegadas al techo lógico (wallHeight), 0.5 = colgando 50cm por debajo.")]
        [SerializeField] private float lampDropFromCeiling = 0.5f;
        [Tooltip("Si está activo, añade un Light component real a cada lámpara para iluminar la escena.")]
        [SerializeField] private bool lampsEmitLight = true;
        [Tooltip("Color de la luz emitida por las lámparas. Blanco para máxima luminosidad, tonos cálidos para ambiente acogedor.")]
        [SerializeField] private Color lampLightColor = new Color(1f, 0.97f, 0.90f);
        [Tooltip("Intensidad de cada lámpara. Sube hasta 2-3 si necesitas más luz.")]
        [SerializeField] private float lampLightIntensity = 2.0f;
        [Tooltip("Rango de la luz de cada lámpara (metros). Aumentar reduce zonas oscuras entre lámparas.")]
        [SerializeField] private float lampLightRange = 15f;
        [Tooltip("Tipo de sombras que proyectan las lámparas. None = más rápido pero todo plano. Soft = bonito pero pesado en WebGL con muchas lámparas.")]
        [SerializeField] private LightShadows lampShadows = LightShadows.None;

        [Header("Puertas (opcional)")]
        [Tooltip("Prefab de puerta (ej. door_single o door_double). Si está vacío no se colocan puertas.")]
        [SerializeField] private GameObject doorPrefab;
        [SerializeField] private bool doorOnFrontWall = true;
        [SerializeField] private bool doorOnBackWall  = true;
        [SerializeField] private bool doorOnLeftWall  = false;
        [SerializeField] private bool doorOnRightWall = false;
        [Tooltip("Rotación euler base aplicada a las puertas. Ajusta si la puerta queda al revés.")]
        [SerializeField] private Vector3 doorRotation = Vector3.zero;
        [Tooltip("Offset vertical de la puerta (metros). Útil si el pivot no está en la base.")]
        [SerializeField] private float doorYOffset = 0f;
        [Tooltip("Escala uniforme para las puertas. Si quedan muy pequeñas respecto a la pared, sube a 2 o 3.")]
        [SerializeField] private float doorScale = 2f;

        [Header("Paredes con ventana (opcional)")]
        [Tooltip("Prefab de pared con ventana (ej. wall_2_one). Si está asignado, sustituye cada N tiles de pared.")]
        [SerializeField] private GameObject wallWindowedPrefab;
        [Tooltip("Cada cuántos tiles de pared se pone uno con ventana (empezando por el segundo). 0 = nunca. Valor bajo (2-3) garantiza ventanas en paredes cortas.")]
        [SerializeField] private int wallWindowedEvery = 2;



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

        /// <summary>
        /// Limpia cualquier filtro/highlight activo en todas las ubicaciones.
        /// El parámetro filterType se mantiene por compatibilidad pero ya se ignora — los filtros
        /// por estado (free/product/box/task) fueron retirados, solo queda el filtro por producto
        /// que se aplica vía SetFilterHighlight en cada ubicación.
        /// </summary>
        public void ApplyFilter(string filterType)
        {
            foreach (var kvp in _locationObjects)
            {
                LocationObject loc = kvp.Value;
                loc.SetFilterDim(false);
                loc.SetFilterHighlight(false);
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
                    aisleXPos[a] = xCursor + shelfDepth + locationPadding + doubleShelfExtraGap;
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
            if (floorPrefab != null && floorTileSize > 0.01f)
            {
                BuildFloorTiles(fMinX, fMaxX, fMinZ, fMaxZ);
            }
            else
            {
                GameObject floor = GameObject.CreatePrimitive(PrimitiveType.Cube);
                floor.name = "Floor";
                floor.transform.SetParent(transform);
                floor.transform.localScale = new Vector3(fW, floorThickness, fL);
                floor.transform.localPosition = new Vector3(fCX, -floorThickness / 2f, fCZ);
                if (floorMaterial != null)
                    floor.GetComponent<Renderer>().material = floorMaterial;
            }

            // --- Paredes ---
            if (wallPrefab != null && wallTileWidth > 0.01f && wallTileHeight > 0.01f)
            {
                BuildWallTiles(fMinX, fMaxX, fMinZ, fMaxZ, wallHeight);
            }
            else
            {
                CreateWall("Wall_Front", fCX, wallHeight / 2f, fMinZ - wallThickness / 2f,
                    new Vector3(fW + wallThickness * 2f, wallHeight, wallThickness));
                CreateWall("Wall_Back", fCX, wallHeight / 2f, fMaxZ + wallThickness / 2f,
                    new Vector3(fW + wallThickness * 2f, wallHeight, wallThickness));
                CreateWall("Wall_Left", fMinX - wallThickness / 2f, wallHeight / 2f, fCZ,
                    new Vector3(wallThickness, wallHeight, fL));
                CreateWall("Wall_Right", fMaxX + wallThickness / 2f, wallHeight / 2f, fCZ,
                    new Vector3(wallThickness, wallHeight, fL));
            }

            // --- Puertas (opcional) ---
            if (doorPrefab != null)
            {
                BuildDoors(fMinX, fMaxX, fMinZ, fMaxZ);
            }

            // --- Techo (3 strips: plano + curvo + plano) ---
            if (roofFlatPrefab != null && roofTileSize > 0.01f)
            {
                BuildRoof(fMinX, fMaxX, fMinZ, fMaxZ, wallHeight);
            }

            // --- Lámparas (opcional) ---
            if (lampPrefab != null && lampSpacing > 0.01f)
            {
                BuildLamps(fMinX, fMaxX, fMinZ, fMaxZ, wallHeight);
            }

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
                // Nota: antes rotaba 180° en Y al shelf back-doble para que las cajas miraran al pasillo opuesto,
                // pero eso también invertía el eje Z de su estructura interna y desalineaba postes/vigas con el frontal.
                // Como los palets/cajas del pack son simétricos, quitarlo no cambia nada visualmente y arregla la alineación.

                foreach (LevelDTO level in shelf.levels)
                {
                    float levelY = (level.level_number - 1) * shelfHeight + levelBaseClearance;

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

                // Tracking común (también para back-doubles) para que los carteles del fondo se calculen bien
                if (!aisleZOffset.ContainsKey(aisle)) aisleZOffset[aisle] = 0f;
                aisleZOffset[aisle] += shelfLength + shelfGap;

                if (!isDoubleBack && shelf.is_double)
                {
                    if (!frontDoubleZ.ContainsKey(aisle)) frontDoubleZ[aisle] = new List<float>();
                    frontDoubleZ[aisle].Add(placedZ);
                }
            }

            // Pintar en amarillo las ubicaciones con tareas activas
            foreach (string locationId in activeTaskSet)
            {
                if (_locationObjects.TryGetValue(locationId, out LocationObject locObj))
                    locObj.SetState(LocationState.Task);
            }

            // Ajustar cámara al almacén generado.
            // Limitamos la distancia máxima para que la cámara nunca salga del recinto de las paredes.
            // Limitamos también Y para que la cámara no atraviese ni suelo ni techo.
            float centerX = (boundsMinX + boundsMaxX) / 2f;
            float centerZ = (boundsMinZ + boundsMaxZ) / 2f;
            float size    = Mathf.Max(boundsMaxX - boundsMinX, boundsMaxZ - boundsMinZ);
            float maxRadiusInsideWalls = size / 2f + margin - 2f;
            OrbitCamera cam = Camera.main != null ? Camera.main.GetComponent<OrbitCamera>() : null;
            if (cam != null)
            {
                cam.SetVerticalBounds(0f, wallHeight, 1.5f);
                cam.SetPitchRange(15f, 65f);
                cam.FitToWarehouse(new Vector3(centerX, 0f, centerZ), size, maxRadiusInsideWalls);
            }

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
        /// Tilea el prefab del suelo cubriendo el área dada. Crea floor tiles en grid.
        /// </summary>
        private void BuildFloorTiles(float minX, float maxX, float minZ, float maxZ)
        {
            int tilesX = Mathf.CeilToInt((maxX - minX) / floorTileSize);
            int tilesZ = Mathf.CeilToInt((maxZ - minZ) / floorTileSize);

            for (int i = 0; i < tilesX; i++)
            {
                for (int j = 0; j < tilesZ; j++)
                {
                    float cx = minX + i * floorTileSize + floorTileSize / 2f;
                    float cz = minZ + j * floorTileSize + floorTileSize / 2f;
                    GameObject tile = Instantiate(floorPrefab, transform);
                    tile.name = $"Floor_{i}_{j}";
                    tile.transform.localPosition = new Vector3(cx, 0, cz);
                }
            }
        }

        /// <summary>
        /// Tilea paredes a lo largo de los 4 lados del almacén. Tilea horizontalmente, escala en Y para cubrir wallHeight + overlap.
        /// Asume pivot del FBX en la base (Y=0). Si el FBX tiene pivot en el centro, usa wallYOffset.
        /// </summary>
        private void BuildWallTiles(float minX, float maxX, float minZ, float maxZ, float wallHeight)
        {
            // Las paredes se extienden wallTopOverlap más allá de wallHeight para tapar cualquier hueco con el techo.
            float effectiveWallHeight = wallHeight + wallTopOverlap;
            float yScale  = effectiveWallHeight / wallTileHeight;
            float wallY   = wallYOffset;
            Quaternion baseRot = Quaternion.Euler(wallRotationOffset);

            // Pared FRONT (Z=minZ, interior en +Z): sin rotación, cara +Z del prefab queda mirando al interior.
            TileWall(minX, maxX, "Front", wallY, minZ, baseRot, yScale, axisAlongX: true);
            // Pared BACK (Z=maxZ, interior en -Z): rotada 180° en Y para que su cara +Z mire al interior.
            TileWall(minX, maxX, "Back", wallY, maxZ, baseRot * Quaternion.Euler(0, 180, 0), yScale, axisAlongX: true);
            // Pared LEFT (X=minX, interior en +X): rotada +90° en Y para que su cara +Z mire al interior.
            TileWall(minZ, maxZ, "Left", wallY, minX, baseRot * Quaternion.Euler(0, 90, 0), yScale, axisAlongX: false);
            // Pared RIGHT (X=maxX, interior en -X): rotada -90° en Y para que su cara +Z mire al interior.
            TileWall(minZ, maxZ, "Right", wallY, maxX, baseRot * Quaternion.Euler(0, -90, 0), yScale, axisAlongX: false);
        }

        private void TileWall(float axisMin, float axisMax, string side, float cy, float perpendicularCoord, Quaternion rotation, float yScale, bool axisAlongX)
        {
            float wallLength = axisMax - axisMin;
            int numTiles = Mathf.CeilToInt(wallLength / wallTileWidth);
            // Estiramos cada tile ligeramente para que el total cubra EXACTAMENTE axisMin..axisMax (sin overshoot).
            float effectiveTileWidth = wallLength / numTiles;
            float horizontalScale    = effectiveTileWidth / wallTileWidth;

            for (int i = 0; i < numTiles; i++)
            {
                float center = axisMin + i * effectiveTileWidth + effectiveTileWidth / 2f;

                // Sustituir por pared con ventana en posiciones intermedias.
                // Para paredes de 2 tiles o menos: una ventana en el tile central.
                // Para paredes más largas: cada wallWindowedEvery tiles empezando por el tile 1 (no en esquinas).
                bool useWindowed = false;
                if (wallWindowedPrefab != null && wallWindowedEvery > 0)
                {
                    if (numTiles <= 2)
                        useWindowed = (i == numTiles / 2);
                    else
                        useWindowed = (i > 0 && i < numTiles - 1) && ((i - 1) % wallWindowedEvery == 0);
                }
                GameObject prefab = useWindowed ? wallWindowedPrefab : wallPrefab;

                GameObject tile = Instantiate(prefab, transform);
                tile.name = useWindowed ? $"Wall_{side}_Win_{i}" : $"Wall_{side}_{i}";
                tile.transform.localPosition = axisAlongX
                    ? new Vector3(center, cy, perpendicularCoord)
                    : new Vector3(perpendicularCoord, cy, center);
                tile.transform.localRotation = rotation;
                Vector3 s = tile.transform.localScale;
                tile.transform.localScale = new Vector3(s.x * horizontalScale, s.y * yScale, s.z);
            }
        }

        /// <summary>
        /// Coloca puertas en las paredes seleccionadas, centradas en cada pared.
        /// La puerta se superpone al tile de pared (no esculpe el hueco).
        /// </summary>
        private void BuildDoors(float minX, float maxX, float minZ, float maxZ)
        {
            if (doorPrefab == null) return;
            float midX = (minX + maxX) / 2f;
            float midZ = (minZ + maxZ) / 2f;
            float y    = doorYOffset;
            Quaternion baseRot = Quaternion.Euler(doorRotation);

            if (doorOnFrontWall)  PlaceDoor("Door_Front", midX, y, minZ, baseRot);
            if (doorOnBackWall)   PlaceDoor("Door_Back",  midX, y, maxZ, baseRot * Quaternion.Euler(0, 180, 0));
            if (doorOnLeftWall)   PlaceDoor("Door_Left",  minX, y, midZ, baseRot * Quaternion.Euler(0, 90,  0));
            if (doorOnRightWall)  PlaceDoor("Door_Right", maxX, y, midZ, baseRot * Quaternion.Euler(0, -90, 0));
        }

        private void PlaceDoor(string name, float x, float y, float z, Quaternion rotation)
        {
            GameObject door = Instantiate(doorPrefab, transform);
            door.name = name;
            door.transform.localPosition = new Vector3(x, y, z);
            door.transform.localRotation = rotation;
            Vector3 s = door.transform.localScale;
            door.transform.localScale = new Vector3(s.x * doorScale, s.y * doorScale, s.z * doorScale);
        }

        /// <summary>
        /// Construye el techo en 3 strips: plano-curvo-plano. El curvo va centrado a lo largo del eje configurado.
        /// Las claraboyas (roof_window) se intercalan en el strip curvo.
        /// </summary>
        private void BuildRoof(float minX, float maxX, float minZ, float maxZ, float ceilingY)
        {
            // Todo el techo plano. Sin strips ni curvas. Tilea roofFlatPrefab cubriendo el área entera.
            float y = ceilingY + roofYOffset;
            Quaternion flatRot = Quaternion.Euler(roofFlatRotation);
            BuildRoofStrip(minX, maxX, minZ, maxZ, y, roofFlatPrefab, null, flatRot, flatRot, "Flat");
        }

        /// <summary>
        /// Tilea un strip del techo cubriendo (minX..maxX, minZ..maxZ) a altura y.
        /// Si windowPrefab != null, intercala claraboyas cada roofWindowEvery tiles.
        /// Aplica roofXOffset y roofZOffset a las posiciones para nudgear el techo si no cuadra.
        /// </summary>
        private void BuildRoofStrip(float minX, float maxX, float minZ, float maxZ, float y,
                                    GameObject basePrefab, GameObject windowPrefab,
                                    Quaternion baseRot, Quaternion windowRot, string namePrefix)
        {
            if (basePrefab == null) return;
            int tilesX = Mathf.CeilToInt((maxX - minX) / roofTileSize);
            int tilesZ = Mathf.CeilToInt((maxZ - minZ) / roofTileSize);
            float effTileX = (maxX - minX) / tilesX;
            float effTileZ = (maxZ - minZ) / tilesZ;
            float scaleX = effTileX / roofTileSize;
            float scaleZ = effTileZ / roofTileSize;
            int tileIndex = 0;

            for (int i = 0; i < tilesX; i++)
            {
                for (int j = 0; j < tilesZ; j++)
                {
                    bool useWindow = windowPrefab != null && roofWindowEvery > 0 && tileIndex % roofWindowEvery == 0;
                    GameObject prefab = useWindow ? windowPrefab : basePrefab;
                    Quaternion rot    = useWindow ? windowRot   : baseRot;

                    float cx = minX + i * effTileX + effTileX / 2f + roofXOffset;
                    float cz = minZ + j * effTileZ + effTileZ / 2f + roofZOffset;
                    GameObject tile = Instantiate(prefab, transform);
                    tile.name = useWindow ? $"Roof_Window_{namePrefix}_{i}_{j}" : $"Roof_{namePrefix}_{i}_{j}";
                    tile.transform.localPosition = new Vector3(cx, y, cz);
                    tile.transform.localRotation = rot;
                    Vector3 s = tile.transform.localScale;
                    tile.transform.localScale = new Vector3(s.x * scaleX, s.y, s.z * scaleZ);
                    tileIndex++;
                }
            }
        }

        /// <summary>
        /// Coloca lámparas en grid colgando del techo lógico (a la altura wallHeight - drop).
        /// Si hay techo curvo configurado, las lámparas QUE CAERÍAN sobre el strip curvo se OMITEN
        /// (sólo cuelgan del techo plano).
        /// </summary>
        private void BuildLamps(float minX, float maxX, float minZ, float maxZ, float ceilingY)
        {
            int lampsX = Mathf.FloorToInt((maxX - minX) / lampSpacing);
            int lampsZ = Mathf.FloorToInt((maxZ - minZ) / lampSpacing);
            if (lampsX < 1) lampsX = 1;
            if (lampsZ < 1) lampsZ = 1;

            // Distribuir lámparas centradas en el almacén
            float spreadX = (lampsX - 1) * lampSpacing;
            float spreadZ = (lampsZ - 1) * lampSpacing;
            float startX  = (minX + maxX) / 2f - spreadX / 2f;
            float startZ  = (minZ + maxZ) / 2f - spreadZ / 2f;
            float lampY   = ceilingY - lampDropFromCeiling;

            for (int i = 0; i < lampsX; i++)
            {
                for (int j = 0; j < lampsZ; j++)
                {
                    float lampX = startX + i * lampSpacing;
                    float lampZ = startZ + j * lampSpacing;

                    GameObject lamp = Instantiate(lampPrefab, transform);
                    lamp.name = $"Lamp_{i}_{j}";
                    lamp.transform.localPosition = new Vector3(lampX, lampY, lampZ);

                    if (lampsEmitLight)
                    {
                        Light l = lamp.AddComponent<Light>();
                        l.type      = LightType.Point;
                        l.color     = lampLightColor;
                        l.intensity = lampLightIntensity;
                        l.range     = lampLightRange;
                        l.shadows   = lampShadows;
                    }
                }
            }
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

            // Escalado vertical del poste: solo si el usuario lo activa explícitamente.
            // El poste debe cubrir desde el suelo hasta encima del último nivel — incluye clearance inferior.
            float postYScale = 1f;
            if (scalePostToWarehouseHeight && rackPostNativeHeight > 0.01f)
            {
                float postTargetHeight = numLevels * shelfHeight + levelBaseClearance;
                postYScale = postTargetHeight / rackPostNativeHeight;
            }

            // Postes en los extremos
            InstantiatePost(shelfGO, "Post_Start", new Vector3(0, groundY, startZ), postYScale);
            InstantiatePost(shelfGO, "Post_End",   new Vector3(0, groundY, endZ),   postYScale);

            // Vigas: una por nivel, centradas entre los postes (pivot en el centro del FBX).
            // Rotadas para alinear su eje largo nativo con Z, y escaladas en local-X para extender la longitud
            // (en Unity, el scale se aplica ANTES de la rotación, así que escalamos el eje largo NATIVO, no el rotado).
            if (rackBeamPrefab != null && rackBeamNativeLength > 0.01f)
            {
                float beamLength = shelfLength + 2f * rackBeamExtraLength;
                float beamScale  = beamLength / rackBeamNativeLength;
                float beamMidZ   = (startZ + endZ) / 2f;
                Quaternion beamRotation = Quaternion.Euler(rackBeamRotationEuler);
                for (int lv = 0; lv < numLevels; lv++)
                {
                    float levelBottomY = lv * shelfHeight + groundY + levelBaseClearance;
                    GameObject beam = Instantiate(rackBeamPrefab, shelfGO.transform);
                    beam.name = $"Beam_Level{lv + 1}";
                    beam.transform.localPosition = new Vector3(0, levelBottomY, beamMidZ);
                    beam.transform.localRotation = beamRotation;
                    Vector3 s = beam.transform.localScale;
                    beam.transform.localScale = new Vector3(s.x * beamScale, s.y, s.z);
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
