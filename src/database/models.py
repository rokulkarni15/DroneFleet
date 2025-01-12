from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum, Boolean, JSON
from sqlalchemy.orm import relationship, validates
from datetime import datetime
from src.api.schemas.enums import DroneStatus, DeliveryStatus, MaintenanceType
from .connection import Base
import logging

logger = logging.getLogger(__name__)

class Drone(Base):
    __tablename__ = "drones"

    id = Column(String, primary_key=True)
    model = Column(String, nullable=False)
    status = Column(String, nullable=False, default="idle")
    current_latitude = Column(Float, nullable=False)
    current_longitude = Column(Float, nullable=False)
    current_altitude = Column(Float, nullable=False, default=100.0)
    battery_level = Column(Float, nullable=False, default=100.0)
    maintenance_score = Column(Float, nullable=False, default=100.0)
    total_flight_hours = Column(Float, nullable=False, default=0.0)
    last_maintenance = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_updated = Column(DateTime, nullable=False, default=datetime.utcnow)
    specification = Column(JSON, nullable=False)
    component_health = Column(JSON, nullable=False)

    # Relationships
    deliveries = relationship("Delivery", back_populates="drone", cascade="all, delete-orphan")
    maintenance_logs = relationship("MaintenanceLog", back_populates="drone", cascade="all, delete-orphan")
    telemetry_logs = relationship("TelemetryLog", back_populates="drone", cascade="all, delete-orphan")

    @validates('status')
    def validate_status(self, key, value):
        """Validate drone status."""
        try:
            return DroneStatus(value).value
        except ValueError:
            raise ValueError(f"Invalid drone status: {value}")

    @validates('battery_level', 'maintenance_score')
    def validate_percentage(self, key, value):
        """Validate percentage fields."""
        if not 0 <= float(value) <= 100:
            raise ValueError(f"{key} must be between 0 and 100")
        return float(value)

    def needs_maintenance(self) -> bool:
        """Check if drone needs maintenance."""
        return (
            self.maintenance_score < 80 or
            any(health < 80 for health in self.component_health.values())
        )

    def update_position(self, latitude: float, longitude: float, altitude: float):
        """Update drone position."""
        self.current_latitude = latitude
        self.current_longitude = longitude
        self.current_altitude = altitude
        self.last_updated = datetime.utcnow()

class Delivery(Base):
    __tablename__ = "deliveries"

    id = Column(Integer, primary_key=True)
    drone_id = Column(String, ForeignKey("drones.id", ondelete="CASCADE"))
    status = Column(Enum(DeliveryStatus), nullable=False, default=DeliveryStatus.PENDING)
    start_time = Column(DateTime, nullable=False)
    completion_time = Column(DateTime)
    start_latitude = Column(Float, nullable=False)
    start_longitude = Column(Float, nullable=False)
    destination_latitude = Column(Float, nullable=False)
    destination_longitude = Column(Float, nullable=False)
    payload_weight = Column(Float, nullable=False)
    priority = Column(String, default="normal")
    notes = Column(String)
    route = Column(JSON)
    estimated_delivery_time = Column(Integer)
    actual_delivery_time = Column(Integer)
    weather_conditions = Column(JSON)

    # Relationships
    drone = relationship("Drone", back_populates="deliveries")
    route_logs = relationship("RouteLog", back_populates="delivery", cascade="all, delete-orphan")

    @validates('payload_weight')
    def validate_payload_weight(self, key, value):
        """Validate payload weight."""
        if value <= 0:
            raise ValueError("Payload weight must be positive")
        return value

    def complete_delivery(self):
        """Mark delivery as completed."""
        self.status = DeliveryStatus.COMPLETED
        self.completion_time = datetime.utcnow()
        self.actual_delivery_time = int(
            (self.completion_time - self.start_time).total_seconds() / 60
        )

    def calculate_progress(self) -> float:
        """Calculate delivery progress percentage."""
        if self.status == DeliveryStatus.COMPLETED:
            return 100.0
        elif self.status == DeliveryStatus.CANCELLED:
            return 0.0
            
        if not self.route:
            return 0.0
            
        completed_points = len([
            log for log in self.route_logs 
            if log.status == "reached"
        ])
        return (completed_points / len(self.route)) * 100

class MaintenanceLog(Base):
    __tablename__ = "maintenance_logs"

    id = Column(Integer, primary_key=True)
    drone_id = Column(String, ForeignKey("drones.id", ondelete="CASCADE"))
    maintenance_type = Column(Enum(MaintenanceType), nullable=False)
    description = Column(String)
    scheduled_date = Column(DateTime, nullable=False)
    completed = Column(Boolean, default=False)
    completion_date = Column(DateTime)
    completion_notes = Column(String)
    component_health_before = Column(JSON)
    component_health_after = Column(JSON)
    technician = Column(String)
    cost = Column(Float)

    # Relationships
    drone = relationship("Drone", back_populates="maintenance_logs")

    def complete_maintenance(self, notes: str, new_health: dict):
        """Complete maintenance record."""
        self.completed = True
        self.completion_date = datetime.utcnow()
        self.completion_notes = notes
        self.component_health_after = new_health

class TelemetryLog(Base):
    __tablename__ = "telemetry_logs"

    id = Column(Integer, primary_key=True)
    drone_id = Column(String, ForeignKey("drones.id", ondelete="CASCADE"))
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    altitude = Column(Float, nullable=False)
    battery_level = Column(Float, nullable=False)
    speed = Column(Float)
    heading = Column(Float)
    temperature = Column(Float)
    weather_conditions = Column(JSON)

    # Relationships
    drone = relationship("Drone", back_populates="telemetry_logs")

    @validates('latitude')
    def validate_latitude(self, key, value):
        """Validate latitude."""
        if not -90 <= value <= 90:
            raise ValueError("Invalid latitude")
        return value

    @validates('longitude')
    def validate_longitude(self, key, value):
        """Validate longitude."""
        if not -180 <= value <= 180:
            raise ValueError("Invalid longitude")
        return value

class RouteLog(Base):
    __tablename__ = "route_logs"

    id = Column(Integer, primary_key=True)
    delivery_id = Column(Integer, ForeignKey("deliveries.id", ondelete="CASCADE"))
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    altitude = Column(Float, nullable=False)
    sequence_number = Column(Integer, nullable=False)
    status = Column(String, nullable=False)  # reached, skipped, diverted
    weather_conditions = Column(JSON)

    # Relationships
    delivery = relationship("Delivery", back_populates="route_logs")

    def update_status(self, new_status: str):
        """Update waypoint status."""
        valid_statuses = ["reached", "skipped", "diverted"]
        if new_status not in valid_statuses:
            raise ValueError(f"Invalid status. Must be one of: {valid_statuses}")
        self.status = new_status