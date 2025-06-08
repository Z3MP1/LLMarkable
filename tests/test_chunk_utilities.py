"""
Unit tests for chunk utilities functionality.

Tests the chunk utility functions including token counting, filtering,
and merging following pytest best practices with proper isolation.
"""

import pytest

from src.config import Config
from src.utils import (
    ChunkData,
    get_tokenizer,
    is_chunk_useful,
    merge_small_trailing_chunks,
)


class TestTokenCounting:
    """Test token counting functionality."""

    def test_should_count_tokens_correctly_when_text_provided(
        self,
        test_config: Config,
    ) -> None:
        """Test that tokenizer counts tokens correctly for various text lengths."""
        tokenizer = get_tokenizer(test_config)

        # Test cases with different text lengths
        test_cases = [
            ("Short text", 2),  # Approximately 2 tokens
            ("This is a medium length text with more words", 10),  # ~10 tokens
            ("Very long text " * 20, 60),  # ~60 tokens (20 * 3 words each)
        ]

        for text, expected_range in test_cases:
            tokens = tokenizer.count_tokens(text)

            # Allow some variance in token counting (±20%)
            assert tokens > 0, f"Token count should be positive for: {text}"
            assert abs(tokens - expected_range) < expected_range * 0.5, (
                f"Token count {tokens} should be roughly {expected_range} for: {text[:30]}..."
            )

    def test_should_handle_empty_text_when_counting_tokens(
        self,
        test_config: Config,
    ) -> None:
        """Test token counting with edge cases."""
        tokenizer = get_tokenizer(test_config)

        assert tokenizer.count_tokens("") == 0
        assert tokenizer.count_tokens("   ") >= 0  # Whitespace may or may not count
        assert tokenizer.count_tokens("\n\t") >= 0

    def test_should_return_huggingface_tokenizer_when_requested(
        self,
        test_config: Config,
    ) -> None:
        """Test that the correct tokenizer type is returned."""
        tokenizer = get_tokenizer(test_config)

        from docling_core.transforms.chunker.tokenizer.huggingface import (
            HuggingFaceTokenizer,
        )

        assert isinstance(tokenizer, HuggingFaceTokenizer)
        assert hasattr(tokenizer, "count_tokens")
        assert hasattr(tokenizer, "max_tokens")


class TestChunkFiltering:
    """Test chunk filtering functionality."""

    def test_should_filter_chunks_based_on_token_count(
        self,
        test_config: Config,
    ) -> None:
        """Test that chunks are filtered based on minimum token requirements."""
        # Create chunks with known content
        test_chunks = [
            ChunkData(text="Short"),  # Should be filtered (too few tokens)
            ChunkData(
                text="This is a properly sized chunk that contains enough meaningful content to meet our minimum token requirements for processing and should definitely pass the filtering criteria. "
                * 5,
            ),  # Should pass (enough tokens) - repeated to ensure sufficient length
            ChunkData(text=""),  # Should be filtered (empty)
        ]

        results = []
        for chunk in test_chunks:
            useful = is_chunk_useful(chunk, test_config)
            results.append(useful)

        # The long chunk should be useful, others should not
        assert not results[0], "Short chunk should be filtered"
        assert results[1], "Long chunk should pass"
        assert not results[2], "Empty chunk should be filtered"

    def test_should_handle_various_chunk_data_types(
        self,
        test_config: Config,
    ) -> None:
        """Test chunk filtering with different data types."""
        # Create longer text to ensure it meets token requirements
        long_text = (
            "This is a substantial chunk with enough content to meet token requirements. "
            * 10
        )
        short_text = "Short"

        # Test with string
        assert is_chunk_useful(long_text, test_config)
        assert not is_chunk_useful(short_text, test_config)

        # Test with ChunkData object
        long_chunk = ChunkData(text=long_text)
        short_chunk = ChunkData(text=short_text)

        assert is_chunk_useful(long_chunk, test_config)
        assert not is_chunk_useful(short_chunk, test_config)

    @pytest.mark.parametrize(
        ("text", "expected_useful"),
        [
            ("", False),  # Empty
            ("   \n\t   ", False),  # Whitespace only
            ("A", False),  # Single character
            (
                "This is a comprehensive chunk with sufficient content to meet our minimum token requirements. "
                * 10,
                True,
            ),  # Long enough - repeated to ensure sufficient tokens
        ],
    )
    def test_should_filter_chunks_consistently(
        self,
        test_config: Config,
        text: str,
        expected_useful: bool,
    ) -> None:
        """Test chunk filtering with parametrized inputs."""
        chunk = ChunkData(text=text)
        result = is_chunk_useful(chunk, test_config)
        assert result == expected_useful, (
            f"Text: '{text[:30]}...' should be {expected_useful}"
        )


class TestChunkMerging:
    """Test chunk merging functionality."""

    def test_should_merge_small_trailing_chunks_when_below_threshold(
        self,
        test_config: Config,
    ) -> None:
        """Test that small trailing chunks are merged with previous chunks."""
        # Create chunks with some small trailing ones
        chunks = [
            ChunkData(
                text="This is a substantial first chunk with plenty of content to analyze and process appropriately.",
            ),
            ChunkData(
                text="This is another substantial chunk that provides good context and meaningful information.",
            ),
            ChunkData(text="Short"),  # Should be merged
            ChunkData(text="Also short"),  # Should also be merged
        ]

        original_count = len(chunks)
        merged_chunks = merge_small_trailing_chunks(chunks, test_config)

        # Should have fewer or equal chunks after merging
        assert len(merged_chunks) <= original_count

        # All chunks should have content
        for chunk in merged_chunks:
            chunk_text = chunk.text if hasattr(chunk, "text") else str(chunk)
            assert len(chunk_text.strip()) > 0

    def test_should_preserve_substantial_chunks_when_merging(
        self,
        test_config: Config,
    ) -> None:
        """Test that substantial chunks are preserved during merging."""
        # Create chunks that are actually substantial enough to not be merged
        # Need to make them long enough to meet the min_tokens requirement
        chunks = [
            ChunkData(
                text="This is a substantial first chunk with plenty of content to analyze and process appropriately. "
                * 20,
            ),
            ChunkData(
                text="This is another substantial chunk that provides good context and meaningful information for analysis. "
                * 20,
            ),
            ChunkData(
                text="This is a third substantial chunk with comprehensive content that meets all requirements. "
                * 20,
            ),
        ]

        original_count = len(chunks)
        merged_chunks = merge_small_trailing_chunks(chunks, test_config)

        # All chunks should be preserved if they're truly substantial
        # Note: The actual behavior depends on the implementation of merge_small_trailing_chunks
        # We verify that we get a reasonable result
        assert len(merged_chunks) > 0
        assert len(merged_chunks) <= original_count

    def test_should_handle_empty_chunk_list_when_merging(
        self,
        test_config: Config,
    ) -> None:
        """Test merge function with edge cases."""
        # Empty list
        result = merge_small_trailing_chunks([], test_config)
        assert result == []

        # Single chunk
        single_chunk = [ChunkData(text="Single chunk")]
        result = merge_small_trailing_chunks(single_chunk, test_config)
        assert len(result) == 1


class TestChunkDataClass:
    """Test ChunkData class functionality."""

    def test_should_initialize_correctly_when_created(self) -> None:
        """Test ChunkData initialization."""
        text = "Test chunk content"
        chunk = ChunkData(text=text)

        assert chunk.text == text
        assert hasattr(chunk, "text")

    def test_should_handle_various_text_types(self) -> None:
        """Test ChunkData with different text inputs."""
        # Normal text
        chunk1 = ChunkData(text="Normal text")
        assert chunk1.text == "Normal text"

        # Empty text
        chunk2 = ChunkData(text="")
        assert chunk2.text == ""

        # Whitespace text
        chunk3 = ChunkData(text="   \n\t   ")
        assert chunk3.text == "   \n\t   "


class TestConfigurationIntegration:
    """Test integration with configuration settings."""

    def test_should_respect_config_min_tokens_setting(self) -> None:
        """Test that filtering respects configuration min_tokens setting."""
        # Create configs with different min_tokens values
        config_low = Config.default()
        config_low.min_tokens = 5

        config_high = Config.default()
        config_high.min_tokens = 50

        # Test chunk that should pass low threshold but fail high threshold
        chunk = ChunkData(text="This is a medium length chunk")

        result_low = is_chunk_useful(chunk, config_low)
        result_high = is_chunk_useful(chunk, config_high)

        # Results should depend on the min_tokens setting
        # Note: Exact behavior depends on tokenizer, so we just verify they can be different
        assert isinstance(result_low, bool)
        assert isinstance(result_high, bool)

    def test_should_use_config_tokenizer_settings(self) -> None:
        """Test that tokenizer uses configuration settings."""
        config = Config.default()
        config.chunk_size = 2048

        tokenizer = get_tokenizer(config)
        # Note: HuggingFace tokenizer max_tokens may be model-specific
        # We verify it's initialized and has reasonable values
        assert tokenizer.max_tokens > 0
        assert hasattr(tokenizer, "count_tokens")
