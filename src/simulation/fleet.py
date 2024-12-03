# src/simulation/fleet.py

from typing import Dict, List, Tuple, Optional
from datetime import datetime
import threading
import time
from .drone import Drone, DroneSpecification
from .route import RouteOptimizer, RoutePoint
from .weather import WeatherCondition, WeatherSimulator

class FleetManager:
    def __init__(self, 
                 base_position: Tuple[float, float],
                 weather_bounds: Tuple[Tuple[float, float], Tuple[float, float]] = None):
        self.drones: Dict[str, Drone] = {}
        self.base_position = base_position
        self._lock = threading.Lock()
        self.active_deliveries: Dict[str, Dict] = {}
        
        # Initialize route optimizer and weather simulator
        self.route_optimizer = RouteOptimizer()
        self.weather_simulator = WeatherSimulator(
            weather_bounds or (
                (base_position[0] - 0.1, base_position[1] - 0.1),
                (base_position[0] + 0.1, base_position[1] + 0.1)
            )
        )
        
        # Delivery routes cache
        self.delivery_routes: Dict[str, List[RoutePoint]] = {}
        
        # Start weather update thread
        self._start_weather_updates()

    def _start_weather_updates(self) -> None:
        """Start background thread for weather updates."""
        def update_weather():
            while True:
                self.weather_simulator.update_conditions()
                time.sleep(300)  # Update every 5 minutes

        weather_thread = threading.Thread(target=update_weather, daemon=True)
        weather_thread.start()

    def add_drone(self, drone: Drone) -> str:
        """Add a new drone to the fleet."""
        with self._lock:
            self.drones[drone.id] = drone
            return drone.id

    def remove_drone(self, drone_id: str) -> bool:
        """Remove a drone from the fleet."""
        with self._lock:
            if drone_id in self.drones:
                del self.drones[drone_id]
                return True
            return False

    def get_available_drones(self) -> List[Drone]:
        """Get list of available drones for delivery."""
        return [
            drone for drone in self.drones.values() 
            if drone.status == "idle" and drone.maintenance_score >= 80.0
        ]

    def assign_delivery(self, 
                       destination: Tuple[float, float], 
                       payload_weight: float) -> Optional[str]:
        """Assign delivery to best available drone considering weather and route."""
        available_drones = self.get_available_drones()
        if not available_drones:
            return None

        best_drone = None
        best_route = None
        best_score = float('-inf')

        for drone in available_drones:
            # Calculate optimal route considering weather
            route = self.route_optimizer.calculate_route(
                start=drone.position,
                end=destination,
                weather_data=self._get_weather_data_for_route()
            )

            if not route:
                continue

            # Analyze route risks
            risks = self.weather_simulator.get_flight_risks(
                [(point.position) for point in route],
                datetime.now()
            )

            # Calculate route score based on multiple factors
            route_score = self._calculate_route_score(
                drone,
                route,
                risks,
                payload_weight
            )

            if route_score > best_score:
                best_score = route_score
                best_drone = drone
                best_route = route

        if best_drone and best_route:
            # Store route for the delivery
            self.delivery_routes[best_drone.id] = best_route
            
            # Start the delivery
            if best_drone.start_delivery(destination, payload_weight):
                self.active_deliveries[best_drone.id] = {
                    "destination": destination,
                    "payload_weight": payload_weight,
                    "start_time": datetime.now(),
                    "route": best_route
                }
                return best_drone.id

        return None

    def _calculate_route_score(self,
                             drone: Drone,
                             route: List[RoutePoint],
                             risks: List[Dict],
                             payload_weight: float) -> float:
        """Calculate overall score for a potential delivery route."""
        # Base score starts with drone's maintenance score
        score = drone.maintenance_score

        # Factor in battery efficiency
        estimated_power = sum(
            drone.calculate_power_consumption(
                drone._calculate_distance(route[i].position, route[i+1].position),
                payload_weight
            )
            for i in range(len(route)-1)
        )
        battery_score = 100 * (1 - estimated_power/drone.battery_level)
        
        # Factor in weather risks
        weather_score = sum(
            100 if risk['is_safe'] else sum(risk['safety_scores'].values()) * 25
            for risk in risks
        ) / len(risks)

        # Factor in route length (shorter is better)
        route_length = sum(
            drone._calculate_distance(route[i].position, route[i+1].position)
            for i in range(len(route)-1)
        )
        length_score = 100 * (1 / (1 + route_length/10))  # 10km reference distance

        # Weighted combination of all factors
        return (
            0.3 * drone.maintenance_score +
            0.3 * battery_score +
            0.3 * weather_score +
            0.1 * length_score
        )

    def _get_weather_data_for_route(self) -> Dict[Tuple[float, float], Dict]:
        """Get current weather data for route planning."""
        weather_data = {}
        min_lat, min_lon = self.weather_simulator.region_bounds[0]
        max_lat, max_lon = self.weather_simulator.region_bounds[1]
        
        # Get weather conditions for grid points
        for lat in range(int(min_lat * 100), int(max_lat * 100), 1):
            for lon in range(int(min_lon * 100), int(max_lon * 100), 1):
                pos = (lat/100, lon/100)
                conditions = self.weather_simulator.get_conditions(pos)
                if conditions:
                    weather_data[pos] = conditions

        return weather_data

    def update_fleet_status(self) -> None:
        """Update status of all drones in the fleet."""
        with self._lock:
            current_time = datetime.now()
            
            for drone in self.drones.values():
                # Update drone status based on delivery progress
                if drone.id in self.delivery_routes and drone.status == "in_transit":
                    route = self.delivery_routes[drone.id]
                    delivery = self.active_deliveries[drone.id]
                    
                    # Find next route point based on time
                    elapsed_time = (current_time - delivery["start_time"]).total_seconds()
                    point_index = int(elapsed_time / 120)  # Assume 2 minutes between points
                    
                    if point_index < len(route):
                        # Update drone position to current route point
                        new_position = route[point_index].position
                        drone.update_position(new_position)
                        
                        # Check weather conditions at current position
                        conditions = self.weather_simulator.get_conditions(new_position)
                        if conditions:
                            is_safe, _ = conditions.is_safe_for_flight()
                            if not is_safe:
                                # Implement weather avoidance logic here
                                self._handle_unsafe_weather(drone, conditions)
                    else:
                        # Delivery complete
                        drone.complete_delivery()
                        del self.delivery_routes[drone.id]
                        del self.active_deliveries[drone.id]
                
                # Handle charging and maintenance
                elif drone.status == "charging":
                    drone.charge(1.0)  # Charge for 1 minute
                elif drone.status == "returning":
                    drone.return_to_base(self.base_position)

    def _handle_unsafe_weather(self, drone: Drone, conditions: 'WeatherCondition') -> None:
        """Handle unsafe weather conditions during delivery."""
        # Get safe altitude recommendation
        safe_altitude = self.weather_simulator.get_safe_altitude(drone.position)
        
        if safe_altitude <= self.route_optimizer.max_altitude:
            # Adjust drone altitude
            drone.altitude = safe_altitude
        else:
            # If safe altitude is too high, return to base
            drone.status = "returning"
            if drone.id in self.delivery_routes:
                del self.delivery_routes[drone.id]
            if drone.id in self.active_deliveries:
                del self.active_deliveries[drone.id]

    def get_fleet_status(self) -> Dict:
        """Get status of all drones in the fleet."""
        drones = [drone.get_status() for drone in self.drones.values()]
        
        return {
            "total_drones": len(self.drones),
            "available_drones": len(self.get_available_drones()),
            "active_deliveries": len(self.active_deliveries),
            "weather_conditions": {
                "base": self.weather_simulator.get_conditions(self.base_position),
                "is_safe": self.weather_simulator.get_conditions(self.base_position).is_safe_for_flight()[0]
            },
            "drones": drones,
            "analytics": {
                "total_drones": len(drones),
                "active_drones": len([d for d in drones if d["status"] != "idle"]),
                "average_battery_level": sum(d["battery_level"] for d in drones) / len(drones) if drones else 0,
                "fleet_utilization": len([d for d in drones if d["status"] != "idle"]) / len(drones) if drones else 0
            }
        }

    def get_drone(self, drone_id: str) -> Optional[Drone]:
        """Get specific drone by ID."""
        return self.drones.get(drone_id)

    def get_drone_route(self, drone_id: str) -> Optional[List[RoutePoint]]:
        """Get current route for a drone."""
        return self.delivery_routes.get(drone_id)