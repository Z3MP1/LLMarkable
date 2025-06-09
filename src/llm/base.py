"""LLM provider interfaces for future refinement capabilities."""

from __future__ import annotations

from abc import ABC, abstractmethod


class BaseLLMProvider(ABC):
    """Abstract base class for Phase 2 LLM providers."""

    @abstractmethod
    def refine(self, text: str) -> str:
        """Refine text content using an LLM."""


class NoOpProvider(BaseLLMProvider):
    """Placeholder LLM provider that returns text unchanged."""

    def refine(self, text: str) -> str:
        """Return text without modification."""
        return text
