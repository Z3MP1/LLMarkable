"""
Image-specific document processing pipeline using Docling OCR.

Implements image file conversion with OCR text extraction using Docling's
InputFormat.IMAGE, preserving text content while applying token-aware chunking strategies.
"""

from pathlib import Path
from typing import Any, ClassVar

from docling.chunking import HierarchicalChunker, HybridChunker
from docling.datamodel.base_models import InputFormat
from docling.document_converter import DocumentConverter
from rich.console import Console

from src.config import Config
from src.utils import get_tokenizer, is_chunk_useful, merge_small_trailing_chunks

from .base import BasePipeline


class ImagePipeline(BasePipeline):
    """Image document processing pipeline with Docling OCR integration."""

    # Multiple format support - Images support various extensions
    supported_extensions: ClassVar[list[str]] = [
        ".png",
        ".jpg",
        ".jpeg",
        ".tiff",
        ".tif",
        ".bmp",
        ".gif",
    ]

    # Memory management thresholds for large images
    LARGE_IMAGE_THRESHOLD_MB: ClassVar[int] = 25  # Images can be very large
    MAX_IMAGE_DIMENSION: ClassVar[int] = 4096  # Max width/height for processing

    # OCR quality filtering
    MIN_OCR_CONFIDENCE: ClassVar[float] = 0.3  # Minimum OCR confidence threshold
    MIN_TEXT_LENGTH: ClassVar[int] = 10  # Minimum extracted text length

    # Content processing thresholds
    MIN_MEANINGFUL_WORDS: ClassVar[int] = 3  # Minimum words for meaningful content
    OCR_CHUNK_MIN_TOKENS: ClassVar[int] = 50  # Minimum tokens for OCR chunks

    # Text quality analysis constants
    MIN_WORD_LENGTH: ClassVar[int] = 2  # Minimum meaningful word length
    MAX_WORD_LENGTH: ClassVar[int] = 15  # Maximum reasonable word length
    MIN_ALPHA_RATIO: ClassVar[float] = 0.5  # Minimum alphabetic character ratio

    def __init__(self, config: Config) -> None:
        """Initialize Image pipeline with Docling OCR configuration."""
        super().__init__(config)
        self.console = Console()

        # Get tokenizer using the utils function
        self.tokenizer = get_tokenizer(config)

        # Initialize Docling converter with IMAGE format support
        # Note: Docling handles OCR configuration internally for images
        self.converter = DocumentConverter(
            allowed_formats=[InputFormat.IMAGE],
        )

        # Initialize chunkers with config-driven parameters
        self.hybrid_chunker = HybridChunker(
            tokenizer=self.tokenizer,
            max_tokens=config.chunk_size,
            merge_peers=True,  # Merge adjacent chunks with same metadata
        )

        # Fallback chunker for cases where HybridChunker fails
        self.hierarchical_chunker = HierarchicalChunker()

    def supports_file(self, file_path: Path) -> bool:
        """Override to support multiple image extensions."""
        return file_path.suffix.lower() in self.supported_extensions

    def process(self, input_path: Path) -> list[dict[str, Any]]:
        """
        Process image file with OCR and return structured chunks.

        Args:
            input_path: Path to image file

        Returns:
            List of chunk dictionaries with content and metadata

        Raises:
            FileNotFoundError: If image file doesn't exist
            ValueError: If file is not a supported image format

        """
        self._validate_input(input_path)

        # Check file size for memory management
        file_size_mb = input_path.stat().st_size / (1024 * 1024)
        is_large_image = file_size_mb > self.LARGE_IMAGE_THRESHOLD_MB

        self._log_processing_start(input_path, file_size_mb, is_large_image)

        try:
            # Validate image integrity before processing
            self._validate_image_integrity(input_path)

            # Convert image to DoclingDocument with OCR
            docling_doc = self._convert_image_with_ocr(input_path, is_large_image)

            # Process document through chunking pipeline
            return self._process_image_pipeline(
                docling_doc,
                input_path,
                is_large_image,
            )

        except Exception as e:
            self._handle_processing_error(e, input_path)
            raise  # This will never be reached due to _handle_processing_error raising

    def _validate_input(self, input_path: Path) -> None:
        """Validate input file exists and is supported format."""
        if not input_path.exists():
            msg = f"Image file not found: {input_path}"
            raise FileNotFoundError(msg)

        if not self.supports_file(input_path):
            msg = f"Unsupported image format: {input_path.suffix}"
            raise ValueError(msg)

    def _validate_image_integrity(self, input_path: Path) -> None:
        """Validate image file integrity using PIL."""
        try:
            from PIL import Image

            with Image.open(input_path) as img:
                # Verify image can be opened and read
                img.verify()

                # Check image dimensions for processing feasibility
                if hasattr(img, "size") and self.config.verbose:
                    width, height = img.size
                    if (
                        width > self.MAX_IMAGE_DIMENSION
                        or height > self.MAX_IMAGE_DIMENSION
                    ):
                        self.console.print(
                            f"  -> [yellow]Large image dimensions: {width}x{height}[/yellow]",
                        )

        except ImportError:
            # PIL not available - skip integrity check
            if self.config.verbose:
                self.console.print(
                    "  -> [yellow]PIL not available, skipping image integrity check[/yellow]",
                )
        except Exception as e:
            from src.exceptions import ValidationError

            msg = f"Invalid or corrupted image file: {e!s}"
            raise ValidationError(
                msg,
                field_name="input_file",
                field_value=str(input_path),
            ) from e

    def _log_processing_start(
        self,
        input_path: Path,
        file_size_mb: float,
        is_large_image: bool,
    ) -> None:
        """Log processing start information."""
        self.console.print(
            f"[blue]Processing Image: {input_path.name} ({file_size_mb:.1f}MB)[/blue]",
        )

        if is_large_image and self.config.verbose:
            self.console.print(
                "  -> [yellow]Large image detected, applying memory optimization[/yellow]",
            )

    def _convert_image_with_ocr(
        self,
        input_path: Path,
        is_large_image: bool,
    ) -> object:
        """Convert image to DoclingDocument with OCR processing."""
        try:
            # Docling automatically applies OCR for image files
            result = self.converter.convert(input_path)
            docling_doc = result.document

            if self.config.verbose:
                text_elements = getattr(docling_doc, "texts", [])
                self.console.print(
                    f"  -> OCR extracted {len(text_elements)} text elements",
                )

            # Analyze OCR quality for large images
            if is_large_image:
                ocr_stats = self._analyze_ocr_quality(docling_doc)
                if self.config.verbose:
                    self.console.print(f"  -> OCR quality stats: {ocr_stats}")

            return docling_doc

        except Exception as e:
            from src.exceptions import ConversionError

            msg = f"Image OCR processing failed: {e!s}"
            raise ConversionError(
                msg,
                file_path=str(input_path),
                conversion_stage="ocr_processing",
                original_error=e,
            ) from e

    def _analyze_ocr_quality(self, docling_doc: object) -> dict[str, Any]:
        """Analyze OCR quality and extracted content characteristics."""
        stats = {
            "text_elements": 0,
            "total_text_length": 0,
            "estimated_confidence": "unknown",
            "has_meaningful_text": False,
        }

        # Analyze extracted text elements
        if hasattr(docling_doc, "texts"):
            texts = docling_doc.texts
            stats["text_elements"] = len(texts)

            total_length = 0
            meaningful_words = 0

            for text_elem in texts:
                if hasattr(text_elem, "text"):
                    text_content = text_elem.text
                    total_length += len(text_content)

                    # Count meaningful words (basic heuristic)
                    words = text_content.split()
                    meaningful_words += len(
                        [w for w in words if len(w) > self.MIN_WORD_LENGTH],
                    )

            stats["total_text_length"] = total_length
            stats["has_meaningful_text"] = meaningful_words >= self.MIN_MEANINGFUL_WORDS

            # Estimate confidence based on text characteristics
            if (
                total_length > self.MIN_TEXT_LENGTH
                and meaningful_words >= self.MIN_MEANINGFUL_WORDS
            ):
                stats["estimated_confidence"] = "good"
            elif total_length > 0:
                stats["estimated_confidence"] = "low"
            else:
                stats["estimated_confidence"] = "none"

        return stats

    def _process_image_pipeline(
        self,
        docling_doc: object,
        input_path: Path,
        is_large_image: bool,
    ) -> list[dict[str, Any]]:
        """Process image document through the complete chunking and filtering pipeline."""
        # Apply chunking strategy
        chunks = self._chunk_ocr_content(docling_doc)

        # Convert chunks to structured format
        structured_chunks = self._chunks_to_structured(chunks, input_path)

        # Apply post-processing based on config
        if self.config.merge_small_trailing_chunks:
            structured_chunks = merge_small_trailing_chunks(
                structured_chunks,
                self.config,
            )

        # Filter out non-useful chunks with OCR-specific quality checks
        useful_chunks = self._filter_ocr_chunks(structured_chunks, is_large_image)

        self.console.print(f"  -> Generated {len(useful_chunks)} useful chunks")

        return useful_chunks

    def _chunk_ocr_content(self, docling_doc: object) -> list:
        """Apply chunking strategy to OCR-extracted content."""
        from src.exceptions import ChunkingError

        # Try HybridChunker first (preferred for token-aware chunking)
        try:
            chunks = list(self.hybrid_chunker.chunk(docling_doc))

            if self.config.verbose:
                self.console.print(f"  -> HybridChunker produced {len(chunks)} chunks")

            return chunks

        except (AttributeError, TypeError, ValueError) as hybrid_error:
            if self.config.verbose:
                self.console.print(
                    f"  -> 🔄 Fallback: HybridChunker failed ({hybrid_error!s}), trying HierarchicalChunker",
                )

            # Fallback to HierarchicalChunker
            try:
                chunks = list(self.hierarchical_chunker.chunk(docling_doc))

                if self.config.verbose:
                    self.console.print(
                        f"  -> ✅ HierarchicalChunker produced {len(chunks)} chunks",
                    )

                return chunks

            except Exception as fallback_error:
                # Both chunkers failed - this is a critical error
                msg = f"All chunking strategies failed. HybridChunker: {hybrid_error!s}, HierarchicalChunker: {fallback_error!s}"
                raise ChunkingError(
                    msg,
                    chunker_type="fallback_chain",
                    original_error=fallback_error,
                ) from fallback_error

    def _chunks_to_structured(
        self,
        chunks: list,
        input_path: Path,
    ) -> list[dict[str, Any]]:
        """Convert OCR chunks to structured format with image-specific metadata."""
        structured_chunks = []

        for i, chunk in enumerate(chunks):
            # Handle both chunk objects and plain text
            if hasattr(chunk, "text"):
                text_content = chunk.text
                metadata = getattr(chunk, "meta", {})
            else:
                text_content = str(chunk)
                metadata = {}

            # Skip empty chunks early
            if not text_content or not text_content.strip():
                if self.config.verbose:
                    self.console.print(f"  -> Skipping empty OCR chunk {i}")
                continue

            # Clean and process OCR text
            processed_content = self._clean_ocr_text(text_content)

            # Create structured chunk with image-specific metadata
            structured_chunk = {
                "content": processed_content.strip(),
                "metadata": {
                    "chunk_index": i,
                    "source_file": str(input_path),
                    "file_type": "image",
                    "processing_method": "ocr",
                    "docling_metadata": metadata,
                    "image_specific": self._extract_image_metadata(
                        input_path,
                        processed_content,
                    ),
                },
            }

            structured_chunks.append(structured_chunk)

        return structured_chunks

    def _clean_ocr_text(self, text: str) -> str:
        """Clean and normalize OCR-extracted text."""
        import re

        # Remove excessive whitespace
        text = re.sub(r"\s+", " ", text)

        # Remove common OCR artifacts
        text = re.sub(r"[^\w\s\.\,\!\?\;\:\-\(\)\[\]\"\'\/]", "", text)

        # Fix common OCR character substitutions
        ocr_fixes = {
            "0": "O",  # Zero to letter O in some contexts
            "1": "l",  # One to lowercase L in some contexts
            "5": "S",  # Five to letter S in some contexts
        }

        # Apply fixes only if they make sense in context (basic heuristic)
        for wrong, correct in ocr_fixes.items():
            # Only fix if surrounded by letters
            text = re.sub(rf"(?<=[a-zA-Z]){wrong}(?=[a-zA-Z])", correct, text)

        return text.strip()

    def _extract_image_metadata(self, input_path: Path, content: str) -> dict[str, Any]:
        """Extract image-specific metadata."""
        metadata = {
            "image_format": input_path.suffix.lower().lstrip("."),
            "content_length": len(content),
            "word_count": len(content.split()),
            "estimated_ocr_quality": self._estimate_content_quality(content),
        }

        # Try to get image dimensions if PIL is available
        try:
            from PIL import Image

            with Image.open(input_path) as img:
                metadata["image_dimensions"] = {
                    "width": img.width,
                    "height": img.height,
                }
                metadata["image_mode"] = img.mode

        except ImportError:
            # PIL not available
            pass
        except (OSError, ValueError):
            # Image processing failed
            metadata["image_dimensions"] = "unknown"

        return metadata

    def _estimate_content_quality(self, content: str) -> str:
        """Estimate OCR content quality based on text characteristics."""
        if not content.strip():
            return "empty"

        words = content.split()
        if len(words) < self.MIN_MEANINGFUL_WORDS:
            return "low"

            # Check for reasonable word length distribution
        avg_word_length = sum(len(word) for word in words) / len(words)
        if (
            avg_word_length < self.MIN_WORD_LENGTH
            or avg_word_length > self.MAX_WORD_LENGTH
        ):
            return "low"

        # Check for reasonable character distribution
        alpha_ratio = sum(1 for c in content if c.isalpha()) / len(content)
        if alpha_ratio < self.MIN_ALPHA_RATIO:
            return "low"

        return "good"

    def _filter_ocr_chunks(
        self,
        chunks: list[dict[str, Any]],
        is_large_image: bool,
    ) -> list[dict[str, Any]]:
        """Filter chunks with OCR-specific quality metrics."""
        useful_chunks = []

        for chunk in chunks:
            # Standard usefulness check
            if not is_chunk_useful(chunk, self.config):
                continue

            # Additional OCR-specific quality checks
            image_metadata = chunk["metadata"].get("image_specific", {})
            ocr_quality = image_metadata.get("estimated_ocr_quality", "unknown")

            # Filter out very low quality OCR content
            if ocr_quality == "empty":
                if self.config.verbose:
                    self.console.print(
                        f"  -> Filtering empty OCR chunk {chunk['metadata']['chunk_index']}",
                    )
                continue

            # For large images, be more selective about low quality content
            if is_large_image and ocr_quality == "low":
                word_count = image_metadata.get("word_count", 0)
                if word_count < self.MIN_MEANINGFUL_WORDS:
                    if self.config.verbose:
                        self.console.print(
                            f"  -> Filtering low-quality OCR chunk {chunk['metadata']['chunk_index']}",
                        )
                    continue

            useful_chunks.append(chunk)

        return useful_chunks

    def _handle_processing_error(self, error: Exception, input_path: Path) -> None:
        """Handle processing errors with appropriate exception wrapping."""
        # If it's already one of our custom exceptions, re-raise it
        from src.exceptions import LLMarkableError

        if isinstance(error, LLMarkableError):
            self.console.print(
                f"[red]Error processing image {input_path.name}: {error!s}[/red]",
            )
            raise error

        # Otherwise, wrap in a ConversionError
        from src.exceptions import ConversionError

        wrapped_error = ConversionError(
            f"Unexpected error processing image: {error!s}",
            file_path=str(input_path),
            conversion_stage="unknown",
            original_error=error,
        )
        self.console.print(
            f"[red]Error processing image {input_path.name}: {wrapped_error!s}[/red]",
        )
        raise wrapped_error from error
