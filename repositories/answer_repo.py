from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc

from models.database import Answer
from .base import BaseRepository
import logging

logger = logging.getLogger(__name__)


class AnswerRepository(BaseRepository[Answer]):
    """Repository for Answer model with specific business logic"""
    
    def __init__(self, db_session: Session):
        super().__init__(Answer, db_session)
    
    async def get_by_student_id(self, student_id: str) -> List[Answer]:
        """Get all answers for a specific student"""
        try:
            return self.db.query(Answer).filter(
                Answer.student_id == student_id
            ).order_by(Answer.question_number).all()
        except Exception as e:
            logger.error(f"Error getting answers for student {student_id}: {str(e)}")
            raise
    
    async def get_by_student_and_question(self, student_id: str, question_number: int) -> Optional[Answer]:
        """Get specific answer by student and question number"""
        try:
            return self.db.query(Answer).filter(
                and_(
                    Answer.student_id == student_id,
                    Answer.question_number == question_number
                )
            ).first()
        except Exception as e:
            logger.error(f"Error getting answer for student {student_id}, question {question_number}: {str(e)}")
            raise
    
    async def create_or_update_answer(self, answer_data: Dict) -> Answer:
        """Create new answer or update existing one"""
        try:
            existing_answer = await self.get_by_student_and_question(
                answer_data["student_id"], 
                answer_data["question_number"]
            )
            
            if existing_answer:
                # Update existing answer
                for field, value in answer_data.items():
                    if hasattr(existing_answer, field):
                        setattr(existing_answer, field, value)
                self.db.commit()
                self.db.refresh(existing_answer)
                return existing_answer
            else:
                # Create new answer
                return await self.create(answer_data)
                
        except Exception as e:
            logger.error(f"Error creating/updating answer: {str(e)}")
            raise
    
    async def update_score(self, student_id: str, question_number: int, 
                          score_data: Dict[str, float]) -> Optional[Answer]:
        """Update scores for a specific answer"""
        try:
            answer = await self.get_by_student_and_question(student_id, question_number)
            if answer:
                # Update main score
                if "total_score" in score_data:
                    answer.score = score_data["total_score"]
                
                # Update breakdown scores
                if "task_completion_score" in score_data:
                    answer.task_completion_score = score_data["task_completion_score"]
                if "accuracy_score" in score_data:
                    answer.accuracy_score = score_data["accuracy_score"]
                if "appropriateness_score" in score_data:
                    answer.appropriateness_score = score_data["appropriateness_score"]
                
                self.db.commit()
                self.db.refresh(answer)
            return answer
        except Exception as e:
            logger.error(f"Error updating scores for student {student_id}, question {question_number}: {str(e)}")
            raise
    
    async def get_completed_answers_count(self, student_id: str) -> int:
        """Get count of completed answers (with scores) for a student"""
        try:
            return self.db.query(Answer).filter(
                and_(
                    Answer.student_id == student_id,
                    Answer.score.isnot(None)
                )
            ).count()
        except Exception as e:
            logger.error(f"Error getting completed answers count for student {student_id}: {str(e)}")
            raise
    
    async def get_student_progress(self, student_id: str) -> Dict[str, int]:
        """Get progress information for a student"""
        try:
            total_answers = self.db.query(Answer).filter(
                Answer.student_id == student_id
            ).count()
            
            scored_answers = self.db.query(Answer).filter(
                and_(
                    Answer.student_id == student_id,
                    Answer.score.isnot(None)
                )
            ).count()
            
            return {
                "total_answers": total_answers,
                "scored_answers": scored_answers,
                "remaining": 15 - total_answers,
                "progress_percentage": int((scored_answers / 15) * 100) if scored_answers else 0
            }
        except Exception as e:
            logger.error(f"Error getting progress for student {student_id}: {str(e)}")
            raise
    
    async def get_average_scores_by_student(self, student_id: str) -> Dict[str, float]:
        """Get average scores for all criteria for a student"""
        try:
            answers = await self.get_by_student_id(student_id)
            scored_answers = [a for a in answers if a.score is not None]
            
            if not scored_answers:
                return {"total": 0.0, "task_completion": 0.0, "accuracy": 0.0, "appropriateness": 0.0}
            
            total_score = sum(a.score for a in scored_answers) / len(scored_answers)
            task_completion = sum(a.task_completion_score or 0 for a in scored_answers) / len(scored_answers)
            accuracy = sum(a.accuracy_score or 0 for a in scored_answers) / len(scored_answers)
            appropriateness = sum(a.appropriateness_score or 0 for a in scored_answers) / len(scored_answers)
            
            return {
                "total": round(total_score, 2),
                "task_completion": round(task_completion, 2),
                "accuracy": round(accuracy, 2),
                "appropriateness": round(appropriateness, 2)
            }
        except Exception as e:
            logger.error(f"Error calculating average scores for student {student_id}: {str(e)}")
            raise
    
    async def delete_student_answers(self, student_id: str) -> int:
        """Delete all answers for a specific student"""
        try:
            deleted_count = self.db.query(Answer).filter(
                Answer.student_id == student_id
            ).delete()
            self.db.commit()
            return deleted_count
        except Exception as e:
            logger.error(f"Error deleting answers for student {student_id}: {str(e)}")
            self.db.rollback()
            raise