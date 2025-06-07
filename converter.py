import warnings
from pathlib import Path
import sys

from docling.chunking import HierarchicalChunker, HybridChunker
from docling.document_converter import DocumentConverter
from docling_core.transforms.chunker.tokenizer.huggingface import HuggingFaceTokenizer
from rich.console import Console
from transformers import AutoTokenizer

from utils import is_chunk_useful, merge_small_trailing_chunks

# Suppress transformers warnings
warnings.filterwarnings("ignore", message="Token indices sequence length is longer than the specified maximum")

# --- Configuration ---
INPUT_DIR = Path("input")
OUTPUT_DIR = Path("output")
TARGET_CHUNK_SIZE = 2048
MAX_TOKENS = 2048
MIN_TOKENS = 200
MIN_CHARS = 800
MERGE_SMALL_TRAILING_CHUNKS = True
SUPPORTED_EXTENSIONS = ["*.pdf", "*.html", "*.htm"]
# ---

def setup_directories(console: Console) -> bool:
    """Create the input/output directories if they don't exist."""
    if not INPUT_DIR.exists():
        console.print(f"[bold red]Error: Input directory '{INPUT_DIR}' not found.[/bold red]")
        console.print("[bold yellow]Please create it and place your files inside.[/bold yellow]")
        return False
    OUTPUT_DIR.mkdir(exist_ok=True)
    return True

def get_converter() -> DocumentConverter:
    """Initializes and returns a generic DocumentConverter."""
    # A generic converter can handle multiple file types by auto-detecting them.
    # PDF-specific options are removed to allow for general compatibility.
    return DocumentConverter()

def get_primary_chunker() -> HybridChunker:
    """Creates the primary chunker for breaking documents into larger LLM-friendly pieces."""
    EMBED_MODEL_ID = "BAAI/bge-small-en-v1.5"
    tokenizer = HuggingFaceTokenizer(
        tokenizer=AutoTokenizer.from_pretrained(EMBED_MODEL_ID),
        max_tokens=MAX_TOKENS,
    )
    return HybridChunker(tokenizer=tokenizer, merge_peers=True)

def get_fallback_chunker() -> HierarchicalChunker:
    """Creates a fallback chunker that respects document structure."""
    return HierarchicalChunker(merge_list_items=True)

def process_file(file_path: Path, converter: DocumentConverter, primary_chunker: HybridChunker,
                 fallback_chunker: HierarchicalChunker, console: Console) -> None:
    """Converts a single file, chunks it, and saves the markdown files."""
    console.print(f"Processing '[cyan]{file_path.name}[/cyan]'...")

    try:
        # 1. Convert file to DoclingDocument
        result = converter.convert(str(file_path))
        document = result.document

        # 2. Try primary chunking
        chunks = None
        chunking_method = "primary"
        try:
            chunks = list(primary_chunker.chunk(document))
            console.print(f"  -> Using HybridChunker: {len(chunks)} chunks created")
        except Exception as chunk_error:
            console.print(f"  -> [yellow]HybridChunker failed ({chunk_error}), trying fallback.[/yellow]")
            try:
                chunks = list(fallback_chunker.chunk(document))
                chunking_method = "hierarchical"
                console.print(f"  -> Using HierarchicalChunker: {len(chunks)} chunks created")
            except Exception as fallback_error:
                console.print(f"  -> [yellow]Fallback chunker failed ({fallback_error}), saving as single file.[/yellow]")
                chunking_method = "full_document"
                markdown_content = document.export_to_markdown()
                chunks = [type("MockChunk", (), {"text": markdown_content})()]

        # 3. Filter and merge chunks
        if chunks and chunking_method in ["primary", "hierarchical"]:
            original_count = len(chunks)
            chunks = merge_small_trailing_chunks(chunks, primary_chunker.tokenizer, console, MIN_TOKENS, MERGE_SMALL_TRAILING_CHUNKS)
            
            useful_chunks = []
            for chunk in chunks:
                if hasattr(chunk, "text") and "MergedChunk" in str(chunk.__class__):
                    chunk_text = chunk.text
                elif chunking_method == "primary":
                    chunk_text = primary_chunker.contextualize(chunk)
                else:
                    chunk_text = fallback_chunker.contextualize(chunk)

                if is_chunk_useful(chunk_text, primary_chunker.tokenizer, MIN_CHARS, MIN_TOKENS):
                    useful_chunks.append(chunk_text)
            
            chunks = useful_chunks
            filtered_count = original_count - len(chunks)
            if filtered_count > 0:
                console.print(f"  -> [yellow]Filtered out {filtered_count} small/unuseful chunks[/yellow]")

        # 4. Save chunks to file
        output_stem = file_path.stem
        file_output_dir = OUTPUT_DIR / output_stem
        file_output_dir.mkdir(exist_ok=True)

        if not chunks:
            console.print("  -> [yellow]No useful chunks created, saving as single file[/yellow]")
            markdown_content = document.export_to_markdown()
            output_filename = file_output_dir / "document.md"
            with output_filename.open("w", encoding="utf-8") as f:
                f.write(markdown_content)
            console.print("  -> [green]Success:[/green] Created 1 markdown file.")
        else:
            for i, chunk_content in enumerate(chunks):
                output_filename = file_output_dir / f"chunk_{i+1:03d}.md"
                token_count = primary_chunker.tokenizer.count_tokens(chunk_content)
                metadata_header = f"""<!-- Chunk Metadata
Method: {chunking_method}
Chunk: {i+1}/{len(chunks)}
Characters: {len(chunk_content)}
Tokens: {token_count}
Source: {file_path.name}
-->

"""
                with output_filename.open("w", encoding="utf-8") as f:
                    f.write(metadata_header + chunk_content)
            console.print(f"  -> [green]Success:[/green] Created {len(chunks)} markdown chunks in '{output_stem}/'.")

    except Exception as e:
        console.print(f"  -> [bold red]Error processing {file_path.name}: {e}[/bold red]")

def main() -> None:
    """Main function to run the conversion process."""
    console = Console()
    console.print("[bold green]Starting Document Conversion Process[/bold green]")
    console.print(f"[blue]Configuration: Target chunk size ≈ {TARGET_CHUNK_SIZE} tokens, Min tokens = {MIN_TOKENS}[/blue]")

    if not setup_directories(console):
        return

    converter = get_converter()
    primary_chunker = get_primary_chunker()
    fallback_chunker = get_fallback_chunker()

    if len(sys.argv) > 1:
        file_name = sys.argv[1]
        file_path = INPUT_DIR / file_name
        if not file_path.exists():
            console.print(f"[red]Error: File '{file_name}' not found in '{INPUT_DIR}'.[/red]")
            return
        console.print(f"Processing single file: {file_name}")
        process_file(file_path, converter, primary_chunker, fallback_chunker, console)
    else:
        files_to_process = []
        for ext in SUPPORTED_EXTENSIONS:
            files_to_process.extend(INPUT_DIR.glob(ext))
        
        if not files_to_process:
            console.print(f"[yellow]No supported files ({', '.join(SUPPORTED_EXTENSIONS)}) found in '{INPUT_DIR}'.[/yellow]")
            return

        console.print(f"Found {len(files_to_process)} file(s) to process.")
        for file_path in files_to_process:
            process_file(file_path, converter, primary_chunker, fallback_chunker, console)

    console.print("\n[bold green]Conversion process finished.[/bold green]")

if __name__ == "__main__":
    main()
