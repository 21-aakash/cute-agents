from pydantic_settings import BaseSettings, SettingsConfigDict
from openai import OpenAI

class Settings(BaseSettings):
    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "gpt-4o"
    OPENAI_BASE_URL: str | None = None
    MAX_ITERATIONS: int = 10
    REFUND_CAP: float = 500.0
    
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

# Singleton instance
settings = Settings()

# Create OpenAI client
def get_openai_client() -> OpenAI:
    """Get OpenAI client with proxy bypass for corporate networks."""
    client = OpenAI(
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_BASE_URL,
        timeout=30.0,
        max_retries=2
    )
    return client

