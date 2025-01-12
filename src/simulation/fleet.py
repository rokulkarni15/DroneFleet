from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
import threading
import time
from .drone import Drone, DroneSpecification, DroneStatus
from .route import RouteOptimizer, RoutePoint
from .weather import WeatherSimulator, WeatherCondition

class FleetManager:
    def __init__(self, 
                 base_position: Tuple[float, float],
                 weather_bounds: Tuple[Tuple[float, float], Tuple[float, float]] = None):
        """Initialize fleet manager."""
        self.drones: Dict[str, Drone] = {}
        self.base_position = base_position
        self._lock = threading.Lock()
        self.active_deliveries: Dict[str, Dict] = {}
        
        # Initialize components
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

    def add_drone(self, drone: Drone) -> str:
        """Add a new drone to the fleet."""
        with self._lock:
            self.drones[drone.id] = drone
            print(f"Added drone {drone.id} to fleet")
            return drone.id

    def remove_drone(self, drone_id: str) -> bool:
        """Remove a drone from the fleet."""
        with self._lock:
            if drone_id in self.drones:
                if self.drones[drone_id].status != DroneStatus.IDLE.value:
                    return False
                del self.drones[drone_id]
                return True
            return False

    def get_drone(self, drone_id: str) -> Optional[Drone]:
        """Get specific drone by ID."""
        return self.drones.get(drone_id)

    def get_available_drones(self) -> List[Drone]:
        """Get list of available drones for delivery."""
        return [
            drone for drone in self.drones.values()
            if drone.status == DroneStatus.IDLE.value 
            and drone.maintenance_score >= 80.0
            and drone.battery_level >= 30.0
        ]

    def assign_delivery(self, 
                       destination: Tuple[float, float], 
                       payload_weight: float) -> Optional[str]:
        """Assign delivery to best available drone."""
        print("Starting delivery assignment")
        with self._lock:
            available_drones = self.get_available_drones()
            if not available_drones:
                print("No available drones")
                return None

            print(f"Found {len(available_drones)} available drones")
            
            best_drone = None
            best_route = None
            best_score = float('-inf')
            
            # Get weather data for destination
            weather = self.weather_simulator.get_conditions(destination)
            
            for drone in available_drones:
                if drone.maintenance_score < 80 or drone.battery_level < 30:
                    continue
                    
                print(f"Calculating route for drone {drone.id}")
                route = self.route_optimizer.calculate_route(
                    start=drone.position,
                    end=destination,
                    weather=weather
                )
                
                if route:
                    score = self._calculate_delivery_score(
                        drone=drone,
                        route=route,
                        payload_weight=payload_weight
                    )
                    
                    if score > best_score:
                        best_score = score
                        best_drone = drone
                        best_route = route
                        print(f"New best route found for drone {drone.id}")

            if best_drone and best_route:
                print(f"Assigning delivery to drone {best_drone.id}")
                best_drone.status = DroneStatus.IN_TRANSIT.value
                self.delivery_routes[best_drone.id] = best_route
                self.active_deliveries[best_drone.id] = {
                    "destination": destination,
                    "payload_weight": payload_weight,
                    "start_time": datetime.utcnow(),
                    "route": best_route
                }
                return best_drone.id

            print("No suitable drone found")
            return None

    def _calculate_delivery_score(self, 
                                drone: Drone, 
                                route: List[RoutePoint],
                                payload_weight: float) -> float:
        """Calculate score for potential delivery assignment."""
        # Base score from drone health
        score = drone.maintenance_score
        
        # Factor in battery efficiency
        total_distance = sum(
            self.route_optimizer._calculate_distance(
                route[i].position, 
                route[i+1].position
            )
            for i in range(len(route)-1)
        )
        battery_requirement = (total_distance * drone.specification.power_consumption_rate * 
                             (1 + payload_weight/drone.specification.max_payload))
        battery_score = 100 * (1 - battery_requirement/drone.battery_level)
        
        # Factor in route length (shorter is better)
        distance_score = 100 * (1 / (1 + total_distance/10))
        
        # Weighted combination
        return (0.4 * drone.maintenance_score +
                0.4 * battery_score +
                0.2 * distance_score)

    def get_drone_route(self, drone_id: str) -> Optional[List[RoutePoint]]:
        """Get current route for a drone."""
        return self.delivery_routes.get(drone_id)

    def get_fleet_status(self) -> Dict:
        """Get current fleet status."""
        return {
            "total_drones": len(self.drones),
            "available_drones": len(self.get_available_drones()),
            "active_deliveries": len(self.active_deliveries),
            "drones": [drone.get_status() for drone in self.drones.values()]
        }

    def update_fleet_status(self) -> None:
        """Update status of all drones in the fleet."""
        with self._lock:
            current_time = datetime.utcnow()
            for drone_id, drone in self.drones.items():
                if drone_id in self.active_deliveries:
                    delivery = self.active_deliveries[drone_id]
                    route = self.delivery_routes.get(drone_id, [])
                    
                    if route:
                        # Update drone position along route
                        elapsed_time = (current_time - delivery["start_time"]).total_seconds()
                        point_index = int(elapsed_time / 120)  # 2 minutes per point
                        
                        if point_index < len(route):
                            new_position = route[point_index].position
                            new_altitude = route[point_index].altitude
                            current_weather = self.weather_simulator.get_conditions(new_position)
                            drone.update_position(new_position, new_altitude, current_weather)
                        else:
                            # Delivery complete
                            self._complete_delivery(drone_id)

    def _complete_delivery(self, drone_id: str) -> None:
        """Complete a delivery and update drone status."""
        if drone_id in self.active_deliveries:
            del self.active_deliveries[drone_id]
        if drone_id in self.delivery_routes:
            del self.delivery_routes[drone_id]
        
        drone = self.drones.get(drone_id)
        if drone:
            drone.status = DroneStatus.IDLE.value

    def _start_weather_updates(self) -> None:
        """Start background thread for weather updates."""
        def update_weather():
            while True:
                self.weather_simulator.update_conditions()
                time.sleep(300)  # Update every 5 minutes

        weather_thread = threading.Thread(target=update_weather, daemon=True)
        weather_thread.start()

    def get_completed_deliveries_count(self, since: Optional[datetime] = None) -> int:
        """Get count of completed deliveries since given time."""
        count = 0
        if since:
            for drone in self.drones.values():
                count += len([d for d in drone.completed_deliveries 
                            if d.get('completion_time', datetime.min) >= since])
        return count

    def get_average_delivery_time(self) -> float:
        """Get average delivery time in minutes."""
        delivery_times = []
        for drone in self.drones.values():
            for delivery in drone.completed_deliveries:
                if delivery.get('completion_time') and delivery.get('start_time'):
                    delta = delivery['completion_time'] - delivery['start_time']
                    delivery_times.append(delta.total_seconds() / 60)
        return sum(delivery_times) / len(delivery_times) if delivery_times else 0

    def get_failed_deliveries_count(self) -> int:
        """Get count of failed deliveries."""
        count = 0
        for drone in self.drones.values():
            count += len([d for d in drone.completed_deliveries 
                         if d.get('status') == 'failed'])
        return count

    def init_emergency_return(self, drone_id: str) -> bool:
        """Initiate emergency return for a drone."""
        drone = self.get_drone(drone_id)
        if not drone:
            return False

        # Calculate return route
        return_route = self.route_optimizer.calculate_route(
            start=drone.position,
            end=self.base_position,
            weather=self.weather_simulator.get_conditions(drone.position)
        )

        if return_route:
            drone.status = DroneStatus.EMERGENCY.value
            self.delivery_routes[drone_id] = return_route
            if drone_id in self.active_deliveries:
                self.active_deliveries[drone_id]["emergency_return"] = True
            return True

        return False