import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Database
    NEO4J_URI: str
    NEO4J_USER: str
    NEO4J_PASSWORD: str
    
    # Security
    JWT_SECRET_KEY: str
    ALGORITHM: str = "HS256"
    
    OPENAI_API_KEY: str

    class Config:
        env_file = ".env"

settings = Settings()