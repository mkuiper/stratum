"""Unit tests for LLM provider."""
import pytest
from unittest.mock import Mock, patch
import os

from stratum.llm.provider import LLMProvider, create_llm_for_crewai


class TestLLMProvider:
    """Tests for LLMProvider class."""

    def test_initialization(self):
        """Test LLMProvider initialization."""
        provider = LLMProvider(
            model="gpt-4o",
            api_key="test-key",
            temperature=0.5,
            max_tokens=2000
        )

        assert provider.model == "gpt-4o"
        assert provider.api_key == "test-key"
        assert provider.temperature == 0.5
        assert provider.max_tokens == 2000

    def test_initialization_sets_openai_env(self):
        """Test that OpenAI API key is set in environment."""
        # Clear env first
        if "OPENAI_API_KEY" in os.environ:
            del os.environ["OPENAI_API_KEY"]

        provider = LLMProvider(model="gpt-4o", api_key="test-openai-key")

        assert os.environ.get("OPENAI_API_KEY") == "test-openai-key"

    def test_initialization_sets_anthropic_env(self):
        """Test that Anthropic API key is set in environment."""
        # Clear env first
        if "ANTHROPIC_API_KEY" in os.environ:
            del os.environ["ANTHROPIC_API_KEY"]

        provider = LLMProvider(model="claude-3-5-sonnet-20241022", api_key="test-anthropic-key")

        assert os.environ.get("ANTHROPIC_API_KEY") == "test-anthropic-key"

    @patch('stratum.llm.provider.completion')
    def test_generate(self, mock_completion):
        """Test generate method."""
        # Mock LiteLLM response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Generated response"
        mock_completion.return_value = mock_response

        provider = LLMProvider(model="gpt-4o", temperature=0.7)
        messages = [{"role": "user", "content": "Test prompt"}]

        result = provider.generate(messages)

        assert result == "Generated response"
        mock_completion.assert_called_once()

        # Verify call parameters
        call_kwargs = mock_completion.call_args[1]
        assert call_kwargs["model"] == "gpt-4o"
        assert call_kwargs["messages"] == messages
        assert call_kwargs["temperature"] == 0.7

    @patch('stratum.llm.provider.completion')
    def test_generate_with_override(self, mock_completion):
        """Test generate with parameter overrides."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Response"
        mock_completion.return_value = mock_response

        provider = LLMProvider(model="gpt-4o", temperature=0.7)
        messages = [{"role": "user", "content": "Test"}]

        provider.generate(messages, temperature=0.0, max_tokens=100)

        call_kwargs = mock_completion.call_args[1]
        assert call_kwargs["temperature"] == 0.0  # Overridden
        assert call_kwargs["max_tokens"] == 100  # Overridden

    @patch('stratum.llm.provider.completion')
    def test_generate_error_handling(self, mock_completion):
        """Test error handling in generate."""
        mock_completion.side_effect = Exception("API error")

        provider = LLMProvider(model="gpt-4o")
        messages = [{"role": "user", "content": "Test"}]

        with pytest.raises(Exception) as exc:
            provider.generate(messages)

        assert "LLM generation failed" in str(exc.value)
        assert "API error" in str(exc.value)

    @patch('stratum.llm.provider.completion')
    def test_generate_json(self, mock_completion):
        """Test JSON generation for supported models."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '{"key": "value"}'
        mock_completion.return_value = mock_response

        provider = LLMProvider(model="gpt-4o")
        messages = [{"role": "user", "content": "Generate JSON"}]

        result = provider.generate_json(messages)

        assert result == '{"key": "value"}'

        # For GPT models, should include response_format
        call_kwargs = mock_completion.call_args[1]
        assert "response_format" in call_kwargs
        assert call_kwargs["response_format"]["type"] == "json_object"

    def test_from_settings(self):
        """Test creating provider from settings."""
        mock_settings = Mock()
        mock_settings.LLM_MODEL = "gpt-4o-mini"
        mock_settings.LLM_TEMPERATURE = 0.8
        mock_settings.LLM_MAX_TOKENS = 3000
        mock_settings.get_api_key.return_value = "test-key"

        provider = LLMProvider.from_settings(mock_settings)

        assert provider.model == "gpt-4o-mini"
        assert provider.temperature == 0.8
        assert provider.max_tokens == 3000
        assert provider.api_key == "test-key"

    def test_repr(self):
        """Test string representation."""
        provider = LLMProvider(model="gpt-4o", temperature=0.5)
        repr_str = repr(provider)

        assert "gpt-4o" in repr_str
        assert "0.5" in repr_str


class TestCreateLLMForCrewAI:
    """Tests for create_llm_for_crewai function."""

    def test_returns_model_string(self):
        """Test that function returns model string."""
        mock_settings = Mock()
        mock_settings.LLM_MODEL = "gpt-4o"
        mock_settings.get_api_key.return_value = None

        result = create_llm_for_crewai(mock_settings)

        assert result == "gpt-4o"

    def test_sets_openai_env_var(self):
        """Test that OpenAI API key is set in environment."""
        if "OPENAI_API_KEY" in os.environ:
            del os.environ["OPENAI_API_KEY"]

        mock_settings = Mock()
        mock_settings.LLM_MODEL = "gpt-4o"
        mock_settings.get_api_key.return_value = "test-api-key"

        create_llm_for_crewai(mock_settings)

        assert os.environ.get("OPENAI_API_KEY") == "test-api-key"

    def test_sets_anthropic_env_var(self):
        """Test that Anthropic API key is set in environment."""
        if "ANTHROPIC_API_KEY" in os.environ:
            del os.environ["ANTHROPIC_API_KEY"]

        mock_settings = Mock()
        mock_settings.LLM_MODEL = "claude-3-5-sonnet-20241022"
        mock_settings.get_api_key.return_value = "test-claude-key"

        create_llm_for_crewai(mock_settings)

        assert os.environ.get("ANTHROPIC_API_KEY") == "test-claude-key"

    def test_ollama_no_api_key_required(self):
        """Test that Ollama models don't require API keys."""
        mock_settings = Mock()
        mock_settings.LLM_MODEL = "ollama/llama3.2"
        mock_settings.get_api_key.return_value = None

        result = create_llm_for_crewai(mock_settings)

        assert result == "ollama/llama3.2"
        # Should not raise any errors
