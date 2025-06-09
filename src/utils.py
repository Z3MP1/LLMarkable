"""
Chunk consolidation utilities for document processing pipeline.

This module provides utilities for consolidating and filtering document chunks
based on token counts and content quality. Functions use Docling's recommended
HuggingFaceTokenizer for precise token counting.
"""

from dataclasses import dataclass
from typing import Any

from docling_core.transforms.chunker.tokenizer.huggingface import HuggingFaceTokenizer
from transformers import AutoTokenizer

from .config import Config


@dataclass
class ChunkData:
    """Represents a document chunk with metadata."""

    text: str
    chunk_id: int | None = None
    source: str | None = None


class TokenizerCache:
    """Simple cache for tokenizer instances to improve performance."""

    def __init__(self) -> None:
        """Initialize empty tokenizer cache."""
        self._cache: dict[str, HuggingFaceTokenizer] = {}

    def get_tokenizer(self, model_name: str, max_tokens: int | None = None) -> HuggingFaceTokenizer:
        """
        Get cached tokenizer instance or create new one.

        Args:
            model_name: Name of the tokenizer model
            max_tokens: Maximum tokens to configure for the tokenizer

        Returns:
            Configured HuggingFaceTokenizer instance

        """
        cache_key = f"{model_name}:{max_tokens}"

        if cache_key not in self._cache:
            try:
                auto_tokenizer = AutoTokenizer.from_pretrained(model_name)

                # Configure HuggingFaceTokenizer with max_tokens if provided
                if max_tokens is not None:
                    hf_tokenizer = HuggingFaceTokenizer(
                        tokenizer=auto_tokenizer,
                        max_tokens=max_tokens,
                    )
                else:
                    # Use default behavior (derives max_tokens from tokenizer)
                    hf_tokenizer = HuggingFaceTokenizer(tokenizer=auto_tokenizer)

                self._cache[cache_key] = hf_tokenizer

            except Exception as e:
                from .exceptions import TokenizerError

                msg = f"Failed to load tokenizer '{model_name}': {e!s}"
                raise TokenizerError(
                    msg,
                    model_name=model_name,
                    original_error=e,
                ) from e

        return self._cache[cache_key]


# Global tokenizer cache instance
_tokenizer_cache = TokenizerCache()


def get_tokenizer(config: Config) -> HuggingFaceTokenizer:
    """
    Get tokenizer instance for token counting with proper max_tokens configuration.

    Args:
        config: Configuration containing tokenizer model name and chunk_size

    Returns:
        HuggingFaceTokenizer instance for token counting with optimal configuration

    """
    # Use tokenizer model specified in configuration
    model_name = config.tokenizer_model

    # Configure max_tokens to match chunk_size for optimal chunking behavior
    max_tokens = config.chunk_size

    return _tokenizer_cache.get_tokenizer(model_name, max_tokens=max_tokens)


def extract_text_content(chunk: object) -> str:
    """
    Extract text content from various chunk formats.

    Args:
        chunk: Chunk object that may have text, content, or page_content attributes

    Returns:
        String content of the chunk

    """
    # Check for dictionary-like objects first
    if hasattr(chunk, "get") and callable(chunk.get):
        content = chunk.get("content", "")
        return str(content)
    # Then check for object attributes
    if hasattr(chunk, "page_content"):
        return str(chunk.page_content)
    if hasattr(chunk, "text"):
        return str(chunk.text)
    if hasattr(chunk, "content"):
        return str(chunk.content)
    return str(chunk)


def is_chunk_useful(
    chunk: str | object,
    config: Config,
    tokenizer: HuggingFaceTokenizer | None = None,
) -> bool:
    """
    Determine if a chunk is useful for LLM retrieval based on token count and content quality.

    Args:
        chunk: Text chunk or chunk object to evaluate
        config: Configuration containing min_tokens threshold
        tokenizer: Optional tokenizer instance (will create if not provided)

    Returns:
        True if chunk meets usefulness criteria, False otherwise

    """
    # Get tokenizer if not provided
    if tokenizer is None:
        tokenizer = get_tokenizer(config)

    # Extract text content
    chunk_text = chunk if isinstance(chunk, str) else extract_text_content(chunk)

    # Primary filter: token count
    token_count = tokenizer.count_tokens(chunk_text)
    if token_count < config.min_tokens:
        return False

    # Secondary filter: content quality
    lines = [line.strip() for line in chunk_text.strip().split("\n") if line.strip()]

    # If it's a single line that looks like a URL or reference, skip it
    if len(lines) == 1:
        line = lines[0]
        if (
            line.startswith(("http://", "https://", "www."))
            or line.endswith((".com", ".org", ".net", ".pdf"))
            or len(line.split()) < 5  # noqa: PLR2004
        ):  # Less than 5 words
            return False

    return True


def merge_chunks(chunk_list: list[dict[str, Any]]) -> ChunkData:
    """
    Merge multiple chunks into one consolidated chunk.

    Args:
        chunk_list: List of chunks to merge

    Returns:
        ChunkData object with combined text content

    """
    if not chunk_list:
        return ChunkData(text="")

    # Combine all text content
    combined_text = []
    for chunk in chunk_list:
        chunk_text = extract_text_content(chunk)
        combined_text.append(chunk_text)

    # Create consolidated chunk
    merged_content = "\n\n".join(combined_text)
    return ChunkData(
        text=merged_content,
        source="merged",
    )


def merge_small_trailing_chunks(
    chunks: list[dict[str, Any]],
    config: Config,
    tokenizer: HuggingFaceTokenizer | None = None,
    verbose: bool = False,
) -> list[dict[str, Any]]:
    """
    Merge small chunks at the end of documents, especially source lists and references.

    This function identifies trailing small chunks and consolidates them to avoid
    information loss while maintaining meaningful chunk sizes for retrieval.

    Args:
        chunks: List of document chunks to process
        config: Configuration containing min_tokens and merge settings
        tokenizer: Optional tokenizer instance (will create if not provided)
        verbose: Whether to print merge information

    Returns:
        List of chunks with small trailing chunks merged

    """
    if not chunks or not getattr(config, "merge_small_trailing_chunks", True):
        return chunks

    # Get tokenizer if not provided
    if tokenizer is None:
        tokenizer = get_tokenizer(config)

    merged_chunks: list[dict[str, Any]] = []
    trailing_small_chunks: list[dict[str, Any]] = []

    # Identify trailing small chunks
    for i, chunk in enumerate(chunks):
        chunk_text = extract_text_content(chunk)
        token_count = tokenizer.count_tokens(chunk_text)

        # Check if this chunk is small and at the end
        remaining_chunks = chunks[i + 1 :]
        remaining_small = all(
            tokenizer.count_tokens(extract_text_content(c)) < config.min_tokens for c in remaining_chunks
        )

        # If this is a small chunk and all remaining chunks are small, start collecting for merge
        if token_count < config.min_tokens and (remaining_small or not remaining_chunks):
            trailing_small_chunks.append(chunk)
        elif trailing_small_chunks:
            # If we were collecting small chunks but hit a large one, merge the collected ones
            if len(trailing_small_chunks) > 1:
                merged_chunk_data = merge_chunks(trailing_small_chunks)
                # Convert ChunkData back to dict format
                merged_chunk = {
                    "content": merged_chunk_data.text,
                    "metadata": {"source": "merged", "chunk_count": len(trailing_small_chunks)},
                }
                merged_chunks.append(merged_chunk)
            else:
                merged_chunks.extend(trailing_small_chunks)
            trailing_small_chunks = []
            merged_chunks.append(chunk)
        else:
            merged_chunks.append(chunk)

    # Handle any remaining small chunks at the very end
    if trailing_small_chunks:
        if len(trailing_small_chunks) > 1:
            merged_chunk_data = merge_chunks(trailing_small_chunks)
            # Convert ChunkData back to dict format
            merged_chunk = {
                "content": merged_chunk_data.text,
                "metadata": {"source": "merged", "chunk_count": len(trailing_small_chunks)},
            }
            merged_chunks.append(merged_chunk)
        else:
            merged_chunks.extend(trailing_small_chunks)

    # Print merge information if verbose
    if verbose and len(merged_chunks) < len(chunks):
        from rich.console import Console

        console = Console()
        merge_count = len(chunks) - len(merged_chunks)
        console.print(f"Merged {merge_count} small trailing chunks")

    return merged_chunks


def filter_useful_chunks(
    chunks: list[dict[str, Any]],
    config: Config,
    tokenizer: HuggingFaceTokenizer | None = None,
    verbose: bool = False,
) -> list[dict[str, Any]]:
    """
    Filter chunks to keep only useful ones based on content quality and token count.

    Args:
        chunks: List of chunks to filter
        config: Configuration containing filtering parameters
        tokenizer: Optional tokenizer instance (will create if not provided)
        verbose: Whether to print filtering information

    Returns:
        List of filtered chunks that meet usefulness criteria

    """
    if not chunks:
        return chunks

    # Get tokenizer if not provided
    if tokenizer is None:
        tokenizer = get_tokenizer(config)

    useful_chunks = []
    filtered_count = 0

    for chunk in chunks:
        if is_chunk_useful(chunk, config, tokenizer):
            useful_chunks.append(chunk)
        else:
            filtered_count += 1

    # Print filtering information if verbose
    if verbose and filtered_count > 0:
        from rich.console import Console

        console = Console()
        console.print(f"Filtered out {filtered_count} small/unuseful chunks")

    return useful_chunks
