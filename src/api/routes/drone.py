from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from ..dependencies import get_db, get_fleet_manager
from ..schemas.models import (
    DroneCreate, DroneUpdate, DroneResponse, 
    MaintenanceCreate, MaintenanceResponse, RouteUpdate
)
from src.database import models
from src.simulation.drone import DroneSpecification, Drone
from ..schemas.enums import DroneStatus

router = APIRouter()

@router.post("/", response_model=DroneResponse, status_code=status.HTTP_201_CREATED)
async def create_drone(
    drone_data: DroneCreate,
    db: Session = Depends(get_db),
    fleet_manager = Depends(get_fleet_manager)
):
    """Create a new drone and add it to the fleet."""
    try:
        # Create specification object
        spec = DroneSpecification(**drone_data.specification.dict())
        
        # Create simulation drone
        simulation_drone = Drone(
            position=drone_data.initial_position,
            specification=spec
        )
        
        # Add to fleet manager
        drone_id = fleet_manager.add_drone(simulation_drone)
        
        # Create database entry
        db_drone = models.Drone(
            id=drone_id,
            model=spec.model,
            status="idle",  
            current_latitude=simulation_drone.position[0],
            current_longitude=simulation_drone.position[1],
            current_altitude=simulation_drone.altitude,
            battery_level=simulation_drone.battery_level,
            maintenance_score=simulation_drone.maintenance_score,
            total_flight_hours=0.0,
            last_maintenance=datetime.utcnow(),
            last_updated=datetime.utcnow(),
            specification=drone_data.specification.dict(),
            component_health=simulation_drone.component_health
        )
        
        db.add(db_drone)
        db.commit()
        db.refresh(db_drone)
        
        return simulation_drone.get_status()
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create drone: {str(e)}"
        )

@router.get("/", response_model=List[DroneResponse])
async def get_all_drones(
    status: Optional[str] = None,
    battery_level_min: Optional[float] = None,
    skip: int = 0,
    limit: int = 100,
    fleet_manager = Depends(get_fleet_manager)
):
    """Get all drones with optional filtering."""
    drones = fleet_manager.get_fleet_status()["drones"]
    
    if status:
        drones = [d for d in drones if d["status"] == status]
    if battery_level_min:
        drones = [d for d in drones if d["battery_level"] >= battery_level_min]
    
    return drones[skip : skip + limit]

@router.get("/{drone_id}", response_model=DroneResponse)
async def get_drone(drone_id: str, fleet_manager = Depends(get_fleet_manager)):
    """Get specific drone details."""
    drone = fleet_manager.get_drone(drone_id)
    if not drone:
        raise HTTPException(status_code=404, detail="Drone not found")
    return drone.get_status()

@router.patch("/{drone_id}", response_model=DroneResponse)
async def update_drone(
    drone_id: str,
    drone_data: DroneUpdate,
    db: Session = Depends(get_db),
    fleet_manager = Depends(get_fleet_manager)
):
    """Update drone properties."""
    drone = fleet_manager.get_drone(drone_id)
    if not drone or drone.status != "idle":
        raise HTTPException(status_code=400, detail="Drone not found or not idle")

    for field, value in drone_data.dict(exclude_unset=True).items():
        if hasattr(drone, field):
            setattr(drone, field, value)
    
    db.query(models.Drone).filter(models.Drone.id == drone_id).update(
        drone_data.dict(exclude_unset=True)
    )
    db.commit()
    return drone.get_status()

@router.delete("/{drone_id}", status_code=204)
async def delete_drone(
    drone_id: str,
    db: Session = Depends(get_db),
    fleet_manager = Depends(get_fleet_manager)
):
    """Remove drone from fleet."""
    drone = fleet_manager.get_drone(drone_id)
    if not drone or drone.status != "idle":
        raise HTTPException(status_code=400, detail="Drone not found or not idle")
    
    fleet_manager.remove_drone(drone_id)
    db.query(models.Drone).filter(models.Drone.id == drone_id).delete()
    db.commit()

@router.post("/{drone_id}/maintenance", response_model=MaintenanceResponse)
async def create_maintenance(
    drone_id: str,
    maintenance: MaintenanceCreate,
    db: Session = Depends(get_db),
    fleet_manager = Depends(get_fleet_manager)
):
    """Schedule maintenance for a drone."""
    drone = fleet_manager.get_drone(drone_id)
    if not drone or not drone.request_maintenance():
        raise HTTPException(status_code=400, detail="Cannot schedule maintenance")
    
    db_maintenance = models.MaintenanceLog(**maintenance.dict(), drone_id=drone_id)
    db.add(db_maintenance)
    db.commit()
    return db_maintenance

@router.patch("/{drone_id}/route")
async def update_route(
    drone_id: str,
    route_data: RouteUpdate,
    fleet_manager = Depends(get_fleet_manager)
):
    """Update drone's current route."""
    drone = fleet_manager.get_drone(drone_id)
    if not drone or drone.status != "in_transit":
        raise HTTPException(status_code=400, detail="Invalid drone state")

    new_route = fleet_manager.route_optimizer.calculate_route(
        start=drone.position,
        end=route_data.destination,
        weather=fleet_manager.weather_simulator.get_conditions(drone.position)
    )
    
    if not new_route:
        raise HTTPException(status_code=400, detail="Could not calculate valid route")
    
    fleet_manager.delivery_routes[drone_id] = new_route
    return {"status": "route updated", "new_route": new_route}

@router.post("/{drone_id}/emergency-return")
async def emergency_return(drone_id: str, fleet_manager = Depends(get_fleet_manager)):
    """Initiate emergency return for a drone."""
    drone = fleet_manager.get_drone(drone_id)
    if not drone:
        raise HTTPException(status_code=404, detail="Drone not found")

    drone.status = DroneStatus.EMERGENCY
    return {"status": "emergency return initiated"}