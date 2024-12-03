from dataclasses import dataclass
from typing import Tuple, Dict, Optional, List, Union
from datetime import datetime
import uuid
import math
from enum import Enum

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
            max_battery_life=30.0,
            max_payload=2.5,
            charging_time=20.0,
            max_altitude=400.0,
            min_altitude=50.0,
            max_wind_speed=15.0,
            max_precipitation=5.0,
            battery_capacity=500.0,
            power_consumption_rate=100.0,
            emergency_reserve=20.0
        )
        
        # Core status attributes
        self.battery_level = 100.0
        self._status = DroneStatus.IDLE
        self.altitude = 100.0
        self.heading = 0.0
        self.speed = 0.0
        self.maintenance_score = 100.0
        
        # Health monitoring
        self.component_health = {
            "motors": 100.0,
            "battery": 100.0,
            "propellers": 100.0,
            "controllers": 100.0,
            "sensors": 100.0
        }
        
        # Delivery attributes
        self.current_delivery: Optional[Dict] = None
        self.current_route: Optional[List[Tuple[float, float]]] = None
        self.route_index: int = 0
        
        # Monitoring
        self.telemetry_history: List[Dict] = []
        self.last_updated = datetime.now()
        self.last_position = position
        self.emergency_status: Optional[str] = None
        self.total_flight_hours = 0.0
        self.last_maintenance = datetime.now()

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
        """Get comprehensive drone status."""
        return {
            "id": self.id,
            "position": self.position,
            "altitude": self.altitude,
            "battery_level": self.battery_level,
            "status": self.status,
            "maintenance_score": self.maintenance_score,
            "component_health": self.component_health,
            "current_delivery": self.current_delivery,
            "emergency_status": self.emergency_status,
            "last_updated": self.last_updated.isoformat(),
            "total_flight_hours": self.total_flight_hours,
            "last_maintenance": self.last_maintenance.isoformat(),
            "specification": self.specification.__dict__
        }

    def update_position(self, 
                       new_position: Tuple[float, float],
                       new_altitude: Optional[float] = None,
                       weather_conditions: Optional[Dict] = None) -> bool:
        """Update drone position and status considering weather and obstacles."""
        try:
            distance = self._calculate_distance(self.position, new_position)
            
            if new_altitude is not None and not self._is_safe_altitude(new_altitude):
                return False
                
            if weather_conditions and not self._is_safe_weather(weather_conditions):
                self._initiate_weather_safety_protocol(weather_conditions)
                return False
            
            power_consumed = self._calculate_power_consumption(
                distance,
                self.altitude,
                weather_conditions
            )
            
            if not self._has_sufficient_power(power_consumed):
                self._initiate_low_battery_protocol()
                return False
            
            self.last_position = self.position
            self.position = new_position
            if new_altitude is not None:
                self.altitude = new_altitude
            self.battery_level -= power_consumed
            self.last_updated = datetime.now()
            
            self._update_component_health(distance)
            self._record_telemetry()
            
            return True
            
        except Exception as e:
            self.emergency_status = f"Position update failed: {str(e)}"
            self.status = DroneStatus.EMERGENCY
            return False

    def _calculate_power_consumption(self, 
                                   distance: float,
                                   altitude: float,
                                   weather: Optional[Dict] = None) -> float:
        """Calculate power consumption based on distance, altitude, and weather."""
        power = distance * self.specification.power_consumption_rate
        altitude_factor = 1 + (altitude / 1000) * 0.1
        power *= altitude_factor
        
        if weather:
            wind_speed = weather.get('wind_speed', 0)
            wind_factor = 1 + (wind_speed / self.specification.max_wind_speed) * 0.2
            power *= wind_factor
        
        if self.current_delivery:
            payload_factor = 1 + (self.current_delivery['payload_weight'] / 
                                self.specification.max_payload) * 0.3
            power *= payload_factor
        
        return power

    def _calculate_distance(self, point1: Tuple[float, float], point2: Tuple[float, float]) -> float:
        """Calculate distance between two points using Haversine formula."""
        lat1, lon1 = point1
        lat2, lon2 = point2
        
        R = 6371  # Earth's radius in kilometers
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        
        a = (math.sin(dlat/2) * math.sin(dlat/2) +
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
             math.sin(dlon/2) * math.sin(dlon/2))
        
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        return R * c

    def _update_component_health(self, distance_traveled: float) -> None:
        """Update component health based on usage."""
        flight_time = (datetime.now() - self.last_updated).total_seconds() / 3600
        self.total_flight_hours += flight_time
        
        wear_factor = (distance_traveled * 0.01) + (flight_time * 0.1)
        
        for component in self.component_health:
            random_wear = math.sin(self.total_flight_hours) * 0.1
            self.component_health[component] = max(
                0,
                self.component_health[component] - wear_factor - random_wear
            )
        
        self.maintenance_score = sum(self.component_health.values()) / len(self.component_health)

    def _record_telemetry(self) -> None:
        """Record telemetry data."""
        telemetry = {
            "timestamp": datetime.now(),
            "position": self.position,
            "altitude": self.altitude,
            "battery_level": self.battery_level,
            "status": self.status,
            "maintenance_score": self.maintenance_score,
            "component_health": self.component_health.copy()
        }
        
        self.telemetry_history.append(telemetry)
        if len(self.telemetry_history) > 1000:
            self.telemetry_history.pop(0)

    def _is_safe_altitude(self, altitude: float) -> bool:
        """Check if altitude is safe."""
        return self.specification.min_altitude <= altitude <= self.specification.max_altitude

    def _is_safe_weather(self, weather: Dict) -> bool:
        """Check if weather conditions are safe."""
        return (
            weather.get('wind_speed', 0) <= self.specification.max_wind_speed and
            weather.get('precipitation', 0) <= self.specification.max_precipitation
        )

    def _has_sufficient_power(self, power_needed: float) -> bool:
        """Check if drone has sufficient power."""
        return (self.battery_level - power_needed) >= self.specification.emergency_reserve

    def _initiate_weather_safety_protocol(self, weather: Dict) -> None:
        """Handle unsafe weather conditions."""
        self.emergency_status = f"Unsafe weather: Wind={weather.get('wind_speed')}m/s, " \
                              f"Precip={weather.get('precipitation')}mm/h"
        self.status = DroneStatus.EMERGENCY

    def _initiate_low_battery_protocol(self) -> None:
        """Handle low battery situation."""
        self.emergency_status = f"Low battery: {self.battery_level}%"
        self.status = DroneStatus.EMERGENCY