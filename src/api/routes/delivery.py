from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from ..dependencies import get_db, get_fleet_manager
from ..schemas.models import DeliveryCreate, DeliveryUpdate, DeliveryResponse
from src.database import models

router = APIRouter()

@router.post("/", response_model=DeliveryResponse)
async def create_delivery(
    delivery: DeliveryCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    fleet_manager = Depends(get_fleet_manager)
):
    """Create a new delivery request."""
    drone_id = fleet_manager.assign_delivery(
        destination=delivery.destination,
        payload_weight=delivery.payload_weight
    )
    
    if not drone_id:
        raise HTTPException(status_code=400, detail="No available drones")

    drone = fleet_manager.get_drone(drone_id)
    route = fleet_manager.get_drone_route(drone_id)
    
    db_delivery = models.Delivery(
        drone_id=drone_id,
        status="in_progress",
        start_time=datetime.utcnow(),
        start_latitude=drone.position[0],
        start_longitude=drone.position[1],
        destination_latitude=delivery.destination[0],
        destination_longitude=delivery.destination[1],
        payload_weight=delivery.payload_weight
    )
    db.add(db_delivery)
    db.commit()
    
    return {
        "delivery_id": db_delivery.id,
        "drone_id": drone_id,
        "status": "in_progress",
        "estimated_delivery_time": len(route) * 2 if route else None,
        "route": route
    }

@router.get("/", response_model=List[DeliveryResponse])
async def get_deliveries(
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Get all deliveries with optional filtering."""
    query = db.query(models.Delivery)
    if status:
        query = query.filter(models.Delivery.status == status)
    return query.offset(skip).limit(limit).all()

@router.get("/{delivery_id}", response_model=DeliveryResponse)
async def get_delivery(delivery_id: int, db: Session = Depends(get_db)):
    """Get delivery details."""
    delivery = db.query(models.Delivery).filter(models.Delivery.id == delivery_id).first()
    if not delivery:
        raise HTTPException(status_code=404, detail="Delivery not found")
    return delivery

@router.patch("/{delivery_id}", response_model=DeliveryResponse)
async def update_delivery(
    delivery_id: int,
    delivery_data: DeliveryUpdate,
    db: Session = Depends(get_db)
):
    """Update delivery details."""
    delivery = db.query(models.Delivery).filter(models.Delivery.id == delivery_id).first()
    if not delivery:
        raise HTTPException(status_code=404, detail="Delivery not found")
    
    for field, value in delivery_data.dict(exclude_unset=True).items():
        setattr(delivery, field, value)
    
    db.commit()
    return delivery

@router.delete("/{delivery_id}", status_code=204)
async def cancel_delivery(
    delivery_id: int,
    db: Session = Depends(get_db)
):
    """Cancel a scheduled delivery."""
    delivery = db.query(models.Delivery).filter(models.Delivery.id == delivery_id).first()
    if not delivery or delivery.status not in ["scheduled", "pending"]:
        raise HTTPException(status_code=400, detail="Cannot cancel delivery")
    
    delivery.status = "cancelled"
    delivery.completion_time = datetime.utcnow()
    db.commit()