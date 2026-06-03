using System;
using System.Text;
using UnityEngine;
using Newtonsoft.Json;
using NativeWebSocket;
using WarehouseTwin.Data;

namespace WarehouseTwin.Network
{
    public class WebSocketClient : MonoBehaviour
    {
        public static WebSocketClient Instance { get; private set; }

        public event Action<WebSocketEventDTO> OnInventoryUpdated;
        public event Action<WebSocketEventDTO> OnMovementCreated;
        public event Action<WebSocketEventDTO> OnTaskAssigned;
        public event Action<WebSocketEventDTO> OnTaskStatusChanged;

        [Header("Configuración")]
        [SerializeField] private string wsUrl = "wss://tfg-production-1c10.up.railway.app";

        private WebSocket _socket;
        private bool _isConnected = false;

        private void Awake()
        {
            if (Instance != null && Instance != this) { Destroy(gameObject); return; }
            Instance = this;
            DontDestroyOnLoad(gameObject);
        }

        private void Update()
        {
            #if !UNITY_WEBGL || UNITY_EDITOR
                _socket?.DispatchMessageQueue();
            #endif
        }

        public async void ConnectAsync(string authToken)
        {
            if (_isConnected)
            {
                Debug.LogWarning("WebSocket ya está conectado.");
                return;
            }

            string url = $"{wsUrl}?token={authToken}";
            _socket = new WebSocket(url);

            _socket.OnOpen += () =>
            {
                _isConnected = true;
                Debug.Log("WebSocket conectado al backend.");
            };

            _socket.OnMessage += (bytes) =>
            {
                string json = Encoding.UTF8.GetString(bytes);
                HandleMessage(json);
            };

            _socket.OnError += (error) =>
            {
                Debug.LogError($"WebSocket error: {error}");
                _isConnected = false;
            };

            _socket.OnClose += (code) =>
            {
                _isConnected = false;
                Debug.Log($"WebSocket cerrado. Código: {code}");
            };

            Debug.Log($"Conectando WebSocket a {url}");
            await _socket.Connect();
        }

        private void HandleMessage(string json)
        {
            try
            {
                WebSocketEventDTO evt = JsonConvert.DeserializeObject<WebSocketEventDTO>(json);
                Debug.Log($"Evento WebSocket: {evt.@event}");

                switch (evt.@event)
                {
                    case "inventory_updated":
                        OnInventoryUpdated?.Invoke(evt);
                        break;
                    case "movement_created":
                        OnMovementCreated?.Invoke(evt);
                        break;
                    case "task_assigned":
                        OnTaskAssigned?.Invoke(evt);
                        break;
                    case "task_status_changed":
                        OnTaskStatusChanged?.Invoke(evt);
                        break;
                    default:
                        Debug.LogWarning($"Evento WebSocket desconocido: {evt.@event}");
                        break;
                }
            }
            catch (Exception e)
            {
                Debug.LogError($"Error al procesar mensaje WebSocket: {e.Message}");
            }
        }

        private async void OnDestroy()
        {
            if (_isConnected && _socket != null)
            {
                await _socket.Close();
                Debug.Log("WebSocket desconectado.");
            }
        }
    }
}