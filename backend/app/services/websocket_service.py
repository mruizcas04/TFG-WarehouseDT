from fastapi import WebSocket
import json

class WebSocketService:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, event: str, data: dict):
        message = json.dumps({"event": event, "data": data}, default=str)
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                disconnected.append(connection)
        for connection in disconnected:
            self.disconnect(connection)

    async def broadcast_inventory_updated(self, location_id: str, data: dict):
        await self.broadcast("inventory_updated", {
            "location_id": location_id,
            **data
        })

    async def broadcast_movement_created(self, movement_id: str, data: dict):
        await self.broadcast("movement_created", {
            "movement_id": movement_id,
            **data
        })

    async def broadcast_task_assigned(self, task_id: str, assigned_to: str, origin_location_id: str | None = None, destination_location_id: str | None = None):
        await self.broadcast("task_assigned", {
            "task_id": task_id,
            "assigned_to": assigned_to,
            "origin_location_id": origin_location_id,
            "destination_location_id": destination_location_id,
        })

    async def broadcast_task_status_changed(self, task_id: str, status: str, origin_location_id: str | None = None, destination_location_id: str | None = None):
        await self.broadcast("task_status_changed", {
            "task_id": task_id,
            "status": status,
            "origin_location_id": origin_location_id,
            "destination_location_id": destination_location_id,
        })

websocket_service = WebSocketService()