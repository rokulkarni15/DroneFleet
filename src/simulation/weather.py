from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
import math
import random
import numpy as np
from collections import defaultdict

@dataclass
class WeatherCondition:
    temperature: float  # Celsius
    wind_speed: float  # meters per second
    wind_direction: float  # degrees from north (0-360)
    precipitation: float  # mm/hour
    visibility: float  # kilometers
    pressure: float  # hPa
    turbulence: float  # 0-1 scale
    cloud_coverage: float  # percentage (0-100)
    
    def is_safe_for_flight(self, min_safety_threshold: float = 0.7) -> Tuple[bool, Dict[str, float]]:
        """
        Determine if weather conditions are safe for drone flight.
        Returns (is_safe, safety_scores)
        """
        safety_scores = {
            'wind': self._calculate_wind_safety(),
            'visibility': self._calculate_visibility_safety(),
            'precipitation': self._calculate_precipitation_safety(),
            'turbulence': 1 - self.turbulence
        }
        
        overall_safety = sum(safety_scores.values()) / len(safety_scores)
        return overall_safety >= min_safety_threshold, safety_scores
    
    def _calculate_wind_safety(self) -> float:
        """Calculate safety score based on wind conditions (0-1)."""
        # Assume max safe wind speed is 15 m/s
        return max(0, 1 - (self.wind_speed / 15))
    
    def _calculate_visibility_safety(self) -> float:
        """Calculate safety score based on visibility (0-1)."""
        # Assume minimum safe visibility is 2km, optimal is 10km
        return min(1, max(0, (self.visibility - 2) / 8))
    
    def _calculate_precipitation_safety(self) -> float:
        """Calculate safety score based on precipitation (0-1)."""
        # Assume maximum safe precipitation is 10mm/hour
        return max(0, 1 - (self.precipitation / 10))

class WeatherSimulator:
    def __init__(self, 
                 region_bounds: Tuple[Tuple[float, float], Tuple[float, float]],
                 grid_resolution: float = 0.01):  # approximately 1km
        """
        Initialize weather simulator for a region.
        region_bounds: ((min_lat, min_lon), (max_lat, max_lon))
        """
        self.region_bounds = region_bounds
        self.grid_resolution = grid_resolution
        self.current_conditions: Dict[Tuple[float, float], WeatherCondition] = {}
        self.forecast_data: Dict[datetime, Dict[Tuple[float, float], WeatherCondition]] = defaultdict(dict)
        
        # Initialize base weather conditions
        self._initialize_weather()

    def _initialize_weather(self) -> None:
        """Initialize weather conditions across the region."""
        min_lat, min_lon = self.region_bounds[0]
        max_lat, max_lon = self.region_bounds[1]
        
        # Create weather grid points
        for lat in np.arange(min_lat, max_lat, self.grid_resolution):
            for lon in np.arange(min_lon, max_lon, self.grid_resolution):
                self.current_conditions[(lat, lon)] = self._generate_base_conditions()

    def _generate_base_conditions(self) -> WeatherCondition:
        """Generate realistic base weather conditions."""
        return WeatherCondition(
            temperature=random.uniform(15, 25),
            wind_speed=random.uniform(0, 8),
            wind_direction=random.uniform(0, 360),
            precipitation=random.uniform(0, 2),
            visibility=random.uniform(8, 15),
            pressure=random.uniform(1010, 1020),
            turbulence=random.uniform(0, 0.3),
            cloud_coverage=random.uniform(0, 70)
        )

    def update_conditions(self, time_delta: timedelta = timedelta(minutes=5)) -> None:
        """Update weather conditions based on time passage and weather patterns."""
        # Update current conditions
        for position in self.current_conditions:
            self.current_conditions[position] = self._evolve_weather(
                self.current_conditions[position],
                time_delta
            )
        
        # Generate new forecast data
        self._update_forecast()

    def _evolve_weather(self, 
                       current: WeatherCondition, 
                       time_delta: timedelta) -> WeatherCondition:
        """Evolve weather conditions over time."""
        hours = time_delta.total_seconds() / 3600
        
        # Add some random variations
        temp_change = random.gauss(0, 0.5) * hours
        wind_speed_change = random.gauss(0, 0.3) * hours
        wind_dir_change = random.gauss(0, 5) * hours
        precip_change = random.gauss(0, 0.1) * hours
        
        return WeatherCondition(
            temperature=current.temperature + temp_change,
            wind_speed=max(0, current.wind_speed + wind_speed_change),
            wind_direction=(current.wind_direction + wind_dir_change) % 360,
            precipitation=max(0, current.precipitation + precip_change),
            visibility=max(2, current.visibility + random.gauss(0, 0.2) * hours),
            pressure=current.pressure + random.gauss(0, 0.5) * hours,
            turbulence=max(0, min(1, current.turbulence + random.gauss(0, 0.05) * hours)),
            cloud_coverage=max(0, min(100, current.cloud_coverage + random.gauss(0, 2) * hours))
        )

    def _update_forecast(self, hours_ahead: int = 24) -> None:
        """Generate weather forecast data."""
        current_time = datetime.now()
        
        for hour in range(hours_ahead):
            forecast_time = current_time + timedelta(hours=hour)
            
            # Generate forecast for each grid point
            for position in self.current_conditions:
                if hour == 0:
                    # Use current conditions for current hour
                    self.forecast_data[forecast_time][position] = self.current_conditions[position]
                else:
                    # Evolve from previous hour with increasing uncertainty
                    prev_conditions = self.forecast_data[forecast_time - timedelta(hours=1)][position]
                    uncertainty_factor = math.sqrt(hour) * 0.1
                    
                    self.forecast_data[forecast_time][position] = self._evolve_weather(
                        prev_conditions,
                        timedelta(hours=1)
                    )

    def get_conditions(self, 
                      position: Tuple[float, float], 
                      time: Optional[datetime] = None) -> Optional[WeatherCondition]:
        """Get weather conditions for a specific position and time."""
        if time is None:
            return self._interpolate_conditions(position, self.current_conditions)
        
        # Find nearest forecast time
        forecast_times = list(self.forecast_data.keys())
        if not forecast_times:
            return None
        
        nearest_time = min(forecast_times, key=lambda x: abs((x - time).total_seconds()))
        return self._interpolate_conditions(position, self.forecast_data[nearest_time])

    def _interpolate_conditions(self, 
                              position: Tuple[float, float], 
                              conditions_dict: Dict[Tuple[float, float], WeatherCondition]) -> WeatherCondition:
        """Interpolate weather conditions for a specific position."""
        lat, lon = position
        
        # Find four nearest grid points
        grid_lat = round(lat / self.grid_resolution) * self.grid_resolution
        grid_lon = round(lon / self.grid_resolution) * self.grid_resolution
        
        nearby_points = [
            (grid_lat, grid_lon),
            (grid_lat + self.grid_resolution, grid_lon),
            (grid_lat, grid_lon + self.grid_resolution),
            (grid_lat + self.grid_resolution, grid_lon + self.grid_resolution)
        ]
        
        # Calculate weights based on distance
        weights = []
        for point in nearby_points:
            distance = math.sqrt((lat - point[0])**2 + (lon - point[1])**2)
            weights.append(1 / (distance + 1e-6))  # Add small epsilon to avoid division by zero
        
        # Normalize weights
        total_weight = sum(weights)
        weights = [w / total_weight for w in weights]
        
        # Interpolate each weather parameter
        interpolated = {
            'temperature': 0,
            'wind_speed': 0,
            'wind_direction': 0,
            'precipitation': 0,
            'visibility': 0,
            'pressure': 0,
            'turbulence': 0,
            'cloud_coverage': 0
        }
        
        for point, weight in zip(nearby_points, weights):
            if point in conditions_dict:
                conditions = conditions_dict[point]
                for key in interpolated:
                    interpolated[key] += getattr(conditions, key) * weight
        
        return WeatherCondition(**interpolated)

    def get_safe_altitude(self, 
                         position: Tuple[float, float], 
                         time: Optional[datetime] = None) -> float:
        """Calculate safe operating altitude based on weather conditions."""
        conditions = self.get_conditions(position, time)
        if not conditions:
            return 100.0  # Default safe altitude
        
        base_altitude = 100.0
        
        # Adjust for wind conditions
        wind_factor = max(0, conditions.wind_speed - 5) * 10
        
        # Adjust for visibility
        visibility_factor = max(0, 10 - conditions.visibility) * 20
        
        # Adjust for turbulence
        turbulence_factor = conditions.turbulence * 50
        
        return base_altitude + wind_factor + visibility_factor + turbulence_factor

    def get_flight_risks(self, 
                        route: List[Tuple[float, float]], 
                        start_time: datetime) -> List[Dict]:
        """Analyze weather-related risks along a flight route."""
        risks = []
        
        for i, position in enumerate(route):
            estimated_time = start_time + timedelta(minutes=i*2)  # Assume 2 minutes between waypoints
            conditions = self.get_conditions(position, estimated_time)
            
            if conditions:
                is_safe, safety_scores = conditions.is_safe_for_flight()
                risks.append({
                    'position': position,
                    'time': estimated_time,
                    'is_safe': is_safe,
                    'safety_scores': safety_scores,
                    'conditions': conditions
                })
        
        return risks