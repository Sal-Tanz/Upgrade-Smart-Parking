"""FastAPI main application."""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.database import engine
from api.models.base import Base
from api.routes import vehicles, parking, events, auth_routes, attendance, schedules, detection
from api.services.mqtt_service import mqtt_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await mqtt_service.connect()
    yield
    await mqtt_service.disconnect()


app = FastAPI(
    title="Smart Parking System API",
    description="API backend untuk sistem parkir cerdas dengan ALPR dan IoT",
    version="1.0.0",
    lifespan=lifespan,
)

# Explicit origins are required when credentials are enabled. Set a comma-
# separated list in CORS_ORIGINS for deployment, e.g. frontend URLs.
_cors_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(vehicles.router)
app.include_router(parking.router)
app.include_router(events.router)
app.include_router(auth_routes.router)
app.include_router(detection.router)

try:
    app.include_router(attendance.router)
except ImportError:
    pass

try:
    app.include_router(schedules.router)
except ImportError:
    pass


@app.get("/")
async def root():
    return {"message": "Smart Parking System API", "status": "running"}


@app.get("/health")
async def health():
    return {"status": "healthy"}
