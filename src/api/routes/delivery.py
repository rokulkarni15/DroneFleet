from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, status
from sqlalchemy.orm import Session
from typing import List, Optional, Tuple
from datetime import datetime, timedelta

from src.api.schemas.enums import DeliveryStatus, DeliveryPriority
from src.api.dependencies import get_db, get_fleet_manager
from src.api.schemas.models import DeliveryCreate, DeliveryUpdate, DeliveryResponse
from src.database import models
from src.simulation.route import RoutePoint

router = APIRouter()

@router.post("/", response_model=DeliveryResponse)
async def create_delivery(
    delivery: DeliveryCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    fleet_manager = Depends(get_fleet_manager)
):
    """Create a new delivery request with optimized route."""
    try:
        print("Starting delivery creation...")
        
        # Validate input coordinates
        if not _validate_coordinates(delivery.destination):
            raise HTTPException(status_code=400, detail="Invalid destination coordinates")

        # Get available drone
        drone_id = fleet_manager.assign_delivery(
            destination=delivery.destination,
            payload_weight=delivery.payload_weight
        )
        
        if not drone_id:
            raise HTTPException(status_code=400, detail="No available drones")

        print(f"Delivery assigned to drone: {drone_id}")
        
        # Get route
        drone = fleet_manager.get_drone(drone_id)
        route = fleet_manager.get_drone_route(drone_id)
        
        if not route:
            print("Warning: No route calculated")
            current_time = datetime.utcnow()
            route = [
                RoutePoint(
                    position=drone.position,
                    altitude=100.0,
                    time=current_time
                ),
                RoutePoint(
                    position=delivery.destination,
                    altitude=100.0,
                    time=current_time + timedelta(minutes=2)
                )
            ]

        # Calculate total distance and estimated time
        total_distance = 0
        for i in range(len(route)-1):
            start_point = route[i].position
            end_point = route[i+1].position
            segment_distance = fleet_manager.route_optimizer._calculate_distance(start_point, end_point)
            total_distance += segment_distance

        # Calculate estimated delivery time based on drone speed and distance
        avg_speed = drone.specification.max_speed * 0.7  # 70% of max speed for safety
        flight_time = (total_distance / avg_speed) * 60  # Convert to minutes
        buffer_time = 4  # Buffer time for takeoff/landing
        estimated_time = int(flight_time) + buffer_time

        print(f"Route calculated - Distance: {total_distance:.2f}km, Estimated time: {estimated_time} minutes")

        # Format route for storage
        route_json = [
            {
                "lat": float(point.position[0]),
                "lon": float(point.position[1]),
                "altitude": float(point.altitude),
                "timestamp": point.time.timestamp()
            }
            for point in route
        ]

        # Create delivery record
        try:
            db_delivery = models.Delivery(
                drone_id=drone_id,
                status=DeliveryStatus.IN_PROGRESS,
                start_time=datetime.utcnow(),
                start_latitude=float(drone.position[0]),
                start_longitude=float(drone.position[1]),
                destination_latitude=float(delivery.destination[0]),
                destination_longitude=float(delivery.destination[1]),
                payload_weight=float(delivery.payload_weight),
                priority=delivery.priority,
                notes=delivery.notes,
                route=route_json,
                estimated_delivery_time=estimated_time
            )

            db.add(db_delivery)
            db.commit()
            db.refresh(db_delivery)

        except Exception as e:
            db.rollback()
            print(f"Database error: {str(e)}")
            raise HTTPException(status_code=500, detail="Database error occurred")

        # Prepare response
        response_data = {
            "delivery_id": db_delivery.id,
            "drone_id": drone_id,
            "status": DeliveryStatus.IN_PROGRESS.value,
            "route": route_json,
            "estimated_delivery_time": estimated_time,
            "start_time": db_delivery.start_time,
            "completion_time": None,
            "payload_weight": delivery.payload_weight,
            "priority": delivery.priority,
            "notes": delivery.notes
        }

        print("Delivery created successfully")
        return response_data

    except HTTPException:
        raise
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

def _validate_coordinates(coords: Tuple[float, float]) -> bool:
    """Validate latitude and longitude coordinates."""
    try:
        lat, lon = coords
        return -90 <= lat <= 90 and -180 <= lon <= 180
    except Exception:
        return False

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