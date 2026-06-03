using System;
using System.Collections;
using UnityEngine;
using UnityEngine.Networking;
using Newtonsoft.Json;
using WarehouseTwin.Data;

namespace WarehouseTwin.Network
{
    public class ApiClient : MonoBehaviour
    {
        [Header("Configuración")]
        [SerializeField] private string baseUrl = "http://localhost:8000";

        [Header("Solo para testing en el editor")]
        [SerializeField] private string debugToken;

        private string _authToken;

        public static ApiClient Instance { get; private set; }

        private void Awake()
        {
            if (Instance != null && Instance != this)
            {
                Destroy(gameObject);
                return;
            }
            Instance = this;
            DontDestroyOnLoad(gameObject);

            // Si hay un token de debug en el Inspector, usarlo directamente
            if (!string.IsNullOrEmpty(debugToken))
                _authToken = debugToken;
        }

        public void SetAuthToken(string token)
        {
            _authToken = token;
        }

        public IEnumerator GetWarehouseFull(
            string warehouseId,
            Action<WarehouseDTO> onSuccess,
            Action<string> onError)
        {
            string url = $"{baseUrl}/warehouses/{warehouseId}/full";

            using UnityWebRequest request = UnityWebRequest.Get(url);

            request.SetRequestHeader("Authorization", $"Bearer {_authToken}");
            request.SetRequestHeader("Content-Type", "application/json");

            yield return request.SendWebRequest();

            if (request.result != UnityWebRequest.Result.Success)
            {
                string error = $"Error al obtener el almacén: {request.error} (código {request.responseCode})";
                Debug.LogError(error);
                onError?.Invoke(error);
                yield break;
            }

            try
            {
                string json = request.downloadHandler.text;
                WarehouseDTO warehouse = JsonConvert.DeserializeObject<WarehouseDTO>(json);
                Debug.Log($"Almacén cargado: {warehouse.name} ({warehouse.num_shelves} estanterías)");
                onSuccess?.Invoke(warehouse);
            }
            catch (Exception e)
            {
                string error = $"Error al deserializar el almacén: {e.Message}";
                Debug.LogError(error);
                onError?.Invoke(error);
            }
        }
    }
}