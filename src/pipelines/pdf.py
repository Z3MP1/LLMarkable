"""
PDF document processing pipeline with Docling integration.

Converts PDF files to Markdown chunks using Docling's DocumentConverter
with optimized table extraction, OCR configuration, and advanced chunking.
"""

from pathlib import Path
from typing import Any

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions, TableFormerMode
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling_core.transforms.chunker.base import BaseChunk
from docling_core.transforms.chunker.hierarchical_chunker import HierarchicalChunker
from docling_core.transforms.chunker.hybrid_chunker import HybridChunker
from docling_core.types.doc.document import DoclingDocument
from rich.console import Console

from src.config import Config
from src.utils import get_tokenizer, is_chunk_useful, merge_small_trailing_chunks

from .base import BasePipeline


class PDFPipeline(BasePipeline):
    """PDF document processing pipeline with Docling integration."""

    def __init__(self, config: Config) -> None:
        """Initialize PDF pipeline with optimized Docling configuration."""
        super().__init__(config)
        self.console = Console()
        self.tokenizer = get_tokenizer(config)

        # Initialize chunkers with correct API
        self.hybrid_chunker = HybridChunker(
            tokenizer=self.tokenizer,
        )

        self.hierarchical_chunker = HierarchicalChunker()

        # Initialize Docling converter with optimized PDF options
        pdf_pipeline_options = PdfPipelineOptions(
            # Core processing options
            do_ocr=True,
            do_table_structure=config.preserve_tables,
        )

        # Configure advanced table processing if enabled
        if config.preserve_tables:
            # Use accurate TableFormer mode for better quality (new in v1.16.0)
            pdf_pipeline_options.table_structure_options.mode = TableFormerMode.ACCURATE

            # Use predicted text cells for better column separation
            # This improves quality when multiple columns are erroneously merged
            pdf_pipeline_options.table_structure_options.do_cell_matching = False

        # Configure OCR language options based on config
        if hasattr(config, "ocr_languages") and config.ocr_languages:
            pdf_pipeline_options.ocr_options.lang = config.ocr_languages
        else:
            # Default to English and common European languages
            pdf_pipeline_options.ocr_options.lang = ["en", "fr", "de", "es"]

        pdf_format_option = PdfFormatOption(pipeline_options=pdf_pipeline_options)

        self.converter = DocumentConverter(
            format_options={
                InputFormat.PDF: pdf_format_option,
            },
        )

        if config.verbose:
            self.console.print("✅ PDF pipeline initialized with optimized Docling configuration")
            if config.preserve_tables:
                self.console.print("  -> Advanced table processing enabled (ACCURATE mode)")
            self.console.print(f"  -> OCR languages: {pdf_pipeline_options.ocr_options.lang}")

    def process(self, input_path: Path) -> list[dict[str, Any]]:
        """
        Process PDF file through optimized Docling conversion and chunking pipeline.

        Args:
            input_path: Path to PDF file

        Returns:
            List of processed chunks with metadata

        Raises:
            FileAccessError: If PDF file cannot be read
            ConversionError: If PDF conversion fails
            ChunkingError: If chunking fails

        """
        from src.exceptions import ChunkingError, ConversionError

        if self.config.verbose:
            self.console.print(f"🔄 Processing PDF: {input_path.name}")

        try:
            # Convert PDF using optimized Docling configuration
            if self.config.verbose:
                self.console.print("  -> Converting PDF with optimized Docling settings...")

            result = self.converter.convert(
                input_path,
                max_file_size=self.config.max_file_size_bytes,
                max_num_pages=self.config.max_num_pages,
            )
            docling_doc = result.document

            if self.config.verbose:
                self.console.print("  -> ✅ PDF converted successfully")
                # Note: num_pages() may not have type annotations in docling_core yet
                pages = docling_doc.num_pages()
                self.console.print(f"  -> Document pages: {pages}")

        except Exception as err:
            msg = f"Failed to convert PDF: {err}"
            raise ConversionError(
                msg,
                file_path=str(input_path),
                conversion_stage="pdf_conversion",
            ) from err

        try:
            # Chunk the document using optimized chunking strategy
            if self.config.verbose:
                self.console.print("  -> Chunking document with hybrid strategy...")

            chunks = self._chunk_document(docling_doc)

            if self.config.verbose:
                self.console.print(f"  -> ✅ Generated {len(chunks)} chunks")

        except Exception as err:
            msg = f"Failed to chunk PDF document: {err}"
            raise ChunkingError(
                msg,
                chunker_type="hybrid_with_hierarchical_fallback",
            ) from err

        # Process chunks into final format
        return self._process_chunks(chunks, input_path)

    def _chunk_document(self, docling_doc: DoclingDocument) -> list[BaseChunk]:
        """
        Chunk PDF document using HybridChunker with HierarchicalChunker fallback.

        Uses optimized chunking strategy with intelligent fallback for robustness.

        Args:
            docling_doc: Docling document object

        Returns:
            List of BaseChunk objects

        """
        try:
            # Try HybridChunker first - optimal for most PDF documents
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

        Args:
            chunks: List of BaseChunk objects from chunker
            input_path: Original file path for metadata

        Returns:
            List of processed chunks with rich metadata

        """
        processed_chunks: list[dict[str, Any]] = []
        base_metadata = {
            "source_file": input_path.name,
            "file_type": "pdf",
            "processing_pipeline": "pdf_docling_optimized",
            "table_processing": "accurate" if self.config.preserve_tables else "disabled",
        }

        for i, chunk in enumerate(chunks):
            # Extract text content
            content = chunk.text

            # Apply content filtering with PDF-specific parameters
            if not is_chunk_useful(content, self.config):
                if self.config.verbose:
                    self.console.print(f"  -> Skipping chunk {i} (insufficient content)")
                continue

            # Create enhanced chunk metadata
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

        # Apply trailing chunk consolidation with PDF-specific logic
        if self.config.merge_small_trailing_chunks:
            processed_chunks = merge_small_trailing_chunks(
                processed_chunks,
                self.config,
                tokenizer=self.tokenizer,
                verbose=self.config.verbose,
            )

        if self.config.verbose:
            self.console.print(f"  -> Final output: {len(processed_chunks)} processed chunks")

        return processed_chunks

    def supports_file(self, file_path: Path) -> bool:
        """Check if this pipeline supports PDF files."""
        from .factory import supports_file_extension

        return supports_file_extension(file_path, PDFPipeline)
