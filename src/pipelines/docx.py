"""
DOCX-specific document processing pipeline using Docling.

Implements Microsoft Word document conversion with WordFormatOption and SimplePipeline,
preserving document structure while applying token-aware chunking strategies.
"""

from pathlib import Path
from typing import Any, ClassVar

from docling.chunking import HierarchicalChunker, HybridChunker
from docling.datamodel.base_models import InputFormat
from docling.document_converter import DocumentConverter, WordFormatOption
from docling.pipeline.simple_pipeline import SimplePipeline
from rich.console import Console

from src.config import Config
from src.utils import get_tokenizer, is_chunk_useful, merge_small_trailing_chunks

from .base import BasePipeline


class DocxPipeline(BasePipeline):
    """DOCX document processing pipeline with Docling WordFormatOption."""

    # Memory management thresholds
    LARGE_DOCUMENT_THRESHOLD_MB: ClassVar[int] = 10
    LARGE_DOC_MAX_TOKENS: ClassVar[int] = 1024
    CHUNK_BATCH_SIZE: ClassVar[int] = 50

    # Content quality filtering
    MIN_CONTENT_DENSITY: ClassVar[int] = 3  # words per paragraph
    STRUCTURED_CONTENT_TOKEN_MULTIPLIER: ClassVar[float] = 0.75

    # Table analysis thresholds
    COMPLEX_TABLE_MIN_ROWS: ClassVar[int] = 10
    COMPLEX_TABLE_MIN_COLS: ClassVar[int] = 5

    def __init__(self, config: Config) -> None:
        """Initialize DOCX pipeline with Docling configuration."""
        super().__init__(config)
        self.console = Console()

        # Get tokenizer using the utils function
        self.tokenizer = get_tokenizer(config)

        # Configure Word document processing options
        self.word_options = WordFormatOption(
            # Use SimplePipeline for office documents
            pipeline_cls=SimplePipeline,
        )

        # Initialize Docling converter with Word options
        self.converter = DocumentConverter(
            format_options={
                InputFormat.DOCX: self.word_options,
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
        Process DOCX document with advanced memory management and performance optimization.

        Args:
            input_path: Path to DOCX file

        Returns:
            List of chunk dictionaries with content and metadata

        Raises:
            FileNotFoundError: If DOCX file doesn't exist
            ValueError: If file is not a supported DOCX format

        """
        self._validate_input(input_path)

        # Check file size for memory management
        file_size_mb = input_path.stat().st_size / (1024 * 1024)
        is_large_document = file_size_mb > self.LARGE_DOCUMENT_THRESHOLD_MB

        self._log_processing_start(input_path, file_size_mb, is_large_document)

        try:
            # Convert DOCX to DoclingDocument with memory-aware processing
            docling_doc = self._convert_document(input_path, is_large_document)

            # Process document through chunking pipeline
            return self._process_document_pipeline(
                docling_doc,
                input_path,
                is_large_document,
            )

        except Exception as e:
            self._handle_processing_error(e, input_path)
            raise  # This will never be reached due to _handle_processing_error raising

    def _validate_input(self, input_path: Path) -> None:
        """Validate input file exists and is supported format."""
        if not input_path.exists():
            msg = f"DOCX file not found: {input_path}"
            raise FileNotFoundError(msg)

        if not self.supports_file(input_path):
            msg = f"Unsupported file type: {input_path.suffix}"
            raise ValueError(msg)

    def _log_processing_start(
        self,
        input_path: Path,
        file_size_mb: float,
        is_large_document: bool,
    ) -> None:
        """Log processing start information."""
        self.console.print(
            f"[blue]Processing DOCX: {input_path.name} ({file_size_mb:.1f}MB)[/blue]",
        )

        if is_large_document and self.config.verbose:
            self.console.print(
                "  -> [yellow]Large document detected, applying memory optimization[/yellow]",
            )

    def _convert_document(self, input_path: Path, is_large_document: bool) -> object:
        """Convert DOCX to DoclingDocument with error handling."""
        try:
            result = self.converter.convert(input_path)
            docling_doc = result.document

            if self.config.verbose:
                self.console.print(
                    f"  -> Converted to DoclingDocument with {len(docling_doc.texts)} text elements",
                )

            # Log document characteristics for large files
            if is_large_document:
                doc_stats = self._analyze_document_complexity(docling_doc)
                self.console.print(f"  -> Document stats: {doc_stats}")

            return docling_doc

        except Exception as e:
            from src.exceptions import ConversionError

            msg = f"DOCX conversion failed: {e!s}"
            raise ConversionError(
                msg,
                file_path=str(input_path),
                conversion_stage="document_parsing",
                original_error=e,
            ) from e

    def _process_document_pipeline(
        self,
        docling_doc: object,
        input_path: Path,
        is_large_document: bool,
    ) -> list[dict[str, Any]]:
        """Process document through the complete chunking and filtering pipeline."""
        # Apply chunking strategy with memory optimization for large documents
        chunks = self._chunk_document_optimized(docling_doc, is_large_document)

        # Convert chunks to structured format with memory management
        structured_chunks = self._chunks_to_structured_optimized(
            chunks,
            input_path,
            is_large_document,
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
            is_large_document,
        )

        self.console.print(f"  -> Generated {len(useful_chunks)} useful chunks")

        # Log memory usage for large documents
        if is_large_document and self.config.verbose:
            self._log_processing_stats(useful_chunks)

        return useful_chunks

    def _log_processing_stats(self, useful_chunks: list[dict[str, Any]]) -> None:
        """Log processing statistics for large documents."""
        avg_chunk_size = (
            sum(len(chunk["content"]) for chunk in useful_chunks) / len(useful_chunks)
            if useful_chunks
            else 0
        )
        self.console.print(
            f"  -> Average chunk size: {avg_chunk_size:.0f} characters",
        )

    def _handle_processing_error(self, error: Exception, input_path: Path) -> None:
        """Handle processing errors with appropriate exception wrapping."""
        # If it's already one of our custom exceptions, re-raise it
        from src.exceptions import LLMarkableError

        if isinstance(error, LLMarkableError):
            self.console.print(
                f"[red]Error processing DOCX {input_path.name}: {error!s}[/red]",
            )
            raise error

        # Otherwise, wrap in a ConversionError
        from src.exceptions import ConversionError

        wrapped_error = ConversionError(
            f"Unexpected error processing DOCX: {error!s}",
            file_path=str(input_path),
            conversion_stage="unknown",
            original_error=error,
        )
        self.console.print(
            f"[red]Error processing DOCX {input_path.name}: {wrapped_error!s}[/red]",
        )
        raise wrapped_error from error

    def _analyze_document_complexity(self, docling_doc: object) -> dict[str, Any]:
        """Analyze document complexity for performance optimization."""
        stats = {
            "text_elements": len(getattr(docling_doc, "texts", [])),
            "total_length": 0,
            "has_tables": False,
            "has_images": False,
        }

        # Calculate total content length and detect complex elements
        if hasattr(docling_doc, "texts"):
            for text_elem in docling_doc.texts:
                if hasattr(text_elem, "text"):
                    stats["total_length"] += len(text_elem.text)

        # Check for tables and images
        if hasattr(docling_doc, "tables"):
            stats["has_tables"] = len(docling_doc.tables) > 0
            stats["table_count"] = len(docling_doc.tables)

        if hasattr(docling_doc, "pictures"):
            stats["has_images"] = len(docling_doc.pictures) > 0
            stats["image_count"] = len(docling_doc.pictures)

        return stats

    def _chunk_document_optimized(
        self,
        docling_doc: object,
        is_large_document: bool,
    ) -> list:
        """Apply chunking strategy with performance optimization for large documents."""
        # For large documents, use more aggressive chunking parameters
        if is_large_document:
            # Create optimized chunker for large documents
            large_doc_chunker = HybridChunker(
                tokenizer=self.tokenizer,
                max_tokens=min(
                    self.config.chunk_size,
                    self.LARGE_DOC_MAX_TOKENS,
                ),  # Smaller chunks for large docs
                merge_peers=False,  # Disable merging to reduce memory usage
            )

            try:
                chunks = list(large_doc_chunker.chunk(docling_doc))

                if self.config.verbose:
                    self.console.print(
                        f"  -> Large document chunker produced {len(chunks)} chunks",
                    )

                return chunks

            except (AttributeError, TypeError, ValueError) as large_doc_error:
                if self.config.verbose:
                    self.console.print(
                        f"  -> Large document chunker failed ({large_doc_error!s}), falling back to standard chunking",
                    )
                # Fall through to standard chunking

        # Standard chunking process (same as before)
        return self._chunk_document(docling_doc)

    def _chunks_to_structured_optimized(
        self,
        chunks: list,
        input_path: Path,
        is_large_document: bool,
    ) -> list[dict[str, Any]]:
        """Convert chunks to structured format with memory optimization for large documents."""
        if is_large_document:
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
        # Standard processing for smaller documents
        return self._chunks_to_structured(chunks, input_path)

    def _process_chunk_batch(
        self,
        batch: list,
        input_path: Path,
        start_index: int,
    ) -> list[dict[str, Any]]:
        """Process a batch of chunks with memory management."""
        structured_batch = []

        for local_i, chunk in enumerate(batch):
            global_i = start_index + local_i

            # Handle both chunk objects and plain text with enhanced metadata extraction
            if hasattr(chunk, "text"):
                text_content = chunk.text
                metadata = getattr(chunk, "meta", {})
                docx_metadata = self._extract_docx_metadata(chunk, metadata)
            else:
                text_content = str(chunk)
                metadata = {}
                docx_metadata = {}

            # Skip empty chunks early
            if not text_content or not text_content.strip():
                continue

            # Process content with minimal memory footprint
            processed_content = self._process_embedded_content(text_content)
            optimized_content = self._optimize_paragraph_boundaries(processed_content)

            structured_chunk = {
                "content": optimized_content.strip(),
                "metadata": {
                    "chunk_index": global_i,
                    "source_file": str(input_path),
                    "file_type": "docx",
                    "docling_metadata": metadata,
                    "docx_specific": docx_metadata,
                    "content_stats": self._analyze_content_structure(optimized_content),
                },
            }

            structured_batch.append(structured_chunk)

        return structured_batch

    def _filter_chunks_with_quality_metrics(
        self,
        chunks: list[dict[str, Any]],
        is_large_document: bool,
    ) -> list[dict[str, Any]]:
        """Filter chunks with enhanced quality metrics for large documents."""
        useful_chunks = []

        for chunk in chunks:
            # Standard usefulness check
            if not is_chunk_useful(chunk, self.config):
                continue

            # Additional quality checks for large documents
            if is_large_document:
                content_stats = chunk["metadata"].get("content_stats", {})

                # Filter out very low-density content in large documents
                density = content_stats.get("content_density", 0)
                if density < self.MIN_CONTENT_DENSITY:
                    if self.config.verbose:
                        self.console.print(
                            f"  -> Filtering low-density chunk {chunk['metadata']['chunk_index']}",
                        )
                    continue

                # Prefer chunks with meaningful structure
                has_structure = any(
                    [
                        content_stats.get("has_headings", False),
                        content_stats.get("has_lists", False),
                        content_stats.get("has_tables", False),
                        content_stats.get("paragraph_count", 0) > 1,
                    ],
                )

                # For large documents, slightly favor structured content
                word_count = content_stats.get("word_count", 0)
                if (
                    word_count
                    < self.config.min_tokens * self.STRUCTURED_CONTENT_TOKEN_MULTIPLIER
                    and not has_structure
                ):
                    continue

            useful_chunks.append(chunk)

        return useful_chunks

    def _chunk_document(self, docling_doc: object) -> list:
        """Apply chunking strategy with HybridChunker and hierarchical fallback."""
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
        """Convert raw chunks to structured format with enhanced metadata and memory optimization."""
        structured_chunks = []

        for i, chunk in enumerate(chunks):
            # Handle both chunk objects and plain text with enhanced metadata extraction
            if hasattr(chunk, "text"):
                text_content = chunk.text
                metadata = getattr(chunk, "meta", {})

                # Extract additional DOCX-specific metadata
                docx_metadata = self._extract_docx_metadata(chunk, metadata)
            else:
                text_content = str(chunk)
                metadata = {}
                docx_metadata = {}

            # Skip empty chunks early
            if not text_content or not text_content.strip():
                if self.config.verbose:
                    self.console.print(f"  -> Skipping empty chunk {i}")
                continue

            # Process embedded images and extract alt text
            processed_content = self._process_embedded_content(text_content)

            # Optimize memory by ensuring proper paragraph boundaries
            optimized_content = self._optimize_paragraph_boundaries(processed_content)

            # Create structured chunk with comprehensive metadata
            structured_chunk = {
                "content": optimized_content.strip(),
                "metadata": {
                    "chunk_index": i,
                    "source_file": str(input_path),
                    "file_type": "docx",
                    "docling_metadata": metadata,
                    "docx_specific": docx_metadata,
                    "content_stats": self._analyze_content_structure(optimized_content),
                },
            }

            structured_chunks.append(structured_chunk)

        return structured_chunks

    def _extract_docx_metadata(
        self,
        chunk: object,
    ) -> dict[str, Any]:
        """Extract DOCX-specific metadata from chunk objects."""
        docx_metadata = {}

        # Extract heading levels and section information
        if hasattr(chunk, "prov"):
            prov_data = chunk.prov
            if hasattr(prov_data, "__iter__"):
                for prov in prov_data:
                    if hasattr(prov, "page_no"):
                        docx_metadata["page_number"] = prov.page_no
                    if hasattr(prov, "section_header"):
                        docx_metadata["section_header"] = prov.section_header

        # Extract formatting information
        if hasattr(chunk, "label"):
            docx_metadata["element_type"] = chunk.label

        # Extract table information if present
        if "table" in str(getattr(chunk, "label", "")).lower():
            docx_metadata["contains_table"] = True
            docx_metadata["table_analysis"] = self._analyze_table_content(chunk.text)

        return docx_metadata

    def _process_embedded_content(self, content: str) -> str:
        """Process embedded images and extract alt text for accessibility."""
        import re

        # Pattern to identify image references or alt text in DOCX content
        image_pattern = r"\[Image:([^\]]+)\]"
        alt_text_pattern = r'alt="([^"]*)"'

        # Replace image references with descriptive text
        content = re.sub(
            image_pattern,
            r"[Image: \1]",
            content,
            flags=re.IGNORECASE,
        )

        # Extract and format alt text
        content = re.sub(
            alt_text_pattern,
            r"(Image description: \1)",
            content,
            flags=re.IGNORECASE,
        )

        return content

    def _optimize_paragraph_boundaries(self, content: str) -> str:
        """Optimize paragraph boundaries to maintain proper document structure."""
        import re

        # Ensure proper paragraph separation
        content = re.sub(r"\n\s*\n\s*\n+", "\n\n", content)

        # Maintain list formatting
        content = re.sub(r"\n(\s*[•\-\*]\s)", r"\n\n\1", content)

        # Preserve section breaks
        content = re.sub(r"\n(#{1,6}\s)", r"\n\n\1", content)

        return content.strip()

    def _analyze_content_structure(self, content: str) -> dict[str, Any]:
        """Analyze content structure for quality metrics."""
        import re

        # Count various content elements
        word_count = len(content.split())
        sentence_count = len(re.findall(r"[.!?]+", content))
        paragraph_count = len([p for p in content.split("\n\n") if p.strip()])

        # Detect content types
        has_lists = bool(re.search(r"^\s*[•\-\*]\s", content, re.MULTILINE))
        has_headings = bool(re.search(r"^#{1,6}\s", content, re.MULTILINE))
        has_tables = "table" in content.lower() or "|" in content

        return {
            "word_count": word_count,
            "sentence_count": sentence_count,
            "paragraph_count": paragraph_count,
            "has_lists": has_lists,
            "has_headings": has_headings,
            "has_tables": has_tables,
            "content_density": word_count / max(paragraph_count, 1),
        }

    def _analyze_table_content(self, content: str) -> dict[str, Any]:
        """Analyze table structure and content for better processing."""
        # Basic table analysis
        pipe_count = content.count("|")
        row_count = len([line for line in content.split("\n") if "|" in line])

        # Estimate column count
        if row_count > 0:
            sample_row = next((line for line in content.split("\n") if "|" in line), "")
            col_count = sample_row.count("|") + 1
        else:
            col_count = 0

        return {
            "estimated_rows": row_count,
            "estimated_columns": col_count,
            "pipe_separators": pipe_count,
            "is_complex_table": (
                row_count > self.COMPLEX_TABLE_MIN_ROWS
                or col_count > self.COMPLEX_TABLE_MIN_COLS
            ),
        }
