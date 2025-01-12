from dataclasses import dataclass
from typing import Tuple, Dict, Optional, Union
from datetime import datetime
import uuid
import math
from enum import Enum
from .weather import WeatherCondition

class DroneStatus(str, Enum):
    IDLE = "idle"
    IN_TRANSIT = "in_transit"
    DELIVERING = "delivering"
    RETURNING = "returning"
    CHARGING = "charging"
    MAINTENANCE = "maintenance"
    EMERGENCY = "emergency"

@dataclass
class DroneSpecification:
    model: str
    max_speed: float      # meters per second
    max_payload: float    # kilograms
    max_altitude: float   # meters
    min_altitude: float   # meters
    max_wind_speed: float # meters per second
    battery_capacity: float  # watt-hours
    power_consumption_rate: float  # watts per kilometer

class Drone:
    def __init__(
        self,
        position: Tuple[float, float],
        specification: Optional[DroneSpecification] = None
    ):
        self.id = str(uuid.uuid4())
        self.position = position
        self.specification = specification or DroneSpecification(
            model="DJI-X1",
            max_speed=20.0,
            max_payload=2.5,
            max_altitude=400.0,
            min_altitude=50.0,
            max_wind_speed=15.0,
            battery_capacity=500.0,
            power_consumption_rate=100.0
        )
        
        # Core status
        self.battery_level = 100.0
        self._status = DroneStatus.IDLE
        self.altitude = 100.0
        self.maintenance_score = 100.0
        
        # Component health
        self.component_health = {
            "motors": 100.0,
            "battery": 100.0,
            "propellers": 100.0
        }
        
        # Mission details
        self.current_delivery = None
        self.total_flight_hours = 0.0
        self.last_maintenance = datetime.utcnow()

    @property
    def status(self) -> str:
        return self._status.value

    @status.setter
    def status(self, value: Union[str, DroneStatus]):
        if isinstance(value, str):
            self._status = DroneStatus(value)
        else:
            self._status = value

    def get_status(self) -> Dict:
        """Get drone status."""
        return {
            "id": self.id,
            "position": self.position,
            "altitude": self.altitude,
            "battery_level": self.battery_level,
            "status": self.status,
            "maintenance_score": self.maintenance_score,
            "component_health": self.component_health,
            "current_delivery": self.current_delivery,
            "total_flight_hours": self.total_flight_hours,
            "last_maintenance": self.last_maintenance.isoformat(),
            "specification": self.specification.__dict__
        }

    def update_position(self, 
                       new_position: Tuple[float, float],
                       new_altitude: Optional[float] = None,
                       weather: Optional[WeatherCondition] = None) -> bool:
        """Update drone position with safety checks."""
        try:
            # Calculate movement details
            distance = self._calculate_distance(self.position, new_position)
            
            # Safety checks
            if not self._check_safety(new_altitude, weather):
                return False
            
            # Calculate power consumption
            power_consumed = self._calculate_power_consumption(distance, weather)
            if self.battery_level - power_consumed < 20:  # 20% emergency reserve
                self.status = DroneStatus.EMERGENCY
                return False
            
            # Update position and metrics
            self.position = new_position
            if new_altitude is not None:
                self.altitude = new_altitude
            
            self.battery_level -= power_consumed
            self._update_component_health(distance)
            
            return True
            
        except Exception as e:
            print(f"Error updating position: {str(e)}")
            return False

    def _check_safety(self, new_altitude: Optional[float], weather: Optional[WeatherCondition]) -> bool:
        """Basic safety checks."""
        if new_altitude and not (self.specification.min_altitude <= new_altitude <= self.specification.max_altitude):
            return False
            
        if weather:
            if weather.wind_speed > self.specification.max_wind_speed:
                return False
                
        return True

    def _calculate_power_consumption(self, distance: float, weather: Optional[WeatherCondition]) -> float:
        """Calculate power consumption for movement."""
        power = distance * self.specification.power_consumption_rate
        
        if self.current_delivery:
            payload_factor = 1 + (self.current_delivery.get('payload_weight', 0) / 
                                self.specification.max_payload)
            power *= payload_factor
        
        if weather:
            weather_factor = 1 + (weather.wind_speed / self.specification.max_wind_speed)
            power *= weather_factor
            
        return power

    def _calculate_distance(self, point1: Tuple[float, float], point2: Tuple[float, float]) -> float:
        """Calculate distance using Haversine formula."""
        lat1, lon1 = point1
        lat2, lon2 = point2
        
        R = 6371  # Earth's radius in kilometers
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        
        a = (math.sin(dlat/2) * math.sin(dlat/2) +
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
             math.sin(dlon/2) * math.sin(dlon/2))
        
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        return R * c * 1000  # Convert to meters

    def _update_component_health(self, distance: float):
        """Update component health based on usage."""
        wear_factor = distance * 0.0001  # 0.01% wear per kilometer
        
        for component in self.component_health:
            self.component_health[component] = max(
                0,
                self.component_health[component] - wear_factor
            )
        
        self.maintenance_score = sum(self.component_health.values()) / len(self.component_health)

    def start_charging(self) -> bool:
        """Start charging process."""
        if self.status != DroneStatus.IDLE or self.battery_level >= 95:
            return False
        self.status = DroneStatus.CHARGING
        return True

    def charge_battery(self, duration: float) -> float:
        """Charge battery for given duration (hours)."""
        if self.status != DroneStatus.CHARGING:
            return self.battery_level
            
        charge_amount = duration * 20  # 20% per hour
        self.battery_level = min(100, self.battery_level + charge_amount)
        
        if self.battery_level >= 95:
            self.status = DroneStatus.IDLE
            
        return self.battery_level