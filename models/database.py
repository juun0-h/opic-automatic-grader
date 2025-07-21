from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from config.database import Base


class Question(Base):
    __tablename__ = "question"
    
    id = Column(Integer, primary_key=True, index=True)
    property = Column(String(100), nullable=False, index=True)
    link = Column(Integer, nullable=False, index=True)
    question_text = Column(Text, nullable=False)
    
    # Relationships
    answers = relationship("Answer", back_populates="question_ref")


class Answer(Base):
    __tablename__ = "answer"
    
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String(50), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    question_number = Column(Integer, nullable=False)
    question_text = Column(Text, nullable=False)
    answer_text = Column(Text, nullable=False)
    score = Column(Float, nullable=True)
    
    # Scoring breakdown
    task_completion_score = Column(Float, nullable=True)
    accuracy_score = Column(Float, nullable=True)
    appropriateness_score = Column(Float, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Foreign key (optional - if we want to reference the original question)
    question_id = Column(Integer, ForeignKey("question.id"), nullable=True)
    
    # Relationships
    question_ref = relationship("Question", back_populates="answers")
    grade = relationship("Grade", back_populates="answers", foreign_keys="[Grade.student_id]")


class Grade(Base):
    __tablename__ = "grade"
    
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String(50), nullable=False, unique=True, index=True)
    name = Column(String(100), nullable=False)
    grade = Column(String(10), nullable=False)  # NH, IL, IM, IH, AL
    total_score = Column(Float, nullable=False)
    feedback = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    answers = relationship("Answer", back_populates="grade", 
                          foreign_keys="[Answer.student_id]",
                          primaryjoin="Grade.student_id == Answer.student_id")


class SurveyResponse(Base):
    __tablename__ = "survey_response"
    
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String(50), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    
    # Survey answers (stored as JSON-like strings or separate columns)
    occupation = Column(String(100), nullable=True)  # 종사 분야
    living_situation = Column(String(200), nullable=True)  # 거주 방식  
    hobbies = Column(Text, nullable=True)  # 취미 (comma-separated or JSON)
    
    created_at = Column(DateTime, default=datetime.utcnow)


class ProcessingStatus(Base):
    __tablename__ = "processing_status"
    
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String(50), nullable=False, unique=True, index=True)
    current_stage = Column(String(50), nullable=False)  # transcription, scoring, feedback, completed
    completed_questions = Column(Integer, default=0)
    total_questions = Column(Integer, default=15)
    
    # Processing metadata
    started_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    # Error handling
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)


class AudioFile(Base):
    __tablename__ = "audio_file"
    
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String(50), nullable=False, index=True)
    question_number = Column(Integer, nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=True)
    duration = Column(Float, nullable=True)  # in seconds
    
    # Processing status
    transcribed = Column(String(20), default="pending")  # pending, processing, completed, failed
    transcription_text = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)