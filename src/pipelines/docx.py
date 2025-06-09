"""
DOCX-specific document processing pipeline using Docling.

Implements Microsoft Word document conversion with structure preservation
and intelligent chunking strategies.
"""

from pathlib import Path
from typing import Any

from docling.datamodel.base_models import InputFormat
from docling.document_converter import DocumentConverter, WordFormatOption
from docling.pipeline.simple_pipeline import SimplePipeline
from docling_core.transforms.chunker.base import BaseChunk
from docling_core.transforms.chunker.hierarchical_chunker import HierarchicalChunker
from docling_core.transforms.chunker.hybrid_chunker import HybridChunker
from docling_core.types.doc.document import DoclingDocument

from src.config import Config
from src.serializers import TableOptimizedSerializerProvider

from .base import BasePipeline


class DocxPipeline(BasePipeline):
    """DOCX document processing pipeline with Docling integration."""

    def __init__(self, config: Config) -> None:
        """Initialize DOCX pipeline with Docling configuration."""
        super().__init__(config)

        # Initialize chunkers with optimized configuration following Docling best practices
        # Use table-optimized serializer for DOCX documents which often contain structured content
        serializer_provider = TableOptimizedSerializerProvider()

        self.hybrid_chunker = HybridChunker(
            tokenizer=self.tokenizer,
            merge_peers=True,  # Explicitly enable peer merging for better coherence
            serializer_provider=serializer_provider,  # Optimized for table-heavy documents
        )

        self.hierarchical_chunker = HierarchicalChunker()

        # Initialize Docling converter with optimized DOCX options
        word_format_option = WordFormatOption(
            pipeline_cls=SimplePipeline,  # Recommended pipeline for office formats
        )

        self.converter = DocumentConverter(
            format_options={
                InputFormat.DOCX: word_format_option,
            },
        )

        if config.verbose:
            self.console.print("✅ DOCX pipeline initialized with optimized WordFormatOption")
            self.console.print("  -> Using SimplePipeline for office document optimization")

    def process(self, input_path: Path) -> list[dict[str, Any]]:
        """
        Process DOCX file through Docling conversion and chunking pipeline.

        Args:
            input_path: Path to DOCX file

        Returns:
            List of processed chunks with metadata

        Raises:
            FileAccessError: If DOCX file cannot be read
            ConversionError: If DOCX conversion fails
            ChunkingError: If chunking fails

        """
        from src.exceptions import ChunkingError, ConversionError

        if self.config.verbose:
            self.console.print(f"🔄 Processing DOCX: {input_path.name}")

        try:
            # Convert DOCX using Docling
            if self.config.verbose:
                self.console.print("  -> Converting DOCX with Docling...")

            result = self.converter.convert(
                input_path,
                max_file_size=self.config.max_file_size_bytes,
            )
            docling_doc = result.document

            if self.config.verbose:
                self.console.print("  -> ✅ DOCX converted successfully")

        except Exception as err:
            msg = f"Failed to convert DOCX: {err}"
            raise ConversionError(
                msg,
                file_path=str(input_path),
                conversion_stage="docx_conversion",
            ) from err

        try:
            # Chunk the document
            if self.config.verbose:
                self.console.print("  -> Chunking document...")

            chunks = self._chunk_document(docling_doc)

            if self.config.verbose:
                self.console.print(f"  -> ✅ Generated {len(chunks)} chunks")

        except Exception as err:
            msg = f"Failed to chunk DOCX document: {err}"
            raise ChunkingError(
                msg,
                chunker_type="hybrid_with_hierarchical_fallback",
            ) from err

        # Process chunks into final format
        return self._process_chunks(chunks, input_path)

    def _chunk_document(self, docling_doc: DoclingDocument) -> list[BaseChunk]:
        """
        Chunk DOCX document using HybridChunker with HierarchicalChunker fallback.

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
        """Process DOCX chunks using shared base implementation."""
        return self._process_chunks_with_metadata(
            chunks=chunks,
            input_path=input_path,
            file_type="docx",
            processing_pipeline="docx_docling",
        )

    def supports_file(self, file_path: Path) -> bool:
        """Check if this pipeline supports DOCX files."""
        from .factory import supports_file_extension

        return supports_file_extension(file_path, DocxPipeline)
