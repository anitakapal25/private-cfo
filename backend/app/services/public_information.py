"""Contracts for sourced public information; no provider is enabled by default."""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True)
class PublicInformationEvidence:
    topic: str
    source_name: str
    source_url: str
    retrieved_at: datetime
    source_version: str | None
    limitations: tuple[str, ...]


@dataclass(frozen=True)
class PublicInformationResult:
    summary: str
    evidence: PublicInformationEvidence


class PublicInformationSource(Protocol):
    async def lookup(self, topic: str) -> PublicInformationResult: ...


class PublicInformationUnavailableError(RuntimeError):
    pass


class DisabledPublicInformationSource:
    async def lookup(self, topic: str) -> PublicInformationResult:
        del topic
        raise PublicInformationUnavailableError(
            "Current public information is unavailable until an approved source and licence are configured"
        )
