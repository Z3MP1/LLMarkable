"""Tests for CLI configuration parsing."""

from main import CLIOptions, _create_config_from_options
from src.config import Config


class TestCLIConfigParsing:
    """Ensure CLI options are stored in Config."""

    def test_should_store_refine_options(self) -> None:
        options = CLIOptions(refine=True, llm_provider="noop")
        config = _create_config_from_options(options)

        assert isinstance(config, Config)
        assert config.refine is True
        assert config.llm_provider == "noop"
