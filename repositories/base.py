from typing import Generic, TypeVar, Type, List, Optional, Union
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from abc import ABC, abstractmethod
import logging

from config.database import Base

logger = logging.getLogger(__name__)

# Generic type for database models
ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType], ABC):
    """Base repository implementing common CRUD operations"""
    
    def __init__(self, model: Type[ModelType], db_session: Session):
        self.model = model
        self.db = db_session
    
    async def create(self, obj_data: dict) -> ModelType:
        """Create a new record"""
        try:
            db_obj = self.model(**obj_data)
            self.db.add(db_obj)
            self.db.commit()
            self.db.refresh(db_obj)
            return db_obj
        except SQLAlchemyError as e:
            logger.error(f"Error creating {self.model.__name__}: {str(e)}")
            self.db.rollback()
            raise
    
    async def get_by_id(self, obj_id: int) -> Optional[ModelType]:
        """Get record by ID"""
        try:
            return self.db.query(self.model).filter(self.model.id == obj_id).first()
        except SQLAlchemyError as e:
            logger.error(f"Error getting {self.model.__name__} by ID {obj_id}: {str(e)}")
            raise
    
    async def get_all(self, skip: int = 0, limit: int = 100) -> List[ModelType]:
        """Get all records with pagination"""
        try:
            return self.db.query(self.model).offset(skip).limit(limit).all()
        except SQLAlchemyError as e:
            logger.error(f"Error getting all {self.model.__name__}: {str(e)}")
            raise
    
    async def update(self, obj_id: int, obj_data: dict) -> Optional[ModelType]:
        """Update record by ID"""
        try:
            db_obj = await self.get_by_id(obj_id)
            if db_obj:
                for field, value in obj_data.items():
                    if hasattr(db_obj, field):
                        setattr(db_obj, field, value)
                self.db.commit()
                self.db.refresh(db_obj)
            return db_obj
        except SQLAlchemyError as e:
            logger.error(f"Error updating {self.model.__name__} {obj_id}: {str(e)}")
            self.db.rollback()
            raise
    
    async def delete(self, obj_id: int) -> bool:
        """Delete record by ID"""
        try:
            db_obj = await self.get_by_id(obj_id)
            if db_obj:
                self.db.delete(db_obj)
                self.db.commit()
                return True
            return False
        except SQLAlchemyError as e:
            logger.error(f"Error deleting {self.model.__name__} {obj_id}: {str(e)}")
            self.db.rollback()
            raise
    
    async def exists(self, obj_id: int) -> bool:
        """Check if record exists"""
        try:
            return self.db.query(self.model).filter(self.model.id == obj_id).first() is not None
        except SQLAlchemyError as e:
            logger.error(f"Error checking existence of {self.model.__name__} {obj_id}: {str(e)}")
            raise
    
    async def count(self) -> int:
        """Get total count of records"""
        try:
            return self.db.query(self.model).count()
        except SQLAlchemyError as e:
            logger.error(f"Error counting {self.model.__name__}: {str(e)}")
            raise