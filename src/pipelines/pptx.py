"""
PPTX-specific document processing pipeline using Docling.

Implements Microsoft PowerPoint presentation conversion with WordFormatOption and SimplePipeline,
preserving slide structure while applying token-aware chunking strategies.
"""

from datetime import UTC
from pathlib import Path
from typing import Any, ClassVar

from docling.chunking import HierarchicalChunker, HybridChunker
from docling.datamodel.base_models import InputFormat
from docling.document_converter import DocumentConverter, WordFormatOption
from docling.pipeline.simple_pipeline import SimplePipeline
from rich.console import Console

from src.config import Config
from src.utils import get_tokenizer

from .base import BasePipeline


class PptxPipeline(BasePipeline):
    """PPTX document processing pipeline with Docling WordFormatOption."""

    # Memory management thresholds
    LARGE_PRESENTATION_THRESHOLD_MB: ClassVar[int] = (
        15  # Presentations tend to be larger due to media
    )
    LARGE_PRES_MAX_TOKENS: ClassVar[int] = 1024
    CHUNK_BATCH_SIZE: ClassVar[int] = 50

    # Content quality filtering for presentations
    MIN_SLIDE_CONTENT_DENSITY: ClassVar[int] = 2  # words per slide element
    SLIDE_CONTENT_TOKEN_MULTIPLIER: ClassVar[float] = (
        0.8  # Presentations often have less dense text
    )

    # Slide title detection threshold
    MAX_SLIDE_TITLE_LENGTH: ClassVar[int] = 100

    # Presentation complexity analysis thresholds
    HIGH_COMPLEXITY_TEXT_THRESHOLD: ClassVar[int] = 500
    HIGH_COMPLEXITY_MEDIA_THRESHOLD: ClassVar[int] = 10
    LOW_COMPLEXITY_TEXT_THRESHOLD: ClassVar[int] = 100
    LOW_COMPLEXITY_MEDIA_THRESHOLD: ClassVar[int] = 3
    MIN_MEANINGFUL_WORD_COUNT: ClassVar[int] = 10

    def __init__(self, config: Config) -> None:
        """Initialize PPTX pipeline with Docling configuration."""
        super().__init__(config)
        self.console = Console()

        # Get tokenizer using the utils function
        self.tokenizer = get_tokenizer(config)

        # Configure PowerPoint document processing options
        self.word_options = WordFormatOption(
            # Use SimplePipeline for office documents (including PPTX)
            pipeline_cls=SimplePipeline,
        )

        # Initialize Docling converter with Word options (works for PPTX too)
        self.converter = DocumentConverter(
            format_options={
                InputFormat.PPTX: self.word_options,
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

    def process(self, input_path: Path) -> list[dict[str, Any]]:
        """
        Process PPTX presentation with slide-aware memory management and optimization.

        Args:
            input_path: Path to PPTX file

        Returns:
            List of chunk dictionaries with content and metadata

        Raises:
            FileNotFoundError: If PPTX file doesn't exist
            ValueError: If file is not a supported PPTX format

        """
        if not input_path.exists():
            msg = f"PPTX file not found: {input_path}"
            raise FileNotFoundError(msg)

        if not self.supports_file(input_path):
            msg = f"Unsupported file type: {input_path.suffix}"
            raise ValueError(msg)

        # Check file size for memory management (presentations can be large due to media)
        file_size_mb = input_path.stat().st_size / (1024 * 1024)
        is_large_presentation = file_size_mb > self.LARGE_PRESENTATION_THRESHOLD_MB

        self.console.print(
            f"[blue]Processing PPTX: {input_path.name} ({file_size_mb:.1f}MB)[/blue]",
        )

        if is_large_presentation and self.config.verbose:
            self.console.print(
                "  -> [yellow]Large presentation detected, applying memory optimization[/yellow]",
            )

        try:
            # Convert PPTX to DoclingDocument with memory-aware processing
            docling_doc = self._convert_presentation(input_path, is_large_presentation)

            # Process presentation through chunking pipeline with memory optimization
            return self._process_presentation_pipeline(
                docling_doc,
                input_path,
                is_large_presentation,
            )

        except Exception as e:
            # If it's already one of our custom exceptions, re-raise it
            from src.exceptions import LLMarkableError

            if isinstance(e, LLMarkableError):
                self.console.print(
                    f"[red]Error processing PPTX {input_path.name}: {e!s}[/red]",
                )
                raise

            # Otherwise, wrap in a ConversionError
            from src.exceptions import ConversionError

            error = ConversionError(
                f"Unexpected error processing PPTX: {e!s}",
                file_path=str(input_path),
                conversion_stage="unknown",
                original_error=e,
            )
            self.console.print(
                f"[red]Error processing PPTX {input_path.name}: {error!s}[/red]",
            )
            raise error from e

    def _chunk_presentation(self, docling_doc: object) -> list:
        """Apply chunking strategy to presentation document."""
        try:
            chunks = list(self.hybrid_chunker.chunk(docling_doc))
            if self.config.verbose:
                self.console.print(f"  -> HybridChunker produced {len(chunks)} chunks")
            return chunks

        except (AttributeError, TypeError, ValueError) as e:
            if self.config.verbose:
                self.console.print(
                    f"  -> HybridChunker failed ({e!s}), falling back to HierarchicalChunker",
                )

            # Fallback to hierarchical chunker
            try:
                chunks = list(self.hierarchical_chunker.chunk(docling_doc))
                if self.config.verbose:
                    self.console.print(
                        f"  -> HierarchicalChunker produced {len(chunks)} chunks",
                    )
                return chunks

            except Exception as fallback_error:
                from src.exceptions import ChunkingError

                msg = f"Both chunking strategies failed: {e!s}, {fallback_error!s}"
                raise ChunkingError(
                    msg,
                    file_path="unknown",
                    chunking_strategy="hybrid_and_hierarchical",
                    original_error=fallback_error,
                ) from fallback_error

    def _chunks_to_structured(
        self,
        chunks: list,
        input_path: Path,
    ) -> list[dict[str, Any]]:
        """Convert chunks to structured format with metadata."""
        structured_chunks = []

        for i, chunk in enumerate(chunks):
            content = getattr(chunk, "text", "")

            if not content.strip():
                continue

            # Create base metadata
            base_metadata = {
                "source_file": input_path.name,
                "file_type": "pptx",
                "chunk_index": i,
                "processing_timestamp": self._get_timestamp(),
            }

            # Extract PPTX-specific metadata
            metadata = self._extract_pptx_metadata(chunk, base_metadata)

            # Process content for presentations
            processed_content = self._process_slide_content(content)

            structured_chunks.append(
                {
                    "content": processed_content,
                    "metadata": metadata,
                    "token_count": len(self.tokenizer.encode(processed_content)),
                },
            )

        return structured_chunks

    def _extract_pptx_metadata(
        self,
        chunk: object,
        base_metadata: dict,
    ) -> dict[str, Any]:
        """Extract PPTX-specific metadata from chunk."""
        metadata = base_metadata.copy()

        # Extract slide-specific information
        content = getattr(chunk, "text", "")

        # Detect slide boundaries and numbers
        slide_info = self._detect_slide_information(content)
        metadata.update(slide_info)

        # Add presentation-specific metadata
        metadata.update(
            {
                "content_type": "presentation",
                "slide_element_count": content.count("\n") + 1,
                "estimated_reading_time": len(content.split()) // 200,  # ~200 WPM
            },
        )

        return metadata

    def _detect_slide_information(self, content: str) -> dict[str, Any]:
        """Detect slide numbers and boundaries from content."""
        import re

        slide_info = {
            "slide_number": None,
            "estimated_slide_number": 0,
            "is_slide_title": False,
            "has_title": False,
            "has_bullet_points": False,
            "slide_section": None,
            "word_count": len(content.split()),
            "content_density": 0,
        }

        # Look for slide number patterns
        slide_patterns = [
            r"slide\s+(\d+)",
            r"page\s+(\d+)",
            r"^(\d+)\.",  # Number at start of line
        ]

        for pattern in slide_patterns:
            match = re.search(pattern, content.lower())
            if match:
                slide_number = int(match.group(1))
                slide_info["slide_number"] = slide_number
                slide_info["estimated_slide_number"] = slide_number
                break

        # Detect if this looks like a slide title
        lines = content.strip().split("\n")
        if (
            lines
            and len(lines[0]) < self.MAX_SLIDE_TITLE_LENGTH
            and not lines[0].endswith(".")
        ):
            slide_info["is_slide_title"] = True
            slide_info["has_title"] = True

        # Detect bullet points
        bullet_patterns = [r"^\s*[-•▪▫◦‣]\s", r"^\s*\d+\.\s"]
        for pattern in bullet_patterns:
            if re.search(pattern, content, re.MULTILINE):
                slide_info["has_bullet_points"] = True
                break

        # Calculate content density (words per line)
        line_count = max(1, len(lines))
        slide_info["content_density"] = slide_info["word_count"] / line_count

        return slide_info

    def _process_slide_content(self, content: str) -> str:
        """Process and optimize slide content for better readability."""
        # Clean up common presentation artifacts
        content = self._clean_presentation_artifacts(content)

        # Optimize slide boundaries
        content = self._optimize_slide_boundaries(content)

        return content.strip()

    def _clean_presentation_artifacts(self, content: str) -> str:
        """Clean up presentation-specific artifacts and formatting."""
        import re

        # Remove slide transition markers
        content = re.sub(r"\[slide\s+\d+\]", "", content, flags=re.IGNORECASE)

        # Clean up bullet point formatting (using standard bullet characters)
        content = re.sub(r"^[\s]*[•▪▫◦‣-]\s*", "- ", content, flags=re.MULTILINE)

        # Normalize spacing around slide elements
        content = re.sub(r"\n{3,}", "\n\n", content)

        return content

    def _optimize_slide_boundaries(self, content: str) -> str:
        """Optimize slide boundaries for better chunk organization."""
        lines = content.split("\n")
        optimized_lines = []

        for i, line in enumerate(lines):
            # Add extra spacing before slide titles
            if (
                i > 0
                and len(line.strip()) < self.MAX_SLIDE_TITLE_LENGTH
                and not line.strip().endswith(".")
                and line.strip()
                and not line.startswith(" ")
            ):
                optimized_lines.append("")

            optimized_lines.append(line)

        return "\n".join(optimized_lines)

    def _get_timestamp(self) -> str:
        """Get current timestamp for metadata."""
        from datetime import datetime

        return datetime.now(UTC).isoformat()

    def _convert_presentation(
        self,
        input_path: Path,
        is_large_presentation: bool,
    ) -> object:
        """Convert PPTX to DoclingDocument with error handling and memory optimization."""
        try:
            result = self.converter.convert(input_path)
            docling_doc = result.document

            if self.config.verbose:
                self.console.print(
                    f"  -> Converted to DoclingDocument with {len(docling_doc.texts)} text elements",
                )

            # Log presentation characteristics for large files
            if is_large_presentation:
                pres_stats = self._analyze_presentation_complexity(docling_doc)
                self.console.print(f"  -> Presentation stats: {pres_stats}")

            return docling_doc

        except Exception as e:
            from src.exceptions import ConversionError

            msg = f"PPTX conversion failed: {e!s}"
            raise ConversionError(
                msg,
                file_path=str(input_path),
                conversion_stage="document_parsing",
                original_error=e,
            ) from e

    def _process_presentation_pipeline(
        self,
        docling_doc: object,
        input_path: Path,
        is_large_presentation: bool,
    ) -> list[dict[str, Any]]:
        """Process presentation through the complete chunking and filtering pipeline."""
        from src.utils import merge_small_trailing_chunks

        # Apply chunking strategy with memory optimization for large presentations
        chunks = self._chunk_presentation_optimized(docling_doc, is_large_presentation)

        # Convert chunks to structured format with memory management
        structured_chunks = self._chunks_to_structured_optimized(
            chunks,
            input_path,
            is_large_presentation,
        )

        # Apply post-processing based on config
        if self.config.merge_small_trailing_chunks:
            structured_chunks = merge_small_trailing_chunks(
                structured_chunks,
                self.config,
            )

        # Filter out non-useful chunks with enhanced quality checks
        useful_chunks = self._filter_chunks_with_quality_metrics(
            structured_chunks,
            is_large_presentation,
        )

        self.console.print(f"  -> Generated {len(useful_chunks)} useful chunks")

        # Log memory usage for large presentations
        if is_large_presentation and self.config.verbose:
            self._log_processing_stats(useful_chunks)

        return useful_chunks

    def _analyze_presentation_complexity(self, docling_doc: object) -> dict[str, Any]:
        """Analyze presentation complexity for memory optimization decisions."""
        stats = {
            "total_elements": len(getattr(docling_doc, "texts", [])),
            "estimated_slides": 0,
            "has_media": False,
            "complexity_score": "medium",
        }

        # Estimate slide count and media presence
        texts = getattr(docling_doc, "texts", [])
        slide_indicators = 0
        media_indicators = 0

        for text_elem in texts[:100]:  # Sample first 100 elements for performance
            text_content = getattr(text_elem, "text", "").lower()
            if any(indicator in text_content for indicator in ["slide", "page"]):
                slide_indicators += 1
            if any(
                indicator in text_content for indicator in ["image", "chart", "graph"]
            ):
                media_indicators += 1

        stats["estimated_slides"] = max(slide_indicators, len(texts) // 10)
        stats["has_media"] = media_indicators > 0

        # Determine complexity
        if (
            len(texts) > self.HIGH_COMPLEXITY_TEXT_THRESHOLD
            or media_indicators > self.HIGH_COMPLEXITY_MEDIA_THRESHOLD
        ):
            stats["complexity_score"] = "high"
        elif (
            len(texts) < self.LOW_COMPLEXITY_TEXT_THRESHOLD
            and media_indicators < self.LOW_COMPLEXITY_MEDIA_THRESHOLD
        ):
            stats["complexity_score"] = "low"

        return stats

    def _chunk_presentation_optimized(
        self,
        docling_doc: object,
        is_large_presentation: bool,
    ) -> list:
        """Apply chunking strategy with performance optimization for large presentations."""
        # For large presentations, use more aggressive chunking parameters
        if is_large_presentation:
            # Create optimized chunker for large presentations
            large_pres_chunker = HybridChunker(
                tokenizer=self.tokenizer,
                max_tokens=min(
                    self.config.chunk_size,
                    self.LARGE_PRES_MAX_TOKENS,
                ),  # Smaller chunks for large presentations
                merge_peers=False,  # Disable merging to reduce memory usage
            )

            try:
                chunks = list(large_pres_chunker.chunk(docling_doc))

                if self.config.verbose:
                    self.console.print(
                        f"  -> Large presentation chunker produced {len(chunks)} chunks",
                    )

                return chunks

            except (AttributeError, TypeError, ValueError) as large_pres_error:
                if self.config.verbose:
                    self.console.print(
                        f"  -> Large presentation chunker failed ({large_pres_error!s}), falling back to standard chunking",
                    )
                # Fall through to standard chunking

        # Standard chunking process (same as before)
        return self._chunk_presentation(docling_doc)

    def _chunks_to_structured_optimized(
        self,
        chunks: list,
        input_path: Path,
        is_large_presentation: bool,
    ) -> list[dict[str, Any]]:
        """Convert chunks to structured format with memory optimization for large presentations."""
        if is_large_presentation:
            # Process chunks in batches to manage memory
            structured_chunks = []

            for i in range(0, len(chunks), self.CHUNK_BATCH_SIZE):
                batch = chunks[i : i + self.CHUNK_BATCH_SIZE]
                batch_structured = self._process_chunk_batch(batch, input_path, i)
                structured_chunks.extend(batch_structured)

                if self.config.verbose and len(chunks) > self.CHUNK_BATCH_SIZE:
                    progress = min(i + self.CHUNK_BATCH_SIZE, len(chunks))
                    self.console.print(
                        f"  -> Processed {progress}/{len(chunks)} chunks",
                    )

            return structured_chunks
        # Standard processing for smaller presentations
        return self._chunks_to_structured(chunks, input_path)

    def _process_chunk_batch(
        self,
        batch: list,
        input_path: Path,
        start_index: int,
    ) -> list[dict[str, Any]]:
        """Process a batch of chunks with memory management for presentations."""
        structured_batch = []

        for local_i, chunk in enumerate(batch):
            global_i = start_index + local_i

            # Handle both chunk objects and plain text with enhanced metadata extraction
            if hasattr(chunk, "text"):
                text_content = chunk.text
                metadata = getattr(chunk, "meta", {})
                pptx_metadata = self._extract_pptx_metadata(chunk, metadata)
            else:
                text_content = str(chunk)
                metadata = {}
                pptx_metadata = {}

            # Skip empty chunks early
            if not text_content or not text_content.strip():
                continue

            # Process content with minimal memory footprint
            processed_content = self._process_slide_content(text_content)
            optimized_content = self._optimize_slide_boundaries(processed_content)

            structured_chunk = {
                "content": optimized_content.strip(),
                "metadata": {
                    "chunk_index": global_i,
                    "source_file": str(input_path),
                    "file_type": "pptx",
                    "docling_metadata": metadata,
                    "pptx_specific": pptx_metadata,
                    "slide_info": self._detect_slide_information(optimized_content),
                },
            }

            structured_batch.append(structured_chunk)

        return structured_batch

    def _filter_chunks_with_quality_metrics(
        self,
        chunks: list[dict[str, Any]],
        is_large_presentation: bool,
    ) -> list[dict[str, Any]]:
        """Filter chunks with enhanced quality metrics for large presentations."""
        from src.utils import is_chunk_useful

        useful_chunks = []

        for chunk in chunks:
            # Standard usefulness check
            if not is_chunk_useful(chunk, self.config):
                continue

            # Additional quality checks for large presentations
            if is_large_presentation:
                slide_info = chunk["metadata"].get("slide_info", {})

                # Filter out very low-density content in large presentations
                content_density = slide_info.get("content_density", 0)
                if content_density < self.MIN_SLIDE_CONTENT_DENSITY:
                    if self.config.verbose:
                        self.console.print(
                            f"  -> Filtering low-density slide chunk {chunk['metadata']['chunk_index']}",
                        )
                    continue

                # Prefer chunks with meaningful slide structure
                has_structure = any(
                    [
                        slide_info.get("has_title", False),
                        slide_info.get("has_bullet_points", False),
                        slide_info.get("estimated_slide_number", 0) > 0,
                        slide_info.get("word_count", 0)
                        > self.MIN_MEANINGFUL_WORD_COUNT,
                    ],
                )

                # For large presentations, slightly favor structured content
                word_count = slide_info.get("word_count", 0)
                if (
                    word_count
                    < self.config.min_tokens * self.SLIDE_CONTENT_TOKEN_MULTIPLIER
                    and not has_structure
                ):
                    continue

            useful_chunks.append(chunk)

        return useful_chunks

    def _log_processing_stats(self, useful_chunks: list[dict[str, Any]]) -> None:
        """Log processing statistics for large presentations."""
        if not useful_chunks:
            return

        total_slides = len(
            {
                chunk["metadata"].get("slide_info", {}).get("estimated_slide_number", 0)
                for chunk in useful_chunks
            },
        )

        avg_chunk_size = sum(len(chunk["content"]) for chunk in useful_chunks) // len(
            useful_chunks,
        )

        self.console.print(
            f"  -> Stats: ~{total_slides} slides, avg chunk size: {avg_chunk_size} chars",
        )
