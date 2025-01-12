from typing import List, Tuple, Optional, Dict, Set
from dataclasses import dataclass
from datetime import datetime, timedelta
import heapq
import math
from .weather import WeatherCondition

@dataclass
class RoutePoint:
    position: Tuple[float, float]
    altitude: float
    time: datetime

class RouteOptimizer:
    def __init__(self):
        self.grid_size = 0.002  # Approximately 200 meters
        self.min_altitude = 100.0
        self.max_altitude = 400.0
        self.safety_margin = 50.0
        self.base_position = (37.7749, -122.4194)
        self.no_fly_radius = 0.5  # 500m radius

        # Define movement patterns
        small_step = self.grid_size
        medium_step = self.grid_size * 2
        large_step = self.grid_size * 3

        self.movements = [
            # Outward movement patterns
            (0, large_step), (large_step, 0),
            (0, -large_step), (-large_step, 0),
            (medium_step, medium_step), (medium_step, -medium_step),
            (-medium_step, medium_step), (-medium_step, -medium_step),
            # Fine adjustments
            (small_step, 0), (-small_step, 0),
            (0, small_step), (0, -small_step),
            (small_step, small_step), (-small_step, small_step),
            (small_step, -small_step), (-small_step, -small_step)
        ]

    def calculate_route(self,
                       start: Tuple[float, float],
                       end: Tuple[float, float],
                       weather: Optional[WeatherCondition] = None) -> List[RoutePoint]:
        """Calculate optimal route considering weather and no-fly zones."""
        print(f"\nCalculating route from {start} to {end}")
        
        path = self._find_path(start, end, weather)
        
        if not path:
            print("No path found, using fallback path")
            return self._create_fallback_path(start, end)

        # Convert path to route points
        route_points = []
        current_time = datetime.utcnow()
        total_distance = 0

        for i in range(len(path)):
            if i > 0:
                segment_dist = self._calculate_distance(path[i-1], path[i])
                total_distance += segment_dist

            altitude = self._calculate_safe_altitude(path[i], weather)
            route_points.append(RoutePoint(
                position=path[i],
                altitude=altitude,
                time=current_time + timedelta(minutes=2*i)
            ))

        print(f"Total route distance: {total_distance:.2f} km")
        return route_points

    def _find_path(self, 
                  start: Tuple[float, float], 
                  end: Tuple[float, float],
                  weather: Optional[WeatherCondition]) -> List[Tuple[float, float]]:
        """A* pathfinding implementation."""
        print("\nA* Pathfinding Details:")
        print(f"Start: {start}")
        print(f"End: {end}")
        print(f"Grid size: {self.grid_size}")

        def heuristic(point: Tuple[float, float]) -> float:
            """Calculate heuristic distance."""
            dx = abs(end[0] - point[0])
            dy = abs(end[1] - point[1])
            base_cost = math.sqrt(dx * dx + dy * dy)
            
            # Add NFZ influence
            nfz_dist = self._calculate_distance(self.base_position, point)
            nfz_factor = 1.0
            if nfz_dist < self.no_fly_radius * 1.5:
                nfz_factor = 2.0
                
            return base_cost * nfz_factor * 0.9

        open_set = []
        heapq.heappush(open_set, (0, start))
        came_from = {}
        g_score = {start: 0}
        f_score = {start: heuristic(start)}
        explored = set()
        
        iteration = 0
        max_iterations = 1000

        while open_set and iteration < max_iterations:
            iteration += 1
            current = heapq.heappop(open_set)[1]
            
            if current in explored:
                continue
                
            print(f"Exploring point: {current}")
            explored.add(current)

            if self._is_goal_reached(current, end):
                print("Goal reached! Reconstructing path...")
                return self._reconstruct_path(came_from, current)

            for dx, dy in self.movements:
                neighbor = (
                    round(current[0] + dx, 6),
                    round(current[1] + dy, 6)
                )
                
                if neighbor in explored:
                    continue

                if not self._is_valid_point(neighbor):
                    continue

                movement_cost = math.sqrt(dx*dx + dy*dy)

                # Add weather cost
                if weather:
                    weather_cost = self._calculate_weather_cost(neighbor, weather)
                    print(f"Weather cost for point {neighbor}: {weather_cost}")
                    movement_cost *= (1 + weather_cost)

                tentative_g_score = g_score[current] + movement_cost

                if neighbor not in g_score or tentative_g_score < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g_score
                    f_score = tentative_g_score + heuristic(neighbor)
                    heapq.heappush(open_set, (f_score, neighbor))

        print(f"No path found after {iteration} iterations")
        return []

    def _reconstruct_path(self, came_from: Dict, current: Tuple[float, float]) -> List[Tuple[float, float]]:
        """Reconstruct path from A* search result."""
        path = [current]
        while current in came_from:
            current = came_from[current]
            path.append(current)
        
        path = list(reversed(path))
        
        print(f"Found path with {len(path)} waypoints")
        for i, point in enumerate(path):
            print(f"Waypoint {i}: {point}")
            
        # minimum waypoints
        if len(path) < 3:
            midpoint = (
                (path[0][0] + path[-1][0]) / 2,
                (path[0][1] + path[-1][1]) / 2
            )
            # Adjust midpoint if too close to NFZ
            nfz_dist = self._calculate_distance(self.base_position, midpoint)
            if nfz_dist < self.no_fly_radius * 1.2:
                offset = 0.01  # About 1km
                if midpoint[1] < self.base_position[1]:
                    midpoint = (midpoint[0], midpoint[1] - offset)
                else:
                    midpoint = (midpoint[0], midpoint[1] + offset)
            path = [path[0], midpoint, path[-1]]
        
        return path

    def _is_valid_point(self, point: Tuple[float, float]) -> bool:
        """Check if point is valid and not in no-fly zone."""
        lat, lon = point
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            return False
            
        distance = self._calculate_distance(self.base_position, point)
        if distance <= self.no_fly_radius * 0.8:  
            print(f"Point {point} rejected - too close to no-fly zone")
            return False
            
        return True

    def _calculate_weather_cost(self, point: Tuple[float, float], weather: WeatherCondition) -> float:
        """Calculate weather-based cost factor."""
        base_cost = 0.0
        
        # Wind cost
        if weather.wind_speed > 8:
            base_cost += (weather.wind_speed - 8) * 0.1
            
        # Visibility cost
        if weather.visibility < 5:
            base_cost += (5 - weather.visibility) * 0.1
            
        # Add position-based variation
        lat_factor = abs(point[0] - self.base_position[0]) * 0.02
        lon_factor = abs(point[1] - self.base_position[1]) * 0.02
        
        return base_cost + lat_factor + lon_factor

    def _calculate_safe_altitude(self, point: Tuple[float, float], weather: Optional[WeatherCondition]) -> float:
        """Calculate safe altitude considering weather and NFZ."""
        base_altitude = self.min_altitude + self.safety_margin
        
        # Increase altitude near NFZ
        nfz_dist = self._calculate_distance(self.base_position, point)
        if nfz_dist < self.no_fly_radius * 1.5:
            base_altitude += 50 * (1 - (nfz_dist / (self.no_fly_radius * 1.5)))
            
        if weather and weather.wind_speed > 8:
            base_altitude += (weather.wind_speed - 8) * 10
                
        return min(base_altitude, self.max_altitude)

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
        return R * c

    def _is_goal_reached(self, current: Tuple[float, float], goal: Tuple[float, float]) -> bool:
        """Check if current point is close enough to goal."""
        return self._calculate_distance(current, goal) < self.grid_size

    def _create_fallback_path(self, start: Tuple[float, float], end: Tuple[float, float]) -> List[RoutePoint]:
        """Create a safe fallback path with proper NFZ avoidance."""
        current_time = datetime.utcnow()
        
        # Calculate midpoint with offset
        mid_lat = (start[0] + end[0]) / 2
        offset = self.no_fly_radius * 1.5
        
        # Choose offset direction
        if start[1] < self.base_position[1]:
            mid_lon = start[1] - offset
        else:
            mid_lon = start[1] + offset
            
        return [
            RoutePoint(start, self.min_altitude + self.safety_margin, current_time),
            RoutePoint(
                (mid_lat, mid_lon),
                self.min_altitude + self.safety_margin + 50,
                current_time + timedelta(minutes=2)
            ),
            RoutePoint(end, self.min_altitude + self.safety_margin, current_time + timedelta(minutes=4))
        ]