"""Test script for validating chunk utilities implementation."""

import sys

from converter.config import Config
from converter.utils import (
    ChunkData,
    get_tokenizer,
    is_chunk_useful,
    merge_small_trailing_chunks,
)


def test_token_counting() -> bool:
    """Test token counting with various chunk sizes."""
    print("=== Testing Token Counting ===")

    config = Config()
    tokenizer = get_tokenizer(config)

    # Test cases with different chunk sizes
    test_cases = [
        ("Short chunk", 50),
        ("Medium chunk that should meet minimum requirements for usefulness", 200),
        ("Very long chunk " * 100, 1000),
    ]

    for text, _expected_range in test_cases:
        tokens = tokenizer.count_tokens(text)
        is_useful = is_chunk_useful(text, config)

        print(f"Text: '{text[:30]}...' → {tokens} tokens (useful: {is_useful})")

        # Validate that usefulness aligns with token count vs min_tokens
        expected_useful = tokens >= config.min_tokens
        assert is_useful == expected_useful, (
            f"Expected useful={expected_useful}, got {is_useful}"
        )


def test_chunk_filtering() -> bool:
    """Test chunk filtering with different content types."""
    print("\n=== Testing Chunk Filtering ===")

    config = Config()

    test_chunks = [
        ChunkData(text="Too short"),  # Should be filtered
        ChunkData(
            text="This is a properly sized chunk that contains enough meaningful content to meet our minimum token requirements for processing.",
        ),  # Should pass
        ChunkData(text=""),  # Edge case: empty
        ChunkData(text="   \n\t   "),  # Edge case: whitespace only
    ]

    for i, chunk in enumerate(test_chunks):
        useful = is_chunk_useful(chunk, config)
        print(
            f"Chunk {i + 1}: '{chunk.text[:30]}...' → {'KEEP' if useful else 'FILTER'}",
        )

        # Basic expectation: non-empty chunks with sufficient tokens should be useful
        if chunk.text.strip():
            tokenizer = get_tokenizer(config)
            token_count = tokenizer.count_tokens(chunk.text)
            expected = token_count >= config.min_tokens
        else:
            expected = False

        assert useful == expected, (
            f"Chunk {i + 1}: Expected useful={expected}, got {useful}"
        )


def test_chunk_merging() -> bool:
    """Test chunk merging functionality."""
    print("\n=== Testing Chunk Merging ===")

    config = Config()

    # Create test chunks with small trailing chunks
    chunks = [
        ChunkData(
            text="This is a substantial first chunk with plenty of content to analyze.",
        ),
        ChunkData(text="This is another substantial chunk that provides good context."),
        ChunkData(text="Short"),  # Should be merged
        ChunkData(text="Also short"),  # Should also be merged
    ]

    print(f"Original chunks: {len(chunks)}")
    for i, chunk in enumerate(chunks):
        print(f"  {i + 1}: '{chunk.text[:30]}...' ({len(chunk.text)} chars)")

    merged_chunks = merge_small_trailing_chunks(chunks, config)

    print(f"\nAfter merging: {len(merged_chunks)}")
    for i, chunk in enumerate(merged_chunks):
        chunk_text = chunk.text if hasattr(chunk, "text") else str(chunk)
        print(f"  {i + 1}: '{chunk_text[:50]}...' ({len(chunk_text)} chars)")

    # Should have fewer or equal chunks after merging
    assert len(merged_chunks) <= len(chunks), (
        f"Expected {len(merged_chunks)} <= {len(chunks)}"
    )


def test_docling_compatibility() -> bool:
    """Test compatibility with Docling patterns."""
    print("\n=== Testing Docling Compatibility ===")

    config = Config()
    tokenizer = get_tokenizer(config)

    # Verify we're using HuggingFaceTokenizer
    from docling_core.transforms.chunker.tokenizer.huggingface import (
        HuggingFaceTokenizer,
    )

    is_correct_type = isinstance(tokenizer, HuggingFaceTokenizer)

    print(f"Tokenizer type: {type(tokenizer)}")
    print(f"Is HuggingFaceTokenizer: {is_correct_type}")

    assert is_correct_type, f"Expected HuggingFaceTokenizer, got {type(tokenizer)}"


# Keep the main function for standalone execution
def main() -> bool:
    """Run all validation tests."""
    print("🧪 Starting Post-Implementation Validation\n")

    tests = [
        ("Token Counting", test_token_counting),
        ("Chunk Filtering", test_chunk_filtering),
        ("Chunk Merging", test_chunk_merging),
        ("Docling Compatibility", test_docling_compatibility),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            test_func()
            print(f"\n✅ PASS: {test_name}")
            results.append(True)
        except Exception as e:  # noqa: BLE001
            print(f"\n❌ ERROR in {test_name}: {e}")
            results.append(False)

    print(f"\n{'=' * 50}")
    passed = sum(results)
    total = len(results)

    print(f"Tests: {passed}/{total} passed")

    if passed == total:
        print("✅ All validation tests passed!")
        return True
    print("❌ Some tests failed. Please review implementation.")
    return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
