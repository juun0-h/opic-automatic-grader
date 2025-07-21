from pydantic import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Database settings
    db_host: str = "localhost"
    db_user: str
    db_password: str
    db_database: str
    
    # Security
    flask_secret_key: str
    jwt_secret_key: str = "your-jwt-secret-key"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # HuggingFace settings
    huggingface_api_token: str
    
    # Model settings
    whisper_model_id: str = "openai/whisper-large-v3"
    llama_model_id: str = "meta-llama/Meta-Llama-3-8B-Instruct"
    
    # Paths
    upload_folder: str = "./records"
    model_cache_dir: str = "./model_cache"
    
    # API settings
    api_prefix: str = "/api"
    cors_origins: list[str] = ["*"]
    
    # Redis settings (for caching and background tasks)
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: Optional[str] = None
    
    # Application settings
    max_file_size: int = 50 * 1024 * 1024  # 50MB
    max_recording_duration: int = 300  # 5 minutes
    max_concurrent_requests: int = 10
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()