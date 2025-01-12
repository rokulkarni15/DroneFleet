from typing import Any, Dict, Type, TypeVar, Optional, List, Union
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc
from datetime import datetime, timedelta
import logging
from .connection import Base

logger = logging.getLogger(__name__)

# Define type variable for database models
DBModel = TypeVar("DBModel", bound=Base) # type: ignore

class DatabaseUtils:
    """Generic database operations with error handling and logging."""
    
    @staticmethod
    def create(db: Session, model: Type[DBModel], **kwargs) -> Optional[DBModel]:
        """
        Create a new database record.
        
        Args:
            db: Database session
            model: Model class to create
            **kwargs: Model fields and values
            
        Returns:
            Created model instance or None if failed
        """
        try:
            db_item = model(**kwargs)
            db.add(db_item)
            db.commit()
            db.refresh(db_item)
            logger.info(f"Created new {model.__name__} record")
            return db_item
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating {model.__name__}: {str(e)}")
            return None

    @staticmethod
    def get_by_id(db: Session, model: Type[DBModel], id: Any) -> Optional[DBModel]:
        """Get a record by ID with error handling."""
        try:
            return db.query(model).filter(model.id == id).first()
        except Exception as e:
            logger.error(f"Error retrieving {model.__name__}: {str(e)}")
            return None

    @staticmethod
    def get_all(
        db: Session,
        model: Type[DBModel],
        filters: Optional[Dict[str, Any]] = None,
        or_filters: Optional[Dict[str, Any]] = None,
        skip: int = 0,
        limit: int = 100,
        order_by: Optional[str] = None,
        order_direction: str = "asc"
    ) -> List[DBModel]:
        """
        Get all records with comprehensive filtering options.
        
        Args:
            filters: AND conditions as field-value pairs
            or_filters: OR conditions as field-value pairs
            order_direction: "asc" or "desc"
        """
        try:
            query = db.query(model)
            
            # Apply AND filters
            if filters:
                filter_conditions = []
                for key, value in filters.items():
                    if hasattr(model, key):
                        filter_conditions.append(getattr(model, key) == value)
                if filter_conditions:
                    query = query.filter(and_(*filter_conditions))
            
            # Apply OR filters
            if or_filters:
                or_conditions = []
                for key, value in or_filters.items():
                    if hasattr(model, key):
                        or_conditions.append(getattr(model, key) == value)
                if or_conditions:
                    query = query.filter(or_(*or_conditions))
            
            # Apply ordering
            if order_by and hasattr(model, order_by):
                order_func = desc if order_direction == "desc" else asc
                query = query.order_by(order_func(getattr(model, order_by)))
            
            return query.offset(skip).limit(limit).all()
            
        except Exception as e:
            logger.error(f"Error retrieving {model.__name__} list: {str(e)}")
            return []

    @staticmethod
    def update(
        db: Session,
        model: Type[DBModel],
        id: Any,
        update_data: Dict[str, Any],
        exclude_fields: Optional[List[str]] = None
    ) -> Optional[DBModel]:
        """
        Update an existing record with field exclusion.
        
        Args:
            exclude_fields: List of fields to exclude from update
        """
        try:
            db_item = db.query(model).filter(model.id == id).first()
            if not db_item:
                return None

            # Filter out excluded fields
            if exclude_fields:
                update_data = {
                    k: v for k, v in update_data.items() 
                    if k not in exclude_fields
                }
                
            for key, value in update_data.items():
                if hasattr(db_item, key):
                    setattr(db_item, key, value)
            
            db.commit()
            db.refresh(db_item)
            logger.info(f"Updated {model.__name__} record {id}")
            return db_item
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error updating {model.__name__}: {str(e)}")
            return None

    @staticmethod
    def delete(db: Session, model: Type[DBModel], id: Any) -> bool:
        """Delete a record with error handling."""
        try:
            result = db.query(model).filter(model.id == id).delete()
            db.commit()
            logger.info(f"Deleted {model.__name__} record {id}")
            return result > 0
        except Exception as e:
            db.rollback()
            logger.error(f"Error deleting {model.__name__}: {str(e)}")
            return False

    @staticmethod
    def bulk_create(
        db: Session,
        model: Type[DBModel],
        items: List[Dict[str, Any]]
    ) -> List[DBModel]:
        """Bulk create records with validation."""
        try:
            if not items:
                return []
                
            db_items = [model(**item) for item in items]
            db.bulk_save_objects(db_items)
            db.commit()
            logger.info(f"Bulk created {len(items)} {model.__name__} records")
            return db_items
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error bulk creating {model.__name__}: {str(e)}")
            return []

    @staticmethod
    def bulk_update(
        db: Session,
        model: Type[DBModel],
        items: List[Dict[str, Any]],
        key_field: str = "id"
    ) -> bool:
        """Bulk update records using a key field."""
        try:
            for item in items:
                if key_field not in item:
                    continue
                    
                db.query(model).filter(
                    getattr(model, key_field) == item[key_field]
                ).update(item)
                
            db.commit()
            logger.info(f"Bulk updated {len(items)} {model.__name__} records")
            return True
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error bulk updating {model.__name__}: {str(e)}")
            return False

    @staticmethod
    def cleanup_old_records(
        db: Session,
        model: Type[DBModel],
        field: str,
        days: int
    ) -> int:
        """Delete old records based on a date field."""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            result = db.query(model).filter(
                getattr(model, field) < cutoff_date
            ).delete()
            db.commit()
            logger.info(f"Cleaned up {result} old {model.__name__} records")
            return result
        except Exception as e:
            db.rollback()
            logger.error(f"Error cleaning up {model.__name__}: {str(e)}")
            return 0