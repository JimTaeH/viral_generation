"""
Factory module for instantiating different Language Models.
Supports Google Gemini, OpenAI, and OpenAI-compatible endpoints like OpenTyphoon.
"""
import logging
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from core.config import settings

logger = logging.getLogger(__name__)

class LLMFactory:
    """
    Factory class to create LLM instances based on the specified provider.
    """

    @staticmethod
    def create_llm(
        provider: str, 
        model_name: str, 
        temperature: float = 0.1, 
        max_tokens: int = 4096
    ) -> BaseChatModel:
        """
        Creates and returns a LangChain BaseChatModel instance.

        Args:
            provider (str): The LLM provider (e.g., 'google', 'typhoon', 'openai').
            model_name (str): The specific model version to use.
            temperature (float): The sampling temperature.
            max_tokens (int): The maximum number of tokens to generate.

        Returns:
            BaseChatModel: An instantiated LangChain chat model.
        
        Raises:
            ValueError: If an unsupported provider is specified.
        """
        provider = provider.lower().strip()

        if provider == "google":
            logger.info(f"Initializing Google LLM with model: {model_name}")
            return ChatGoogleGenerativeAI(
                model=model_name,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=30,
                max_retries=2,
                api_key=settings.GOOGLE_API_KEY
            )
            
        elif provider == "typhoon":
            # OpenTyphoon uses an OpenAI-compatible endpoint structure
            logger.info(f"Initializing Typhoon LLM with model: {model_name}")
            return ChatOpenAI(
                model=model_name,
                temperature=temperature,
                max_tokens=max_tokens,
                max_retries=2,
                api_key=settings.TYPHOON_API_KEY,
                base_url="https://api.opentyphoon.ai/v1" # Target the Typhoon API endpoint
            )
            
        elif provider == "thaillm":
            logger.info(f"Initializing Thai LLM with model: {model_name}")
            return ChatOpenAI(
                model=model_name,
                temperature=temperature,
                max_tokens=max_tokens,
                max_retries=2,
                api_key=settings.THAI_LLM_API_KEY,
                base_url="http://thaillm.or.th/api/v1",
                default_headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Accept": "application/json"
                }
            )
            
        elif provider == "openai":
            logger.info(f"Initializing OpenAI LLM with model: {model_name}")
            return ChatOpenAI(
                model=model_name,
                temperature=temperature,
                max_tokens=max_tokens,
                max_retries=2,
                api_key=settings.OPENAI_API_KEY
            )
            
        else:
            logger.error(f"Unsupported LLM provider requested: {provider}")
            raise ValueError(f"Unsupported LLM provider: {provider}")