from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from app.api import auth, warehouses, shelves, locations, products, boxes, inventory, tasks, movements
from app.services.websocket_service import websocket_service
from app.core.security import decode_access_token

app = FastAPI(
    title="Warehouse Digital Twin API",
    description="API para el sistema de gestión de almacenes con gemelo digital",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(warehouses.router)
app.include_router(shelves.router)
app.include_router(locations.router)
app.include_router(products.router)
app.include_router(boxes.router)
app.include_router(inventory.router)
app.include_router(tasks.router)
app.include_router(movements.router)

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str):
    payload = decode_access_token(token)
    if payload is None:
        await websocket.close(code=1008)
        return

    await websocket_service.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        websocket_service.disconnect(websocket)