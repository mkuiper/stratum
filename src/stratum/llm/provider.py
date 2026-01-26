"""LLM abstraction layer using LiteLLM for model-agnostic access."""
from typing import Optional, Dict, Any, List
from litellm import completion, acompletion
import os


class LLMProvider:
    """
    Model-agnostic LLM wrapper using LiteLLM.

    Supports:
    - OpenAI (gpt-4o, gpt-4o-mini, etc.)
    - Anthropic (claude-3-5-sonnet-20241022, etc.)
    - Ollama (ollama/llama3.2, ollama/mistral, etc.)
    - Any other LiteLLM-supported provider

    LiteLLM handles all provider-specific differences automatically.
    """

    def __init__(
        self,
        model: str,
        api_key: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4000,
        **kwargs
    ):
        """
        Initialize LLM provider.

        Args:
            model: Model identifier (e.g., "gpt-4o", "claude-3-5-sonnet-20241022", "ollama/llama3.2")
            api_key: Optional API key (will use env vars if not provided)
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional provider-specific parameters
        """
        self.model = model
        self.api_key = api_key
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.kwargs = kwargs

        # Set API key in environment if provided (LiteLLM reads from env)
        if api_key:
            if "gpt" in model.lower():
                os.environ["OPENAI_API_KEY"] = api_key
            elif "claude" in model.lower():
                os.environ["ANTHROPIC_API_KEY"] = api_key

    def generate(
        self,
        messages: List[Dict[str, str]],
        **override_kwargs
    ) -> str:
        """
        Generate completion using LiteLLM's unified interface.

        Args:
            messages: List of message dicts with 'role' and 'content'
                     [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}]
            **override_kwargs: Override default parameters for this call

        Returns:
            Generated text as string

        Raises:
            Exception: If LLM call fails
        """
        try:
            # Merge default params with overrides
            params = {
                "model": self.model,
                "messages": messages,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                **self.kwargs,
                **override_kwargs
            }

            response = completion(**params)
            return response.choices[0].message.content

        except Exception as e:
            raise Exception(f"LLM generation failed: {str(e)}") from e

    async def generate_async(
        self,
        messages: List[Dict[str, str]],
        **override_kwargs
    ) -> str:
        """
        Async version of generate().

        Args:
            messages: List of message dicts
            **override_kwargs: Override default parameters

        Returns:
            Generated text as string
        """
        try:
            params = {
                "model": self.model,
                "messages": messages,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                **self.kwargs,
                **override_kwargs
            }

            response = await acompletion(**params)
            return response.choices[0].message.content

        except Exception as e:
            raise Exception(f"Async LLM generation failed: {str(e)}") from e

    def generate_json(
        self,
        messages: List[Dict[str, str]],
        **override_kwargs
    ) -> str:
        """
        Generate completion with JSON mode enabled (if supported by model).

        Args:
            messages: List of message dicts
            **override_kwargs: Override default parameters

        Returns:
            Generated JSON string
        """
        # For models that support JSON mode
        json_params = {}
        if "gpt" in self.model.lower():
            json_params["response_format"] = {"type": "json_object"}

        return self.generate(messages, **json_params, **override_kwargs)

    @classmethod
    def from_settings(cls, settings) -> "LLMProvider":
        """
        Create LLMProvider from Settings object.

        Args:
            settings: Settings instance from config.settings

        Returns:
            Configured LLMProvider instance
        """
        return cls(
            model=settings.LLM_MODEL,
            api_key=settings.get_api_key(),
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS
        )

    def __repr__(self) -> str:
        return f"LLMProvider(model={self.model}, temperature={self.temperature})"


def create_llm_for_crewai(settings) -> str:
    """
    Create LLM model string for CrewAI agents.

    CrewAI can use LiteLLM model strings directly.

    Args:
        settings: Settings instance

    Returns:
        Model string for CrewAI (e.g., "gpt-4o", "ollama/llama3.2")
    """
    # Ensure API keys are in environment
    api_key = settings.get_api_key()
    if api_key:
        if "gpt" in settings.LLM_MODEL.lower():
            os.environ["OPENAI_API_KEY"] = api_key
        elif "claude" in settings.LLM_MODEL.lower():
            os.environ["ANTHROPIC_API_KEY"] = api_key

    # CrewAI uses LiteLLM model strings directly
    return settings.LLM_MODEL
