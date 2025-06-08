"""
Unit tests for custom exception classes.

Tests the exception hierarchy and error handling functionality
following pytest best practices.
"""

from src.exceptions import (
    ChunkingError,
    ConversionError,
    FileAccessError,
    LLMarkableError,
    TokenizerError,
    UnsupportedFormatError,
    ValidationError,
)


class TestLLMarkableError:
    """Test base LLMarkableError functionality."""

    def test_should_create_basic_error_when_message_provided(self) -> None:
        """Test basic error creation with message."""
        error = LLMarkableError("Test error message")

        assert str(error) == "Test error message"
        assert isinstance(error, Exception)
        assert error.original_error is None

    def test_should_store_original_error_when_provided(self) -> None:
        """Test error with original exception."""
        original = ValueError("Original error")
        error = LLMarkableError("Wrapped error", original_error=original)

        assert str(error) == "Wrapped error"
        assert error.original_error is original
        assert isinstance(error.original_error, ValueError)


class TestValidationError:
    """Test ValidationError functionality."""

    def test_should_inherit_from_llmarkable_error(self) -> None:
        """Test that ValidationError inherits from LLMarkableError."""
        error = ValidationError("Validation failed")

        assert isinstance(error, LLMarkableError)
        assert isinstance(error, Exception)

    def test_should_store_field_information_when_provided(self) -> None:
        """Test validation error with field information."""
        error = ValidationError(
            "Invalid value",
            field_name="chunk_size",
            field_value=0,
        )

        assert str(error) == "Invalid value"
        assert error.field_name == "chunk_size"
        assert error.field_value == 0

    def test_should_handle_none_field_values(self) -> None:
        """Test validation error with None field values."""
        error = ValidationError("Error", field_name=None, field_value=None)

        assert error.field_name is None
        assert error.field_value is None

    def test_should_store_original_error(self) -> None:
        """Test validation error with original exception."""
        original = TypeError("Type error")
        error = ValidationError("Validation failed", original_error=original)

        assert error.original_error is original


class TestUnsupportedFormatError:
    """Test UnsupportedFormatError functionality."""

    def test_should_inherit_from_llmarkable_error(self) -> None:
        """Test that UnsupportedFormatError inherits from LLMarkableError."""
        error = UnsupportedFormatError(".unknown")

        assert isinstance(error, LLMarkableError)

    def test_should_store_file_format(self) -> None:
        """Test that file format is stored correctly."""
        error = UnsupportedFormatError(".docx")

        assert error.file_format == ".docx"
        assert "Unsupported file format '.docx'" in str(error)

    def test_should_include_supported_formats_in_message(self) -> None:
        """Test that supported formats are included in error message."""
        supported = [".pdf", ".html", ".htm"]
        error = UnsupportedFormatError(".docx", supported_formats=supported)

        assert error.file_format == ".docx"
        assert error.supported_formats == supported
        assert ".pdf, .html, .htm" in str(error)

    def test_should_handle_empty_supported_formats(self) -> None:
        """Test error with empty supported formats list."""
        error = UnsupportedFormatError(".unknown", supported_formats=[])

        assert error.supported_formats == []
        assert "Unsupported file format '.unknown'" in str(error)


class TestConversionError:
    """Test ConversionError functionality."""

    def test_should_inherit_from_llmarkable_error(self) -> None:
        """Test that ConversionError inherits from LLMarkableError."""
        error = ConversionError("Conversion failed")

        assert isinstance(error, LLMarkableError)

    def test_should_store_file_path_and_stage(self) -> None:
        """Test conversion error with file path and stage information."""
        error = ConversionError(
            "Parsing failed",
            file_path="/test/doc.pdf",
            conversion_stage="parsing",
        )

        assert str(error) == "Parsing failed"
        assert error.file_path == "/test/doc.pdf"
        assert error.conversion_stage == "parsing"

    def test_should_handle_none_attributes(self) -> None:
        """Test conversion error with None attributes."""
        error = ConversionError("Error", file_path=None, conversion_stage=None)

        assert error.file_path is None
        assert error.conversion_stage is None

    def test_should_store_original_error(self) -> None:
        """Test conversion error with original exception."""
        original = OSError("File read error")
        error = ConversionError("Conversion failed", original_error=original)

        assert error.original_error is original


class TestChunkingError:
    """Test ChunkingError functionality."""

    def test_should_inherit_from_llmarkable_error(self) -> None:
        """Test that ChunkingError inherits from LLMarkableError."""
        error = ChunkingError("Chunking failed")

        assert isinstance(error, LLMarkableError)

    def test_should_store_chunker_information(self) -> None:
        """Test chunking error with chunker-specific information."""
        error = ChunkingError(
            "Chunking failed",
            chunker_type="HybridChunker",
            chunk_count=5,
        )

        assert str(error) == "Chunking failed"
        assert error.chunker_type == "HybridChunker"
        assert error.chunk_count == 5

    def test_should_handle_none_chunker_attributes(self) -> None:
        """Test chunking error with None attributes."""
        error = ChunkingError("Error", chunker_type=None, chunk_count=None)

        assert error.chunker_type is None
        assert error.chunk_count is None

    def test_should_store_original_error(self) -> None:
        """Test chunking error with original exception."""
        original = RuntimeError("Runtime error")
        error = ChunkingError("Chunking failed", original_error=original)

        assert error.original_error is original


class TestFileAccessError:
    """Test FileAccessError functionality."""

    def test_should_inherit_from_llmarkable_error(self) -> None:
        """Test that FileAccessError inherits from LLMarkableError."""
        error = FileAccessError("File access failed")

        assert isinstance(error, LLMarkableError)

    def test_should_store_file_and_operation_information(self) -> None:
        """Test file access error with file and operation details."""
        error = FileAccessError(
            "Cannot read file",
            file_path="/test/file.pdf",
            operation="read",
        )

        assert str(error) == "Cannot read file"
        assert error.file_path == "/test/file.pdf"
        assert error.operation == "read"

    def test_should_handle_none_file_attributes(self) -> None:
        """Test file access error with None attributes."""
        error = FileAccessError("Error", file_path=None, operation=None)

        assert error.file_path is None
        assert error.operation is None

    def test_should_store_original_error(self) -> None:
        """Test file access error with original exception."""
        original = PermissionError("Permission denied")
        error = FileAccessError("File access failed", original_error=original)

        assert error.original_error is original


class TestTokenizerError:
    """Test TokenizerError functionality."""

    def test_should_inherit_from_llmarkable_error(self) -> None:
        """Test that TokenizerError inherits from LLMarkableError."""
        error = TokenizerError("Tokenizer failed")

        assert isinstance(error, LLMarkableError)

    def test_should_store_model_name(self) -> None:
        """Test tokenizer error with model name."""
        error = TokenizerError("Tokenizer failed", model_name="gpt2")

        assert str(error) == "Tokenizer failed"
        assert error.model_name == "gpt2"

    def test_should_handle_none_model_name(self) -> None:
        """Test tokenizer error with None model name."""
        error = TokenizerError("Error", model_name=None)

        assert error.model_name is None

    def test_should_store_original_error(self) -> None:
        """Test tokenizer error with original exception."""
        original = ImportError("Model not found")
        error = TokenizerError("Tokenizer failed", original_error=original)

        assert error.original_error is original


class TestExceptionHierarchy:
    """Test exception inheritance hierarchy."""

    def test_should_all_inherit_from_llmarkable_error(self) -> None:
        """Test that all custom exceptions inherit from LLMarkableError."""
        exceptions_to_test = [
            ValidationError("validation"),
            UnsupportedFormatError(".unknown"),
            ConversionError("conversion"),
            ChunkingError("chunking"),
            FileAccessError("file"),
            TokenizerError("tokenizer"),
        ]

        for exception in exceptions_to_test:
            assert isinstance(exception, LLMarkableError)
            assert isinstance(exception, Exception)

    def test_should_all_inherit_from_exception(self) -> None:
        """Test that all exceptions properly inherit from Exception."""
        base_error = LLMarkableError("test")

        assert isinstance(base_error, Exception)

    def test_should_preserve_message_through_hierarchy(self) -> None:
        """Test that error messages are preserved through inheritance."""
        test_message = "Test error message"

        exceptions_to_test = [
            LLMarkableError(test_message),
            ValidationError(test_message),
            ConversionError(test_message),
            ChunkingError(test_message),
            FileAccessError(test_message),
            TokenizerError(test_message),
        ]

        for exception in exceptions_to_test:
            assert str(exception) == test_message
