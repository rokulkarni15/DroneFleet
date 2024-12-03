from typing import List, Tuple, Dict, Optional
import numpy as np
from dataclasses import dataclass
import heapq
from datetime import datetime
import math

@dataclass
class WeatherCondition:
    wind_speed: float  # meters per second
    wind_direction: float  # degrees from north
    precipitation: float  # mm/hour
    visibility: float  # kilometers

@dataclass
class RoutePoint:
    position: Tuple[float, float]  # (latitude, longitude)
    altitude: float  # meters
    time: datetime
    weather: Optional[WeatherCondition] = None

class RouteOptimizer:
    def __init__(self, 
                 no_fly_zones: List[List[Tuple[float, float]]] = None,
                 min_altitude: float = 100.0,
                 max_altitude: float = 400.0):
        self.no_fly_zones = no_fly_zones or []
        self.min_altitude = min_altitude
        self.max_altitude = max_altitude
        self.safety_margin = 50.0  # meters
        self.grid_size = 0.001  # approximately 100m in latitude/longitude

    def calculate_route(self,
                       start: Tuple[float, float],
                       end: Tuple[float, float],
                       weather_data: Optional[Dict[Tuple[float, float], WeatherCondition]] = None) -> List[RoutePoint]:
        """Calculate optimal route considering obstacles and weather conditions."""
        
        # Initialize path with A* algorithm
        path = self._a_star_search(start, end)
        if not path:
            return []

        # Optimize altitude profile
        route_points = self._create_altitude_profile(path)

        # Apply weather optimizations if weather data is available
        if weather_data:
            route_points = self._optimize_for_weather(route_points, weather_data)

        # Smooth the path
        smoothed_route = self._smooth_path(route_points)

        return smoothed_route

    def _a_star_search(self, start: Tuple[float, float], end: Tuple[float, float]) -> List[Tuple[float, float]]:
        """A* pathfinding algorithm implementation."""
        def heuristic(a: Tuple[float, float], b: Tuple[float, float]) -> float:
            return self._calculate_distance(a, b)

        def get_neighbors(pos: Tuple[float, float]) -> List[Tuple[float, float]]:
            lat, lon = pos
            neighbors = []
            for dlat in [-self.grid_size, 0, self.grid_size]:
                for dlon in [-self.grid_size, 0, self.grid_size]:
                    if dlat == 0 and dlon == 0:
                        continue
                    new_pos = (lat + dlat, lon + dlon)
                    if not self._is_in_no_fly_zone(new_pos):
                        neighbors.append(new_pos)
            return neighbors

        # Initialize the open and closed sets
        open_set = [(0, start)]
        came_from = {}
        g_score = {start: 0}
        f_score = {start: heuristic(start, end)}
        closed_set = set()

        while open_set:
            current = heapq.heappop(open_set)[1]

            if self._calculate_distance(current, end) < self.grid_size:
                return self._reconstruct_path(came_from, current, start)

            closed_set.add(current)

            for neighbor in get_neighbors(current):
                if neighbor in closed_set:
                    continue

                tentative_g_score = g_score[current] + self._calculate_distance(current, neighbor)

                if neighbor not in g_score or tentative_g_score < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g_score
                    f_score[neighbor] = g_score[neighbor] + heuristic(neighbor, end)
                    heapq.heappush(open_set, (f_score[neighbor], neighbor))

        return []

    def _create_altitude_profile(self, path: List[Tuple[float, float]]) -> List[RoutePoint]:
        """Create altitude profile for the route."""
        route_points = []
        current_time = datetime.now()

        for i, point in enumerate(path):
            # Calculate optimal altitude based on distance from obstacles
            optimal_altitude = self._calculate_optimal_altitude(point)
            
            route_points.append(RoutePoint(
                position=point,
                altitude=optimal_altitude,
                time=current_time
            ))

        return route_points

    def _optimize_for_weather(self, 
                            route_points: List[RoutePoint],
                            weather_data: Dict[Tuple[float, float], WeatherCondition]) -> List[RoutePoint]:
        """Optimize route considering weather conditions."""
        optimized_points = []
        
        for point in route_points:
            weather = self._get_nearest_weather(point.position, weather_data)
            if weather:
                # Adjust altitude based on weather conditions
                new_altitude = self._adjust_altitude_for_weather(point.altitude, weather)
                
                optimized_points.append(RoutePoint(
                    position=point.position,
                    altitude=new_altitude,
                    time=point.time,
                    weather=weather
                ))

        return optimized_points

    def _smooth_path(self, route_points: List[RoutePoint]) -> List[RoutePoint]:
        """Apply path smoothing to remove unnecessary waypoints."""
        if len(route_points) <= 2:
            return route_points

        smoothed = [route_points[0]]
        current_idx = 1

        while current_idx < len(route_points) - 1:
            prev_point = smoothed[-1]
            current_point = route_points[current_idx]
            next_point = route_points[current_idx + 1]

            # Check if we can skip the current point
            if self._can_skip_point(prev_point, current_point, next_point):
                current_idx += 1
                continue

            smoothed.append(current_point)
            current_idx += 1

        smoothed.append(route_points[-1])
        return smoothed

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

    def _is_in_no_fly_zone(self, point: Tuple[float, float]) -> bool:
        """Check if a point is within any no-fly zone."""
        def point_in_polygon(x: float, y: float, polygon: List[Tuple[float, float]]) -> bool:
            n = len(polygon)
            inside = False
            p1x, p1y = polygon[0]
            for i in range(n + 1):
                p2x, p2y = polygon[i % n]
                if y > min(p1y, p2y):
                    if y <= max(p1y, p2y):
                        if x <= max(p1x, p2x):
                            if p1y != p2y:
                                xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                            if p1x == p2x or x <= xinters:
                                inside = not inside
                p1x, p1y = p2x, p2y
            return inside

        return any(point_in_polygon(point[0], point[1], zone) for zone in self.no_fly_zones)

    def _calculate_optimal_altitude(self, point: Tuple[float, float]) -> float:
        """Calculate optimal altitude considering obstacles and minimum safety height."""
        # Start with minimum altitude
        altitude = self.min_altitude

        # Check distance to nearest no-fly zone and adjust altitude if needed
        for zone in self.no_fly_zones:
            min_distance = min(self._calculate_distance(point, zone_point) for zone_point in zone)
            if min_distance < 1.0:  # If within 1km of no-fly zone
                # Increase altitude based on proximity
                altitude = min(
                    self.max_altitude,
                    altitude + (1.0 - min_distance) * self.safety_margin
                )

        return altitude

    def _get_nearest_weather(self, 
                           position: Tuple[float, float],
                           weather_data: Dict[Tuple[float, float], WeatherCondition]) -> Optional[WeatherCondition]:
        """Get weather data from nearest weather station."""
        if not weather_data:
            return None

        nearest_point = min(
            weather_data.keys(),
            key=lambda x: self._calculate_distance(position, x)
        )
        return weather_data[nearest_point]

    def _adjust_altitude_for_weather(self, 
                                   current_altitude: float,
                                   weather: WeatherCondition) -> float:
        """Adjust altitude based on weather conditions."""
        adjusted_altitude = current_altitude

        # Adjust for wind speed
        if weather.wind_speed > 10:  # m/s
            adjusted_altitude += min(50, weather.wind_speed * 2)

        # Adjust for poor visibility
        if weather.visibility < 5:  # km
            adjusted_altitude += (5 - weather.visibility) * 20

        # Adjust for precipitation
        if weather.precipitation > 0:
            adjusted_altitude += min(30, weather.precipitation * 5)

        # Ensure altitude stays within bounds
        return max(self.min_altitude, min(self.max_altitude, adjusted_altitude))

    def _can_skip_point(self,
                       prev: RoutePoint,
                       current: RoutePoint,
                       next_point: RoutePoint) -> bool:
        """Determine if a point can be skipped in path smoothing."""
        # Check if skipping the point would create a path through a no-fly zone
        if self._is_in_no_fly_zone(current.position):
            return False

        # Check if altitude change is too dramatic
        altitude_change = abs(prev.altitude - next_point.altitude)
        if altitude_change > self.safety_margin:
            return False

        return True

    def _reconstruct_path(self,
                         came_from: Dict[Tuple[float, float], Tuple[float, float]],
                         current: Tuple[float, float],
                         start: Tuple[float, float]) -> List[Tuple[float, float]]:
        """Reconstruct path from A* search result."""
        path = [current]
        while current in came_from:
            current = came_from[current]
            path.append(current)
        path.reverse()
        return path
            