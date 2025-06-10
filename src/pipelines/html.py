"""
HTML-specific document processing pipeline using Docling.

Implements HTML to markdown conversion with optimized Docling chunking strategies.
"""

from pathlib import Path
from typing import Any

from docling.document_converter import DocumentConverter
from docling_core.transforms.chunker.base import BaseChunk
from docling_core.transforms.chunker.hierarchical_chunker import HierarchicalChunker
from docling_core.transforms.chunker.hybrid_chunker import HybridChunker
from docling_core.types.doc.document import DoclingDocument

from src.config import Config
from src.serializers import LLMarkableSerializerProvider

from .base import BasePipeline


class HTMLPipeline(BasePipeline):
    """HTML document processing pipeline with Docling integration."""

    def __init__(self, config: Config) -> None:
        """Initialize HTML pipeline with optimized Docling configuration."""
        super().__init__(config)

        # Initialize chunkers with optimized configuration following Docling best practices
        serializer_provider = LLMarkableSerializerProvider(
            image_placeholder="<!-- HTML Image: Web content visual element -->",
        )

        self.hybrid_chunker = HybridChunker(
            tokenizer=self.tokenizer,
            merge_peers=True,  # Explicitly enable peer merging for better coherence
            serializer_provider=serializer_provider,  # Custom formatting for tables/images
        )

        self.hierarchical_chunker = HierarchicalChunker()

        # Initialize Docling converter with HTML options
        self.converter = DocumentConverter()

        if config.verbose:
            self.console.print("✅ HTML pipeline initialized with optimized Docling chunking")

    def supports_file(self, file_path: Path) -> bool:
        """Check if this pipeline supports HTML files."""
        from .factory import supports_file_extension

        return supports_file_extension(file_path, HTMLPipeline)

    def _chunk_document(self, docling_doc: DoclingDocument) -> list[BaseChunk]:
        """
        Chunk HTML document using HybridChunker with HierarchicalChunker fallback.

        Uses the same optimized chunking strategy as other pipelines for consistency.

        Args:
            docling_doc: Docling document object

        Returns:
            List of BaseChunk objects

        """
        try:
            # Try HybridChunker first - optimal for most HTML documents
            chunks = list(self.hybrid_chunker.chunk(dl_doc=docling_doc))
        except Exception as err:  # noqa: BLE001
            if self.config.verbose:
                self.console.print(
                    f"  -> ⚠️ HybridChunker failed ({err}), falling back to HierarchicalChunker",
                )

            try:
                chunks = list(self.hierarchical_chunker.chunk(docling_doc))
            except Exception as fallback_err:
                from src.exceptions import ChunkingError

                msg = f"Both chunking strategies failed. HybridChunker: {err}, HierarchicalChunker: {fallback_err}"
                raise ChunkingError(
                    msg,
                    chunker_type="fallback_chain",
                ) from fallback_err
            else:
                if self.config.verbose:
                    self.console.print(
                        f"  -> ✅ HierarchicalChunker produced {len(chunks)} chunks",
                    )
                return chunks
        else:
            if self.config.verbose:
                self.console.print(f"  -> HybridChunker produced {len(chunks)} chunks")
            return chunks

    def process(self, file_path: Path) -> list[dict[str, Any]]:  # noqa: C901 - complex but readable
        """
        Process HTML file and return structured chunks using optimized Docling chunking.

        Args:
            file_path: Path to the HTML file to process

        Returns:
            List of chunk dictionaries with content and metadata

        Raises:
            FileNotFoundError: If the file doesn't exist
            ValueError: If the file format is not supported

        """
        if not file_path.exists():
            msg = f"File not found: {file_path}"
            raise FileNotFoundError(msg)

        if not self.supports_file(file_path):
            msg = f"Unsupported file extension: {file_path.suffix}"
            raise ValueError(msg)

        if self.config.verbose:
            self.console.print(f"🔄 Processing HTML: {file_path.name}")

        try:
            # Convert HTML document using Docling
            try:
                if self.config.verbose:
                    self.console.print("  -> Converting HTML with Docling...")

                result = self.converter.convert(
                    str(file_path),
                    max_file_size=self.config.max_file_size_bytes,
                )
                docling_doc = result.document

                if self.config.verbose:
                    self.console.print("  -> ✅ HTML converted successfully")

            except Exception as e:
                from src.exceptions import ConversionError

                msg = f"HTML parsing failed: {e!s}"
                raise ConversionError(
                    msg,
                    file_path=str(file_path),
                    conversion_stage="document_parsing",
                    original_error=e,
                ) from e

            try:
                # Chunk the document using optimized chunking strategy
                if self.config.verbose:
                    self.console.print("  -> Chunking document with hybrid strategy...")

                chunks = self._chunk_document(docling_doc)

                if self.config.verbose:
                    self.console.print(f"  -> ✅ Generated {len(chunks)} chunks")

            except Exception as e:
                from src.exceptions import ChunkingError

                msg = f"HTML chunking failed: {e!s}"
                raise ChunkingError(
                    msg,
                    chunker_type="hybrid_with_hierarchical_fallback",
                    original_error=e,
                ) from e

            # Process chunks into final format
            processed_chunks = self._process_chunks(chunks, file_path)
            return self._maybe_synthesize_chunks(processed_chunks)

        except Exception as e:
            # If it's already one of our custom exceptions, re-raise it
            from src.exceptions import ConversionError, LLMarkableError

            if isinstance(e, LLMarkableError):
                raise

            # Otherwise, wrap in a ConversionError
            error = ConversionError(
                f"Unexpected error processing HTML: {e!s}",
                file_path=str(file_path),
                conversion_stage="unknown",
                original_error=e,
            )
            raise error from e

    def _process_chunks(
        self,
        chunks: list[BaseChunk],
        input_path: Path,
    ) -> list[dict[str, Any]]:
        """Process HTML chunks using shared base implementation."""
        return self._process_chunks_with_metadata(
            chunks=chunks,
            input_path=input_path,
            file_type="html",
            processing_pipeline="html_docling_optimized",
        )
