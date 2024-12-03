from pydantic import BaseModel, Field
from typing import List, Tuple, Dict, Optional
from datetime import datetime
from .enums import DroneStatus, DeliveryStatus, MaintenanceType


class FleetAnalyticsResponse(BaseModel):
    total_drones: int
    active_drones: int
    available_drones: int
    average_battery_level: float
    total_deliveries: int
    fleet_utilization: float

# Drone Schemas
class DroneSpecificationSchema(BaseModel):
    model: str
    max_speed: float
    max_battery_life: float
    max_payload: float
    charging_time: float
    max_altitude: float
    min_altitude: float
    max_wind_speed: float
    max_precipitation: float
    battery_capacity: float
    power_consumption_rate: float
    emergency_reserve: float

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

    class Config:
        orm_mode = True

# Delivery Schemas

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

class DeliveryResponse(BaseModel):
    delivery_id: int
    drone_id: str
    status: DeliveryStatus
    route: Optional[List[Tuple[float, float]]]
    estimated_delivery_time: Optional[int]
    start_time: datetime
    completion_time: Optional[datetime]
    payload_weight: float
    priority: str
    notes: Optional[str]

    class Config:
        orm_mode = True

# Fleet Schemas
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
                    "visibility": 10.0
                },
                "is_safe_for_flight": True
            }
        }


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

# Route Schemas
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