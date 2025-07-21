from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Generator, Optional
import jwt
import logging

from config.database import get_db
from config.settings import settings
from repositories.question_repo import QuestionRepository
from repositories.answer_repo import AnswerRepository
from repositories.grade_repo import GradeRepository
from repositories.survey_repo import SurveyRepository
from services.audio_service import AudioService
from services.scoring_service import ScoringService
from services.feedback_service import FeedbackService
from services.survey_service import SurveyService

logger = logging.getLogger(__name__)

# Security
security = HTTPBearer(auto_error=False)


# Database Dependencies
def get_question_repository(db: Session = Depends(get_db)) -> QuestionRepository:
    """Get Question Repository instance"""
    return QuestionRepository(db)


def get_answer_repository(db: Session = Depends(get_db)) -> AnswerRepository:
    """Get Answer Repository instance"""
    return AnswerRepository(db)


def get_grade_repository(db: Session = Depends(get_db)) -> GradeRepository:
    """Get Grade Repository instance"""
    return GradeRepository(db)


def get_survey_repository(db: Session = Depends(get_db)) -> SurveyRepository:
    """Get Survey Repository instance"""
    return SurveyRepository(db)


# Service Dependencies
def get_audio_service() -> AudioService:
    """Get Audio Service instance (Singleton)"""
    return AudioService()


def get_scoring_service() -> ScoringService:
    """Get Scoring Service instance (Singleton)"""
    return ScoringService()


def get_feedback_service() -> FeedbackService:
    """Get Feedback Service instance (Singleton)"""
    return FeedbackService()


def get_survey_service(db: Session = Depends(get_db)) -> SurveyService:
    """Get Survey Service instance"""
    return SurveyService(db)


# Authentication Dependencies
async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[dict]:
    """
    Get current user from JWT token
    For now, this is simplified - in production you'd want proper user management
    """
    if not credentials:
        return None
    
    try:
        token = credentials.credentials
        payload = jwt.decode(
            token, 
            settings.jwt_secret_key, 
            algorithms=[settings.jwt_algorithm]
        )
        
        student_id: str = payload.get("sub")
        if student_id is None:
            return None
        
        return {
            "student_id": student_id,
            "name": payload.get("name", ""),
        }
        
    except jwt.PyJWTError:
        return None


async def get_current_user_required(
    current_user: Optional[dict] = Depends(get_current_user)
) -> dict:
    """
    Require authenticated user
    """
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return current_user


# Session-based user (temporary for migration from Flask)
class SessionUser:
    """Temporary session-based user management for migration compatibility"""
    
    def __init__(self):
        self._users = {}  # In-memory storage - replace with Redis in production
    
    def set_user(self, session_id: str, user_data: dict):
        """Set user data for session"""
        self._users[session_id] = user_data
    
    def get_user(self, session_id: str) -> Optional[dict]:
        """Get user data for session"""
        return self._users.get(session_id)
    
    def remove_user(self, session_id: str):
        """Remove user data for session"""
        self._users.pop(session_id, None)


# Global session manager (replace with Redis in production)
session_manager = SessionUser()


def get_session_user(session_id: Optional[str] = None) -> Optional[dict]:
    """
    Get user from session (temporary for Flask migration)
    In production, this should use Redis or proper session management
    """
    if not session_id:
        return None
    
    return session_manager.get_user(session_id)


# Utility functions
def create_access_token(data: dict) -> str:
    """Create JWT access token"""
    import datetime
    
    to_encode = data.copy()
    expire = datetime.datetime.utcnow() + datetime.timedelta(
        minutes=settings.access_token_expire_minutes
    )
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.jwt_secret_key, 
        algorithm=settings.jwt_algorithm
    )
    
    return encoded_jwt


def verify_student_access(current_student_id: str, requested_student_id: str) -> bool:
    """
    Verify that the current user can access the requested student's data
    In a multi-user system, you'd check permissions here
    """
    return current_student_id == requested_student_id


# Request validation
def validate_question_number(question_number: int) -> int:
    """Validate question number is within valid range"""
    if not 1 <= question_number <= 15:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question number must be between 1 and 15"
        )
    return question_number


def validate_student_id(student_id: str) -> str:
    """Validate student ID format"""
    if not student_id or len(student_id.strip()) < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Student ID is required"
        )
    return student_id.strip()


# Error handlers
def handle_repository_error(error: Exception, operation: str) -> HTTPException:
    """Handle repository errors and convert to HTTP exceptions"""
    logger.error(f"Repository error during {operation}: {str(error)}")
    
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Database error during {operation}"
    )


def handle_service_error(error: Exception, operation: str) -> HTTPException:
    """Handle service errors and convert to HTTP exceptions"""
    logger.error(f"Service error during {operation}: {str(error)}")
    
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Service error during {operation}"
    )