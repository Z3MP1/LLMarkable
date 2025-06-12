"""Test the ContentSynthesizer."""
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.config import Config
from src.synthesis.engine import ContentSynthesizer, ContentValidator, PromptManager


@pytest.mark.asyncio
@pytest.mark.parametrize(("refinement_level", "expected_start"), [
    ("light", "Improve clarity and grammar of the following text"),
    ("moderate", "Refine the following text for clarity, style, and readability"),
    ("aggressive", "Rewrite the following text to be concise, well-structured, and engaging"),
])
async def test_refine_chunk_should_call_provider_with_correct_prompt(refinement_level: str, expected_start: str) -> None:
    """Test that the ContentSynthesizer calls the provider with the correct prompt."""
    provider = MagicMock()
    provider.generate = AsyncMock(return_value="refined content")
    config = Config.default()
    config.refinement_level = refinement_level
    synthesizer = ContentSynthesizer(provider)
    chunk = "This is a test chunk."
    result = await synthesizer.refine_chunk(chunk, config)
    provider.generate.assert_awaited_once()
    called_prompt = provider.generate.call_args[0][0]
    assert called_prompt.startswith(expected_start)
    assert chunk in called_prompt
    assert result == "refined content"

def test_prompt_manager_should_return_correct_prompt_for_each_level() -> None:
    """Test that the PromptManager returns the correct prompt for each refinement level."""
    pm = PromptManager()
    chunk = "Some text."
    assert pm.get_prompt("light", chunk).startswith("Improve clarity and grammar")
    assert pm.get_prompt("moderate", chunk).startswith("Refine the following text for clarity")
    assert pm.get_prompt("aggressive", chunk).startswith("Rewrite the following text to be concise")

def test_readability_score_basic() -> None:
    """Test that the readability score is a float between 0 and 206.835."""
    validator = ContentValidator()
    text = "This is a simple sentence. It is easy to read."
    score = validator.readability_score(text)
    assert isinstance(score, float)
    assert 0 <= score <= 206.835

def test_readability_score_edge_cases() -> None:
    """Test that the readability score is a float between 0 and 206.835."""
    validator = ContentValidator()
    # Empty string
    assert validator.readability_score("") == 206.84
    # One word
    assert validator.readability_score("Hello") == 206.84
    # Complex sentence
    text = "Notwithstanding the aforementioned, the implementation of such a protocol necessitates a comprehensive understanding of the underlying theoretical framework."
    score = validator.readability_score(text)
    assert score < 100  # Should be harder to read
