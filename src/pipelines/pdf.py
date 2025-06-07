"""
PDF-specific document processing pipeline using Docling.

Implements optimized PDF to markdown conversion with table structure preservation
and token-aware chunking strategies.
"""

# Import utilities from root level utils.py
import sys
from pathlib import Path

from docling.chunking import HierarchicalChunker, HybridChunker
from docling.datamodel.base_models import InputFormat
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling_core.transforms.chunker.tokenizer.huggingface import HuggingFaceTokenizer
from rich.console import Console

sys.path.append(str(Path(__file__).parent.parent.parent))
from src.config import Config
from utils import is_chunk_useful, merge_small_trailing_chunks

from .base import BasePipeline


class PDFPipeline(BasePipeline):
    """PDF document processing pipeline with Docling integration."""

    def __init__(self, config: Config) -> None:
        """Initialize PDF pipeline with Docling configuration."""
        super().__init__(config)
        self.console = Console()

        # Initialize tokenizer for chunking (using same as HybridChunker)
        from transformers import AutoTokenizer

        base_tokenizer = AutoTokenizer.from_pretrained("microsoft/DialoGPT-medium")
        self.tokenizer = HuggingFaceTokenizer(
            tokenizer=base_tokenizer,
            max_tokens=self.config.chunk_size,
        )

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

    def process(self, input_path: Path) -> list[str]:
        """
        Process PDF document and return markdown chunks.

        Args:
            input_path: Path to PDF file

        Returns:
            List of markdown text chunks

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

            # Convert chunks to markdown strings
            markdown_chunks = self._chunks_to_markdown(chunks)

            # Apply post-processing based on config
            if self.config.merge_small_trailing_chunks:
                markdown_chunks = self._merge_small_chunks(markdown_chunks)

            # Filter out non-useful chunks
            useful_chunks = self._filter_useful_chunks(markdown_chunks)

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

    def _chunks_to_markdown(self, chunks: list) -> list[str]:
        """Convert Docling chunks to markdown strings."""
        markdown_chunks = []

        for chunk in chunks:
            try:
                # Use Docling's contextualize method for proper markdown conversion
                # Extract text directly if available, otherwise use Docling's serialization
                markdown_text = chunk.text if hasattr(chunk, "text") else str(chunk)

                # Basic cleanup
                markdown_text = markdown_text.strip()
                if markdown_text:
                    markdown_chunks.append(markdown_text)

            except (AttributeError, TypeError, ValueError) as e:
                if self.config.verbose:
                    self.console.print(
                        f"  -> Warning: Failed to convert chunk to markdown: {e!s}",
                    )
                continue

        return markdown_chunks

    def _merge_small_chunks(self, chunks: list[str]) -> list[str]:
        """Apply small chunk merging using utility function."""
        # Convert strings to mock chunk objects for utility function
        mock_chunks = [type("Chunk", (), {"text": chunk})() for chunk in chunks]

        merged_chunks = merge_small_trailing_chunks(
            chunks=mock_chunks,
            tokenizer=self.tokenizer,
            console=self.console,
            min_tokens=self.config.min_tokens,
            merge_flag=self.config.merge_small_trailing_chunks,
        )

        # Convert back to strings
        return [chunk.text for chunk in merged_chunks]

    def _filter_useful_chunks(self, chunks: list[str]) -> list[str]:
        """Filter chunks based on usefulness criteria."""
        useful_chunks = []

        for chunk in chunks:
            if is_chunk_useful(chunk, self.tokenizer, self.config.min_tokens):
                useful_chunks.append(chunk)
            elif self.config.verbose:
                token_count = self.tokenizer.count_tokens(chunk)
                self.console.print(
                    f"  -> Filtered out chunk with {token_count} tokens (below {self.config.min_tokens})",
                )

        return useful_chunks
