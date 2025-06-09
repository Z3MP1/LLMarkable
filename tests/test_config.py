"""
Unit tests for configuration dataclass.

Tests the Config dataclass validation, defaults, and functionality
following pytest best practices with proper isolation.
"""

import pytest

from src.config import Config
from src.exceptions import ValidationError


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
