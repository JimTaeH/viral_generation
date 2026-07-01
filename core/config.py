"""
Configuration module for the application.
Loads environment variables required for LINE API and database connections.
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Settings:
    """
    Application settings containing secret keys and credentials.
    """
    PROJECT_NAME: str = "viral_generation"

    # LLM API Keys
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    TYPHOON_API_KEY: str = os.getenv("TYPHOON_API_KEY", "")
    THAI_LLM_API_KEY: str = os.getenv("THAI_LLM_API_KEY", "")

settings = Settings()