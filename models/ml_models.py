import torch
from transformers import (
    AutomaticSpeechRecognitionPipeline,
    WhisperForConditionalGeneration,
    WhisperTokenizer,
    WhisperProcessor,
    AutoModelForSpeechSeq2Seq,
    AutoProcessor,
    pipeline,
    RobertaForSequenceClassification,
    RobertaTokenizer
)
from typing import Dict, Optional, Union
import logging
from abc import ABC, abstractmethod
import os
from huggingface_hub import login

from config.settings import settings

logger = logging.getLogger(__name__)


class ModelManager(ABC):
    """Abstract base class for model management"""
    
    def __init__(self):
        self._model = None
        self._tokenizer = None
        self._processor = None
        
    @abstractmethod
    def load_model(self) -> None:
        """Load the model"""
        pass
    
    @abstractmethod
    def predict(self, input_data) -> Union[str, float, Dict]:
        """Make predictions"""
        pass
    
    def is_loaded(self) -> bool:
        """Check if model is loaded"""
        return self._model is not None


class WhisperModelManager(ModelManager):
    """Whisper ASR model manager using Factory pattern"""
    
    def __init__(self, model_id: str = None):
        super().__init__()
        self.model_id = model_id or settings.whisper_model_id
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32
        self._pipeline = None
    
    def load_model(self) -> None:
        """Load Whisper model and create pipeline"""
        try:
            logger.info(f"Loading Whisper model: {self.model_id}")
            
            # Load model and processor
            self._model = AutoModelForSpeechSeq2Seq.from_pretrained(
                self.model_id,
                torch_dtype=self.torch_dtype,
                low_cpu_mem_usage=True,
                use_safetensors=True,
                cache_dir=settings.model_cache_dir
            )
            
            self._model.to(self.device).float()
            self._processor = AutoProcessor.from_pretrained(
                self.model_id,
                cache_dir=settings.model_cache_dir
            )
            
            # Create pipeline
            self._pipeline = pipeline(
                "automatic-speech-recognition",
                model=self._model,
                tokenizer=self._processor.tokenizer,
                feature_extractor=self._processor.feature_extractor,
                max_new_tokens=256,
                chunk_length_s=30,
                batch_size=16,
                return_timestamps=True,
                torch_dtype=self.torch_dtype,
                device=self.device,
            )
            
            logger.info("Whisper model loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {str(e)}")
            raise
    
    def predict(self, audio_file_path: str) -> Dict[str, Union[str, float]]:
        """Transcribe audio file"""
        if not self.is_loaded():
            self.load_model()
            
        try:
            result = self._pipeline(audio_file_path)
            return {
                "transcription": result["text"],
                "confidence": getattr(result, "confidence", None)
            }
        except Exception as e:
            logger.error(f"Failed to transcribe audio: {str(e)}")
            raise


class RobertaScoringModelManager(ModelManager):
    """RoBERTa scoring model manager for different criteria"""
    
    def __init__(self, model_path: str, criterion: str):
        super().__init__()
        self.model_path = model_path
        self.criterion = criterion  # task_completion, accuracy, appropriateness
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
    
    def load_model(self) -> None:
        """Load RoBERTa model for scoring"""
        try:
            logger.info(f"Loading RoBERTa model for {self.criterion}: {self.model_path}")
            
            if not os.path.exists(self.model_path):
                logger.warning(f"Model path does not exist: {self.model_path}")
                return
            
            self._model = RobertaForSequenceClassification.from_pretrained(
                self.model_path,
                cache_dir=settings.model_cache_dir
            )
            self._tokenizer = RobertaTokenizer.from_pretrained(
                self.model_path,
                cache_dir=settings.model_cache_dir
            )
            
            self._model.to(self.device)
            self._model.eval()
            
            logger.info(f"RoBERTa model for {self.criterion} loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load RoBERTa model for {self.criterion}: {str(e)}")
            raise
    
    def predict(self, text: str, question: str = "") -> float:
        """Score the text based on the criterion"""
        if not self.is_loaded():
            self.load_model()
            
        try:
            # Combine question and answer if needed
            input_text = f"{question} [SEP] {text}" if question else text
            
            inputs = self._tokenizer(
                input_text,
                return_tensors="pt",
                truncation=True,
                padding=True,
                max_length=512
            ).to(self.device)
            
            with torch.no_grad():
                outputs = self._model(**inputs)
                # Assuming regression output (single score)
                score = outputs.logits.squeeze().item()
                # Normalize to 0-10 scale if needed
                score = max(0, min(10, score))
                
            return score
            
        except Exception as e:
            logger.error(f"Failed to score text with {self.criterion}: {str(e)}")
            raise


class LlamaFeedbackModelManager(ModelManager):
    """LLaMA model manager for feedback generation"""
    
    def __init__(self, model_id: str = None):
        super().__init__()
        self.model_id = model_id or settings.llama_model_id
        self._pipeline = None
    
    def load_model(self) -> None:
        """Load LLaMA model for feedback generation"""
        try:
            logger.info(f"Loading LLaMA model: {self.model_id}")
            
            # Initialize HuggingFace Hub login
            login(token=settings.huggingface_api_token)
            
            # Create text generation pipeline
            self._pipeline = pipeline(
                "text-generation",
                model=self.model_id,
                device_map="auto",
                torch_dtype=torch.float16,
                cache_dir=settings.model_cache_dir
            )
            
            logger.info("LLaMA model loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load LLaMA model: {str(e)}")
            raise
    
    def predict(self, prompt: str, max_length: int = 500) -> str:
        """Generate feedback text"""
        if not self.is_loaded():
            self.load_model()
            
        try:
            result = self._pipeline(
                prompt,
                max_length=max_length,
                num_return_sequences=1,
                temperature=0.7,
                do_sample=True,
                pad_token_id=self._pipeline.tokenizer.eos_token_id
            )
            
            generated_text = result[0]["generated_text"]
            # Extract only the generated part (remove the prompt)
            feedback = generated_text[len(prompt):].strip()
            
            return feedback
            
        except Exception as e:
            logger.error(f"Failed to generate feedback: {str(e)}")
            raise


class ModelFactory:
    """Factory class for creating ML models using Singleton pattern"""
    
    _instances = {}
    
    @classmethod
    def get_whisper_model(cls) -> WhisperModelManager:
        """Get Whisper model instance (Singleton)"""
        if "whisper" not in cls._instances:
            cls._instances["whisper"] = WhisperModelManager()
        return cls._instances["whisper"]
    
    @classmethod
    def get_roberta_model(cls, criterion: str) -> RobertaScoringModelManager:
        """Get RoBERTa model instance for specific criterion (Singleton)"""
        key = f"roberta_{criterion}"
        if key not in cls._instances:
            model_path = f"./model/{criterion.title()}"
            cls._instances[key] = RobertaScoringModelManager(model_path, criterion)
        return cls._instances[key]
    
    @classmethod
    def get_llama_model(cls) -> LlamaFeedbackModelManager:
        """Get LLaMA model instance (Singleton)"""
        if "llama" not in cls._instances:
            cls._instances["llama"] = LlamaFeedbackModelManager()
        return cls._instances["llama"]
    
    @classmethod
    def load_all_models(cls) -> None:
        """Load all models at startup"""
        try:
            logger.info("Loading all ML models...")
            
            # Load Whisper model
            whisper_model = cls.get_whisper_model()
            whisper_model.load_model()
            
            # Load RoBERTa models
            criteria = ["Task_Completion", "Accuracy", "Appropriateness"]
            for criterion in criteria:
                roberta_model = cls.get_roberta_model(criterion.lower())
                roberta_model.load_model()
            
            # Load LLaMA model
            llama_model = cls.get_llama_model()
            llama_model.load_model()
            
            logger.info("All ML models loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load models: {str(e)}")
            raise
    
    @classmethod
    def cleanup(cls) -> None:
        """Clean up model resources"""
        for instance in cls._instances.values():
            if hasattr(instance, '_model') and instance._model is not None:
                del instance._model
            if hasattr(instance, '_tokenizer') and instance._tokenizer is not None:
                del instance._tokenizer
        cls._instances.clear()
        torch.cuda.empty_cache() if torch.cuda.is_available() else None