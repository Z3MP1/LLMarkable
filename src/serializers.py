"""
Custom serializer providers for consistent chunk formatting.

This module provides ChunkingSerializerProvider implementations that follow
Docling best practices for table and image serialization.
"""

from typing import TYPE_CHECKING

from docling_core.transforms.chunker.hierarchical_chunker import (
    ChunkingDocSerializer,
    ChunkingSerializerProvider,
)
from docling_core.transforms.serializer.markdown import (
    MarkdownParams,
    MarkdownTableSerializer,
)

if TYPE_CHECKING:
    from docling_core.types.doc.document import DoclingDocument


class LLMarkableSerializerProvider(ChunkingSerializerProvider):
    """
    Custom serializer provider for LLMarkable with optimized table and image handling.

    Provides consistent markdown formatting with proper table serialization
    and customizable image placeholders.
    """

    def __init__(self, image_placeholder: str = "<!-- LLMarkable Image -->") -> None:
        """
        Initialize serializer provider.

        Args:
            image_placeholder: Custom placeholder text for images

        """
        self.image_placeholder = image_placeholder

    def get_serializer(self, doc: "DoclingDocument") -> ChunkingDocSerializer:
        """
        Get configured ChunkingDocSerializer for the document.

        Args:
            doc: DoclingDocument to serialize

        Returns:
            Configured ChunkingDocSerializer with optimized settings

        """
        return ChunkingDocSerializer(
            doc=doc,
            table_serializer=MarkdownTableSerializer(),  # Use proper Markdown table formatting
            params=MarkdownParams(
                image_placeholder=self.image_placeholder,
            ),
        )


class TableOptimizedSerializerProvider(ChunkingSerializerProvider):
    """
    Serializer provider optimized specifically for documents with complex tables.

    Uses MarkdownTableSerializer for better table structure preservation
    in LLM-friendly formats.
    """

    def get_serializer(self, doc: "DoclingDocument") -> ChunkingDocSerializer:
        """
        Get table-optimized ChunkingDocSerializer.

        Args:
            doc: DoclingDocument to serialize

        Returns:
            ChunkingDocSerializer optimized for table processing

        """
        return ChunkingDocSerializer(
            doc=doc,
            table_serializer=MarkdownTableSerializer(),
            params=MarkdownParams(
                image_placeholder="<!-- Table Document Image -->",
            ),
        )


class ImageOptimizedSerializerProvider(ChunkingSerializerProvider):
    """
    Serializer provider optimized for documents with significant image content.

    Provides enhanced image placeholder text that's more descriptive
    for LLM processing.
    """

    def get_serializer(self, doc: "DoclingDocument") -> ChunkingDocSerializer:
        """
        Get image-optimized ChunkingDocSerializer.

        Args:
            doc: DoclingDocument to serialize

        Returns:
            ChunkingDocSerializer optimized for image-heavy documents

        """
        return ChunkingDocSerializer(
            doc=doc,
            params=MarkdownParams(
                image_placeholder="<!-- Document Image: Visual content not transcribed -->",
            ),
        )
