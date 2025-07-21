import asyncio
import logging
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor

from models.ml_models import ModelFactory
from models.schemas import ScoreBreakdown, FinalScore
from config.settings import settings

logger = logging.getLogger(__name__)


class FeedbackService:
    """Service for generating personalized feedback using LLaMA model"""
    
    def __init__(self):
        self.llama_model = ModelFactory.get_llama_model()
        self.executor = ThreadPoolExecutor(max_workers=2)
        
        # Feedback templates for different score ranges
        self.score_templates = {
            "excellent": "우수한 답변입니다",
            "good": "좋은 답변이지만 개선의 여지가 있습니다",
            "average": "평균적인 답변입니다", 
            "needs_improvement": "많은 개선이 필요합니다"
        }
    
    async def generate_individual_feedback(self, answer_text: str, question_text: str, 
                                         scores: ScoreBreakdown, question_number: int) -> str:
        """Generate feedback for a single answer"""
        try:
            prompt = self._build_feedback_prompt(answer_text, question_text, scores, question_number)
            
            # Generate feedback asynchronously
            loop = asyncio.get_event_loop()
            feedback = await loop.run_in_executor(
                self.executor,
                self._generate_feedback_sync,
                prompt
            )
            
            return feedback
            
        except Exception as e:
            logger.error(f"Error generating individual feedback for question {question_number}: {str(e)}")
            return self._get_fallback_feedback(scores, question_number)
    
    async def generate_overall_feedback(self, student_name: str, final_score: float, 
                                      grade: str, individual_scores: List[ScoreBreakdown],
                                      answers_data: List[Dict]) -> str:
        """Generate comprehensive overall feedback"""
        try:
            prompt = self._build_overall_feedback_prompt(
                student_name, final_score, grade, individual_scores, answers_data
            )
            
            # Generate overall feedback asynchronously
            loop = asyncio.get_event_loop()
            feedback = await loop.run_in_executor(
                self.executor,
                self._generate_feedback_sync,
                prompt
            )
            
            return feedback
            
        except Exception as e:
            logger.error(f"Error generating overall feedback: {str(e)}")
            return self._get_fallback_overall_feedback(student_name, final_score, grade)
    
    def _generate_feedback_sync(self, prompt: str) -> str:
        """Synchronous feedback generation for thread execution"""
        try:
            if not self.llama_model.is_loaded():
                self.llama_model.load_model()
            
            feedback = self.llama_model.predict(prompt, max_length=500)
            
            # Clean up the feedback
            feedback = self._clean_feedback(feedback)
            
            logger.info("Feedback generated successfully")
            return feedback
            
        except Exception as e:
            logger.error(f"Error in sync feedback generation: {str(e)}")
            raise
    
    def _build_feedback_prompt(self, answer_text: str, question_text: str, 
                              scores: ScoreBreakdown, question_number: int) -> str:
        """Build prompt for individual question feedback"""
        prompt = f"""
다음은 OPIC 영어 말하기 평가에서 학생의 답변입니다. 건설적이고 구체적인 피드백을 한국어로 제공해주세요.

질문: {question_text}

학생 답변: {answer_text}

채점 결과:
- 과제 완성도: {scores.task_completion}/10
- 정확성: {scores.accuracy}/10  
- 적절성: {scores.appropriateness}/10
- 총점: {scores.total}/30

다음 항목들을 포함한 피드백을 작성해주세요:
1. 답변의 강점
2. 개선이 필요한 부분
3. 구체적인 개선 방법
4. 격려의 말

피드백:
"""
        return prompt
    
    def _build_overall_feedback_prompt(self, student_name: str, final_score: float,
                                     grade: str, individual_scores: List[ScoreBreakdown],
                                     answers_data: List[Dict]) -> str:
        """Build prompt for overall feedback"""
        
        # Calculate average scores for each criterion
        avg_task_completion = sum(s.task_completion for s in individual_scores) / len(individual_scores)
        avg_accuracy = sum(s.accuracy for s in individual_scores) / len(individual_scores)
        avg_appropriateness = sum(s.appropriateness for s in individual_scores) / len(individual_scores)
        
        # Find strongest and weakest areas
        criterions = {
            "과제 완성도": avg_task_completion,
            "정확성": avg_accuracy,
            "적절성": avg_appropriateness
        }
        strongest = max(criterions, key=criterions.get)
        weakest = min(criterions, key=criterions.get)
        
        prompt = f"""
{student_name} 학생의 OPIC 영어 말하기 평가 종합 결과입니다. 개인화된 종합 피드백을 한국어로 제공해주세요.

평가 결과:
- 최종 점수: {final_score:.1f}/450 (15문제 × 30점)
- 등급: {grade}
- 평균 과제 완성도: {avg_task_completion:.1f}/10
- 평균 정확성: {avg_accuracy:.1f}/10
- 평균 적절성: {avg_appropriateness:.1f}/10

가장 강한 영역: {strongest}
가장 약한 영역: {weakest}

다음 내용을 포함한 종합 피드백을 작성해주세요:
1. 전반적인 평가와 축하 메시지
2. 주요 강점 분석
3. 개선이 필요한 영역과 구체적인 학습 방법
4. 향후 학습 계획 제안
5. 격려와 동기부여 메시지

종합 피드백:
"""
        return prompt
    
    def _clean_feedback(self, raw_feedback: str) -> str:
        """Clean and format generated feedback"""
        try:
            # Remove any unwanted tokens or formatting
            feedback = raw_feedback.strip()
            
            # Remove any repetitive content
            lines = feedback.split('\n')
            unique_lines = []
            for line in lines:
                line = line.strip()
                if line and line not in unique_lines:
                    unique_lines.append(line)
            
            # Join lines back
            cleaned_feedback = '\n'.join(unique_lines)
            
            # Ensure feedback is not too long
            if len(cleaned_feedback) > 1000:
                cleaned_feedback = cleaned_feedback[:1000] + "..."
            
            return cleaned_feedback
            
        except Exception as e:
            logger.error(f"Error cleaning feedback: {str(e)}")
            return raw_feedback
    
    def _get_fallback_feedback(self, scores: ScoreBreakdown, question_number: int) -> str:
        """Generate fallback feedback when AI generation fails"""
        try:
            score_level = self._get_score_level(scores.total)
            
            base_feedback = f"질문 {question_number}번에 대한 답변 분석:\n\n"
            
            if score_level == "excellent":
                base_feedback += "우수한 답변입니다! 모든 평가 기준에서 높은 점수를 받았습니다.\n"
            elif score_level == "good":
                base_feedback += "좋은 답변입니다. 몇 가지 부분에서 개선하면 더 좋을 것 같습니다.\n"
            elif score_level == "average":
                base_feedback += "평균적인 답변입니다. 더 구체적이고 자세한 설명이 필요합니다.\n"
            else:
                base_feedback += "답변에 더 많은 노력이 필요합니다. 질문에 더 직접적으로 답해보세요.\n"
            
            # Add specific criterion feedback
            if scores.task_completion < 6:
                base_feedback += "• 질문의 요구사항을 더 완전히 답변해보세요.\n"
            if scores.accuracy < 6:
                base_feedback += "• 문법과 어휘 사용에 더 주의를 기울여보세요.\n"
            if scores.appropriateness < 6:
                base_feedback += "• 상황에 더 적절한 표현을 사용해보세요.\n"
            
            return base_feedback
            
        except Exception as e:
            logger.error(f"Error generating fallback feedback: {str(e)}")
            return "답변에 대한 피드백을 생성할 수 없습니다. 다시 시도해주세요."
    
    def _get_fallback_overall_feedback(self, student_name: str, final_score: float, grade: str) -> str:
        """Generate fallback overall feedback"""
        try:
            feedback = f"{student_name} 학생의 OPIC 평가 결과\n\n"
            feedback += f"최종 점수: {final_score:.1f}점\n"
            feedback += f"등급: {grade}\n\n"
            
            if grade in ["AL", "IH"]:
                feedback += "뛰어난 영어 실력을 보여주셨습니다! 계속해서 다양한 주제로 연습하시기 바랍니다."
            elif grade in ["IM", "IL"]:
                feedback += "좋은 기초 실력을 가지고 계십니다. 더 복잡한 표현과 어휘를 늘려가시기 바랍니다."
            else:
                feedback += "기본기를 더 다져가시기 바랍니다. 꾸준한 연습을 통해 실력 향상을 기대합니다."
            
            return feedback
            
        except Exception as e:
            logger.error(f"Error generating fallback overall feedback: {str(e)}")
            return "종합 피드백을 생성할 수 없습니다."
    
    def _get_score_level(self, score: float) -> str:
        """Determine score level for template selection"""
        if score >= 24:  # 80% and above
            return "excellent"
        elif score >= 18:  # 60-79%
            return "good"
        elif score >= 12:  # 40-59%
            return "average"
        else:  # Below 40%
            return "needs_improvement"
    
    async def generate_batch_feedback(self, feedback_requests: List[Dict]) -> List[str]:
        """Generate feedback for multiple answers concurrently"""
        try:
            tasks = []
            for request in feedback_requests:
                task = self.generate_individual_feedback(
                    request["answer_text"],
                    request["question_text"],
                    request["scores"],
                    request["question_number"]
                )
                tasks.append(task)
            
            feedbacks = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Handle exceptions
            valid_feedbacks = []
            for i, feedback in enumerate(feedbacks):
                if isinstance(feedback, Exception):
                    logger.error(f"Failed to generate feedback {i}: {str(feedback)}")
                    valid_feedbacks.append(f"피드백 생성에 실패했습니다. (질문 {i+1})")
                else:
                    valid_feedbacks.append(feedback)
            
            return valid_feedbacks
            
        except Exception as e:
            logger.error(f"Error generating batch feedback: {str(e)}")
            raise