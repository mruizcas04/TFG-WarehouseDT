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
        [SerializeField] private float minVertical   = 10f;  // ángulo mínimo vertical
        [SerializeField] private float maxVertical   = 80f;  // ángulo máximo vertical

        private float _yaw   = 0f;
        private float _pitch = 35f;

        public void FitToWarehouse(Vector3 center, float size)
        {
            target      = center;
            distance    = size * 1.5f;
            maxDistance = size * 3f;
            minDistance = size * 0.3f;
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
            transform.position  = target + offset;

            // Mirar siempre al target
            transform.LookAt(target);
        }
    }
}