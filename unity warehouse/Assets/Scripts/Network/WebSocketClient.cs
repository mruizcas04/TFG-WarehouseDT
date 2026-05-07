using System;
using System.Collections;
using System.Net.WebSockets;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using UnityEngine;
using Newtonsoft.Json;
using WarehouseTwin.Data;

namespace WarehouseTwin.Network
{
    /// Gestiona la conexión WebSocket persistente con el backend.
    /// Escucha eventos en tiempo real y notifica al resto de la escena
    /// mediante Actions (callbacks).
    public class WebSocketClient : MonoBehaviour
    {
        // Singleton
        public static WebSocketClient Instance { get; private set; }

        // Eventos a los que se pueden suscribir otros scripts
        // WarehouseGenerator los usará para actualizar el estado visual
        public event Action<WebSocketEventDTO> OnInventoryUpdated;
        public event Action<WebSocketEventDTO> OnMovementCreated;

        [Header("Configuración")]
        [SerializeField] private string wsUrl = "ws://localhost:8000/ws";

        private ClientWebSocket _socket;
        private CancellationTokenSource _cts;
        private bool _isConnected = false;

        // Buffer para recibir mensajes del WebSocket
        private readonly byte[] _buffer = new byte[4096];

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

        /// Conecta al WebSocket del backend usando el token JWT.
        /// Se llama desde WarehouseManager una vez que tenemos el token.
        public async Task ConnectAsync(string authToken)
        {
            if (_isConnected)
            {
                Debug.LogWarning("WebSocket ya está conectado.");
                return;
            }

            try
            {
                _socket = new ClientWebSocket();
                _cts = new CancellationTokenSource();

                // El token se pasa como parámetro en la URL, igual que
                // está definido en el backend: WS /ws?token=...
                Uri uri = new Uri($"{wsUrl}?token={authToken}");

                await _socket.ConnectAsync(uri, _cts.Token);
                _isConnected = true;
                Debug.Log("WebSocket conectado al backend.");

                // Empezar a escuchar mensajes en segundo plano
                _ = ReceiveLoopAsync();
            }
            catch (Exception e)
            {
                Debug.LogError($"Error al conectar WebSocket: {e.Message}");
                _isConnected = false;
            }
        }

        /// Bucle que escucha mensajes entrantes del WebSocket continuamente.
        /// Se ejecuta en segundo plano mientras la conexión esté activa.
        private async Task ReceiveLoopAsync()
        {
            while (_isConnected && _socket.State == WebSocketState.Open)
            {
                try
                {
                    WebSocketReceiveResult result = await _socket.ReceiveAsync(
                        new ArraySegment<byte>(_buffer),
                        _cts.Token
                    );

                    if (result.MessageType == WebSocketMessageType.Close)
                    {
                        Debug.Log("WebSocket cerrado por el servidor.");
                        _isConnected = false;
                        break;
                    }

                    // Convertir los bytes recibidos a string JSON
                    string json = Encoding.UTF8.GetString(_buffer, 0, result.Count);
                    HandleMessage(json);
                }
                catch (OperationCanceledException)
                {
                    // Cancelación normal al cerrar la app
                    break;
                }
                catch (Exception e)
                {
                    Debug.LogError($"Error en WebSocket ReceiveLoop: {e.Message}");
                    _isConnected = false;
                    break;
                }
            }
        }

        /// Procesa el mensaje JSON recibido y lanza el evento correspondiente.
        private void HandleMessage(string json)
        {
            try
            {
                WebSocketEventDTO evt = JsonConvert.DeserializeObject<WebSocketEventDTO>(json);

                Debug.Log($"Evento WebSocket recibido: {evt.type} — location: {evt.location_id}");

                // Despachar el evento en el hilo principal de Unity
                // (los callbacks de Unity deben ejecutarse en el main thread)
                UnityMainThreadDispatcher.Instance.Enqueue(() =>
                {
                    switch (evt.type)
                    {
                        case "inventory_updated":
                            OnInventoryUpdated?.Invoke(evt);
                            break;
                        case "movement_created":
                            OnMovementCreated?.Invoke(evt);
                            break;
                        default:
                            Debug.LogWarning($"Evento WebSocket desconocido: {evt.type}");
                            break;
                    }
                });
            }
            catch (Exception e)
            {
                Debug.LogError($"Error al procesar mensaje WebSocket: {e.Message}");
            }
        }

        /// Cierra la conexión WebSocket limpiamente al destruir el objeto.
        private async void OnDestroy()
        {
            if (_isConnected && _socket != null)
            {
                _cts.Cancel();
                await _socket.CloseAsync(
                    WebSocketCloseStatus.NormalClosure,
                    "Cerrando aplicación",
                    CancellationToken.None
                );
                _socket.Dispose();
                _isConnected = false;
                Debug.Log("WebSocket desconectado.");
            }
        }

        /// Desconecta manualmente el WebSocket.
        public void Disconnect()
        {
            _cts?.Cancel();
            _isConnected = false;
        }
    }
}