"""
Configuration management for the document conversion pipeline.

Simple dataclass-based configuration for Phase 1 implementation.
"""

from dataclasses import dataclass
from pathlib import Path


@dataclass
class Config:
    """
    Configuration settings for document conversion pipeline.

    Phase 2 will introduce optional LLM-powered refinement using these
    configuration flags.
    """

    # Validation constants
    MIN_MULTIPLIER: float = 0.1
    MAX_MULTIPLIER: float = 2.0

    # Chunk size settings (token-based, following Docling best practices)
    min_tokens: int = 330  # Balanced between useful chunks and token efficiency
    chunk_size: int = 2048  # Target chunk size, also used as max_tokens for HybridChunker
    chunk_overlap: int = 100  # Small overlap between chunks to preserve context

    # Input/Output directories
    input_dir: str = "input"
    output_dir: str = "output"

    # Pipeline settings
    preserve_tables: bool = True
    preserve_images: bool = False
    merge_small_trailing_chunks: bool = True  # Feature we implemented

    # Tokenizer model configuration
    tokenizer_model: str = "BAAI/bge-small-en-v1.5"

    # Memory management and file size limits (restored from original implementation)
    max_file_size_mb: int = 20  # Maximum file size in MB (Docling recommendation: ~20MB)
    max_num_pages: int = 1000  # Maximum number of pages to process
    large_document_threshold_mb: int = 10  # Threshold for large document handling
    large_image_threshold_mb: int = 25  # Threshold for large image handling

    # General processing parameters
    chunk_batch_size: int = 50  # Number of chunks to process in batch
    min_content_density: int = 3  # Minimum words per content unit (paragraphs, etc.)

    # PDF-specific parameters
    pdf_structured_content_token_multiplier: float = 0.75  # Token adjustment for structured content
    pdf_complex_table_min_rows: int = 10  # Threshold for complex table detection
    pdf_complex_table_min_cols: int = 5  # Threshold for complex table detection

    # DOCX-specific parameters
    docx_large_doc_max_tokens: int = 1024  # Max tokens for large documents
    docx_structured_content_token_multiplier: float = 0.75  # Token adjustment for structured content
    docx_complex_table_min_rows: int = 10  # Threshold for complex table detection
    docx_complex_table_min_cols: int = 5  # Threshold for complex table detection

    # PPTX-specific parameters
    pptx_large_presentation_threshold_mb: int = 15  # Presentations tend to be larger due to media
    pptx_large_pres_max_tokens: int = 1024  # Max tokens for large presentations
    pptx_min_slide_content_density: int = 2  # Words per slide element
    pptx_slide_content_token_multiplier: float = 0.8  # Presentations often have less dense text
    pptx_max_slide_title_length: int = 100  # Maximum slide title length
    pptx_high_complexity_text_threshold: int = 500  # High complexity text threshold
    pptx_high_complexity_media_threshold: int = 10  # High complexity media threshold
    pptx_low_complexity_text_threshold: int = 100  # Low complexity text threshold
    pptx_low_complexity_media_threshold: int = 3  # Low complexity media threshold
    pptx_min_meaningful_word_count: int = 10  # Minimum meaningful word count

    # HTML-specific parameters
    html_min_paragraph_length: int = 50  # Minimum paragraph length to process

    # Image-specific parameters
    image_min_text_confidence: float = 0.7  # Minimum OCR confidence threshold
    image_min_meaningful_chars: int = 10  # Minimum characters for meaningful text

    # Advanced Image OCR Configuration
    image_ocr_engine: str = "easyocr"  # Options: "easyocr", "tesseract", "rapidocr"
    image_force_full_page_ocr: bool = False  # Force full page OCR scanning
    image_use_gpu: bool = False  # Use GPU for OCR processing (if available)

    # Docling v2 Enrichment Features (Advanced PDF/Image processing)
    enable_picture_description: bool = True  # Enable picture description via vision models (default: True)
    enable_picture_classification: bool = True  # Enable picture classification via vision models (default: True)
    enable_code_enrichment: bool = False  # Enable code block detection and enrichment
    enable_formula_enrichment: bool = False  # Enable formula detection and enrichment

    # OCR Language Configuration
    ocr_languages: list[str] | None = None  # None = auto-detect, or specify ['en', 'fr', 'de', 'es']

    # Table Processing Optimization
    enable_table_cell_matching: bool = False  # False = better column separation for merged cells

    # Output format
    output_format: str = "markdown"
    include_metadata: bool = True
    individual_chunks: bool = False  # False = consolidated, True = individual files

    # Logging
    log_level: str = "INFO"
    verbose: bool = False

    # Advanced Docling Configuration Options
    artifacts_path: str | None = None  # Path to local model artifacts for offline operation
    allow_external_plugins: bool = False  # Enable third-party Docling plugins
    enable_remote_services: bool = False  # Enable cloud OCR, hosted LLMs, etc.

    # Backend Selection (None = use default)
    pdf_backend: str | None = None  # Options: "pypdfium2", "dlparse_v1", "dlparse_v2"

    # Advanced Vision Model Configuration
    vision_model_repo_id: str | None = None  # Custom Hugging Face model for picture description/classification
    vision_model_prompt: str = "Describe this picture in three to five sentences. Be precise and concise."
    vision_model_temperature: float = 0.0  # Temperature for vision model generation
    vision_model_scale: float = 2.0  # Image scaling factor for vision models

    # Pre-defined vision models (shortcuts)
    use_granite_vision: bool = False  # Use IBM Granite vision model
    use_smolvlm: bool = False  # Use SmolVLM model

    # Phase 2 LLM refinement
    refine: bool = False  # Enable content refinement (Phase 2 feature)
    llm_provider: str | None = None  # Selected provider name for refinement

    # Phase 2 LLM integration (provider settings)
    llm_model: str | None = None  # Selected model name for refinement
    openai_api_key: str | None = None  # OpenAI API key (if using OpenAI provider)
    anthropic_api_key: str | None = None  # Anthropic API key (if using Anthropic provider)
    google_api_key: str | None = None  # Google API key (if using Gemini provider)
    ollama_base_url: str = "http://localhost:11434"  # Ollama server URL (for local LLMs)
    # Synthesis control flags
    refinement_level: str = "moderate"  # Synthesis refinement level: light, moderate, aggressive
    preserve_structure: bool = True  # Preserve document structure during synthesis
    # Network and error handling settings
    max_retries: int = 3  # Maximum number of retries for LLM API calls
    base_delay: float = 1.0  # Base delay (seconds) for exponential backoff
    circuit_breaker_threshold: int = 5  # Number of failures before opening circuit
    circuit_breaker_timeout: int = 60  # Timeout (seconds) before circuit breaker resets

    @classmethod
    def default(cls) -> "Config":
        """Create a configuration with default values."""
        return cls()

    def validate(self) -> bool:
        """Validate configuration values."""
        self._validate_chunk_settings()
        self._validate_file_limits()
        self._validate_processing_parameters()
        self._validate_multipliers()
        self._validate_confidence_thresholds()
        self._validate_tokenizer_settings()
        self._validate_synthesis_settings()
        return True

    def _validate_chunk_settings(self) -> None:
        """Validate chunk-related configuration parameters."""
        from .exceptions import ValidationError

        if self.min_tokens <= 0:
            msg = "min_tokens must be positive"
            raise ValidationError(msg, field_name="min_tokens", field_value=self.min_tokens)

        if self.chunk_size <= self.min_tokens:
            msg = f"chunk_size ({self.chunk_size}) must be greater than min_tokens ({self.min_tokens})"
            raise ValidationError(msg, field_name="chunk_size", field_value=self.chunk_size)

        if self.chunk_overlap < 0:
            msg = "chunk_overlap must be non-negative"
            raise ValidationError(msg, field_name="chunk_overlap", field_value=self.chunk_overlap)

        if self.chunk_overlap >= self.chunk_size:
            msg = f"chunk_overlap ({self.chunk_overlap}) must be less than chunk_size ({self.chunk_size})"
            raise ValidationError(msg, field_name="chunk_overlap", field_value=self.chunk_overlap)

    def _validate_file_limits(self) -> None:
        """Validate file size and limit parameters."""
        from .exceptions import ValidationError

        for field_name, field_value in [
            ("max_file_size_mb", self.max_file_size_mb),
            ("max_num_pages", self.max_num_pages),
            ("large_document_threshold_mb", self.large_document_threshold_mb),
            ("large_image_threshold_mb", self.large_image_threshold_mb),
        ]:
            if field_value <= 0:
                msg = f"{field_name} must be positive"
                raise ValidationError(msg, field_name=field_name, field_value=field_value)

        if self.log_level not in ["DEBUG", "INFO", "WARNING", "ERROR"]:
            msg = f"Invalid log_level '{self.log_level}'. Must be one of: DEBUG, INFO, WARNING, ERROR"
            raise ValidationError(msg, field_name="log_level", field_value=self.log_level)

    def _validate_processing_parameters(self) -> None:
        """Validate general processing parameters."""
        from .exceptions import ValidationError

        for field_name, field_value in [
            ("chunk_batch_size", self.chunk_batch_size),
            ("min_content_density", self.min_content_density),
        ]:
            if field_value <= 0:
                msg = f"{field_name} must be positive"
                raise ValidationError(msg, field_name=field_name, field_value=field_value)

    def _validate_multipliers(self) -> None:
        """Validate token multiplier parameters."""
        from .exceptions import ValidationError

        multipliers = [
            ("pdf_structured_content_token_multiplier", self.pdf_structured_content_token_multiplier),
            ("docx_structured_content_token_multiplier", self.docx_structured_content_token_multiplier),
            ("pptx_slide_content_token_multiplier", self.pptx_slide_content_token_multiplier),
        ]

        for multiplier_name, multiplier_value in multipliers:
            if not self.MIN_MULTIPLIER <= multiplier_value <= self.MAX_MULTIPLIER:
                msg = f"{multiplier_name} must be between {self.MIN_MULTIPLIER} and {self.MAX_MULTIPLIER}"
                raise ValidationError(msg, field_name=multiplier_name, field_value=multiplier_value)

    def _validate_confidence_thresholds(self) -> None:
        """Validate confidence threshold parameters."""
        from .exceptions import ValidationError

        if not 0.0 <= self.image_min_text_confidence <= 1.0:
            msg = "image_min_text_confidence must be between 0.0 and 1.0"
            raise ValidationError(
                msg,
                field_name="image_min_text_confidence",
                field_value=self.image_min_text_confidence,
            )

    def _validate_tokenizer_settings(self) -> None:
        """Validate tokenizer model configuration."""
        from .exceptions import ValidationError

        if not isinstance(self.tokenizer_model, str) or not self.tokenizer_model.strip():
            msg = "tokenizer_model must be a non-empty string"
            raise ValidationError(
                msg,
                field_name="tokenizer_model",
                field_value=self.tokenizer_model,
            )

    def _validate_synthesis_settings(self) -> None:
        """Validate LLM synthesis and provider-related settings."""
        from .exceptions import ValidationError

        # Phase 2 LLM parameter validation
        if self.refine:
            if not isinstance(self.llm_model, str) or not self.llm_model.strip():
                msg = "llm_model must be a non-empty string when refine is enabled"
                raise ValidationError(msg, field_name="llm_model", field_value=self.llm_model)
            if self.llm_provider == "openai" and (
                not isinstance(self.openai_api_key, str) or not self.openai_api_key.strip()
            ):
                msg = "openai_api_key must be a non-empty string when using OpenAI provider"
                raise ValidationError(msg, field_name="openai_api_key", field_value=self.openai_api_key)
            if self.llm_provider == "anthropic" and (
                not isinstance(self.anthropic_api_key, str) or not self.anthropic_api_key.strip()
            ):
                msg = "anthropic_api_key must be a non-empty string when using Anthropic provider"
                raise ValidationError(msg, field_name="anthropic_api_key", field_value=self.anthropic_api_key)
            if self.llm_provider == "google" and (
                not isinstance(self.google_api_key, str) or not self.google_api_key.strip()
            ):
                msg = "google_api_key must be a non-empty string when using Google provider"
                raise ValidationError(msg, field_name="google_api_key", field_value=self.google_api_key)
            if self.refinement_level not in ["light", "moderate", "aggressive"]:
                msg = "refinement_level must be one of: light, moderate, aggressive"
                raise ValidationError(msg, field_name="refinement_level", field_value=self.refinement_level)
            if not isinstance(self.preserve_structure, bool):
                msg = "preserve_structure must be a boolean value"
                raise ValidationError(msg, field_name="preserve_structure", field_value=self.preserve_structure)
            if self.max_retries < 0:
                msg = "max_retries must be >= 0"
                raise ValidationError(msg, field_name="max_retries", field_value=self.max_retries)
            if self.base_delay <= 0:
                msg = "base_delay must be > 0"
                raise ValidationError(msg, field_name="base_delay", field_value=self.base_delay)
            if self.circuit_breaker_threshold <= 0:
                msg = "circuit_breaker_threshold must be > 0"
                raise ValidationError(
                    msg,
                    field_name="circuit_breaker_threshold",
                    field_value=self.circuit_breaker_threshold,
                )
            if self.circuit_breaker_timeout <= 0:
                msg = "circuit_breaker_timeout must be > 0"
                raise ValidationError(
                    msg,
                    field_name="circuit_breaker_timeout",
                    field_value=self.circuit_breaker_timeout,
                )

    @property
    def input_path(self) -> Path:
        """Get input directory as Path object."""
        return Path(self.input_dir)

    @property
    def output_path(self) -> Path:
        """Get output directory as Path object."""
        return Path(self.output_dir)

    @property
    def max_file_size_bytes(self) -> int:
        """Get maximum file size in bytes for Docling convert() method."""
        return self.max_file_size_mb * 1024 * 1024

    @property
    def large_document_threshold_bytes(self) -> int:
        """Get large document threshold in bytes."""
        return self.large_document_threshold_mb * 1024 * 1024

    @property
    def large_image_threshold_bytes(self) -> int:
        """Get large image threshold in bytes."""
        return self.large_image_threshold_mb * 1024 * 1024

    @property
    def pptx_large_presentation_threshold_bytes(self) -> int:
        """Get large presentation threshold in bytes."""
        return self.pptx_large_presentation_threshold_mb * 1024 * 1024
