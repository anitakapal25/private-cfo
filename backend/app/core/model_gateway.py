"""Provider-neutral model boundary; disabled until the model release gate passes."""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ModelRequest:
    intent: str
    redacted_context: dict
    tool_results: list[dict]


class ModelGateway(Protocol):
    async def compose(self, request: ModelRequest) -> str: ...


class ModelDisabledError(RuntimeError):
    pass


class DisabledModelGateway:
    async def compose(self, request: ModelRequest) -> str:
        raise ModelDisabledError(
            "External model use is disabled until privacy review and model safety evaluations pass"
        )
