from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    NEO4J_URI: str
    NEO4J_USER: str
    NEO4J_PASSWORD: str

    JWT_SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    
    OPENAI_API_KEY: Optional[str] = None  
    
    CLOUDINARY_CLOUD_NAME: str
    CLOUDINARY_API_KEY: str
    CLOUDINARY_API_SECRET: str
    
    class Config:
        env_file = ".env"
        extra = "ignore" 

settings = Settings()