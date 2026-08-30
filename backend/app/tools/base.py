from abc import ABC, abstractmethod
from typing import Dict, Any
import asyncio

class BaseTool(ABC):
    """Abstract base class for all tools in the Financial Freedom Copilot agent system.

    This ensures consistent interface for all tools that the agent can use.
    Each tool must implement execute() and get_description() methods.
    """

    def __init__(self):
        self.name = self.__class__.__name__

    @abstractmethod
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the tool with the given input data.

        Args:
            input_data: Dictionary containing parameters needed for tool execution

        Returns:
            Dictionary containing the tool's output/result
        """
        pass

    @abstractmethod
    def get_description(self) -> str:
        """Get a human-readable description of what this tool does.

        Returns:
            String description of the tool's purpose and functionality
        """
        pass

    def get_name(self) -> str:
        """Get the tool's name.

        Returns:
            String name of the tool
        """
        return self.name