"""Application settings loaded from environment variables."""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path
from typing import Optional


class Settings(BaseSettings):
    """Application configuration loaded from .env file."""

    # LLM Configuration
    LLM_MODEL: str = "gpt-4o"
    LLM_API_KEY: Optional[str] = None
    LLM_TEMPERATURE: float = 0.7
    LLM_MAX_TOKENS: int = 4000

    # Optional model-specific keys (LiteLLM auto-detects these)
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None

    # GROBID Configuration
    GROBID_URL: str = "http://localhost:8070/api"

    # Recursion Settings
    MAX_DEPTH: int = 3
    MAX_CITATIONS_PER_PAPER: int = 5

    # Paths
    OUTPUT_DIR: Path = Path("./output")
    CACHE_DIR: Path = Path("./data")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"  # Ignore extra environment variables
    )

    def get_api_key(self) -> Optional[str]:
        """
        Get the appropriate API key based on the model.

        LiteLLM will automatically use OPENAI_API_KEY or ANTHROPIC_API_KEY
        from environment if available, so this is mainly for explicit usage.
        """
        if self.LLM_API_KEY:
            return self.LLM_API_KEY

        # Model-specific fallbacks
        if "gpt" in self.LLM_MODEL.lower() and self.OPENAI_API_KEY:
            return self.OPENAI_API_KEY
        elif "claude" in self.LLM_MODEL.lower() and self.ANTHROPIC_API_KEY:
            return self.ANTHROPIC_API_KEY

        return None

    def ensure_directories(self) -> None:
        """Create output and cache directories if they don't exist."""
        self.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        (self.OUTPUT_DIR / "papers").mkdir(exist_ok=True)

        self.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        (self.CACHE_DIR / "pdfs").mkdir(exist_ok=True)
        (self.CACHE_DIR / "processed").mkdir(exist_ok=True)
        (self.CACHE_DIR / "state").mkdir(exist_ok=True)


# Global settings instance
settings = Settings()
