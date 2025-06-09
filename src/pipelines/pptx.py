"""
PPTX-specific document processing pipeline using Docling.

Implements Microsoft PowerPoint presentation conversion with slide structure preservation
and intelligent chunking strategies.
"""

from pathlib import Path
from typing import Any

from docling.datamodel.base_models import InputFormat
from docling.document_converter import DocumentConverter, PowerpointFormatOption
from docling_core.transforms.chunker.base import BaseChunk
from docling_core.transforms.chunker.hierarchical_chunker import HierarchicalChunker
from docling_core.transforms.chunker.hybrid_chunker import HybridChunker
from docling_core.types.doc.document import DoclingDocument
from rich.console import Console

from src.config import Config
from src.utils import get_tokenizer, is_chunk_useful, merge_small_trailing_chunks

from .base import BasePipeline


class PPTXPipeline(BasePipeline):
    """PPTX document processing pipeline with Docling integration."""

    def __init__(self, config: Config) -> None:
        """Initialize PPTX pipeline with Docling configuration."""
        super().__init__(config)
        self.console = Console()

        # Get tokenizer using the utils function
        self.tokenizer = get_tokenizer(config)

        # Initialize chunkers with correct API
        self.hybrid_chunker = HybridChunker(
            tokenizer=self.tokenizer,
        )

        self.hierarchical_chunker = HierarchicalChunker()

        # Initialize Docling converter with PPTX options
        pptx_format_option = PowerpointFormatOption()

        self.converter = DocumentConverter(
            format_options={
                InputFormat.PPTX: pptx_format_option,
            },
        )

        if config.verbose:
            self.console.print("✅ PPTX pipeline initialized with Docling")

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
        return self._process_chunks(chunks, input_path)

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
        Process raw chunks into final structured format.

        Args:
            chunks: List of BaseChunk objects from chunker
            input_path: Original file path for metadata

        Returns:
            List of processed chunks with metadata

        """
        processed_chunks: list[dict[str, Any]] = []
        base_metadata = {
            "source_file": input_path.name,
            "file_type": "pptx",
            "processing_pipeline": "pptx_docling",
        }

        for i, chunk in enumerate(chunks):
            # Extract text content
            content = chunk.text

            # Apply content filtering
            if not is_chunk_useful(content, self.config):
                if self.config.verbose:
                    self.console.print(f"  -> Skipping chunk {i} (insufficient content)")
                continue

            # Create chunk metadata
            chunk_metadata = {
                **base_metadata,
                "chunk_id": i,
                "token_count": self.tokenizer.count_tokens(content),
                "chunk_metadata": chunk.meta.export_json_dict() if hasattr(chunk.meta, "export_json_dict") else {},
            }

            processed_chunks.append(
                {
                    "content": content,
                    "metadata": chunk_metadata,
                },
            )

        # Apply trailing chunk consolidation
        if self.config.merge_small_trailing_chunks:
            processed_chunks = merge_small_trailing_chunks(
                processed_chunks,
                self.config,
                tokenizer=self.tokenizer,
                verbose=self.config.verbose,
            )

        return processed_chunks

    def supports_file(self, file_path: Path) -> bool:
        """Check if this pipeline supports PPTX files."""
        from .factory import supports_file_extension

        return supports_file_extension(file_path, PPTXPipeline)
