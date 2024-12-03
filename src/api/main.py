from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import asyncio
from datetime import datetime
import os
from dotenv import load_dotenv

from src.simulation.fleet import FleetManager
from .routes import drone, fleet, delivery
from .dependencies import get_fleet_manager
from src.database.connection import init_db

# Load environment variables
load_dotenv()

app = FastAPI(
    title="DroneFleet API",
    description="API for managing autonomous drone delivery fleet",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(drone.router, prefix="/drones", tags=["drones"])
app.include_router(fleet.router, prefix="/fleet", tags=["fleet"])
app.include_router(delivery.router, prefix="/deliveries", tags=["deliveries"])

# Background task to update fleet status
async def update_fleet_status():
    fleet_manager = get_fleet_manager()
    while True:
        fleet_manager.update_fleet_status()
        await asyncio.sleep(5)

@app.on_event("startup")
async def startup_event():
    # Initialize database
    init_db()
    # Start background task
    asyncio.create_task(update_fleet_status())

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow(),
        "version": "1.0.0"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=os.getenv("API_HOST", "0.0.0.0"),
        port=int(os.getenv("API_PORT", 8000)),
        reload=True
    )