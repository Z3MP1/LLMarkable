"""Test the main CLI."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from typer.testing import CliRunner

from main import app
from src.config import Config

runner = CliRunner()

@patch("main.create_pipeline")
@patch("main._save_individual_chunks", lambda *a, **k: {"location": "dummy", "file_count": 1})
@patch("main._save_consolidated_output", lambda *a, **k: {"location": "dummy"})
@patch("main._validate_input_file", lambda *a, **k: None)
@patch("main._validate_file_format", lambda *a, **k: None)
@patch("main.ContentSynthesizer")
@patch("main.ProviderFactory.get_provider")
@patch("src.config.Config.default")
def test_cli_refine_flag_and_options(mock_config_default: MagicMock, mock_get_provider: MagicMock, mock_synth: MagicMock, mock_create_pipeline: MagicMock, tmp_path: Path) -> None:
    """Test that the CLI handles the refine flag and options correctly."""
    config_instance = Config()
    config_instance.openai_api_key = "sk-test"
    config_instance.llm_model = "gpt-3.5-turbo"
    config_instance.llm_provider = "openai"
    config_instance.refinement_level = "aggressive"
    config_instance.refine = True
    mock_config_default.return_value = config_instance
    mock_provider = MagicMock()
    mock_get_provider.return_value = mock_provider
    mock_synth.return_value.refine_chunk = AsyncMock(return_value="refined")
    # Patch pipeline to return dummy chunks
    mock_pipeline = MagicMock()
    mock_pipeline.process.return_value = [{"content": "dummy chunk"}]
    mock_create_pipeline.return_value = mock_pipeline
    fake_file = tmp_path / "testfile.pdf"
    fake_file.write_text("dummy content")
    result = runner.invoke(
        app,
        [
            "convert",
            str(fake_file),
            "--refine",
            "--llm-provider", "openai",
            "--llm-model", "gpt-3.5-turbo",
            "--refinement-level", "aggressive",
            "--output-dir", str(tmp_path),
        ],
    )
    assert result.exit_code == 0
    assert "Successfully converted" in result.output


def test_cli_help_shows_synthesis_options() -> None:
    """Test that the help message shows the synthesis options."""
    result = runner.invoke(app, ["convert", "--help"])
    assert "--refine" in result.output
    assert "--llm-provider" in result.output
    assert "--llm-model" in result.output
    assert "--refinement-level" in result.output
