#!/usr/bin/env python3
"""
LLMarkable - Document Conversion Tool.

Transform source files (PDF, HTML, etc.) into remarkable, LLM-friendly Markdown outputs.
"""

from pathlib import Path
from typing import Annotated

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
    if not is_supported_format(input_file):
        supported = ", ".join(get_supported_formats())
        console.print(f"❌ Unsupported file format: {input_file.suffix}")
        console.print(f"   Supported formats: {supported}")
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

    return config


def _validate_and_create_output_dir(config: Config) -> Path:
    """Validate configuration and create output directory."""
    try:
        config.validate()
    except ValueError as e:
        console.print(f"❌ Configuration error: {e}")
        raise typer.Exit(1) from e

    output_path = Path(config.output_dir)
    try:
        output_path.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        console.print(f"❌ Cannot create output directory: {e}")
        raise typer.Exit(1) from e

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
            output_file = _generate_output_filename(input_file, output_path)

            # Save results
            _save_markdown_output(chunks, output_file)

            progress.update(task, description="Complete!")

        # Show success message
        console.print(f"✅ Successfully converted {input_file.name}")
        console.print(f"   📄 Output: {output_file}")
        console.print(f"   📊 Generated {len(chunks)} chunks")

    except (FileNotFoundError, ValueError, OSError) as e:
        console.print(f"❌ Conversion failed: {e}")
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
    # Check if input file exists
    if not input_file.exists():
        console.print(f"❌ File not found: {input_file}")
        raise typer.Exit(1)

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


def _generate_output_filename(input_file: Path, output_dir: Path) -> Path:
    """Generate output filename based on input file."""
    base_name = input_file.stem
    return output_dir / f"{base_name}_converted.md"


def _save_markdown_output(chunks: list, output_file: Path) -> None:
    """Save processed chunks to markdown file."""
    with Path.open(output_file, "w", encoding="utf-8") as f:
        f.write("# Document Conversion Results\n\n")
        f.write("*Generated by LLMarkable*\n\n")
        f.write(f"Total chunks: {len(chunks)}\n\n")
        f.write("---\n\n")

        for i, chunk in enumerate(chunks, 1):
            f.write(f"## Chunk {i}\n\n")

            # Extract content based on chunk type
            if hasattr(chunk, "get"):  # Dictionary-like object
                content = chunk.get("content", "")
                metadata = chunk.get("metadata", {})
            elif hasattr(chunk, "text"):  # ChunkData object
                content = chunk.text
                metadata = {
                    "chunk_id": getattr(chunk, "chunk_id", None),
                    "source": getattr(chunk, "source", None),
                }
            elif hasattr(chunk, "content"):  # Other object with content attribute
                content = chunk.content
                metadata = {}
            else:  # Fallback to string representation
                content = str(chunk)
                metadata = {}

            f.write(content)
            f.write("\n\n")

            # Write chunk metadata if available
            if metadata and any(v is not None for v in metadata.values()):
                f.write("**Metadata:**\n")
                for key, value in metadata.items():
                    if value is not None:
                        f.write(f"- {key}: {value}\n")
                f.write("\n")

            f.write("---\n\n")


if __name__ == "__main__":
    app()
