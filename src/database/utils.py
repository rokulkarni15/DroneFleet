from typing import Any, Dict, Type, TypeVar, Optional, List
from sqlalchemy.orm import Session

DBModel = TypeVar("DBModel")

from sqlalchemy import and_
from datetime import datetime, timedelta

from .connection import Base, get_db

# Define type variable with string literal for forward reference
DBModel = TypeVar("DBModel", bound=Base) # type: ignore

class DatabaseUtils:
    """Generic database operations with error handling and logging."""
    
    @staticmethod
    def create(db: Session, model: Type[DBModel], **kwargs) -> Optional[DBModel]:
        """Create a new database record."""
        try:
            db_item = model(**kwargs)
            db.add(db_item)
            db.commit()
            db.refresh(db_item)
            return db_item
        except Exception as e:
            db.rollback()
            print(f"Error creating {model.__name__}: {str(e)}")
            return None

    @staticmethod
    def update(
        db: Session,
        model: Type[DBModel],
        id: Any,
        update_data: Dict[str, Any]
    ) -> Optional[DBModel]:
        """Update an existing record."""
        try:
            db_item = db.query(model).filter(model.id == id).first()
            if not db_item:
                return None
                
            for key, value in update_data.items():
                setattr(db_item, key, value)
            
            db.commit()
            db.refresh(db_item)
            return db_item
        except Exception as e:
            db.rollback()
            print(f"Error updating {model.__name__}: {str(e)}")
            return None

    @staticmethod
    def delete(db: Session, model: Type[DBModel], id: Any) -> bool:
        """Delete a record."""
        try:
            result = db.query(model).filter(model.id == id).delete()
            db.commit()
            return result > 0
        except Exception as e:
            db.rollback()
            print(f"Error deleting {model.__name__}: {str(e)}")
            return False

    @staticmethod
    def get_by_id(
        db: Session, 
        model: Type[DBModel], 
        id: Any
    ) -> Optional[DBModel]:
        """Get a record by ID."""
        try:
            return db.query(model).filter(model.id == id).first()
        except Exception as e:
            print(f"Error retrieving {model.__name__}: {str(e)}")
            return None

    @staticmethod
    def get_all(
        db: Session,
        model: Type[DBModel],
        filters: Optional[Dict[str, Any]] = None,
        skip: int = 0,
        limit: int = 100,
        order_by: Optional[str] = None
    ) -> List[DBModel]:
        """Get all records with filtering, pagination and ordering."""
        try:
            query = db.query(model)
            
            if filters:
                filter_conditions = []
                for key, value in filters.items():
                    if hasattr(model, key):
                        filter_conditions.append(getattr(model, key) == value)
                if filter_conditions:
                    query = query.filter(and_(*filter_conditions))
            
            if order_by and hasattr(model, order_by):
                query = query.order_by(getattr(model, order_by))
            
            return query.offset(skip).limit(limit).all()
        except Exception as e:
            print(f"Error retrieving {model.__name__} list: {str(e)}")
            return []

    @staticmethod
    def bulk_create(
        db: Session,
        model: Type[DBModel],
        items: List[Dict[str, Any]]
    ) -> List[DBModel]:
        """Bulk create records."""
        try:
            db_items = [model(**item) for item in items]
            db.bulk_save_objects(db_items)
            db.commit()
            return db_items
        except Exception as e:
            db.rollback()
            print(f"Error bulk creating {model.__name__}: {str(e)}")
            return []

    @staticmethod
    def cleanup_old_records(
        db: Session,
        model: Type[DBModel],
        field: str,
        days: int
    ) -> int:
        """Clean up old records based on a date field."""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            result = db.query(model).filter(
                getattr(model, field) < cutoff_date
            ).delete()
            db.commit()
            return result
        except Exception as e:
            db.rollback()
            print(f"Error cleaning up {model.__name__}: {str(e)}")
            return 0