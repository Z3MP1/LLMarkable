"""
Image-specific document processing pipeline using Docling.

Implements OCR-based image conversion with intelligent text extraction
and chunking strategies for various image formats.
"""

from pathlib import Path
from typing import Any

from docling.document_converter import DocumentConverter
from docling_core.transforms.chunker.base import BaseChunk
from docling_core.transforms.chunker.hierarchical_chunker import HierarchicalChunker
from docling_core.transforms.chunker.hybrid_chunker import HybridChunker
from docling_core.types.doc.document import DoclingDocument
from rich.console import Console

from src.config import Config
from src.utils import get_tokenizer, is_chunk_useful, merge_small_trailing_chunks

from .base import BasePipeline


class ImagePipeline(BasePipeline):
    """Image processing pipeline with OCR capabilities using Docling."""

    def __init__(self, config: Config) -> None:
        """Initialize Image pipeline with Docling OCR configuration."""
        super().__init__(config)
        self.console = Console()

        # Get tokenizer using the utils function
        self.tokenizer = get_tokenizer(config)

        # Initialize chunkers with correct API
        self.hybrid_chunker = HybridChunker(
            tokenizer=self.tokenizer,
        )

        self.hierarchical_chunker = HierarchicalChunker()

        # Initialize Docling converter for image processing
        self.converter = DocumentConverter()

        if config.verbose:
            self.console.print("✅ Image pipeline initialized with Docling OCR")

    def process(self, input_path: Path) -> list[dict[str, Any]]:
        """
        Process image file through Docling OCR and chunking pipeline.

        Args:
            input_path: Path to image file

        Returns:
            List of processed chunks with metadata

        Raises:
            FileAccessError: If image file cannot be read
            ConversionError: If OCR conversion fails
            ChunkingError: If chunking fails

        """
        from src.exceptions import ChunkingError, ConversionError

        if self.config.verbose:
            self.console.print(f"🔄 Processing Image: {input_path.name}")

        try:
            # Convert image using Docling OCR
            if self.config.verbose:
                self.console.print("  -> Running OCR with Docling...")

            result = self.converter.convert(
                input_path,
                max_file_size=self.config.large_image_threshold_bytes,  # Use larger threshold for images
            )
            docling_doc = result.document

            if self.config.verbose:
                self.console.print("  -> ✅ OCR completed successfully")

        except Exception as err:
            msg = f"Failed to process image with OCR: {err}"
            raise ConversionError(
                msg,
                file_path=str(input_path),
                conversion_stage="ocr_processing",
            ) from err

        try:
            # Chunk the document
            if self.config.verbose:
                self.console.print("  -> Chunking extracted text...")

            chunks = self._chunk_document(docling_doc)

            if self.config.verbose:
                self.console.print(f"  -> ✅ Generated {len(chunks)} chunks")

        except Exception as err:
            msg = f"Failed to chunk image text: {err}"
            raise ChunkingError(
                msg,
                chunker_type="hybrid_with_hierarchical_fallback",
            ) from err

        # Process chunks into final format
        return self._process_chunks(chunks, input_path)

    def _chunk_document(self, docling_doc: DoclingDocument) -> list[BaseChunk]:
        """
        Chunk image document using HybridChunker with HierarchicalChunker fallback.

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
            "file_type": "image",
            "processing_pipeline": "image_ocr_docling",
            "image_format": input_path.suffix.lower().lstrip("."),
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
        """Check if this pipeline supports image files."""
        from .factory import supports_file_extension

        return supports_file_extension(file_path, ImagePipeline)
