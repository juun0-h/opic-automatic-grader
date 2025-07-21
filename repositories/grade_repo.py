from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from sqlalchemy import desc

from models.database import Grade
from .base import BaseRepository
import logging

logger = logging.getLogger(__name__)


class GradeRepository(BaseRepository[Grade]):
    """Repository for Grade model with specific business logic"""
    
    def __init__(self, db_session: Session):
        super().__init__(Grade, db_session)
    
    async def get_by_student_id(self, student_id: str) -> Optional[Grade]:
        """Get grade for a specific student"""
        try:
            return self.db.query(Grade).filter(
                Grade.student_id == student_id
            ).first()
        except Exception as e:
            logger.error(f"Error getting grade for student {student_id}: {str(e)}")
            raise
    
    async def create_or_update_grade(self, grade_data: Dict) -> Grade:
        """Create new grade or update existing one"""
        try:
            existing_grade = await self.get_by_student_id(grade_data["student_id"])
            
            if existing_grade:
                # Update existing grade
                for field, value in grade_data.items():
                    if hasattr(existing_grade, field):
                        setattr(existing_grade, field, value)
                self.db.commit()
                self.db.refresh(existing_grade)
                return existing_grade
            else:
                # Create new grade
                return await self.create(grade_data)
                
        except Exception as e:
            logger.error(f"Error creating/updating grade: {str(e)}")
            raise
    
    async def get_grades_by_level(self, grade_level: str) -> List[Grade]:
        """Get all grades of a specific level (NH, IL, IM, IH, AL)"""
        try:
            return self.db.query(Grade).filter(
                Grade.grade == grade_level
            ).order_by(desc(Grade.total_score)).all()
        except Exception as e:
            logger.error(f"Error getting grades by level {grade_level}: {str(e)}")
            raise
    
    async def get_recent_grades(self, limit: int = 10) -> List[Grade]:
        """Get most recent grades"""
        try:
            return self.db.query(Grade).order_by(
                desc(Grade.created_at)
            ).limit(limit).all()
        except Exception as e:
            logger.error(f"Error getting recent grades: {str(e)}")
            raise
    
    async def get_grade_statistics(self) -> Dict[str, any]:
        """Get overall grade statistics"""
        try:
            total_students = await self.count()
            
            if total_students == 0:
                return {
                    "total_students": 0,
                    "grade_distribution": {},
                    "average_score": 0.0,
                    "score_range": {"min": 0.0, "max": 0.0}
                }
            
            # Grade distribution
            grade_distribution = {}
            grade_levels = ["NH", "IL", "IM", "IH", "AL"]
            
            for level in grade_levels:
                count = self.db.query(Grade).filter(Grade.grade == level).count()
                grade_distribution[level] = count
            
            # Score statistics
            all_grades = await self.get_all()
            scores = [grade.total_score for grade in all_grades]
            
            return {
                "total_students": total_students,
                "grade_distribution": grade_distribution,
                "average_score": round(sum(scores) / len(scores), 2) if scores else 0.0,
                "score_range": {
                    "min": round(min(scores), 2) if scores else 0.0,
                    "max": round(max(scores), 2) if scores else 0.0
                }
            }
        except Exception as e:
            logger.error(f"Error getting grade statistics: {str(e)}")
            raise
    
    async def search_students(self, search_term: str) -> List[Grade]:
        """Search students by name or student ID"""
        try:
            return self.db.query(Grade).filter(
                Grade.name.contains(search_term) | 
                Grade.student_id.contains(search_term)
            ).order_by(desc(Grade.created_at)).all()
        except Exception as e:
            logger.error(f"Error searching students with term '{search_term}': {str(e)}")
            raise
    
    async def get_top_performers(self, limit: int = 10) -> List[Grade]:
        """Get top performing students by score"""
        try:
            return self.db.query(Grade).order_by(
                desc(Grade.total_score)
            ).limit(limit).all()
        except Exception as e:
            logger.error(f"Error getting top performers: {str(e)}")
            raise
    
    async def delete_student_grade(self, student_id: str) -> bool:
        """Delete grade for a specific student"""
        try:
            grade = await self.get_by_student_id(student_id)
            if grade:
                self.db.delete(grade)
                self.db.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting grade for student {student_id}: {str(e)}")
            self.db.rollback()
            raise