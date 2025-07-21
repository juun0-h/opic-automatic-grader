from typing import List, Optional, Dict
from sqlalchemy.orm import Session

from models.database import SurveyResponse
from .base import BaseRepository
import logging
import json

logger = logging.getLogger(__name__)


class SurveyRepository(BaseRepository[SurveyResponse]):
    """Repository for SurveyResponse model with specific business logic"""
    
    def __init__(self, db_session: Session):
        super().__init__(SurveyResponse, db_session)
    
    async def get_by_student_id(self, student_id: str) -> Optional[SurveyResponse]:
        """Get survey response for a specific student"""
        try:
            return self.db.query(SurveyResponse).filter(
                SurveyResponse.student_id == student_id
            ).first()
        except Exception as e:
            logger.error(f"Error getting survey response for student {student_id}: {str(e)}")
            raise
    
    async def create_or_update_survey(self, survey_data: Dict) -> SurveyResponse:
        """Create new survey response or update existing one"""
        try:
            existing_survey = await self.get_by_student_id(survey_data["student_id"])
            
            # Process hobbies list to string if needed
            if "hobbies" in survey_data and isinstance(survey_data["hobbies"], list):
                survey_data["hobbies"] = json.dumps(survey_data["hobbies"], ensure_ascii=False)
            
            if existing_survey:
                # Update existing survey
                for field, value in survey_data.items():
                    if hasattr(existing_survey, field):
                        setattr(existing_survey, field, value)
                self.db.commit()
                self.db.refresh(existing_survey)
                return existing_survey
            else:
                # Create new survey
                return await self.create(survey_data)
                
        except Exception as e:
            logger.error(f"Error creating/updating survey: {str(e)}")
            raise
    
    async def get_survey_statistics(self) -> Dict[str, any]:
        """Get survey response statistics"""
        try:
            total_responses = await self.count()
            
            if total_responses == 0:
                return {
                    "total_responses": 0,
                    "occupation_distribution": {},
                    "living_distribution": {},
                    "hobby_distribution": {}
                }
            
            all_surveys = await self.get_all()
            
            # Occupation distribution
            occupation_dist = {}
            for survey in all_surveys:
                if survey.occupation:
                    occupation_dist[survey.occupation] = occupation_dist.get(survey.occupation, 0) + 1
            
            # Living situation distribution
            living_dist = {}
            for survey in all_surveys:
                if survey.living_situation:
                    living_dist[survey.living_situation] = living_dist.get(survey.living_situation, 0) + 1
            
            # Hobby distribution
            hobby_dist = {}
            for survey in all_surveys:
                if survey.hobbies:
                    try:
                        hobbies = json.loads(survey.hobbies) if isinstance(survey.hobbies, str) else survey.hobbies
                        if isinstance(hobbies, list):
                            for hobby in hobbies:
                                hobby_dist[hobby] = hobby_dist.get(hobby, 0) + 1
                    except (json.JSONDecodeError, TypeError):
                        # Handle cases where hobbies is not properly formatted
                        continue
            
            return {
                "total_responses": total_responses,
                "occupation_distribution": occupation_dist,
                "living_distribution": living_dist,
                "hobby_distribution": hobby_dist
            }
            
        except Exception as e:
            logger.error(f"Error getting survey statistics: {str(e)}")
            raise
    
    async def get_students_by_occupation(self, occupation: str) -> List[SurveyResponse]:
        """Get students with specific occupation"""
        try:
            return self.db.query(SurveyResponse).filter(
                SurveyResponse.occupation == occupation
            ).all()
        except Exception as e:
            logger.error(f"Error getting students by occupation {occupation}: {str(e)}")
            raise
    
    async def get_students_by_living_situation(self, living_situation: str) -> List[SurveyResponse]:
        """Get students with specific living situation"""
        try:
            return self.db.query(SurveyResponse).filter(
                SurveyResponse.living_situation == living_situation
            ).all()
        except Exception as e:
            logger.error(f"Error getting students by living situation {living_situation}: {str(e)}")
            raise
    
    async def get_students_by_hobby(self, hobby: str) -> List[SurveyResponse]:
        """Get students who have specific hobby"""
        try:
            # This searches for hobby within the JSON string
            return self.db.query(SurveyResponse).filter(
                SurveyResponse.hobbies.contains(hobby)
            ).all()
        except Exception as e:
            logger.error(f"Error getting students by hobby {hobby}: {str(e)}")
            raise
    
    async def delete_student_survey(self, student_id: str) -> bool:
        """Delete survey response for a specific student"""
        try:
            survey = await self.get_by_student_id(student_id)
            if survey:
                self.db.delete(survey)
                self.db.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting survey for student {student_id}: {str(e)}")
            self.db.rollback()
            raise