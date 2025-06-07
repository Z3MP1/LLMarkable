from rich.console import Console
from docling_core.transforms.chunker.tokenizer.huggingface import HuggingFaceTokenizer

def merge_small_trailing_chunks(chunks: list, tokenizer: HuggingFaceTokenizer, console: Console, min_tokens: int, merge_flag: bool) -> list:
    """Merge small chunks at the end of documents, especially source lists and references."""
    if not chunks or not merge_flag:
        return chunks

    merged_chunks = []
    trailing_small_chunks = []

    # Identify trailing small chunks
    for i, chunk in enumerate(chunks):
        # Extract text content
        if hasattr(chunk, "text"):
            chunk_text = chunk.text
        elif hasattr(chunk, "content"):
            chunk_text = chunk.content
        else:
            chunk_text = str(chunk)

        token_count = tokenizer.count_tokens(chunk_text)

        # Check if this chunk is small and at the end
        remaining_chunks = chunks[i+1:]
        remaining_small = all(
            tokenizer.count_tokens(
                getattr(c, "text", getattr(c, "content", str(c)))
            ) < min_tokens
            for c in remaining_chunks
        )

        # If this is a small chunk and all remaining chunks are small, start collecting for merge
        if token_count < min_tokens and (remaining_small or not remaining_chunks):
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

    if len(merged_chunks) < len(chunks):
        console.print(f"  -> [blue]Merged {len(chunks) - len(merged_chunks)} small trailing chunks[/blue]")

    return merged_chunks

def merge_chunks(chunk_list: list) -> type | None:
    """Merge multiple chunks into one."""
    if not chunk_list:
        return None

    # Combine all text content
    combined_text = []
    for chunk in chunk_list:
        if hasattr(chunk, "text"):
            chunk_text = chunk.text
        elif hasattr(chunk, "content"):
            chunk_text = chunk.content
        else:
            chunk_text = str(chunk)
        combined_text.append(chunk_text)

    # Create a new mock chunk with combined text
    merged_content = "\n\n".join(combined_text)
    return type("MergedChunk", (), {"text": merged_content})()

def is_chunk_useful(chunk_text: str, tokenizer: HuggingFaceTokenizer, min_tokens: int) -> bool:
    """Determine if a chunk is useful for LLM retrieval based on token count and content quality."""
    # Count tokens using the same tokenizer - primary filter
    token_count = tokenizer.count_tokens(chunk_text)
    if token_count < min_tokens:
        return False

    # Filter out chunks that are just URLs or references
    lines = [line.strip() for line in chunk_text.strip().split("\n") if line.strip()]

    # If it's a single line that looks like a URL or reference, skip it
    if len(lines) == 1:
        line = lines[0]
        if (line.startswith(("http://", "https://", "www.")) or
            line.endswith((".com", ".org", ".net", ".pdf")) or
            len(line.split()) < 5):  # Less than 5 words
            return False

    return True 