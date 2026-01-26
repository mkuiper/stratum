"""Base tool class for all Stratum tools."""
from crewai.tools import BaseTool
from abc import ABC, abstractmethod
from pydantic import Field
from typing import Any, Optional, Type
from pydantic import BaseModel


class StratumBaseTool(BaseTool, ABC):
    """
    Abstract base class for all Stratum tools.

    Extends CrewAI's BaseTool with Stratum-specific conventions.
    """

    # Tool metadata (subclasses should override)
    name: str = Field(..., description="Tool name")
    description: str = Field(..., description="Tool description for agent")

    class Config:
        """Pydantic configuration."""
        arbitrary_types_allowed = True

    @abstractmethod
    def _run(self, *args: Any, **kwargs: Any) -> Any:
        """
        Execute the tool logic.

        Subclasses must implement this method.

        Returns:
            Tool execution result (type depends on specific tool)

        Raises:
            Exception: If tool execution fails
        """
        pass

    def run(self, *args: Any, **kwargs: Any) -> Any:
        """
        Public run method that wraps _run with error handling.

        Returns:
            Tool execution result
        """
        try:
            return self._run(*args, **kwargs)
        except Exception as e:
            error_msg = f"{self.name} failed: {str(e)}"
            raise Exception(error_msg) from e
