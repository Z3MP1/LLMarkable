"""
PDF-specific document processing pipeline using Docling.

Implements optimized PDF to markdown conversion with table structure preservation
and token-aware chunking strategies.
"""

from pathlib import Path
from typing import Any

from docling.chunking import HierarchicalChunker, HybridChunker
from docling.datamodel.base_models import InputFormat
from docling.document_converter import DocumentConverter, PdfFormatOption
from rich.console import Console

from src.config import Config
from src.utils import get_tokenizer, is_chunk_useful, merge_small_trailing_chunks

from .base import BasePipeline


class PDFPipeline(BasePipeline):
    """PDF document processing pipeline with Docling integration."""

    def __init__(self, config: Config) -> None:
        """Initialize PDF pipeline with Docling configuration."""
        super().__init__(config)
        self.console = Console()

        # Get tokenizer using the new utils function
        self.tokenizer = get_tokenizer(config)

        # Configure PDF processing options
        self.pdf_options = PdfFormatOption(
            # Enable table structure preservation as per research
            do_table_structure=config.preserve_tables,
            # Configure for quality markdown output
            do_ocr=True,  # Enable OCR for scanned PDFs
            ocr_config={"lang": ["en"]},  # Primary language
            # Layout analysis for better structure detection
            do_cell_matching=True,
        )

        # Initialize Docling converter with PDF options
        self.converter = DocumentConverter(
            format_options={
                InputFormat.PDF: self.pdf_options,
            },
        )

        # Initialize chunkers with config-driven parameters
        self.hybrid_chunker = HybridChunker(
            tokenizer=self.tokenizer,
            max_tokens=config.chunk_size,
            merge_peers=True,  # Merge adjacent chunks with same metadata
        )

        # Fallback chunker for cases where HybridChunker fails
        self.hierarchical_chunker = HierarchicalChunker()

    @property
    def supported_extensions(self) -> list[str]:
        """Return supported PDF file extensions."""
        return [".pdf"]

    def process(self, input_path: Path) -> list[dict[str, Any]]:
        """
        Process PDF document and return structured chunks.

        Args:
            input_path: Path to PDF file

        Returns:
            List of chunk dictionaries with content and metadata

        Raises:
            FileNotFoundError: If PDF file doesn't exist
            ValueError: If file is not a supported PDF format

        """
        if not input_path.exists():
            msg = f"PDF file not found: {input_path}"
            raise FileNotFoundError(msg)

        if not self.supports_file(input_path):
            msg = f"Unsupported file type: {input_path.suffix}"
            raise ValueError(msg)

        self.console.print(f"[blue]Processing PDF: {input_path.name}[/blue]")

        try:
            # Convert PDF to DoclingDocument
            result = self.converter.convert(input_path)
            docling_doc = result.document

            if self.config.verbose:
                self.console.print(
                    f"  -> Converted to DoclingDocument with {len(docling_doc.texts)} text elements",
                )

            # Apply chunking strategy with fallback
            chunks = self._chunk_document(docling_doc)

            # Convert chunks to structured format
            structured_chunks = self._chunks_to_structured(chunks, input_path)

            # Apply post-processing based on config
            if self.config.merge_small_trailing_chunks:
                structured_chunks = merge_small_trailing_chunks(
                    structured_chunks,
                    self.config,
                )

            # Filter out non-useful chunks
            useful_chunks = [
                chunk
                for chunk in structured_chunks
                if is_chunk_useful(chunk, self.config)
            ]

            self.console.print(f"  -> Generated {len(useful_chunks)} useful chunks")
            return useful_chunks

        except Exception as e:
            self.console.print(
                f"[red]Error processing PDF {input_path.name}: {e!s}[/red]",
            )
            msg = f"Failed to process PDF: {e!s}"
            raise ValueError(msg) from e

    def _chunk_document(self, docling_doc: object) -> list:
        """Apply chunking strategy with HybridChunker and hierarchical fallback."""
        try:
            # Try HybridChunker first (preferred for token-aware chunking)
            chunks = list(self.hybrid_chunker.chunk(docling_doc))

            if self.config.verbose:
                self.console.print(f"  -> HybridChunker produced {len(chunks)} chunks")

            return chunks

        except (AttributeError, TypeError, ValueError) as e:
            if self.config.verbose:
                self.console.print(
                    f"  -> HybridChunker failed ({e!s}), falling back to HierarchicalChunker",
                )

            # Fallback to HierarchicalChunker
            try:
                chunks = list(self.hierarchical_chunker.chunk(docling_doc))

                if self.config.verbose:
                    self.console.print(
                        f"  -> HierarchicalChunker produced {len(chunks)} chunks",
                    )

                return chunks

            except Exception as fallback_e:
                msg = f"Both chunking strategies failed. HybridChunker: {e!s}, HierarchicalChunker: {fallback_e!s}"
                raise ValueError(
                    msg,
                ) from fallback_e

    def _chunks_to_structured(
        self,
        chunks: list,
        file_path: Path,
    ) -> list[dict[str, Any]]:
        """Convert Docling chunks to structured format."""
        structured_chunks = []

        for i, chunk in enumerate(chunks):
            try:
                # Extract text content from chunk
                if hasattr(chunk, "text"):
                    content = chunk.text
                elif hasattr(chunk, "content"):
                    content = chunk.content
                else:
                    content = str(chunk)

                # Basic cleanup
                content = content.strip()
                if content:
                    chunk_dict = {
                        "content": content,
                        "metadata": {
                            "source_file": str(file_path),
                            "chunk_index": i,
                            "chunk_type": "text",
                            "format": "pdf",
                        },
                    }
                    structured_chunks.append(chunk_dict)

            except (AttributeError, TypeError, ValueError) as e:
                if self.config.verbose:
                    self.console.print(
                        f"  -> Warning: Failed to convert chunk to structured format: {e!s}",
                    )
                continue

        return structured_chunks
