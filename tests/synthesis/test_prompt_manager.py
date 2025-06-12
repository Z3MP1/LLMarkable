"""Test the PromptManager."""

from pathlib import Path

import pytest

from src.synthesis.prompt_manager import PromptManager


@pytest.fixture
def prompts_dir(tmp_path: Path) -> Path:
    """Create a temporary directory for prompts."""
    return tmp_path

@pytest.fixture
def manager(prompts_dir: Path) -> PromptManager:
    """Create a PromptManager instance."""
    return PromptManager(prompts_dir)

def test_get_template_loads_and_caches(manager: PromptManager, prompts_dir: Path) -> None:
    """Test that the template is loaded and cached."""
    # Simulate a template file
    template_path = prompts_dir / "pdf" / "summarize_light.txt"
    template_path.parent.mkdir(parents=True, exist_ok=True)
    template_path.write_text("Summarize: {content}")
    # Patch Path.open to use real file
    result = manager.get_template("pdf", "summarize", "light")
    assert result == "Summarize: {content}"
    # Should be cached
    assert ("pdf/summarize_light.txt" in manager._cache or
            str(template_path) in manager._cache.values())

def test_get_template_missing_raises(manager: PromptManager) -> None:
    """Test that a FileNotFoundError is raised when a template is missing."""
    with pytest.raises(FileNotFoundError):
        manager.get_template("pdf", "not_a_task", "light")

def test_format_template_substitutes_vars(manager: PromptManager) -> None:
    """Test that the template is substituted with the correct variables."""
    template = "Summarize: {content}"
    result = manager.format_template(template, content="Hello")
    assert result == "Summarize: Hello"

def test_format_template_missing_var_raises(manager: PromptManager) -> None:
    """Test that a KeyError is raised when a required variable is missing."""
    template = "Summarize: {content}"
    with pytest.raises(KeyError):
        manager.format_template(template)

def test_all_required_templates_exist() -> None:
    """Test that all required prompt templates exist for each format and task."""
    base_dir = Path("src/synthesis/prompts")
    formats = ["pdf", "html", "markdown", "docx", "pptx", "image"]
    tasks = ["summarize", "reformat", "correct_grammar"]
    levels = ["light", "moderate", "aggressive"]
    # Only summarize has all levels; others only light
    for fmt in formats:
        for task in tasks:
            if task == "summarize":
                for level in levels:
                    path = base_dir / fmt / f"{task}_{level}.txt"
                    assert path.exists(), f"Missing: {path}"
            else:
                path = base_dir / fmt / f"{task}_light.txt"
                assert path.exists(), f"Missing: {path}"
