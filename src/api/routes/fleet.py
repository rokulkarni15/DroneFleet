from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
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
    """Get weather conditions for a specific location."""
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        raise HTTPException(status_code=400, detail="Invalid coordinates")

    weather = fleet_manager.weather_simulator.get_conditions((latitude, longitude))
    if not weather:
        raise HTTPException(status_code=404, detail="Weather data not available")
    
    # Check if conditions are safe for flight
    is_safe, warnings = weather.is_safe_for_flight()
    
    return {
        "conditions": weather.to_dict(),
        "is_safe_for_flight": is_safe
    }

@router.get("/analytics", response_model=FleetAnalyticsResponse)
async def get_fleet_analytics(
    time_period: Optional[str] = "24h",
    fleet_manager = Depends(get_fleet_manager)
):
    """Get fleet analytics and metrics."""
    # Get current fleet status
    fleet_status = fleet_manager.get_fleet_status()
    drones = fleet_status["drones"]
    
    # Calculate time-based metrics
    current_time = datetime.utcnow()
    if time_period == "24h":
        time_filter = current_time - timedelta(hours=24)
    elif time_period == "7d":
        time_filter = current_time - timedelta(days=7)
    elif time_period == "30d":
        time_filter = current_time - timedelta(days=30)
    else:
        time_filter = current_time - timedelta(hours=24)  # Default to 24h

    # Calculate metrics
    active_drones = [d for d in drones if d["status"] != "idle"]
    available_drones = [d for d in drones if d["status"] == "idle"]
    battery_levels = [d["battery_level"] for d in drones]
    
    return {
        "total_drones": len(drones),
        "active_drones": len(active_drones),
        "available_drones": len(available_drones),
        "average_battery_level": sum(battery_levels) / len(battery_levels) if battery_levels else 0,
        "total_deliveries": fleet_manager.get_completed_deliveries_count(since=time_filter),
        "fleet_utilization": len(active_drones) / len(drones) if drones else 0
    }

@router.get("/health")
async def get_fleet_health(fleet_manager = Depends(get_fleet_manager)):
    """Get fleet health status."""
    drones = fleet_manager.get_fleet_status()["drones"]
    
    maintenance_needed = [
        {
            "drone_id": d["id"],
            "maintenance_score": d["maintenance_score"],
            "issues": [
                comp for comp, health in d["component_health"].items() 
                if health < 80
            ]
        }
        for d in drones 
        if d["maintenance_score"] < 80
    ]
    
    low_battery = [
        {
            "drone_id": d["id"],
            "battery_level": d["battery_level"]
        }
        for d in drones 
        if d["battery_level"] < 20
    ]
    
    return {
        "fleet_health_score": sum(d["maintenance_score"] for d in drones) / len(drones) if drones else 0,
        "maintenance_needed": maintenance_needed,
        "low_battery_alerts": low_battery,
        "drones_requiring_attention": len(maintenance_needed) + len(low_battery)
    }

@router.get("/metrics")
async def get_fleet_metrics(fleet_manager = Depends(get_fleet_manager)):
    """Get detailed fleet performance metrics."""
    drones = fleet_manager.get_fleet_status()["drones"]
    
    return {
        "performance": {
            "total_flight_hours": sum(d["total_flight_hours"] for d in drones),
            "average_delivery_time": fleet_manager.get_average_delivery_time(),
            "successful_deliveries": fleet_manager.get_completed_deliveries_count(),
            "failed_deliveries": fleet_manager.get_failed_deliveries_count()
        },
        "utilization": {
            "fleet_size": len(drones),
            "active_drones": len([d for d in drones if d["status"] != "idle"]),
            "available_drones": len([d for d in drones if d["status"] == "idle"]),
            "charging_drones": len([d for d in drones if d["status"] == "charging"]),
            "maintenance_drones": len([d for d in drones if d["status"] == "maintenance"])
        }
    }