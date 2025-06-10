"""
Unit tests for configuration dataclass.

Tests the Config dataclass validation, defaults, and functionality
following pytest best practices with proper isolation.
"""

import pytest

from src.config import Config
from src.exceptions import ValidationError
from src.synthesis.providers.factory import ProviderFactory
from src.synthesis.providers.noop import NoOpProvider


class TestConfigDefaults:
    """Test Config dataclass default values."""

    def test_should_provide_sensible_defaults_when_created(self) -> None:
        """Test that Config.default() provides sensible default values."""
        config = Config.default()

        assert config.chunk_size == 2048
        assert config.min_tokens == 330
        assert config.chunk_overlap == 100
        assert config.preserve_tables is True
        assert config.verbose is False
        assert config.tokenizer_model == "BAAI/bge-small-en-v1.5"
        assert config.refine is False
        assert config.llm_provider is None

    def test_should_be_immutable_after_creation(self) -> None:
        """Test that config values can be modified after creation."""
        config = Config.default()
        original_chunk_size = config.chunk_size

        # Dataclasses are mutable by default, which is what we want
        config.chunk_size = 1024
        assert config.chunk_size == 1024
        assert config.chunk_size != original_chunk_size


class TestConfigValidation:
    """Test Config dataclass validation logic."""

    def test_should_pass_validation_when_valid_parameters_provided(self) -> None:
        """Test that valid configurations pass validation."""
        config = Config.default()

        # Should not raise any exception
        config.validate()

    def test_should_raise_error_when_chunk_size_too_small(self) -> None:
        """Test validation fails when chunk_size is too small."""
        config = Config.default()
        config.chunk_size = 50  # Too small (less than min_tokens=200)

        with pytest.raises(
            ValidationError,
            match="chunk_size .* must be greater than min_tokens",
        ):
            config.validate()

    def test_should_raise_error_when_min_tokens_too_small(self) -> None:
        """Test validation fails when min_tokens is too small."""
        config = Config.default()
        config.min_tokens = 0  # Too small (not positive)

        with pytest.raises(ValidationError, match="min_tokens must be positive"):
            config.validate()

    def test_should_raise_error_when_min_tokens_exceeds_chunk_size(self) -> None:
        """Test validation fails when min_tokens > chunk_size."""
        config = Config.default()
        config.chunk_size = 500
        config.min_tokens = 600  # Larger than chunk_size

        with pytest.raises(
            ValidationError,
            match="chunk_size .* must be greater than min_tokens",
        ):
            config.validate()

    def test_should_raise_error_when_chunk_overlap_negative(self) -> None:
        """Test validation fails when chunk_overlap is negative."""
        config = Config.default()
        config.chunk_overlap = -10

        with pytest.raises(ValidationError, match="chunk_overlap must be non-negative"):
            config.validate()

    def test_should_raise_error_when_chunk_overlap_exceeds_chunk_size(self) -> None:
        """Test validation fails when chunk_overlap > chunk_size."""
        config = Config.default()
        config.chunk_size = 1000
        config.chunk_overlap = 1200  # Larger than chunk_size

        with pytest.raises(
            ValidationError,
            match="chunk_overlap .* must be less than chunk_size",
        ):
            config.validate()

    def test_should_raise_error_when_tokenizer_model_empty(self) -> None:
        """Test validation fails when tokenizer_model is empty."""
        config = Config.default()
        config.tokenizer_model = ""

        with pytest.raises(ValidationError, match="tokenizer_model must be a non-empty string"):
            config.validate()


class TestConfigParameterization:
    """Test Config with various parameter combinations."""

    @pytest.mark.parametrize(
        ("chunk_size", "min_tokens", "should_pass"),
        [
            (1024, 200, True),  # Valid combination
            (2048, 500, True),  # Valid combination
            (512, 100, True),  # Valid combination
            (100, 200, False),  # min_tokens > chunk_size
            (50, 100, False),  # chunk_size too small
            (1024, 0, False),  # min_tokens too small (not positive)
        ],
    )
    def test_should_validate_parameter_combinations_correctly(
        self,
        chunk_size: int,
        min_tokens: int,
        should_pass: bool,
    ) -> None:
        """Test various parameter combinations for validation."""
        config = Config.default()
        config.chunk_size = chunk_size
        config.min_tokens = min_tokens

        if should_pass:
            config.validate()  # Should not raise
        else:
            with pytest.raises(ValidationError):
                config.validate()

    @pytest.mark.parametrize("chunk_overlap", [0, 50, 100, 200])
    def test_should_accept_valid_chunk_overlap_values(self, chunk_overlap: int) -> None:
        """Test that valid chunk_overlap values are accepted."""
        config = Config.default()
        config.chunk_overlap = chunk_overlap

        config.validate()  # Should not raise

    @pytest.mark.parametrize("preserve_tables", [True, False])
    def test_should_accept_boolean_preserve_tables_values(
        self,
        preserve_tables: bool,
    ) -> None:
        """Test that boolean preserve_tables values are accepted."""
        config = Config.default()
        config.preserve_tables = preserve_tables

        config.validate()  # Should not raise
        assert config.preserve_tables is preserve_tables


class TestConfigCustomization:
    """Test Config customization and edge cases."""

    def test_should_allow_custom_configuration_creation(self) -> None:
        """Test creating custom configurations."""
        config = Config(
            chunk_size=1024,
            min_tokens=100,
            chunk_overlap=50,
            preserve_tables=False,
            verbose=True,
        )

        assert config.chunk_size == 1024
        assert config.min_tokens == 100
        assert config.chunk_overlap == 50
        assert config.preserve_tables is False
        assert config.verbose is True

    def test_should_handle_edge_case_minimum_values(self) -> None:
        """Test configuration with minimum allowed values."""
        config = Config(
            chunk_size=100,  # Minimum allowed
            min_tokens=50,  # Minimum allowed
            chunk_overlap=0,  # Minimum allowed
            preserve_tables=True,
            verbose=False,
        )

        config.validate()  # Should not raise

    def test_should_handle_large_values_correctly(self) -> None:
        """Test configuration with large values."""
        config = Config(
            chunk_size=8192,
            min_tokens=1000,
            chunk_overlap=500,
            preserve_tables=True,
            verbose=True,
        )

        config.validate()  # Should not raise


class TestConfigLLMSynthesisValidation:
    """Test validation logic for LLM synthesis and provider settings in Config."""

    def test_should_fail_when_refine_true_and_llm_model_missing(self) -> None:
        """Test validation fails when refine is True and llm_model is missing."""
        config = Config.default()
        config.refine = True
        config.llm_model = None
        with pytest.raises(ValidationError, match="llm_model must be a non-empty string"):
            config.validate()

    def test_should_fail_when_refine_true_and_invalid_refinement_level(self) -> None:
        """Test validation fails when refine is True and refinement_level is invalid."""
        config = Config.default()
        config.refine = True
        config.llm_model = "mistral:7b"
        config.refinement_level = "extreme"
        with pytest.raises(ValidationError, match="refinement_level must be one of"):
            config.validate()

    def test_should_fail_when_refine_true_and_preserve_structure_not_bool(self) -> None:
        """Test validation fails when preserve_structure is not a boolean."""
        config = Config.default()
        config.refine = True
        config.llm_model = "mistral:7b"
        config.preserve_structure = "yes"  # type: ignore[assignment]
        with pytest.raises(ValidationError, match="preserve_structure must be a boolean"):
            config.validate()

    def test_should_fail_when_refine_true_and_max_retries_negative(self) -> None:
        """Test validation fails when max_retries is negative."""
        config = Config.default()
        config.refine = True
        config.llm_model = "mistral:7b"
        config.max_retries = -1
        with pytest.raises(ValidationError, match="max_retries must be >= 0"):
            config.validate()

    def test_should_fail_when_refine_true_and_base_delay_zero(self) -> None:
        """Test validation fails when base_delay is zero."""
        config = Config.default()
        config.refine = True
        config.llm_model = "mistral:7b"
        config.base_delay = 0.0
        with pytest.raises(ValidationError, match="base_delay must be > 0"):
            config.validate()

    def test_should_fail_when_refine_true_and_circuit_breaker_threshold_zero(self) -> None:
        """Test validation fails when circuit_breaker_threshold is zero."""
        config = Config.default()
        config.refine = True
        config.llm_model = "mistral:7b"
        config.circuit_breaker_threshold = 0
        with pytest.raises(ValidationError, match="circuit_breaker_threshold must be > 0"):
            config.validate()

    def test_should_fail_when_refine_true_and_circuit_breaker_timeout_zero(self) -> None:
        """Test validation fails when circuit_breaker_timeout is zero."""
        config = Config.default()
        config.refine = True
        config.llm_model = "mistral:7b"
        config.circuit_breaker_timeout = 0
        with pytest.raises(ValidationError, match="circuit_breaker_timeout must be > 0"):
            config.validate()

    def test_should_fail_when_refine_true_and_openai_provider_missing_api_key(self) -> None:
        """Test validation fails when openai_api_key is missing."""
        config = Config.default()
        config.refine = True
        config.llm_model = "gpt-4"
        config.llm_provider = "openai"
        config.openai_api_key = None
        with pytest.raises(ValidationError, match="openai_api_key must be a non-empty string"):
            config.validate()

    def test_should_fail_when_refine_true_and_anthropic_provider_missing_api_key(self) -> None:
        """Test validation fails when anthropic_api_key is missing."""
        config = Config.default()
        config.refine = True
        config.llm_model = "claude-3"
        config.llm_provider = "anthropic"
        config.anthropic_api_key = None
        with pytest.raises(ValidationError, match="anthropic_api_key must be a non-empty string"):
            config.validate()

    def test_should_fail_when_refine_true_and_google_provider_missing_api_key(self) -> None:
        """Test validation fails when google_api_key is missing."""
        config = Config.default()
        config.refine = True
        config.llm_model = "gemini-pro"
        config.llm_provider = "google"
        config.google_api_key = None
        with pytest.raises(ValidationError, match="google_api_key must be a non-empty string"):
            config.validate()

    def test_should_pass_when_refine_true_and_all_settings_valid(self) -> None:
        """Test validation passes when all synthesis settings are valid."""
        config = Config.default()
        config.refine = True
        config.llm_model = "mistral:7b"
        config.refinement_level = "moderate"
        config.preserve_structure = True
        config.max_retries = 2
        config.base_delay = 1.0
        config.circuit_breaker_threshold = 3
        config.circuit_breaker_timeout = 30
        config.llm_provider = "ollama"
        # No API key required for ollama
        config.validate()


class TestProviderFactory:
    """Test ProviderFactory."""

    def test_should_return_noop_provider_when_refine_false(self) -> None:
        """Test that the factory returns the NoOpProvider when refine is False."""
        config = Config.default()
        config.refine = False
        provider = ProviderFactory.get_provider(config)
        assert isinstance(provider, NoOpProvider)

    def test_should_raise_value_error_for_unknown_provider(self) -> None:
        """Test that the factory raises a ValueError for an unknown provider."""
        config = Config.default()
        config.refine = True
        config.llm_provider = "unknown"
        with pytest.raises(ValueError, match="Unknown LLM provider"):
            ProviderFactory.get_provider(config)

    @pytest.mark.parametrize("provider_name", ["openai", "anthropic", "google"])
    def test_should_raise_not_implemented_for_known_providers(self, provider_name: str) -> None:
        """Test that the factory raises a NotImplementedError for a known provider."""
        config = Config.default()
        config.refine = True
        config.llm_provider = provider_name
        expected_msg = (
            "OpenAIProvider is not yet implemented."
            if provider_name == "openai"
            else f"{provider_name.capitalize()}Provider is not yet implemented."
        )
        with pytest.raises(NotImplementedError, match=expected_msg):
            ProviderFactory.get_provider(config)
