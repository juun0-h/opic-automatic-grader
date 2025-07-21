import random
import logging
from typing import Dict, List, Optional
from sqlalchemy.orm import Session

from repositories.question_repo import QuestionRepository
from repositories.survey_repo import SurveyRepository
from models.schemas import SurveySubmission, SurveyAnswer, QuestionResponse
from config.database import get_db

logger = logging.getLogger(__name__)


class SurveyService:
    """Service for handling survey responses and question generation"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.survey_repo = SurveyRepository(db_session)
        self.question_repo = QuestionRepository(db_session)
        
        # Survey questions and options (from original Flask app)
        self.survey_questions = {
            1: "현재 귀하는 어느 분야에 종사하고 계십니까?",
            2: "현재 귀하는 어디에 살고 계십니까?",
            3: "귀하는 여가 및 취미활동으로 주로 무엇을 하십니까? (두 개 이상 선택)",
        }
        
        self.survey_options = {
            1: ["사업자/직장인", "학생", "취업준비생"],
            2: ["개인주택이나 아파트에 홀로 거주", "친구나 룸메이트와 함께 주택이나 아파트에 거주", "가족과 함께 주택이나 아파트에 거주"],
            3: ["운동", "게임", "SNS", "문화생활", "여행", "자기관리", "예술활동", "자기개발"],
        }
    
    async def get_survey_questions(self) -> Dict[str, any]:
        """Get survey questions and options"""
        try:
            return {
                "questions": self.survey_questions,
                "options": self.survey_options
            }
        except Exception as e:
            logger.error(f"Error getting survey questions: {str(e)}")
            raise
    
    async def submit_survey(self, survey_submission: SurveySubmission) -> Dict[str, any]:
        """Process survey submission and return personalized questions"""
        try:
            # Process survey answers
            processed_survey = await self._process_survey_answers(survey_submission)
            
            # Save survey response
            await self.survey_repo.create_or_update_survey(processed_survey)
            
            # Generate personalized questions based on survey
            questions = await self._generate_personalized_questions(processed_survey)
            
            logger.info(f"Survey submitted and questions generated for student: {survey_submission.student_id}")
            
            return {
                "message": "설문 응답이 성공적으로 저장되었습니다.",
                "questions": questions,
                "total_questions": len(questions)
            }
            
        except Exception as e:
            logger.error(f"Error submitting survey: {str(e)}")
            raise
    
    async def _process_survey_answers(self, submission: SurveySubmission) -> Dict[str, any]:
        """Process raw survey answers into structured data"""
        try:
            processed = {
                "student_id": submission.student_id,
                "name": "",  # Will be populated from user session
                "occupation": None,
                "living_situation": None,
                "hobbies": []
            }
            
            for answer in submission.answers:
                question_id = answer.question_id
                selected_options = answer.selected_options
                
                if question_id == 1:  # 종사 분야
                    processed["occupation"] = selected_options[0] if selected_options else None
                elif question_id == 2:  # 거주 방식
                    processed["living_situation"] = selected_options[0] if selected_options else None
                elif question_id == 3:  # 취미
                    processed["hobbies"] = selected_options
            
            return processed
            
        except Exception as e:
            logger.error(f"Error processing survey answers: {str(e)}")
            raise
    
    async def _generate_personalized_questions(self, survey_data: Dict) -> List[QuestionResponse]:
        """Generate personalized questions based on survey responses"""
        try:
            # This implements the complex question selection logic from the original app
            selected_questions = []
            
            # Get base questions from database
            occupation = survey_data.get("occupation")
            living_situation = survey_data.get("living_situation")
            hobbies = survey_data.get("hobbies", [])
            
            # Select questions based on occupation (questions 1-5)
            if occupation == "사업자/직장인":
                work_questions = await self.question_repo.get_by_property("work")
                selected_questions.extend(work_questions[:5])
            elif occupation == "학생":
                school_questions = await self.question_repo.get_by_property("school")
                selected_questions.extend(school_questions[:5])
            elif occupation == "취업준비생":
                jobseeker_questions = await self.question_repo.get_by_property("jobseeker")
                selected_questions.extend(jobseeker_questions[:5])
            
            # Select questions based on living situation (questions 6-10)
            if "홀로 거주" in living_situation:
                living_questions = await self.question_repo.get_by_property("living_alone")
                selected_questions.extend(living_questions[:5])
            elif "친구나 룸메이트" in living_situation:
                roommate_questions = await self.question_repo.get_by_property("living_roommates")
                selected_questions.extend(roommate_questions[:5])
            elif "가족과 함께" in living_situation:
                family_questions = await self.question_repo.get_by_property("living_family")
                selected_questions.extend(family_questions[:5])
            
            # Select questions based on hobbies (questions 11-15)
            if hobbies:
                hobby_questions = []
                for hobby in hobbies[:2]:  # Take first 2 hobbies
                    hobby_q = await self.question_repo.get_by_property(f"hobby_{hobby.lower()}")
                    hobby_questions.extend(hobby_q[:2])
                selected_questions.extend(hobby_questions[:5])
            
            # If we don't have enough questions, fill with general questions
            if len(selected_questions) < 15:
                general_questions = await self.question_repo.get_by_property("general")
                remaining = 15 - len(selected_questions)
                selected_questions.extend(general_questions[:remaining])
            
            # Convert to response format and ensure we have exactly 15 questions
            question_responses = []
            for i, question in enumerate(selected_questions[:15], 1):
                question_responses.append(QuestionResponse(
                    question_number=i,
                    question_text=question.question_text,
                    property=question.property
                ))
            
            # If still not enough, create placeholder questions
            while len(question_responses) < 15:
                question_responses.append(QuestionResponse(
                    question_number=len(question_responses) + 1,
                    question_text="Tell me about yourself and your daily routine.",
                    property="general"
                ))
            
            logger.info(f"Generated {len(question_responses)} personalized questions")
            return question_responses
            
        except Exception as e:
            logger.error(f"Error generating personalized questions: {str(e)}")
            # Return default questions as fallback
            return await self._get_default_questions()
    
    async def _get_default_questions(self) -> List[QuestionResponse]:
        """Get default questions when personalized generation fails"""
        try:
            default_questions = [
                "Tell me about yourself.",
                "Describe your daily routine.",
                "What do you do in your free time?",
                "Tell me about your family.",
                "Describe your hometown.",
                "What are your hobbies?",
                "Tell me about your job or studies.",
                "Describe a typical weekend for you.",
                "What kind of music do you like?",
                "Tell me about your favorite restaurant.",
                "Describe your home.",
                "What do you like to do when you travel?",
                "Tell me about your friends.",
                "Describe your favorite movie.",
                "What are your future plans?"
            ]
            
            question_responses = []
            for i, question_text in enumerate(default_questions, 1):
                question_responses.append(QuestionResponse(
                    question_number=i,
                    question_text=question_text,
                    property="general"
                ))
            
            logger.info("Using default questions as fallback")
            return question_responses
            
        except Exception as e:
            logger.error(f"Error getting default questions: {str(e)}")
            raise
    
    async def get_student_survey(self, student_id: str) -> Optional[Dict]:
        """Get survey response for a specific student"""
        try:
            survey_response = await self.survey_repo.get_by_student_id(student_id)
            if not survey_response:
                return None
            
            return {
                "student_id": survey_response.student_id,
                "name": survey_response.name,
                "occupation": survey_response.occupation,
                "living_situation": survey_response.living_situation,
                "hobbies": survey_response.hobbies.split(",") if survey_response.hobbies else [],
                "created_at": survey_response.created_at
            }
            
        except Exception as e:
            logger.error(f"Error getting student survey: {str(e)}")
            raise
    
    async def update_student_name(self, student_id: str, name: str) -> bool:
        """Update student name in survey response"""
        try:
            survey_data = {"student_id": student_id, "name": name}
            await self.survey_repo.create_or_update_survey(survey_data)
            return True
            
        except Exception as e:
            logger.error(f"Error updating student name: {str(e)}")
            return False
    
    async def get_survey_statistics(self) -> Dict[str, any]:
        """Get survey response statistics"""
        try:
            return await self.survey_repo.get_survey_statistics()
        except Exception as e:
            logger.error(f"Error getting survey statistics: {str(e)}")
            raise