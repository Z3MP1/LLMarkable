"""
Custom exception classes for LLMarkable document conversion pipeline.

Provides specific exception types for different error scenarios to enable
better error handling and user experience.
"""


class LLMarkableError(Exception):
    """Base exception class for all LLMarkable-specific errors."""

    def __init__(
        self,
        message: str,
        *,
        original_error: Exception | None = None,
    ) -> None:
        """
        Initialize base exception.

        Args:
            message: Human-readable error message
            original_error: Optional original exception that caused this error

        """
        super().__init__(message)
        self.original_error = original_error


class ValidationError(LLMarkableError):
    """Raised when input validation fails."""

    def __init__(
        self,
        message: str,
        *,
        field_name: str | None = None,
        field_value: object = None,
        original_error: Exception | None = None,
    ) -> None:
        """
        Initialize validation error.

        Args:
            message: Human-readable error message
            field_name: Name of the field that failed validation
            field_value: Value that failed validation
            original_error: Optional original exception

        """
        super().__init__(message, original_error=original_error)
        self.field_name = field_name
        self.field_value = field_value


class UnsupportedFormatError(LLMarkableError):
    """Raised when an unsupported file format is encountered."""

    def __init__(
        self,
        file_format: str,
        *,
        supported_formats: list[str] | None = None,
        original_error: Exception | None = None,
    ) -> None:
        """
        Initialize unsupported format error.

        Args:
            file_format: The unsupported file format
            supported_formats: List of supported formats
            original_error: Optional original exception

        """
        if supported_formats:
            supported_str = ", ".join(supported_formats)
            message = f"Unsupported file format '{file_format}'. Supported formats: {supported_str}"
        else:
            message = f"Unsupported file format '{file_format}'"

        super().__init__(message, original_error=original_error)
        self.file_format = file_format
        self.supported_formats = supported_formats or []


class ConversionError(LLMarkableError):
    """Raised when document conversion fails."""

    def __init__(
        self,
        message: str,
        *,
        file_path: str | None = None,
        conversion_stage: str | None = None,
        original_error: Exception | None = None,
    ) -> None:
        """
        Initialize conversion error.

        Args:
            message: Human-readable error message
            file_path: Path to the file that failed conversion
            conversion_stage: Stage where conversion failed (e.g., 'parsing', 'chunking')
            original_error: Optional original exception

        """
        super().__init__(message, original_error=original_error)
        self.file_path = file_path
        self.conversion_stage = conversion_stage


class ChunkingError(LLMarkableError):
    """Raised when document chunking fails."""

    def __init__(
        self,
        message: str,
        *,
        chunker_type: str | None = None,
        chunk_count: int | None = None,
        original_error: Exception | None = None,
    ) -> None:
        """
        Initialize chunking error.

        Args:
            message: Human-readable error message
            chunker_type: Type of chunker that failed (e.g., 'HybridChunker')
            chunk_count: Number of chunks processed before failure
            original_error: Optional original exception

        """
        super().__init__(message, original_error=original_error)
        self.chunker_type = chunker_type
        self.chunk_count = chunk_count


class FileAccessError(LLMarkableError):
    """Raised when file access operations fail."""

    def __init__(
        self,
        message: str,
        *,
        file_path: str | None = None,
        operation: str | None = None,
        original_error: Exception | None = None,
    ) -> None:
        """
        Initialize file access error.

        Args:
            message: Human-readable error message
            file_path: Path to the file that caused the error
            operation: File operation that failed (e.g., 'read', 'write', 'create')
            original_error: Optional original exception

        """
        super().__init__(message, original_error=original_error)
        self.file_path = file_path
        self.operation = operation


class TokenizerError(LLMarkableError):
    """Raised when tokenizer operations fail."""

    def __init__(
        self,
        message: str,
        *,
        model_name: str | None = None,
        original_error: Exception | None = None,
    ) -> None:
        """
        Initialize tokenizer error.

        Args:
            message: Human-readable error message
            model_name: Name of the tokenizer model that failed
            original_error: Optional original exception

        """
        super().__init__(message, original_error=original_error)
        self.model_name = model_name
