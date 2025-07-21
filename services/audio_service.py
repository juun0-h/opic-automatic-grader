import os
import asyncio
import logging
from typing import Dict, Optional, Tuple
from pathlib import Path

from models.ml_models import ModelFactory
from models.schemas import TranscriptionResponse, AudioUpload
from config.settings import settings

logger = logging.getLogger(__name__)


class AudioService:
    """Service for handling audio processing and transcription"""
    
    def __init__(self):
        self.whisper_model = ModelFactory.get_whisper_model()
        self.upload_folder = Path(settings.upload_folder)
        self.max_file_size = settings.max_file_size
        self.max_duration = settings.max_recording_duration
    
    async def save_audio_file(self, file_content: bytes, student_id: str, 
                            question_number: int, file_extension: str = "webm") -> str:
        """Save uploaded audio file to disk"""
        try:
            # Ensure upload directory exists
            self.upload_folder.mkdir(parents=True, exist_ok=True)
            
            # Generate filename
            filename = f"{student_id}_q{question_number}.{file_extension}"
            file_path = self.upload_folder / filename
            
            # Check file size
            if len(file_content) > self.max_file_size:
                raise ValueError(f"File size exceeds maximum allowed size of {self.max_file_size} bytes")
            
            # Save file
            with open(file_path, "wb") as f:
                f.write(file_content)
            
            logger.info(f"Audio file saved: {file_path}")
            return str(file_path)
            
        except Exception as e:
            logger.error(f"Error saving audio file for student {student_id}, question {question_number}: {str(e)}")
            raise
    
    async def transcribe_audio(self, file_path: str) -> Dict[str, any]:
        """Transcribe audio file using Whisper model"""
        try:
            # Check if file exists
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Audio file not found: {file_path}")
            
            # Run transcription in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, 
                self._transcribe_sync, 
                file_path
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error transcribing audio file {file_path}: {str(e)}")
            raise
    
    def _transcribe_sync(self, file_path: str) -> Dict[str, any]:
        """Synchronous transcription method for thread execution"""
        try:
            if not self.whisper_model.is_loaded():
                self.whisper_model.load_model()
            
            result = self.whisper_model.predict(file_path)
            
            logger.info(f"Audio transcribed successfully: {file_path}")
            return result
            
        except Exception as e:
            logger.error(f"Error in sync transcription: {str(e)}")
            raise
    
    async def process_audio_upload(self, file_content: bytes, audio_data: AudioUpload) -> TranscriptionResponse:
        """Complete audio processing pipeline: save + transcribe"""
        try:
            # Save audio file
            file_path = await self.save_audio_file(
                file_content, 
                audio_data.student_id, 
                audio_data.question_number
            )
            
            # Transcribe audio
            transcription_result = await self.transcribe_audio(file_path)
            
            # Create response
            response = TranscriptionResponse(
                question_number=audio_data.question_number,
                transcription=transcription_result["transcription"],
                confidence=transcription_result.get("confidence")
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing audio upload: {str(e)}")
            raise
    
    async def validate_audio_file(self, file_content: bytes, filename: str) -> bool:
        """Validate uploaded audio file"""
        try:
            # Check file size
            if len(file_content) > self.max_file_size:
                return False
            
            # Check file extension
            allowed_extensions = {'.webm', '.wav', '.mp3', '.m4a', '.ogg'}
            file_ext = Path(filename).suffix.lower()
            if file_ext not in allowed_extensions:
                return False
            
            # Additional validation could include:
            # - Audio format validation
            # - Duration check (if possible without full processing)
            # - Content validation (silence detection, etc.)
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating audio file {filename}: {str(e)}")
            return False
    
    async def get_audio_info(self, file_path: str) -> Dict[str, any]:
        """Get audio file information (duration, format, etc.)"""
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Audio file not found: {file_path}")
            
            file_stat = os.stat(file_path)
            
            # Basic file info
            info = {
                "file_path": file_path,
                "file_size": file_stat.st_size,
                "created_at": file_stat.st_ctime,
                "modified_at": file_stat.st_mtime
            }
            
            # TODO: Add audio-specific info using a library like librosa or pydub
            # info.update({
            #     "duration": duration_in_seconds,
            #     "sample_rate": sample_rate,
            #     "channels": num_channels
            # })
            
            return info
            
        except Exception as e:
            logger.error(f"Error getting audio info for {file_path}: {str(e)}")
            raise
    
    async def cleanup_old_files(self, retention_days: int = 7) -> int:
        """Clean up old audio files"""
        try:
            import time
            
            if not self.upload_folder.exists():
                return 0
            
            current_time = time.time()
            cutoff_time = current_time - (retention_days * 24 * 60 * 60)
            deleted_count = 0
            
            for file_path in self.upload_folder.glob("*.webm"):
                try:
                    file_stat = file_path.stat()
                    if file_stat.st_mtime < cutoff_time:
                        file_path.unlink()
                        deleted_count += 1
                        logger.info(f"Deleted old audio file: {file_path}")
                except Exception as e:
                    logger.warning(f"Could not delete file {file_path}: {str(e)}")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error cleaning up old files: {str(e)}")
            raise
    
    def get_file_path(self, student_id: str, question_number: int, 
                     file_extension: str = "webm") -> str:
        """Get the expected file path for an audio file"""
        filename = f"{student_id}_q{question_number}.{file_extension}"
        return str(self.upload_folder / filename)