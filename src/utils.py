"""
Chunk consolidation utilities for document processing pipeline.

This module provides utilities for consolidating and filtering document chunks
based on token counts and content quality. Functions use Docling's recommended
HuggingFaceTokenizer for precise token counting.
"""

from typing import Any, List, Optional, Union
from dataclasses import dataclass

from docling_core.transforms.chunker.tokenizer.huggingface import HuggingFaceTokenizer
from transformers import AutoTokenizer

from .config import Config


@dataclass
class ChunkData:
    """Represents a document chunk with metadata."""
    text: str
    chunk_id: Optional[int] = None
    source: Optional[str] = None
    

class TokenizerCache:
    """Simple cache for tokenizer instances to improve performance."""
    
    def __init__(self):
        self._cache = {}
    
    def get_tokenizer(self, model_name: str) -> HuggingFaceTokenizer:
        """Get cached tokenizer instance or create new one."""
        if model_name not in self._cache:
            tokenizer = AutoTokenizer.from_pretrained(model_name)
            self._cache[model_name] = HuggingFaceTokenizer(tokenizer=tokenizer)
        return self._cache[model_name]


# Global tokenizer cache instance
_tokenizer_cache = TokenizerCache()


def get_tokenizer(config: Config) -> HuggingFaceTokenizer:
    """
    Get tokenizer instance for token counting.
    
    Args:
        config: Configuration containing tokenizer model name
        
    Returns:
        HuggingFaceTokenizer instance for token counting
    """
    # Use a default model that's commonly available for tokenization
    model_name = getattr(config, 'tokenizer_model', 'BAAI/bge-small-en-v1.5')
    return _tokenizer_cache.get_tokenizer(model_name)


def extract_text_content(chunk: Any) -> str:
    """
    Extract text content from various chunk formats.
    
    Args:
        chunk: Chunk object that may have text, content, or page_content attributes
        
    Returns:
        String content of the chunk
    """
    if hasattr(chunk, 'page_content'):
        return chunk.page_content
    elif hasattr(chunk, 'text'):
        return chunk.text
    elif hasattr(chunk, 'content'):
        return chunk.content
    else:
        return str(chunk)


def is_chunk_useful(
    chunk: Union[str, Any], 
    config: Config,
    tokenizer: Optional[HuggingFaceTokenizer] = None
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
    if isinstance(chunk, str):
        chunk_text = chunk
    else:
        chunk_text = extract_text_content(chunk)
    
    # Primary filter: token count
    token_count = tokenizer.count_tokens(chunk_text)
    if token_count < config.min_tokens:
        return False
    
    # Secondary filter: content quality
    lines = [line.strip() for line in chunk_text.strip().split("\n") if line.strip()]
    
    # If it's a single line that looks like a URL or reference, skip it
    if len(lines) == 1:
        line = lines[0]
        if (line.startswith(("http://", "https://", "www.")) or
            line.endswith((".com", ".org", ".net", ".pdf")) or
            len(line.split()) < 5):  # Less than 5 words
            return False
    
    return True


def merge_chunks(chunk_list: List[Any]) -> ChunkData:
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
        source="merged"
    )


def merge_small_trailing_chunks(
    chunks: List[Any], 
    config: Config,
    tokenizer: Optional[HuggingFaceTokenizer] = None,
    verbose: bool = False
) -> List[Any]:
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
    if not chunks or not getattr(config, 'merge_small_trailing_chunks', True):
        return chunks
    
    # Get tokenizer if not provided
    if tokenizer is None:
        tokenizer = get_tokenizer(config)
    
    merged_chunks = []
    trailing_small_chunks = []
    
    # Identify trailing small chunks
    for i, chunk in enumerate(chunks):
        chunk_text = extract_text_content(chunk)
        token_count = tokenizer.count_tokens(chunk_text)
        
        # Check if this chunk is small and at the end
        remaining_chunks = chunks[i+1:]
        remaining_small = all(
            tokenizer.count_tokens(extract_text_content(c)) < config.min_tokens
            for c in remaining_chunks
        )
        
        # If this is a small chunk and all remaining chunks are small, start collecting for merge
        if token_count < config.min_tokens and (remaining_small or not remaining_chunks):
            trailing_small_chunks.append(chunk)
        elif trailing_small_chunks:
            # If we were collecting small chunks but hit a large one, merge the collected ones
            if len(trailing_small_chunks) > 1:
                merged_chunk = merge_chunks(trailing_small_chunks)
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
            merged_chunk = merge_chunks(trailing_small_chunks)
            merged_chunks.append(merged_chunk)
        else:
            merged_chunks.extend(trailing_small_chunks)
    
    # Print merge information if verbose
    if verbose and len(merged_chunks) < len(chunks):
        merge_count = len(chunks) - len(merged_chunks)
        print(f"Merged {merge_count} small trailing chunks")
    
    return merged_chunks


def filter_useful_chunks(
    chunks: List[Any], 
    config: Config,
    tokenizer: Optional[HuggingFaceTokenizer] = None,
    verbose: bool = False
) -> List[Any]:
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
        print(f"Filtered out {filtered_count} small/unuseful chunks")
    
    return useful_chunks 