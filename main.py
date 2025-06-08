#!/usr/bin/env python3
"""
LLMarkable - Document Conversion Tool.

Transform source files (PDF, HTML, etc.) into remarkable, LLM-friendly Markdown outputs.
"""

import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table

from src.config import Config
from src.pipelines.factory import (
    create_pipeline,
    get_supported_formats,
    is_supported_format,
)
from src.utils import get_tokenizer

app = typer.Typer(
    name="llmarkable",
    help="Transform documents into LLM-friendly Markdown",
    add_completion=False,
)
console = Console()


def version_callback(value: bool) -> None:
    """Print version information."""
    if value:
        console.print("LLMarkable version 0.1.0 (Phase 1 - Core Pipeline)")
        raise typer.Exit


def _validate_file_format(input_file: Path) -> None:
    """Validate that the input file format is supported."""
    from src.exceptions import UnsupportedFormatError

    if not is_supported_format(input_file):
        supported_formats = get_supported_formats()
        error = UnsupportedFormatError(
            input_file.suffix,
            supported_formats=supported_formats,
        )
        console.print(f"❌ {error}")
        raise typer.Exit(1)


def _validate_input_file(input_file: Path, *, verbose: bool = False) -> None:
    """Comprehensive input file validation."""
    from src.exceptions import FileAccessError, ValidationError

    # Check file existence
    if not input_file.exists():
        error = FileAccessError(
            f"File not found: {input_file}",
            file_path=str(input_file),
            operation="read",
        )
        console.print(f"❌ {error}")
        raise typer.Exit(1)

    # Check if it's actually a file (not a directory)
    if not input_file.is_file():
        error = ValidationError(
            f"Path is not a file: {input_file}",
            field_name="input_file",
            field_value=str(input_file),
        )
        console.print(f"❌ {error}")
        raise typer.Exit(1)

    # Check file size (reasonable limits for processing)
    try:
        file_size = input_file.stat().st_size
        max_size = 500 * 1024 * 1024  # 500MB limit

        if file_size == 0:
            error = ValidationError(
                f"File is empty: {input_file}",
                field_name="file_size",
                field_value=file_size,
            )
            console.print(f"❌ {error}")
            console.print("   Empty files cannot be processed")
            raise typer.Exit(1)

        if file_size > max_size:
            size_mb = file_size / (1024 * 1024)
            max_mb = max_size / (1024 * 1024)
            error = ValidationError(
                f"File too large: {size_mb:.1f}MB (max: {max_mb:.0f}MB)",
                field_name="file_size",
                field_value=file_size,
            )
            console.print(f"❌ {error}")
            console.print("   Consider splitting large files or processing in batches")
            raise typer.Exit(1)

        if verbose:
            size_mb = file_size / (1024 * 1024)
            console.print(f"   File size: {size_mb:.1f}MB")

    except OSError as e:
        error = FileAccessError(
            f"Cannot access file: {e}",
            file_path=str(input_file),
            operation="stat",
            original_error=e,
        )
        console.print(f"❌ {error}")
        raise typer.Exit(1)

    # Check file permissions
    try:
        with input_file.open("rb") as f:
            # Try to read first few bytes
            f.read(1024)
    except (OSError, PermissionError) as e:
        error = FileAccessError(
            f"Cannot read file: {e}",
            file_path=str(input_file),
            operation="read",
            original_error=e,
        )
        console.print(f"❌ {error}")
        raise typer.Exit(1)


def _create_config_from_args(
    output_dir: Path | None,
    chunk_size: int | None,
    min_tokens: int | None,
    chunk_overlap: int | None,
    *,
    preserve_tables: bool,
    preserve_images: bool,
    verbose: bool,
    individual_chunks: bool,
) -> Config:
    """Create configuration from CLI arguments."""
    config = Config.default()

    # Override configuration with CLI arguments
    if output_dir:
        config.output_dir = str(output_dir)
    if chunk_size:
        config.chunk_size = chunk_size
    if min_tokens:
        config.min_tokens = min_tokens
    if chunk_overlap is not None:
        config.chunk_overlap = chunk_overlap
    config.preserve_tables = preserve_tables
    config.preserve_images = preserve_images
    config.verbose = verbose
    config.log_level = "DEBUG" if verbose else "INFO"

    # Add individual_chunks to config (we'll add this to Config class)
    config.individual_chunks = individual_chunks

    return config


def _validate_and_create_output_dir(config: Config) -> Path:
    """Validate configuration and create output directory."""
    from src.exceptions import FileAccessError, ValidationError

    try:
        config.validate()
    except ValidationError as e:
        console.print(f"❌ Configuration error: {e}")
        if config.verbose and e.field_name:
            console.print(f"   Invalid field: {e.field_name} = {e.field_value}")
        raise typer.Exit(1) from e

    output_path = Path(config.output_dir)
    try:
        output_path.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        error = FileAccessError(
            f"Cannot create output directory: {e}",
            file_path=str(output_path),
            operation="create",
            original_error=e,
        )
        console.print(f"❌ {error}")
        raise typer.Exit(1) from error

    return output_path


def _process_document(input_file: Path, config: Config, output_path: Path) -> None:
    """Process the document and save output."""
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            # Initialize pipeline
            task = progress.add_task("Initializing pipeline...", total=None)
            pipeline = create_pipeline(input_file, config)

            # Process document
            progress.update(task, description="Processing document...")
            chunks = pipeline.process(input_file)

            progress.update(task, description="Generating output...")

            # Save results using new output generation system
            if config.individual_chunks:
                output_info = _save_individual_chunks(
                    chunks,
                    input_file,
                    output_path,
                    config,
                )
            else:
                output_info = _save_consolidated_output(
                    chunks,
                    input_file,
                    output_path,
                    config,
                )

            progress.update(task, description="Complete!")

        # Show success message
        console.print(f"✅ Successfully converted {input_file.name}")
        console.print(f"   📄 Output: {output_info['location']}")
        console.print(f"   📊 Generated {len(chunks)} chunks")
        if config.individual_chunks:
            console.print(f"   📁 Files created: {output_info['file_count']}")

    except Exception as e:
        from src.exceptions import LLMarkableError

        # Handle our custom exceptions with detailed error information
        if isinstance(e, LLMarkableError):
            console.print(f"❌ Conversion failed: {e}")

            # Show additional context for specific error types
            if hasattr(e, "file_path") and e.file_path and config.verbose:
                console.print(f"   File: {e.file_path}")
            if hasattr(e, "conversion_stage") and e.conversion_stage and config.verbose:
                console.print(f"   Stage: {e.conversion_stage}")
            if hasattr(e, "chunker_type") and e.chunker_type and config.verbose:
                console.print(f"   Chunker: {e.chunker_type}")

        else:
            # Handle unexpected errors
            console.print(f"❌ Unexpected error: {e}")

        if config.verbose:
            console.print_exception()
        raise typer.Exit(1) from e


@app.command()
def convert(
    input_file: Annotated[
        Path,
        typer.Argument(help="Input file to convert (PDF, HTML)"),
    ],
    output_dir: Annotated[
        Path | None,
        typer.Option("--output-dir", "-o", help="Output directory (default: output/)"),
    ] = None,
    chunk_size: Annotated[
        int | None,
        typer.Option(
            "--chunk-size",
            help="Target chunk size in tokens (default: 2048)",
            min=100,
            max=8192,
        ),
    ] = None,
    min_tokens: Annotated[
        int | None,
        typer.Option(
            "--min-tokens",
            help="Minimum tokens per chunk (default: 200)",
            min=50,
            max=1000,
        ),
    ] = None,
    chunk_overlap: Annotated[
        int | None,
        typer.Option(
            "--chunk-overlap",
            help="Overlap between chunks in tokens (default: 100)",
            min=0,
        ),
    ] = None,
    preserve_tables: Annotated[
        bool,
        typer.Option(
            "--preserve-tables/--no-preserve-tables",
            help="Preserve table structure (default: enabled)",
        ),
    ] = True,
    preserve_images: Annotated[
        bool,
        typer.Option(
            "--preserve-images/--no-preserve-images",
            help="Preserve image references (default: disabled)",
        ),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Enable verbose output"),
    ] = False,
    individual_chunks: Annotated[
        bool,
        typer.Option(
            "--individual-chunks/--consolidated",
            help="Save chunks as individual files vs single consolidated file (default: consolidated)",
        ),
    ] = False,
    _version: Annotated[
        bool | None,
        typer.Option(
            "--version",
            callback=version_callback,
            is_eager=True,
            help="Show version and exit",
        ),
    ] = None,
) -> None:
    """
    Convert a document to LLM-friendly Markdown format.

    Examples:
        llmarkable document.pdf
        llmarkable document.html --output-dir results/ --chunk-size 1024
        llmarkable file.pdf --verbose --preserve-images

    """
    # Comprehensive input file validation
    _validate_input_file(input_file, verbose=verbose)

    # Validate file format
    _validate_file_format(input_file)

    # Create configuration from arguments
    config = _create_config_from_args(
        output_dir,
        chunk_size,
        min_tokens,
        chunk_overlap,
        preserve_tables=preserve_tables,
        preserve_images=preserve_images,
        verbose=verbose,
        individual_chunks=individual_chunks,
    )

    # Validate configuration and create output directory
    output_path = _validate_and_create_output_dir(config)

    # Display configuration summary in verbose mode
    if verbose:
        _show_config_summary(input_file, config)

    # Process the document
    _process_document(input_file, config, output_path)


@app.command()
def info() -> None:
    """Show information about supported formats and configuration."""
    console.print("🔧 [bold]LLMarkable - Document Converter[/bold]")
    console.print()

    # Supported formats table
    table = Table(title="Supported Formats")
    table.add_column("Extension", style="cyan")
    table.add_column("Description", style="white")

    format_descriptions = {
        ".pdf": "PDF documents (via Docling)",
        ".html": "HTML files",
        ".htm": "HTML files (alternative extension)",
    }

    for ext in get_supported_formats():
        description = format_descriptions.get(ext, "Document format")
        table.add_row(ext, description)

    console.print(table)
    console.print()

    # Default configuration
    config = Config.default()
    console.print("⚙️  [bold]Default Configuration:[/bold]")
    console.print(f"   Chunk Size: {config.chunk_size} tokens")
    console.print(f"   Min Tokens: {config.min_tokens} tokens")
    console.print(f"   Chunk Overlap: {config.chunk_overlap} tokens")
    console.print(f"   Output Directory: {config.output_dir}")
    console.print(f"   Preserve Tables: {config.preserve_tables}")
    console.print(f"   Preserve Images: {config.preserve_images}")


def _show_config_summary(input_file: Path, config: Config) -> None:
    """Display configuration summary in verbose mode."""
    console.print("⚙️  [bold]Configuration Summary:[/bold]")
    console.print(f"   Input: {input_file}")
    console.print(f"   Output Directory: {config.output_dir}")
    console.print(f"   Chunk Size: {config.chunk_size} tokens")
    console.print(f"   Min Tokens: {config.min_tokens} tokens")
    console.print(f"   Chunk Overlap: {config.chunk_overlap} tokens")
    console.print(f"   Preserve Tables: {config.preserve_tables}")
    console.print(f"   Preserve Images: {config.preserve_images}")
    console.print()


def _sanitize_filename(filename: str, max_length: int = 200) -> str:
    """
    Sanitize filename for cross-platform compatibility.

    Args:
        filename: Original filename
        max_length: Maximum filename length

    Returns:
        Sanitized filename safe for all platforms

    """
    # Remove or replace invalid characters for Windows/Linux/macOS
    invalid_chars = r'[<>:"/\\|?*\x00-\x1f]'
    sanitized = re.sub(invalid_chars, "_", filename)

    # Remove leading/trailing dots and spaces
    sanitized = sanitized.strip(". ")

    # Handle reserved Windows names
    reserved_names = {
        "CON",
        "PRN",
        "AUX",
        "NUL",
        "COM1",
        "COM2",
        "COM3",
        "COM4",
        "COM5",
        "COM6",
        "COM7",
        "COM8",
        "COM9",
        "LPT1",
        "LPT2",
        "LPT3",
        "LPT4",
        "LPT5",
        "LPT6",
        "LPT7",
        "LPT8",
        "LPT9",
    }
    if sanitized.upper() in reserved_names:
        sanitized = f"_{sanitized}"

    # Truncate if too long, preserving extension
    if len(sanitized) > max_length:
        if "." in sanitized:
            name, ext = sanitized.rsplit(".", 1)
            max_name_length = max_length - len(ext) - 1
            sanitized = f"{name[:max_name_length]}.{ext}"
        else:
            sanitized = sanitized[:max_length]

    # Ensure we have a valid filename
    return sanitized if sanitized else "document"


def _create_chunk_metadata(
    chunk: dict[str, object] | object,
    chunk_index: int,
    input_file: Path,
    config: Config,
) -> dict[str, Any]:
    """
    Create comprehensive metadata for a chunk.

    Args:
        chunk: Chunk dictionary or object with content and metadata
        chunk_index: Index of the chunk in the document
        input_file: Original input file path
        config: Configuration object

    Returns:
        Dictionary with comprehensive metadata

    """
    # Get tokenizer for token counting
    tokenizer = get_tokenizer(config)

    # Extract content and existing metadata based on chunk type
    if hasattr(chunk, "get"):  # Dictionary-like object
        content = chunk.get("content", "")
        existing_metadata = chunk.get("metadata", {})
    elif hasattr(chunk, "text"):  # ChunkData object
        content = chunk.text
        existing_metadata = {
            "chunk_id": getattr(chunk, "chunk_id", None),
            "source": getattr(chunk, "source", None),
        }
    elif hasattr(chunk, "content"):  # Other object with content attribute
        content = chunk.content
        existing_metadata = {}
    else:  # Fallback to string representation
        content = str(chunk)
        existing_metadata = {}

    # Count tokens in content
    token_count = tokenizer.count_tokens(content)

    # Create comprehensive metadata
    metadata = {
        "source_file": str(input_file),
        "chunk_index": chunk_index,
        "token_count": token_count,
        "processing_timestamp": datetime.now(tz=UTC).isoformat(),
        "chunk_type": existing_metadata.get("chunk_type", "text"),
        "format": existing_metadata.get("format", input_file.suffix.lstrip(".")),
        "llmarkable_version": "0.1.0",
    }

    # Add any additional metadata from the chunk
    for key, value in existing_metadata.items():
        if key not in metadata and value is not None:
            metadata[key] = value

    return metadata


def _format_metadata_header(metadata: dict[str, Any]) -> str:
    """
    Format metadata as YAML-style header for markdown files.

    Args:
        metadata: Metadata dictionary

    Returns:
        Formatted metadata header string

    """
    header_lines = ["---"]

    # Order important metadata first
    ordered_keys = [
        "source_file",
        "chunk_index",
        "token_count",
        "processing_timestamp",
        "chunk_type",
        "format",
    ]

    # Add ordered metadata
    for key in ordered_keys:
        if key in metadata:
            value = metadata[key]
            header_lines.append(f"{key}: {value}")

    # Add remaining metadata
    for key, value in metadata.items():
        if key not in ordered_keys and value is not None:
            header_lines.append(f"{key}: {value}")

    header_lines.append("---")
    return "\n".join(header_lines)


def _save_individual_chunks(
    chunks: list[dict[str, Any] | Any],
    input_file: Path,
    output_path: Path,
    config: Config,
) -> dict[str, Any]:
    """
    Save chunks as individual markdown files with metadata headers.

    Args:
        chunks: List of chunk dictionaries
        input_file: Original input file
        output_path: Base output directory
        config: Configuration object

    Returns:
        Dictionary with output information

    """
    # Create subdirectory for this document
    doc_name = _sanitize_filename(input_file.stem)
    doc_output_dir = output_path / doc_name
    doc_output_dir.mkdir(parents=True, exist_ok=True)

    files_created = 0

    for i, chunk in enumerate(chunks):
        # Create chunk filename
        chunk_filename = f"chunk_{i + 1:03d}.md"
        chunk_file_path = doc_output_dir / chunk_filename

        # Create metadata
        metadata = _create_chunk_metadata(chunk, i, input_file, config)

        # Write chunk file
        try:
            with chunk_file_path.open("w", encoding="utf-8") as f:
                # Write metadata header if enabled
                if config.include_metadata:
                    f.write(_format_metadata_header(metadata))
                    f.write("\n\n")

                # Write content - extract based on chunk type
                if hasattr(chunk, "get"):  # Dictionary-like object
                    content = chunk.get("content", "")
                elif hasattr(chunk, "text"):  # ChunkData object
                    content = chunk.text
                elif hasattr(chunk, "content"):  # Other object with content attribute
                    content = chunk.content
                else:  # Fallback to string representation
                    content = str(chunk)

                f.write(content)
                f.write("\n")

            files_created += 1

        except OSError as e:
            console.print(f"⚠️  Warning: Failed to write {chunk_filename}: {e}")
            continue

    return {
        "location": str(doc_output_dir),
        "file_count": files_created,
        "type": "individual_chunks",
    }


def _save_consolidated_output(
    chunks: list[dict[str, Any] | Any],
    input_file: Path,
    output_path: Path,
    config: Config,
) -> dict[str, Any]:
    """
    Save chunks as a single consolidated markdown file.

    Args:
        chunks: List of chunk dictionaries
        input_file: Original input file
        output_path: Base output directory
        config: Configuration object

    Returns:
        Dictionary with output information

    """
    # Generate output filename
    base_name = _sanitize_filename(input_file.stem)
    output_file = output_path / f"{base_name}_converted.md"

    try:
        with output_file.open("w", encoding="utf-8") as f:
            # Write document header
            f.write(f"# {input_file.name} - Conversion Results\n\n")
            f.write("*Generated by LLMarkable*\n\n")

            # Write document metadata if enabled
            if config.include_metadata:
                doc_metadata = {
                    "source_file": str(input_file),
                    "total_chunks": len(chunks),
                    "processing_timestamp": datetime.now(UTC).isoformat(),
                    "llmarkable_version": "0.1.0",
                    "format": input_file.suffix.lstrip("."),
                }
                f.write(_format_metadata_header(doc_metadata))
                f.write("\n\n")

            f.write(f"**Total chunks:** {len(chunks)}\n\n")
            f.write("---\n\n")

            # Write each chunk
            for i, chunk in enumerate(chunks):
                f.write(f"## Chunk {i + 1}\n\n")

                # Write chunk metadata if enabled
                if config.include_metadata:
                    metadata = _create_chunk_metadata(chunk, i, input_file, config)
                    f.write("**Chunk Metadata:**\n")
                    for key, value in metadata.items():
                        if key not in [
                            "source_file",
                            "llmarkable_version",
                        ]:  # Skip redundant info
                            f.write(f"- **{key}:** {value}\n")
                    f.write("\n")

                # Write content - extract based on chunk type
                if hasattr(chunk, "get"):  # Dictionary-like object
                    content = chunk.get("content", "")
                elif hasattr(chunk, "text"):  # ChunkData object
                    content = chunk.text
                elif hasattr(chunk, "content"):  # Other object with content attribute
                    content = chunk.content
                else:  # Fallback to string representation
                    content = str(chunk)

                f.write(content)
                f.write("\n\n")
                f.write("---\n\n")

        return {
            "location": str(output_file),
            "file_count": 1,
            "type": "consolidated",
        }

    except OSError as e:
        console.print(f"❌ Failed to write output file: {e}")
        raise typer.Exit(1) from e


if __name__ == "__main__":
    app()
