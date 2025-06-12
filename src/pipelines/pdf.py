"""
PDF document processing pipeline with Docling integration.

Converts PDF files to Markdown chunks using Docling's DocumentConverter
with optimized table extraction, OCR configuration, and advanced chunking.
"""

from pathlib import Path
from typing import Any

# PDF-specific imports (format-specific, must remain)
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions, TableFormerMode
from docling.document_converter import DocumentConverter, PdfFormatOption

# Required imports for this pipeline (type hints and instantiation)
from docling_core.transforms.chunker.base import BaseChunk
from docling_core.transforms.chunker.hierarchical_chunker import HierarchicalChunker
from docling_core.transforms.chunker.hybrid_chunker import HybridChunker
from docling_core.types.doc.document import DoclingDocument

from src.config import Config
from src.serializers import LLMarkableSerializerProvider

from .base import BasePipeline


class PDFPipeline(BasePipeline):
    """PDF document processing pipeline with Docling integration."""

    def __init__(self, config: Config) -> None:  # noqa: C901, PLR0912, PLR0915 - initialization logic is extensive
        """Initialize PDF pipeline with optimized Docling configuration."""
        # Base initialization now handles: config, console, tokenizer
        super().__init__(config)

        # Initialize chunkers with optimized configuration following Docling best practices
        # Create custom serializer provider for consistent table/image formatting
        serializer_provider = LLMarkableSerializerProvider(
            image_placeholder="<!-- PDF Image: Visual content extracted via OCR -->",
        )

        self.hybrid_chunker = HybridChunker(
            tokenizer=self.tokenizer,
            merge_peers=True,  # Explicitly enable peer merging for better coherence
            serializer_provider=serializer_provider,  # Custom formatting for tables/images
        )

        self.hierarchical_chunker = HierarchicalChunker()

        # Initialize Docling converter with advanced PDF options
        pdf_pipeline_options = PdfPipelineOptions(
            # Core processing options
            do_ocr=True,
            do_table_structure=config.preserve_tables,
        )

        # Configure offline/artifacts path for air-gapped environments
        if config.artifacts_path:
            pdf_pipeline_options.artifacts_path = config.artifacts_path
            if config.verbose:
                self.console.print(f"  -> Using local artifacts path: {config.artifacts_path}")

        # Enable external plugins if configured
        if config.allow_external_plugins:
            pdf_pipeline_options.allow_external_plugins = True
            if config.verbose:
                self.console.print("  -> External plugins enabled")

        # Enable remote services if configured
        if config.enable_remote_services:
            pdf_pipeline_options.enable_remote_services = True
            if config.verbose:
                self.console.print("  -> Remote services enabled")

        # Configure advanced enrichment features based on config
        if (
            config.enable_picture_description
            or config.use_granite_vision
            or config.use_smolvlm
            or config.vision_model_repo_id
        ):
            pdf_pipeline_options.do_picture_description = True
            pdf_pipeline_options.generate_picture_images = True
            pdf_pipeline_options.images_scale = config.vision_model_scale

            # Configure vision model options
            if config.use_granite_vision:
                from docling.datamodel.pipeline_options import granite_picture_description

                pdf_pipeline_options.picture_description_options = granite_picture_description
                if config.verbose:
                    self.console.print("  -> Using Granite vision model for picture description")
            elif config.use_smolvlm:
                from docling.datamodel.pipeline_options import smolvlm_picture_description

                pdf_pipeline_options.picture_description_options = smolvlm_picture_description
                if config.verbose:
                    self.console.print("  -> Using SmolVLM model for picture description")
            elif config.vision_model_repo_id:
                from docling.datamodel.pipeline_options import PictureDescriptionVlmOptions

                pdf_pipeline_options.picture_description_options = PictureDescriptionVlmOptions(
                    repo_id=config.vision_model_repo_id,
                    prompt=config.vision_model_prompt,
                )
                if config.verbose:
                    self.console.print(f"  -> Using custom vision model: {config.vision_model_repo_id}")
            elif config.verbose:
                self.console.print("  -> Picture description enrichment enabled (default model)")

        # Always enable picture classification unless explicitly disabled
        if config.enable_picture_classification:
            pdf_pipeline_options.do_picture_classification = True
            pdf_pipeline_options.generate_picture_images = True
            pdf_pipeline_options.images_scale = config.vision_model_scale
            if config.verbose:
                self.console.print("  -> Picture classification enrichment enabled (default)")

        if config.enable_code_enrichment:
            pdf_pipeline_options.do_code_enrichment = True
            if config.verbose:
                self.console.print("  -> Code enrichment enabled")

        if config.enable_formula_enrichment:
            pdf_pipeline_options.do_formula_enrichment = True
            if config.verbose:
                self.console.print("  -> Formula enrichment enabled")

        # Configure advanced table processing if enabled
        if config.preserve_tables:
            # Use accurate TableFormer mode for better quality (new in v1.16.0)
            pdf_pipeline_options.table_structure_options.mode = TableFormerMode.ACCURATE

            # Configure cell matching based on config setting
            # do_cell_matching=False improves quality when multiple columns are erroneously merged
            pdf_pipeline_options.table_structure_options.do_cell_matching = config.enable_table_cell_matching

            if config.verbose:
                cell_matching_status = (
                    "enabled" if config.enable_table_cell_matching else "disabled (better column separation)"
                )
                self.console.print(f"  -> Table cell matching: {cell_matching_status}")

        # Configure OCR language options based on config
        if config.ocr_languages:
            pdf_pipeline_options.ocr_options.lang = config.ocr_languages
            if config.verbose:
                self.console.print(f"  -> OCR languages: {config.ocr_languages}")
        else:
            # Default to English and common European languages
            pdf_pipeline_options.ocr_options.lang = ["en", "fr", "de", "es"]
            if config.verbose:
                self.console.print(f"  -> OCR languages (default): {pdf_pipeline_options.ocr_options.lang}")

        pdf_format_option = PdfFormatOption(pipeline_options=pdf_pipeline_options)

        # Configure backend selection based on config
        backend = None
        if config.pdf_backend:
            if config.pdf_backend == "pypdfium2":
                from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend

                backend = PyPdfiumDocumentBackend
                if config.verbose:
                    self.console.print("  -> Using PyPdfium2 backend")
            elif config.pdf_backend in ["dlparse_v1", "dlparse_v2"]:
                # Note: These are potential future backends - keeping for forward compatibility
                if config.verbose:
                    self.console.print(f"  -> Backend '{config.pdf_backend}' specified but may not be available yet")

        # Create DocumentConverter with backend selection
        if backend:
            pdf_format_option_with_backend = PdfFormatOption(
                pipeline_options=pdf_pipeline_options,
                backend=backend,
            )
            self.converter = DocumentConverter(
                format_options={
                    InputFormat.PDF: pdf_format_option_with_backend,
                },
            )
        else:
            self.converter = DocumentConverter(
                format_options={
                    InputFormat.PDF: pdf_format_option,
                },
            )

        if config.verbose:
            self.console.print("✅ PDF pipeline initialized with optimized Docling configuration")

            # Log enabled enrichment features
            enrichments = []
            if config.enable_picture_description:
                enrichments.append("picture description")
            if config.enable_code_enrichment:
                enrichments.append("code enrichment")
            if config.enable_formula_enrichment:
                enrichments.append("formula enrichment")

            if enrichments:
                self.console.print(f"  -> Advanced enrichments: {', '.join(enrichments)}")

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
                pages = docling_doc.num_pages()  # type: ignore[no-untyped-call]
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
        processed_chunks = self._process_chunks(chunks, input_path)
        # Synthesis step: refine chunks if requested
        return self._maybe_synthesize_chunks(processed_chunks)

    def _chunk_document(self, docling_doc: DoclingDocument) -> list[BaseChunk]:
        """
        Chunk PDF document using HybridChunker with HierarchicalChunker fallback.

        Uses shared chunking strategy from BasePipeline for robustness and consistency.

        Args:
            docling_doc: Docling document object

        Returns:
            List of BaseChunk objects

        """
        # Use shared chunking logic from BasePipeline
        return self._chunk_document_with_fallback(
            docling_doc=docling_doc,
            hybrid_chunker=self.hybrid_chunker,
            hierarchical_chunker=self.hierarchical_chunker,
            format_name="PDF",
        )

    def _process_chunks(
        self,
        chunks: list[BaseChunk],
        input_path: Path,
    ) -> list[dict[str, Any]]:
        """
        Process raw chunks into final structured format with enhanced metadata.

        Uses shared processing logic from BasePipeline with PDF-specific metadata.

        Args:
            chunks: List of BaseChunk objects from chunker
            input_path: Original file path for metadata

        Returns:
            List of processed chunks with rich metadata

        """
        # PDF-specific additional metadata
        additional_metadata = {
            "file_type": "pdf",
            "synthesis_task": "summarize",
            "table_processing": "accurate" if self.config.preserve_tables else "disabled",
        }

        # Use shared processing logic from BasePipeline
        return self._process_chunks_with_metadata(
            chunks=chunks,
            input_path=input_path,
            file_type="pdf",
            processing_pipeline="pdf_docling_optimized",
            additional_metadata=additional_metadata,
        )

    def supports_file(self, file_path: Path) -> bool:
        """Check if this pipeline supports PDF files."""
        from .factory import supports_file_extension

        return supports_file_extension(file_path, PDFPipeline)
