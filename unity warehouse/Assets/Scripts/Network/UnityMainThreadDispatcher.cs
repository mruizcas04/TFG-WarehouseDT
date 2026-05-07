using System;
using System.Collections;
using System.Collections.Generic;
using UnityEngine;

namespace WarehouseTwin.Network
{
    /// Helper que permite ejecutar código en el hilo principal de Unity
    /// desde hilos secundarios (como el WebSocket).
    
    /// Unity solo permite modificar GameObjects y componentes desde el
    /// hilo principal. Como el WebSocket recibe mensajes en un hilo
    /// secundario, necesitamos este dispatcher para "encolar" las 
    /// acciones y ejecutarlas en el Update() del hilo principal.
    public class UnityMainThreadDispatcher : MonoBehaviour
    {
        // Singleton
        public static UnityMainThreadDispatcher Instance { get; private set; }

        // Cola de acciones pendientes de ejecutar en el hilo principal
        private readonly Queue<Action> _queue = new Queue<Action>();
        private readonly object _lock = new object();

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

        /// Encola una acción para ejecutarla en el próximo Update()
        /// en el hilo principal de Unity.
        public void Enqueue(Action action)
        {
            lock (_lock)
            {
                _queue.Enqueue(action);
            }
        }

        /// Cada frame, ejecuta todas las acciones pendientes en la cola.
        private void Update()
        {
            while (true)
            {
                Action action = null;

                lock (_lock)
                {
                    if (_queue.Count == 0) break;
                    action = _queue.Dequeue();
                }

                try
                {
                    action?.Invoke();
                }
                catch (Exception e)
                {
                    Debug.LogError($"Error ejecutando acción en hilo principal: {e.Message}");
                }
            }
        }
    }
}