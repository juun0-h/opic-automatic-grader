from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
import logging
from typing import Dict, Any

from config.database import get_db
from models.schemas import UserCreate, UserResponse
from api.deps import create_access_token, session_manager
from repositories.survey_repo import SurveyRepository

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["authentication"])
security = HTTPBearer()


@router.post("/login", response_model=Dict[str, Any])
async def login(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """
    User login - simplified version for OPIC grader
    In the original Flask app, this was just student ID + name entry
    """
    try:
        # Validate input
        if not user_data.student_id.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Student ID is required"
            )
        
        if not user_data.name.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Name is required"
            )
        
        # In the original app, there's no password - just ID and name
        # We'll create a simple session-based auth for now
        
        student_id = user_data.student_id.strip()
        name = user_data.name.strip()
        
        # Create JWT token
        access_token = create_access_token(
            data={"sub": student_id, "name": name}
        )
        
        # Also store in session manager for compatibility
        session_data = {
            "student_id": student_id,
            "name": name,
            "is_authenticated": True
        }
        session_manager.set_user(student_id, session_data)
        
        # Update survey repository with name if needed
        survey_repo = SurveyRepository(db)
        await survey_repo.create_or_update_survey({
            "student_id": student_id,
            "name": name
        })
        
        logger.info(f"User logged in: {student_id}")
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "student_id": student_id,
            "name": name,
            "message": "로그인 성공"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="로그인 처리 중 오류가 발생했습니다"
        )


@router.post("/logout")
async def logout(
    student_id: str,
):
    """
    User logout - remove from session
    """
    try:
        session_manager.remove_user(student_id)
        
        logger.info(f"User logged out: {student_id}")
        
        return {
            "message": "로그아웃 성공"
        }
        
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="로그아웃 처리 중 오류가 발생했습니다"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: dict = Depends(session_manager.get_user)
):
    """
    Get current user information
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    return UserResponse(
        student_id=current_user["student_id"],
        name=current_user["name"]
    )


@router.post("/verify-token")
async def verify_token(
    current_user: dict = Depends(session_manager.get_user)
):
    """
    Verify if the current token/session is valid
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    return {
        "valid": True,
        "student_id": current_user["student_id"],
        "name": current_user["name"]
    }