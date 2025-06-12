"""
PPTX-specific document processing pipeline using Docling.

Implements Microsoft PowerPoint presentation conversion with slide structure preservation
and intelligent chunking strategies.
"""

from pathlib import Path
from typing import Any

from docling.document_converter import DocumentConverter
from docling_core.transforms.chunker.base import BaseChunk
from docling_core.transforms.chunker.hierarchical_chunker import HierarchicalChunker
from docling_core.transforms.chunker.hybrid_chunker import HybridChunker
from docling_core.types.doc.document import DoclingDocument

from src.config import Config

from .base import BasePipeline


class PPTXPipeline(BasePipeline):
    """PPTX document processing pipeline with Docling integration."""

    def __init__(self, config: Config) -> None:
        """Initialize PPTX pipeline with Docling configuration."""
        super().__init__(config)

        # Initialize chunkers with optimized configuration following Docling best practices
        from src.serializers import LLMarkableSerializerProvider

        # Use optimized serializer for PPTX documents with presentation-specific image placeholders
        serializer_provider = LLMarkableSerializerProvider(
            image_placeholder="<!-- Presentation Slide Image: Visual content from slide -->",
        )

        self.hybrid_chunker = HybridChunker(
            tokenizer=self.tokenizer,
            merge_peers=True,  # Explicitly enable peer merging for better coherence
            serializer_provider=serializer_provider,  # Optimized for presentation content
        )

        self.hierarchical_chunker = HierarchicalChunker()

        # Initialize Docling converter with optimized PPTX options

        # For PPTX, we use SimplePipeline (recommended for office formats)
        # Note: PPTX uses the default DocumentConverter configuration with SimplePipeline
        self.converter = DocumentConverter()

        if config.verbose:
            self.console.print("✅ PPTX pipeline initialized with optimized configuration")
            self.console.print("  -> Using SimplePipeline for presentation document optimization")

        # Docling does not support VLM-based enrichments (picture description/classification) for PPTX as of 2025-06.

    def process(self, input_path: Path) -> list[dict[str, Any]]:
        """
        Process PPTX file through Docling conversion and chunking pipeline.

        Args:
            input_path: Path to PPTX file

        Returns:
            List of processed chunks with metadata

        Raises:
            FileAccessError: If PPTX file cannot be read
            ConversionError: If PPTX conversion fails
            ChunkingError: If chunking fails

        """
        from src.exceptions import ChunkingError, ConversionError

        if self.config.verbose:
            self.console.print(f"🔄 Processing PPTX: {input_path.name}")

        try:
            # Convert PPTX using Docling
            if self.config.verbose:
                self.console.print("  -> Converting PPTX with Docling...")

            result = self.converter.convert(
                input_path,
                max_file_size=self.config.max_file_size_bytes,
            )
            docling_doc = result.document

            if self.config.verbose:
                self.console.print("  -> ✅ PPTX converted successfully")

        except Exception as err:
            msg = f"Failed to convert PPTX: {err}"
            raise ConversionError(
                msg,
                file_path=str(input_path),
                conversion_stage="pptx_conversion",
            ) from err

        try:
            # Chunk the document
            if self.config.verbose:
                self.console.print("  -> Chunking document...")

            chunks = self._chunk_document(docling_doc)

            if self.config.verbose:
                self.console.print(f"  -> ✅ Generated {len(chunks)} chunks")

        except Exception as err:
            msg = f"Failed to chunk PPTX document: {err}"
            raise ChunkingError(
                msg,
                chunker_type="hybrid_with_hierarchical_fallback",
            ) from err

        # Process chunks into final format
        processed_chunks = self._process_chunks(chunks, input_path)
        return self._maybe_synthesize_chunks(processed_chunks)

    def _chunk_document(self, docling_doc: DoclingDocument) -> list[BaseChunk]:
        """
        Chunk PPTX document using HybridChunker with HierarchicalChunker fallback.

        Args:
            docling_doc: Docling document object

        Returns:
            List of BaseChunk objects

        """
        try:
            # Try HybridChunker first
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

    def _process_chunks(
        self,
        chunks: list[BaseChunk],
        input_path: Path,
    ) -> list[dict[str, Any]]:
        """
        Process raw chunks into final structured format with enhanced metadata.

        Uses shared processing logic from BasePipeline with PPTX-specific metadata.

        Args:
            chunks: List of BaseChunk objects from chunker
            input_path: Original file path for metadata

        Returns:
            List of processed chunks with rich metadata

        """
        # PPTX-specific additional metadata
        additional_metadata = {
            "file_type": "pptx",
            "synthesis_task": "summarize",
        }

        # Use shared processing logic from BasePipeline
        return self._process_chunks_with_metadata(
            chunks=chunks,
            input_path=input_path,
            file_type="pptx",
            processing_pipeline="pptx_docling_optimized",
            additional_metadata=additional_metadata,
        )

    def supports_file(self, file_path: Path) -> bool:
        """Check if this pipeline supports PPTX files."""
        from .factory import supports_file_extension

        return supports_file_extension(file_path, PPTXPipeline)
