"""
Shared pytest fixtures and configuration for LLMarkable tests.

This module provides common fixtures and test utilities used across
all test modules to ensure consistent test setup and isolation.
"""

from pathlib import Path
from unittest.mock import Mock

import pytest

from src.config import Config


@pytest.fixture
def test_config() -> Config:
    """Create a test configuration with safe defaults."""
    config = Config.default()
    config.verbose = False  # Reduce noise in tests
    config.chunk_size = 1024  # Smaller for faster tests
    config.min_tokens = 50  # Lower threshold for tests
    return config


@pytest.fixture
def test_config_with_output_dir(tmp_path: Path) -> Config:
    """Create a test configuration with a temporary output directory."""
    config = Config.default()
    config.verbose = False
    config.chunk_size = 1024
    config.min_tokens = 50
    config.output_dir = str(tmp_path)
    config.include_metadata = True  # Enable for testing metadata features
    return config


@pytest.fixture
def test_output_dir(tmp_path: Path) -> Path:
    """Provide a clean temporary directory for test outputs."""
    output_dir = tmp_path / "test_output"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


@pytest.fixture
def mock_docling_document() -> Mock:
    """Create a mock Docling document for testing."""
    mock_doc = Mock()
    mock_doc.texts = [
        Mock(text="This is the first chunk of text content."),
        Mock(text="This is the second chunk with more content."),
        Mock(text="Final chunk with conclusion."),
    ]
    mock_doc.tables = []
    return mock_doc


@pytest.fixture
def mock_docling_converter() -> Mock:
    """Create a mock DocumentConverter for testing."""
    mock_converter = Mock()
    mock_result = Mock()
    mock_result.document = Mock()
    mock_converter.convert.return_value = mock_result
    return mock_converter


@pytest.fixture
def mock_tokenizer() -> Mock:
    """Create a mock tokenizer for testing."""
    mock_tokenizer = Mock()
    mock_tokenizer.max_tokens = 1024

    # Mock encode method to return predictable token counts
    def mock_encode(text: str) -> list[int]:
        # Simple approximation: ~4 characters per token
        return list(range(len(text) // 4))

    def mock_count_tokens(text: str) -> int:
        # Simple approximation: ~4 characters per token
        return len(text) // 4

    mock_tokenizer.encode = mock_encode
    mock_tokenizer.count_tokens = mock_count_tokens
    return mock_tokenizer


@pytest.fixture
def sample_chunks() -> list[str]:
    """Provide sample text chunks for testing."""
    return [
        "This is a short chunk with minimal content.",
        "This is a longer chunk with more substantial content that should meet the minimum token requirements for processing.",
        "Another chunk with different content to test various scenarios.",
        "A very short chunk.",
        "Final chunk with comprehensive content that includes multiple sentences and should definitely meet any reasonable token threshold requirements.",
    ]


@pytest.fixture
def test_file_path() -> Path:
    """Provide a test file path for testing."""
    return Path("test_document.pdf")


@pytest.fixture
def mock_chunks() -> list[Mock]:
    """Create mock chunk objects for testing."""
    chunks = []
    for i, text in enumerate(
        [
            "First chunk content with sufficient length to meet minimum token requirements",
            "Second chunk with more content and additional context for testing purposes",
            "Third chunk content that provides meaningful information for processing",
        ],
    ):
        chunk = Mock()
        chunk.text = text
        chunk.meta = {"chunk_id": i}
        chunks.append(chunk)
    return chunks


@pytest.fixture
def sample_input_file(tmp_path: Path) -> Path:
    """Create a sample input file for testing."""
    input_file = tmp_path / "sample.html"
    input_file.write_text(
        """
    <!DOCTYPE html>
    <html>
    <head><title>Test Document</title></head>
    <body>
        <h1>Test Content</h1>
        <p>This is a test paragraph with some content.</p>
        <p>Another paragraph with more content for testing purposes.</p>
    </body>
    </html>
    """,
        encoding="utf-8",
    )
    return input_file


# Test configuration
pytest_plugins: list[str] = []


# Configure pytest behavior
def pytest_configure(config: pytest.Config) -> None:
    """Configure pytest with custom settings."""
    config.addinivalue_line(
        "markers",
        "unit: mark test as a unit test",
    )
    config.addinivalue_line(
        "markers",
        "slow: mark test as slow running",
    )


def pytest_collection_modifyitems(
    items: list[pytest.Item],
) -> None:
    """Modify test collection to add markers automatically."""
    for item in items:
        # Mark all tests as unit tests by default
        if "unit" not in [mark.name for mark in item.iter_markers()]:
            item.add_marker(pytest.mark.unit)
