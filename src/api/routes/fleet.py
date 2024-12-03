from fastapi import APIRouter, HTTPException, Depends
from typing import Optional, List
from datetime import datetime, timedelta

from ..dependencies import get_fleet_manager
from ..schemas.models import (
    FleetStatusResponse, WeatherResponse, FleetAnalyticsResponse
)

router = APIRouter()

@router.get("/status", response_model=FleetStatusResponse)
async def get_fleet_status(fleet_manager = Depends(get_fleet_manager)):
    """Get current fleet status."""
    return fleet_manager.get_fleet_status()

@router.get("/weather", response_model=WeatherResponse)
async def get_weather(
    latitude: float,
    longitude: float,
    fleet_manager = Depends(get_fleet_manager)
):
    """Get weather conditions for a location."""
    weather = fleet_manager.weather_simulator.get_conditions((latitude, longitude))
    if not weather:
        raise HTTPException(status_code=404, detail="Weather data not available")
    
    return {
        "conditions": weather,
        "is_safe_for_flight": fleet_manager.weather_simulator.is_safe_for_flight(weather)
    }

@router.get("/analytics", response_model=FleetAnalyticsResponse)
async def get_fleet_analytics(fleet_manager = Depends(get_fleet_manager)):
    fleet_status = fleet_manager.get_fleet_status()
    drones = fleet_status["drones"]
    
    return {
        "total_drones": len(drones),
        "active_drones": len([d for d in drones if d["status"] != "idle"]),
        "available_drones": len([d for d in drones if d["status"] == "idle"]),
        "average_battery_level": sum(d["battery_level"] for d in drones) / len(drones) if drones else 0,
        "total_deliveries": len([d for d in drones if d["current_delivery"] is not None]),
        "fleet_utilization": len([d for d in drones if d["status"] != "idle"]) / len(drones) if drones else 0
    }