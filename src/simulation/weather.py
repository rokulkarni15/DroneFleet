from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import math
import random

@dataclass
class WeatherCondition:
    """Weather conditions at a specific point."""
    temperature: float      # Celsius
    wind_speed: float      # meters per second
    wind_direction: float  # degrees from north (0-360)
    precipitation: float   # mm/hour
    visibility: float      # kilometers
    
    def is_safe_for_flight(self) -> Tuple[bool, Dict[str, str]]:
        """Check if conditions are safe for flight."""
        warnings = {}
        
        if self.wind_speed > 15:
            warnings['wind_speed'] = f"Wind speed {self.wind_speed:.1f} m/s too high"
            
        if self.visibility < 3:
            warnings['visibility'] = f"Visibility {self.visibility:.1f} km too low"
            
        if self.precipitation > 5:
            warnings['precipitation'] = f"Precipitation {self.precipitation:.1f} mm/h too high"
        
        return len(warnings) == 0, warnings

    def to_dict(self) -> Dict:
        """Convert to dictionary format."""
        return {
            "temperature": self.temperature,
            "wind_speed": self.wind_speed,
            "wind_direction": self.wind_direction,
            "precipitation": self.precipitation,
            "visibility": self.visibility
        }

class WeatherSimulator:
    """Simulates weather conditions across a geographic area."""
    
    def __init__(self, region_bounds: Tuple[Tuple[float, float], Tuple[float, float]]):
        """
        Initialize weather simulator.
        region_bounds: ((min_lat, min_lon), (max_lat, max_lon))
        """
        self.region_bounds = region_bounds
        self.grid_size = 0.01  # approximately 1km
        self.weather_cells: Dict[Tuple[float, float], WeatherCondition] = {}
        
        # Initialize weather grid
        self._initialize_weather()

    def _initialize_weather(self):
        """Initialize weather conditions across the grid."""
        (min_lat, min_lon), (max_lat, max_lon) = self.region_bounds
        
        for lat in range(int(min_lat * 100), int(max_lat * 100) + 1, 1):
            for lon in range(int(min_lon * 100), int(max_lon * 100) + 1, 1):
                position = (lat/100, lon/100)
                self.weather_cells[position] = self._generate_conditions()

    def _generate_conditions(self) -> WeatherCondition:
        """Generate realistic weather conditions."""
        return WeatherCondition(
            temperature=random.uniform(15, 25),
            wind_speed=random.uniform(0, 10),
            wind_direction=random.uniform(0, 360),
            precipitation=random.uniform(0, 2),
            visibility=random.uniform(8, 15)
        )

    def get_conditions(self, position: Tuple[float, float]) -> Optional[WeatherCondition]:
        """Get interpolated weather conditions for a specific position."""
        if not self._is_position_in_bounds(position):
            return None

        # Find nearest grid points
        nearest_points = self._find_nearest_points(position)
        if not nearest_points:
            return self._generate_conditions()

        return self._interpolate_conditions(position, nearest_points)

    def update_conditions(self):
        """Update weather conditions across the grid."""
        for position in self.weather_cells:
            current = self.weather_cells[position]
            
            # Update with random variations
            self.weather_cells[position] = WeatherCondition(
                temperature=max(0, current.temperature + random.uniform(-0.5, 0.5)),
                wind_speed=max(0, current.wind_speed + random.uniform(-1, 1)),
                wind_direction=(current.wind_direction + random.uniform(-10, 10)) % 360,
                precipitation=max(0, current.precipitation + random.uniform(-0.2, 0.2)),
                visibility=max(2, current.visibility + random.uniform(-0.5, 0.5))
            )

    def _is_position_in_bounds(self, position: Tuple[float, float]) -> bool:
        """Check if position is within simulation bounds."""
        lat, lon = position
        (min_lat, min_lon), (max_lat, max_lon) = self.region_bounds
        return min_lat <= lat <= max_lat and min_lon <= lon <= max_lon

    def _find_nearest_points(self, position: Tuple[float, float]) -> List[Tuple[Tuple[float, float], float]]:
        """Find nearest grid points to a position."""
        lat, lon = position
        nearest_points = []
        
        for grid_point in self.weather_cells:
            distance = self._calculate_distance(position, grid_point)
            if distance < 0.1:  # Within ~10km
                nearest_points.append((grid_point, distance))
        
        return sorted(nearest_points, key=lambda x: x[1])[:4]  # Return 4 nearest points

    def _interpolate_conditions(self, 
                              position: Tuple[float, float], 
                              nearest_points: List[Tuple[Tuple[float, float], float]]) -> WeatherCondition:
        """Interpolate weather conditions from nearest points."""
        if not nearest_points:
            return self._generate_conditions()

        # Calculate weights based on distance
        weights = []
        total_weight = 0
        
        for point, distance in nearest_points:
            weight = 1 / (distance + 0.0001)
            weights.append(weight)
            total_weight += weight
        
        weights = [w/total_weight for w in weights]
        
        # Interpolate each parameter
        temp = sum(self.weather_cells[p[0]].temperature * w for p, w in zip(nearest_points, weights))
        wind_speed = sum(self.weather_cells[p[0]].wind_speed * w for p, w in zip(nearest_points, weights))
        wind_dir = sum(self.weather_cells[p[0]].wind_direction * w for p, w in zip(nearest_points, weights))
        precip = sum(self.weather_cells[p[0]].precipitation * w for p, w in zip(nearest_points, weights))
        vis = sum(self.weather_cells[p[0]].visibility * w for p, w in zip(nearest_points, weights))
        
        return WeatherCondition(
            temperature=temp,
            wind_speed=wind_speed,
            wind_direction=wind_dir % 360,
            precipitation=precip,
            visibility=vis
        )

    def _calculate_distance(self, point1: Tuple[float, float], point2: Tuple[float, float]) -> float:
        """Calculate distance between two points."""
        lat1, lon1 = point1
        lat2, lon2 = point2
        return math.sqrt((lat2 - lat1)**2 + (lon2 - lon1)**2)