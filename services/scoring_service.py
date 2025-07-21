import asyncio
import logging
from typing import Dict, List, Tuple
from concurrent.futures import ThreadPoolExecutor
import numpy as np

from models.ml_models import ModelFactory
from models.schemas import ScoreBreakdown, ScoringResult
from config.settings import settings

logger = logging.getLogger(__name__)


class ScoringService:
    """Service for automated scoring using RoBERTa models"""
    
    def __init__(self):
        self.task_completion_model = ModelFactory.get_roberta_model("task_completion")
        self.accuracy_model = ModelFactory.get_roberta_model("accuracy")
        self.appropriateness_model = ModelFactory.get_roberta_model("appropriateness")
        self.executor = ThreadPoolExecutor(max_workers=3)
        
        # Grade thresholds (these should be calibrated based on your models)
        self.grade_thresholds = {
            "NH": (0, 12),      # Novice High: 0-12
            "IL": (13, 17),     # Intermediate Low: 13-17
            "IM": (18, 22),     # Intermediate Mid: 18-22
            "IH": (23, 27),     # Intermediate High: 23-27
            "AL": (28, 30)      # Advanced Low: 28-30
        }
    
    async def score_single_answer(self, answer_text: str, question_text: str, 
                                 question_number: int) -> ScoringResult:
        """Score a single answer using all three criteria"""
        try:
            # Score all three criteria concurrently
            loop = asyncio.get_event_loop()
            
            tasks = [
                loop.run_in_executor(
                    self.executor, 
                    self._score_task_completion, 
                    answer_text, 
                    question_text
                ),
                loop.run_in_executor(
                    self.executor, 
                    self._score_accuracy, 
                    answer_text, 
                    question_text
                ),
                loop.run_in_executor(
                    self.executor, 
                    self._score_appropriateness, 
                    answer_text, 
                    question_text
                )
            ]
            
            task_completion, accuracy, appropriateness = await asyncio.gather(*tasks)
            
            # Calculate total score
            total = task_completion + accuracy + appropriateness
            
            # Create score breakdown
            score_breakdown = ScoreBreakdown(
                task_completion=round(task_completion, 2),
                accuracy=round(accuracy, 2),
                appropriateness=round(appropriateness, 2),
                total=round(total, 2)
            )
            
            # Create scoring result
            result = ScoringResult(
                question_number=question_number,
                score_breakdown=score_breakdown
            )
            
            logger.info(f"Scored question {question_number}: Total={total:.2f}")
            return result
            
        except Exception as e:
            logger.error(f"Error scoring question {question_number}: {str(e)}")
            raise
    
    def _score_task_completion(self, answer_text: str, question_text: str) -> float:
        """Score task completion using RoBERTa model"""
        try:
            if not self.task_completion_model.is_loaded():
                self.task_completion_model.load_model()
            
            score = self.task_completion_model.predict(answer_text, question_text)
            return max(0.0, min(10.0, score))  # Ensure score is between 0-10
            
        except Exception as e:
            logger.error(f"Error scoring task completion: {str(e)}")
            # Return default score on error
            return 5.0
    
    def _score_accuracy(self, answer_text: str, question_text: str) -> float:
        """Score accuracy using RoBERTa model"""
        try:
            if not self.accuracy_model.is_loaded():
                self.accuracy_model.load_model()
            
            score = self.accuracy_model.predict(answer_text, question_text)
            return max(0.0, min(10.0, score))  # Ensure score is between 0-10
            
        except Exception as e:
            logger.error(f"Error scoring accuracy: {str(e)}")
            # Return default score on error
            return 5.0
    
    def _score_appropriateness(self, answer_text: str, question_text: str) -> float:
        """Score appropriateness using RoBERTa model"""
        try:
            if not self.appropriateness_model.is_loaded():
                self.appropriateness_model.load_model()
            
            score = self.appropriateness_model.predict(answer_text, question_text)
            return max(0.0, min(10.0, score))  # Ensure score is between 0-10
            
        except Exception as e:
            logger.error(f"Error scoring appropriateness: {str(e)}")
            # Return default score on error
            return 5.0
    
    async def score_multiple_answers(self, answers_data: List[Dict]) -> List[ScoringResult]:
        """Score multiple answers concurrently"""
        try:
            tasks = []
            for answer_data in answers_data:
                task = self.score_single_answer(
                    answer_data["answer_text"],
                    answer_data["question_text"],
                    answer_data["question_number"]
                )
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Filter out exceptions and log them
            valid_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Failed to score answer {i}: {str(result)}")
                else:
                    valid_results.append(result)
            
            return valid_results
            
        except Exception as e:
            logger.error(f"Error scoring multiple answers: {str(e)}")
            raise
    
    def calculate_final_grade(self, total_score: float) -> str:
        """Calculate final grade based on total score"""
        try:
            for grade, (min_score, max_score) in self.grade_thresholds.items():
                if min_score <= total_score <= max_score:
                    return grade
            
            # Default to NH if score is below minimum
            return "NH"
            
        except Exception as e:
            logger.error(f"Error calculating final grade for score {total_score}: {str(e)}")
            return "NH"
    
    def get_grade_description(self, grade: str) -> str:
        """Get description for a grade level"""
        descriptions = {
            "NH": "Novice High - 제한적이지만 일상적인 주제에 대해 간단한 의사소통 가능",
            "IL": "Intermediate Low - 익숙한 주제에 대해 기본적인 의사소통 가능",
            "IM": "Intermediate Mid - 다양한 주제에 대해 어느 정도 유창한 의사소통 가능",
            "IH": "Intermediate High - 복잡한 주제에 대해서도 효과적인 의사소통 가능",
            "AL": "Advanced Low - 추상적이고 전문적인 주제에 대해 능숙한 의사소통 가능"
        }
        return descriptions.get(grade, "등급 정보 없음")
    
    async def get_score_statistics(self, scores: List[float]) -> Dict[str, float]:
        """Calculate score statistics"""
        try:
            if not scores:
                return {
                    "mean": 0.0,
                    "median": 0.0,
                    "std": 0.0,
                    "min": 0.0,
                    "max": 0.0
                }
            
            scores_array = np.array(scores)
            
            return {
                "mean": round(float(np.mean(scores_array)), 2),
                "median": round(float(np.median(scores_array)), 2),
                "std": round(float(np.std(scores_array)), 2),
                "min": round(float(np.min(scores_array)), 2),
                "max": round(float(np.max(scores_array)), 2)
            }
            
        except Exception as e:
            logger.error(f"Error calculating score statistics: {str(e)}")
            raise
    
    def validate_score(self, score: float, criterion: str) -> bool:
        """Validate score value"""
        if not isinstance(score, (int, float)):
            return False
        if score < 0 or score > 10:
            return False
        return True
    
    def normalize_score(self, raw_score: float, min_val: float = 0.0, 
                       max_val: float = 10.0) -> float:
        """Normalize score to 0-10 range"""
        try:
            normalized = max(min_val, min(max_val, raw_score))
            return round(normalized, 2)
        except Exception as e:
            logger.error(f"Error normalizing score {raw_score}: {str(e)}")
            return 5.0  # Default middle score