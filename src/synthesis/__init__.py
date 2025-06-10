"""Synthesis providers."""

# The synthesis package exposes the providers subpackage for LLM provider implementations.

# Prompt templates for synthesis are stored in the prompts/ directory (format-specific subdirs)

from . import providers

__all__ = ["providers"]
