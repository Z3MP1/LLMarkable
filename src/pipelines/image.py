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
from src.config import Config

from .base import BasePipeline


class ImagePipeline(BasePipeline):
    """Image processing pipeline with OCR capabilities using Docling."""

    def __init__(self, config: Config) -> None:
        """Initialize Image pipeline with Docling OCR configuration."""
        super().__init__(config)

        # Initialize chunkers with optimized configuration following Docling best practices
        from src.serializers import ImageOptimizedSerializerProvider

        # Use image-optimized serializer for image documents
        serializer_provider = ImageOptimizedSerializerProvider()

        self.hybrid_chunker = HybridChunker(
            tokenizer=self.tokenizer,
            merge_peers=True,  # Explicitly enable peer merging for better coherence
            serializer_provider=serializer_provider,  # Optimized for image-heavy documents
        )

        self.hierarchical_chunker = HierarchicalChunker()

        # Initialize Docling converter for image processing with advanced OCR configuration
        from docling.datamodel.pipeline_options import PdfPipelineOptions

        # Configure OCR options based on config settings
        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_ocr = True

        # Configure OCR language options
        if config.ocr_languages:
            pipeline_options.ocr_options.lang = config.ocr_languages
            if config.verbose:
                self.console.print(f"  -> OCR languages: {config.ocr_languages}")
        else:
            # Default to English for images unless specified
            pipeline_options.ocr_options.lang = ["en"]
            if config.verbose:
                self.console.print("  -> OCR language: English (default)")

        # Configure advanced OCR options
        if hasattr(pipeline_options.ocr_options, "force_full_page_ocr"):
            pipeline_options.ocr_options.force_full_page_ocr = config.image_force_full_page_ocr

        if hasattr(pipeline_options.ocr_options, "use_gpu"):
            pipeline_options.ocr_options.use_gpu = config.image_use_gpu
            if config.verbose and config.image_use_gpu:
                self.console.print("  -> GPU acceleration enabled for OCR")

        # Configure VLM-based enrichments (picture description/classification) by default
        if (
            config.enable_picture_description
            or config.use_granite_vision
            or config.use_smolvlm
            or config.vision_model_repo_id
        ):
            pipeline_options.do_picture_description = True
            pipeline_options.generate_picture_images = True
            pipeline_options.images_scale = config.vision_model_scale

            # Configure vision model options
            if config.use_granite_vision:
                from docling.datamodel.pipeline_options import granite_picture_description

                pipeline_options.picture_description_options = granite_picture_description
                if config.verbose:
                    self.console.print("  -> Using Granite vision model for picture description")
            elif config.use_smolvlm:
                from docling.datamodel.pipeline_options import smolvlm_picture_description

                pipeline_options.picture_description_options = smolvlm_picture_description
                if config.verbose:
                    self.console.print("  -> Using SmolVLM model for picture description")
            elif config.vision_model_repo_id:
                from docling.datamodel.pipeline_options import PictureDescriptionVlmOptions

                pipeline_options.picture_description_options = PictureDescriptionVlmOptions(
                    repo_id=config.vision_model_repo_id,
                    prompt=config.vision_model_prompt,
                )
                if config.verbose:
                    self.console.print(f"  -> Using custom vision model: {config.vision_model_repo_id}")
            elif config.verbose:
                self.console.print("  -> Picture description enrichment enabled (default model)")

        # Always enable picture classification unless explicitly disabled
        if config.enable_picture_classification:
            pipeline_options.do_picture_classification = True
            pipeline_options.generate_picture_images = True
            pipeline_options.images_scale = config.vision_model_scale
            if config.verbose:
                self.console.print("  -> Picture classification enrichment enabled (default)")

        # Initialize converter with OCR configuration
        from docling.datamodel.base_models import InputFormat
        from docling.document_converter import PdfFormatOption

        self.converter = DocumentConverter(
            format_options={
                InputFormat.IMAGE: PdfFormatOption(pipeline_options=pipeline_options),
            },
        )

        if config.verbose:
            self.console.print("✅ Image pipeline initialized with advanced Docling OCR")
            self.console.print(f"  -> OCR engine: {config.image_ocr_engine}")
            self.console.print(f"  -> Confidence threshold: {config.image_min_text_confidence}")
            if config.image_force_full_page_ocr:
                self.console.print("  -> Full page OCR enabled")

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
        """Process image chunks using shared base implementation."""

        return self._process_chunks_with_metadata(
            chunks=chunks,
            input_path=input_path,
            file_type='image',
            processing_pipeline='image_ocr_docling',
            additional_metadata={'image_format': input_path.suffix.lower().lstrip('.') , 'ocr_engine': self.config.image_ocr_engine},
        )

    def supports_file(self, file_path: Path) -> bool:
        """Check if this pipeline supports image files."""
        from .factory import supports_file_extension

        return supports_file_extension(file_path, ImagePipeline)
