from typing import Generator
from fastapi import Depends
from sqlalchemy.orm import Session
from src.simulation.fleet import FleetManager
from src.database.connection import SessionLocal
import os
from dotenv import load_dotenv

load_dotenv()

# Initialize fleet manager with base position from env if provided
BASE_LAT = float(os.getenv("BASE_LATITUDE", "37.7749"))
BASE_LON = float(os.getenv("BASE_LONGITUDE", "-122.4194"))
FLEET_MANAGER = FleetManager(base_position=(BASE_LAT, BASE_LON))

def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_fleet_manager() -> FleetManager:
    return FLEET_MANAGER