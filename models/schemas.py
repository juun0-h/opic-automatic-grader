from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class GradeEnum(str, Enum):
    NH = "NH"  # Novice High
    IL = "IL"  # Intermediate Low
    IM = "IM"  # Intermediate Mid
    IH = "IH"  # Intermediate High  
    AL = "AL"  # Advanced Low


class SurveyOptionEnum(str, Enum):
    # 종사 분야
    BUSINESS_WORKER = "사업자/직장인"
    STUDENT = "학생"
    JOB_SEEKER = "취업준비생"
    
    # 거주 방식
    LIVE_ALONE = "개인주택이나 아파트에 홀로 거주"
    LIVE_WITH_FRIENDS = "친구나 룸메이트와 함께 주택이나 아파트에 거주"
    LIVE_WITH_FAMILY = "가족과 함께 주택이나 아파트에 거주"
    
    # 취미
    EXERCISE = "운동"
    GAME = "게임"
    SNS = "SNS"
    CULTURE = "문화생활"
    TRAVEL = "여행"
    SELF_CARE = "자기관리"
    ART = "예술활동"
    SELF_DEVELOPMENT = "자기개발"


# Base schemas
class BaseSchema(BaseModel):
    class Config:
        from_attributes = True


# User schemas
class UserCreate(BaseSchema):
    student_id: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=100)


class UserResponse(BaseSchema):
    student_id: str
    name: str
    created_at: Optional[datetime] = None


# Survey schemas
class SurveyAnswer(BaseSchema):
    question_id: int = Field(..., ge=1, le=3)
    selected_options: List[str]
    
    @validator('selected_options')
    def validate_options(cls, v, values):
        if not v:
            raise ValueError('At least one option must be selected')
        return v


class SurveySubmission(BaseSchema):
    student_id: str
    answers: List[SurveyAnswer]


class SurveyResponse(BaseSchema):
    questions: Dict[int, str]
    options: Dict[int, List[str]]


# Question schemas
class QuestionResponse(BaseSchema):
    question_number: int
    question_text: str
    property: Optional[str] = None


class QuestionListResponse(BaseSchema):
    questions: List[QuestionResponse]
    total_questions: int = 15


# Audio schemas
class AudioUpload(BaseSchema):
    question_number: int = Field(..., ge=1, le=15)
    student_id: str


class TranscriptionResponse(BaseSchema):
    question_number: int
    transcription: str
    confidence: Optional[float] = None


# Answer schemas
class AnswerCreate(BaseSchema):
    student_id: str
    question_number: int = Field(..., ge=1, le=15)
    question_text: str
    answer_text: str
    score: Optional[float] = None


class AnswerResponse(BaseSchema):
    id: int
    student_id: str
    question_number: int
    question_text: str
    answer_text: str
    score: Optional[float]
    created_at: datetime


# Scoring schemas
class ScoreBreakdown(BaseSchema):
    task_completion: float = Field(..., ge=0, le=10)
    accuracy: float = Field(..., ge=0, le=10)
    appropriateness: float = Field(..., ge=0, le=10)
    total: float = Field(..., ge=0, le=30)


class ScoringResult(BaseSchema):
    question_number: int
    score_breakdown: ScoreBreakdown
    feedback: Optional[str] = None


class FinalScore(BaseSchema):
    student_id: str
    name: str
    total_score: float
    grade: GradeEnum
    individual_scores: List[ScoreBreakdown]
    overall_feedback: str


# Grade schemas
class GradeCreate(BaseSchema):
    student_id: str
    name: str
    grade: GradeEnum
    total_score: float
    feedback: str


class GradeResponse(BaseSchema):
    student_id: str
    name: str
    grade: GradeEnum
    total_score: float
    feedback: str
    created_at: datetime


# WebSocket schemas
class ProgressUpdate(BaseSchema):
    student_id: str
    status: str
    progress: int = Field(..., ge=0, le=100)
    message: str
    data: Optional[Dict[str, Any]] = None


class ErrorResponse(BaseSchema):
    error: str
    message: str
    details: Optional[Dict[str, Any]] = None


# Processing status schemas
class ProcessingStatus(BaseSchema):
    student_id: str
    current_stage: str
    completed_questions: int
    total_questions: int = 15
    estimated_time_remaining: Optional[int] = None  # seconds