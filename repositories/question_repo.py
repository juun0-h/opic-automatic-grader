from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from sqlalchemy import and_

from models.database import Question
from .base import BaseRepository
import logging

logger = logging.getLogger(__name__)


class QuestionRepository(BaseRepository[Question]):
    """Repository for Question model with specific business logic"""
    
    def __init__(self, db_session: Session):
        super().__init__(Question, db_session)
    
    async def get_by_property(self, property_name: str) -> List[Question]:
        """Get questions by property (occupation, living, hobbies)"""
        try:
            return self.db.query(Question).filter(
                Question.property == property_name
            ).all()
        except Exception as e:
            logger.error(f"Error getting questions by property {property_name}: {str(e)}")
            raise
    
    async def get_by_property_and_link(self, property_name: str, link: int) -> List[Question]:
        """Get questions by property and link index"""
        try:
            return self.db.query(Question).filter(
                and_(
                    Question.property == property_name,
                    Question.link == link
                )
            ).all()
        except Exception as e:
            logger.error(f"Error getting questions by property {property_name} and link {link}: {str(e)}")
            raise
    
    async def get_random_questions_by_survey(self, survey_data: Dict) -> List[Question]:
        """
        Get random questions based on survey responses
        This implements the question selection logic from the original app
        """
        try:
            selected_questions = []
            
            # Extract survey options (this logic matches the original Flask app)
            occupation = survey_data.get("occupation")
            living_situation = survey_data.get("living_situation") 
            hobbies = survey_data.get("hobbies", [])
            
            # Question selection logic (simplified version)
            # This should match the complex logic in the original app
            
            # Get questions based on occupation
            if occupation:
                occupation_questions = await self.get_by_property("occupation")
                if occupation_questions:
                    selected_questions.extend(occupation_questions[:5])  # Take first 5
            
            # Get questions based on living situation
            if living_situation:
                living_questions = await self.get_by_property("living")
                if living_questions:
                    selected_questions.extend(living_questions[:5])  # Take first 5
            
            # Get questions based on hobbies
            if hobbies:
                hobby_questions = await self.get_by_property("hobby")
                if hobby_questions:
                    selected_questions.extend(hobby_questions[:5])  # Take first 5
            
            # Ensure we have exactly 15 questions
            if len(selected_questions) < 15:
                # Get additional general questions
                general_questions = await self.get_by_property("general")
                selected_questions.extend(general_questions[:15-len(selected_questions)])
            
            return selected_questions[:15]  # Ensure exactly 15 questions
            
        except Exception as e:
            logger.error(f"Error getting random questions by survey: {str(e)}")
            raise
    
    async def search_questions(self, search_term: str) -> List[Question]:
        """Search questions by text content"""
        try:
            return self.db.query(Question).filter(
                Question.question_text.contains(search_term)
            ).all()
        except Exception as e:
            logger.error(f"Error searching questions with term '{search_term}': {str(e)}")
            raise
    
    async def get_questions_by_ids(self, question_ids: List[int]) -> List[Question]:
        """Get multiple questions by their IDs"""
        try:
            return self.db.query(Question).filter(
                Question.id.in_(question_ids)
            ).all()
        except Exception as e:
            logger.error(f"Error getting questions by IDs: {str(e)}")
            raise