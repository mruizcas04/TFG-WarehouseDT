using UnityEngine;

namespace WarehouseTwin.Warehouse
{
    // Cámara orbital que permite al administrador rotar la vista
    // arrastrando el ratón y hacer zoom con la rueda.
    // Se añade directamente a la Main Camera.
    public class OrbitCamera : MonoBehaviour
    {
        [Header("Objetivo")]
        [SerializeField] private Vector3 target = new Vector3(3f, 0f, 2f); // centro del almacén

        [Header("Distancia")]
        [SerializeField] private float distance    = 8f;
        [SerializeField] private float minDistance = 3f;
        [SerializeField] private float maxDistance = 20f;
        [SerializeField] private float zoomSpeed   = 2f;

        [Header("Rotación")]
        [SerializeField] private float rotationSpeed = 200f;
        [SerializeField] private float minVertical   = 5f;   // ángulo mínimo (cercano a horizontal)
        [SerializeField] private float maxVertical   = 80f;  // ángulo máximo (mirando casi en vertical)

        [Header("Clamp de posición")]
        [Tooltip("Y mínimo permitido para la cámara (no debe atravesar el suelo).")]
        [SerializeField] private float minCameraY = 1.5f;
        [Tooltip("Y máximo permitido para la cámara (no debe atravesar el techo).")]
        [SerializeField] private float maxCameraY = 12f;

        private float _yaw   = 0f;
        private float _pitch = 35f;

        // Posición inicial guardada para ResetView
        private Vector3 _initialTarget;
        private float   _initialDistance;
        private float   _initialYaw;
        private float   _initialPitch = 35f;
        private bool    _initialSaved;


        public void FitToWarehouse(Vector3 center, float size)
        {
            target      = center;
            distance    = size * 1.5f;
            maxDistance = size * 3f;
            minDistance = size * 0.3f;
            SaveInitialView();
        }

        /// <summary>
        /// Como FitToWarehouse pero clampea maxDistance a un radio máximo
        /// para que la cámara no salga del recinto de las paredes.
        /// </summary>
        public void FitToWarehouse(Vector3 center, float size, float maxRadiusInsideWalls)
        {
            target      = center;
            distance    = Mathf.Min(size * 1.5f, maxRadiusInsideWalls);
            maxDistance = Mathf.Min(size * 3f, maxRadiusInsideWalls);
            minDistance = size * 0.3f;
            SaveInitialView();
        }

        /// <summary>
        /// Configura los límites verticales del almacén (suelo y techo) para clampear el movimiento.
        /// </summary>
        public void SetVerticalBounds(float floorY, float ceilingY, float safetyMargin = 1.5f)
        {
            minCameraY = floorY + safetyMargin;
            maxCameraY = Mathf.Max(ceilingY - safetyMargin, minCameraY + 1f);
        }

        /// <summary>
        /// Configura el rango angular vertical (pitch) permitido. Útil para evitar ángulos exagerados.
        /// </summary>
        public void SetPitchRange(float minPitch, float maxPitch)
        {
            minVertical = minPitch;
            maxVertical = maxPitch;
            _pitch = Mathf.Clamp(_pitch, minVertical, maxVertical);
        }

        /// <summary>
        /// Vuelve a la vista inicial guardada (target, distancia, ángulos).
        /// </summary>
        public void ResetView()
        {
            if (!_initialSaved) return;
            target   = _initialTarget;
            distance = _initialDistance;
            _yaw     = _initialYaw;
            _pitch   = _initialPitch;
        }

        private void SaveInitialView()
        {
            _initialTarget   = target;
            _initialDistance = distance;
            _initialYaw      = _yaw;
            _initialPitch    = _pitch;
            _initialSaved    = true;
        }

        private void LateUpdate()
        {
            // Rotar arrastrando con el botón derecho del ratón
            if (Input.GetMouseButton(1))
            {
                _yaw   += Input.GetAxis("Mouse X") * rotationSpeed * Time.deltaTime;
                _pitch -= Input.GetAxis("Mouse Y") * rotationSpeed * Time.deltaTime;
                _pitch  = Mathf.Clamp(_pitch, minVertical, maxVertical);
            }

            // Zoom con la rueda del ratón
            float scroll = Input.GetAxis("Mouse ScrollWheel");
            distance -= scroll * zoomSpeed;
            distance  = Mathf.Clamp(distance, minDistance, maxDistance);

            // Calcular la posición de la cámara en esféricas
            Quaternion rotation = Quaternion.Euler(_pitch, _yaw, 0f);
            Vector3 offset      = rotation * new Vector3(0f, 0f, -distance);
            Vector3 position    = target + offset;

            // Clampear Y para que no atraviese suelo ni techo. Fallback a 1.5 si no se han configurado los bounds.
            float effectiveMinY = (minCameraY > 0f) ? minCameraY : 1.5f;
            float effectiveMaxY = (maxCameraY > effectiveMinY) ? maxCameraY : effectiveMinY + 20f;
            position.y = Mathf.Clamp(position.y, effectiveMinY, effectiveMaxY);
            transform.position = position;

            // Mirar siempre al target
            transform.LookAt(target);
        }
    }
}