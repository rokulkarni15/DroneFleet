from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum, Boolean, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from src.api.schemas.enums import DroneStatus, DeliveryStatus, MaintenanceType

from .connection import Base


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