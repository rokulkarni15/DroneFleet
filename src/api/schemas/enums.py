from enum import Enum

class DroneStatus(str, Enum):
    IDLE = "idle"
    IN_TRANSIT = "in_transit"
    DELIVERING = "delivering"
    RETURNING = "returning"
    CHARGING = "charging"
    MAINTENANCE = "maintenance"
    EMERGENCY = "emergency"
    
class DeliveryStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class MaintenanceType(str, Enum):
    ROUTINE = "routine"
    REPAIR = "repair"
    EMERGENCY = "emergency"
    INSPECTION = "inspection"