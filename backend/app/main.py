from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import auth

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

@app.get("/health")
async def health_check():
    return {"status": "ok"}