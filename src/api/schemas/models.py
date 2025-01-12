from pydantic import BaseModel, Field
from typing import List, Tuple, Dict, Optional
from datetime import datetime
from .enums import DroneStatus, DeliveryStatus, MaintenanceType

# Base Models
class DroneSpecificationSchema(BaseModel):
    model: str
    max_speed: float = Field(..., gt=0)
    max_payload: float = Field(..., gt=0)
    max_altitude: float = Field(..., gt=0)
    min_altitude: float = Field(..., gt=0)
    max_wind_speed: float = Field(..., gt=0)
    battery_capacity: float = Field(..., gt=0)
    power_consumption_rate: float = Field(..., gt=0)
    
    class Config:
        schema_extra = {
            "example": {
                "model": "DJI-X1",
                "max_speed": 20.0,
                "max_payload": 2.5,
                "max_altitude": 400.0,
                "min_altitude": 50.0,
                "max_wind_speed": 15.0,
                "battery_capacity": 500.0,
                "power_consumption_rate": 100.0
            }
        }

# Drone Models
class DroneCreate(BaseModel):
    initial_position: Tuple[float, float]
    specification: DroneSpecificationSchema

class DroneUpdate(BaseModel):
    specification: Optional[DroneSpecificationSchema]
    maintenance_score: Optional[float] = Field(None, ge=0, le=100)
    status: Optional[DroneStatus]

class DroneResponse(BaseModel):
    id: str
    position: Tuple[float, float]
    altitude: float
    battery_level: float
    status: str
    maintenance_score: float
    component_health: Dict[str, float]
    specification: Dict
    current_delivery: Optional[Dict]
    total_flight_hours: float
    last_maintenance: datetime

    class Config:
        orm_mode = True

# Delivery Models
class DeliveryCreate(BaseModel):
    destination: Tuple[float, float]
    payload_weight: float = Field(..., gt=0, le=10)
    priority: Optional[str] = "normal"
    notes: Optional[str]

    class Config:
        schema_extra = {
            "example": {
                "destination": (37.7749, -122.4194),
                "payload_weight": 2.5,
                "priority": "high",
                "notes": "Fragile package"
            }
        }

class DeliveryUpdate(BaseModel):
    status: Optional[DeliveryStatus]
    notes: Optional[str]
    priority: Optional[str]

class RoutePoint(BaseModel):
    lat: float
    lon: float
    altitude: float
    timestamp: float

class DeliveryResponse(BaseModel):
    delivery_id: int
    drone_id: str
    status: DeliveryStatus
    route: Optional[List[RoutePoint]]
    estimated_delivery_time: Optional[int]
    start_time: datetime
    completion_time: Optional[datetime]
    payload_weight: float
    priority: str
    notes: Optional[str]

    class Config:
        orm_mode = True

# Maintenance Models
class MaintenanceCreate(BaseModel):
    maintenance_type: MaintenanceType
    description: Optional[str]
    scheduled_date: datetime

    class Config:
        schema_extra = {
            "example": {
                "maintenance_type": "routine",
                "description": "Regular 100-hour inspection",
                "scheduled_date": "2024-01-01T10:00:00"
            }
        }

class MaintenanceUpdate(BaseModel):
    status: Optional[str]
    completion_notes: Optional[str]
    completed: Optional[bool]

class MaintenanceResponse(BaseModel):
    id: int
    drone_id: str
    maintenance_type: MaintenanceType
    description: Optional[str]
    scheduled_date: datetime
    completed: bool
    completion_date: Optional[datetime]
    completion_notes: Optional[str]

    class Config:
        orm_mode = True

# Route Models
class RouteUpdate(BaseModel):
    destination: Tuple[float, float]
    waypoints: Optional[List[Tuple[float, float]]]

    class Config:
        schema_extra = {
            "example": {
                "destination": (37.7749, -122.4194),
                "waypoints": [
                    (37.7749, -122.4194),
                    (37.7750, -122.4195)
                ]
            }
        }

# Fleet Models
class FleetStatusResponse(BaseModel):
    total_drones: int
    available_drones: int
    active_deliveries: int
    weather_conditions: Dict
    drones: List[DroneResponse]

class WeatherResponse(BaseModel):
    conditions: Dict
    is_safe_for_flight: bool

    class Config:
        schema_extra = {
            "example": {
                "conditions": {
                    "wind_speed": 5.2,
                    "wind_direction": 180.0,
                    "precipitation": 0.0,
                    "visibility": 10.0,
                    "temperature": 22.5
                },
                "is_safe_for_flight": True
            }
        }

class FleetAnalyticsResponse(BaseModel):
    total_drones: int
    active_drones: int
    available_drones: int
    average_battery_level: float
    total_deliveries: int
    fleet_utilization: float