"""
Base abstract class for document conversion pipelines.

Provides common interface for PDF, HTML, and other format-specific pipelines.
"""

import asyncio
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

# Common imports used by all pipelines - consolidated here for DRY principle
from docling_core.transforms.chunker.base import BaseChunk
from docling_core.transforms.chunker.hierarchical_chunker import HierarchicalChunker
from docling_core.transforms.chunker.hybrid_chunker import HybridChunker
from docling_core.types.doc.document import DoclingDocument
from rich.console import Console

from src.config import Config
from src.synthesis.engine import ContentSynthesizer
from src.synthesis.providers.factory import ProviderFactory
from src.utils import (
    extract_text_content,
    get_tokenizer,
    is_chunk_useful,
    merge_small_trailing_chunks,
)


class BasePipeline(ABC):
    """Abstract base class for document conversion pipelines."""

    def __init__(self, config: Config) -> None:
        """Initialize pipeline with configuration."""
        self.config = config

        # Common initialization for all pipelines
        self.console = Console()
        self.tokenizer = get_tokenizer(config)

    @abstractmethod
    def process(self, input_path: Path) -> list[dict[str, Any]]:
        """
        Process a document file and return structured chunks with metadata.

        Args:
            input_path: Path to the input document file

        Returns:
            List of structured chunks with metadata

        Raises:
            FileAccessError: If the input file cannot be read
            ProcessingError: If document processing fails
            ChunkingError: If chunking fails

        """

    def _chunk_document_with_fallback(
        self,
        docling_doc: DoclingDocument,
        hybrid_chunker: HybridChunker,
        hierarchical_chunker: HierarchicalChunker,
        format_name: str = "document",
    ) -> list[BaseChunk]:
        """
        Shared chunking logic with HybridChunker and HierarchicalChunker fallback.

        This method implements the common chunking pattern used across all pipelines,
        promoting DRY principle while maintaining robustness.

        Args:
            docling_doc: Docling document object
            hybrid_chunker: Configured HybridChunker instance
            hierarchical_chunker: Configured HierarchicalChunker instance
            format_name: Format name for logging (e.g., "PDF", "HTML")

        Returns:
            List of BaseChunk objects

        Raises:
            ChunkingError: If both chunking strategies fail

        """
        try:
            # Try HybridChunker first - optimal for most documents
            chunks = list(hybrid_chunker.chunk(dl_doc=docling_doc))
        except Exception as err:  # noqa: BLE001
            if self.config.verbose:
                self.console.print(
                    f"  -> ⚠️ HybridChunker failed ({err}), falling back to HierarchicalChunker",
                )

            try:
                chunks = list(hierarchical_chunker.chunk(docling_doc))
            except Exception as fallback_err:
                from src.exceptions import ChunkingError

                msg = (
                    f"Both chunking strategies failed for {format_name}. "
                    f"HybridChunker: {err}, HierarchicalChunker: {fallback_err}"
                )
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

    def _process_chunks_with_metadata(
        self,
        chunks: list[BaseChunk],
        input_path: Path,
        file_type: str,
        processing_pipeline: str,
        additional_metadata: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Shared chunk processing logic with configurable metadata.

        This method implements the common chunk processing pattern used across all pipelines,
        promoting DRY principle while allowing format-specific metadata customization.

        Args:
            chunks: List of BaseChunk objects from chunker
            input_path: Original file path for metadata
            file_type: Type of file being processed (e.g., "pdf", "html", "docx")
            processing_pipeline: Name of the processing pipeline
            additional_metadata: Optional additional metadata to include

        Returns:
            List of processed chunks with rich metadata

        """
        processed_chunks: list[dict[str, Any]] = []

        # Create base metadata with common fields
        base_metadata = {
            "source_file": input_path.name,
            "file_type": file_type,
            "processing_pipeline": processing_pipeline,
        }

        # Add any additional metadata passed by the specific pipeline
        if additional_metadata:
            base_metadata.update(additional_metadata)

        for i, chunk in enumerate(chunks):
            # Extract text content
            content = extract_text_content(chunk)

            # Apply content filtering with shared logic
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

        # Apply trailing chunk consolidation with shared logic
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

    @abstractmethod
    def _chunk_document(self, docling_doc: DoclingDocument) -> list[BaseChunk]:
        """
        Chunk a document using format-specific chunking strategy.

        Args:
            docling_doc: Docling document object (specific type varies by format)

        Returns:
            List of BaseChunk objects from the chunker

        """

    def supports_file(self, file_path: Path) -> bool:  # noqa: ARG002
        """
        Check if this pipeline supports the given file type.

        Args:
            file_path: Path to the file to check

        Returns:
            True if the file type is supported, False otherwise

        """
        # Default implementation - subclasses should override
        return False

    def _maybe_synthesize_chunks(self, chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Optionally refine chunk content using the synthesis engine if config.refine is True.

        Adds synthesis metadata to each chunk if synthesis is performed.

        Args:
            chunks: List of chunks to refine

        Returns:
            List of refined chunks.

        """
        if not self.config.refine:
            return chunks
        provider = ProviderFactory.get_provider(self.config)
        synthesizer = ContentSynthesizer(provider)
        refined_chunks = []
        for chunk in chunks:
            text = chunk["content"] if isinstance(chunk, dict) and "content" in chunk else str(chunk)
            # Determine doc_format, task, and refinement_level
            doc_format = chunk.get("metadata", {}).get("file_type", getattr(self.config, "file_type", "pdf"))
            task = chunk.get("metadata", {}).get("synthesis_task", "summarize")
            refinement_level = getattr(self.config, "refinement_level", "moderate")
            refined, _ = asyncio.run(
                synthesizer.refine_chunk(
                    chunk=text,
                    doc_format=doc_format,
                    task=task,
                    refinement_level=refinement_level,
                ),
            )
            chunk_copy = dict(chunk)
            chunk_copy["content"] = refined
            if "metadata" not in chunk_copy:
                chunk_copy["metadata"] = {}
            chunk_copy["metadata"].update({
                "synthesized": True,
                "llm_provider": self.config.llm_provider,
                "llm_model": self.config.llm_model,
                "refinement_level": refinement_level,
            })
            refined_chunks.append(chunk_copy)
        return refined_chunks
