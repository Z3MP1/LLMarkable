"""Integration tests for pipeline factory functionality validation."""

from pathlib import Path
from unittest.mock import patch

import pytest

from src.config import Config
from src.pipelines import create_pipeline


class TestPipelineFactoryIntegration:
    """Integration tests for pipeline factory validation."""

    def test_should_create_html_pipeline_when_html_file_provided(
        self,
        test_config: Config,
    ) -> None:
        """Test HTML pipeline creation and basic functionality."""
        html_file = Path("test.html")

        with patch("pathlib.Path.exists", return_value=True):
            with patch("src.pipelines.html.HTMLPipeline.process") as mock_process:
                mock_process.return_value = [{"content": "test chunk"}]

                pipeline = create_pipeline(html_file, test_config)
                result = pipeline.process(html_file)

                assert len(result) == 1
                assert result[0]["content"] == "test chunk"

    def test_should_create_pdf_pipeline_when_pdf_file_provided(
        self,
        test_config: Config,
    ) -> None:
        """Test PDF pipeline creation and basic functionality."""
        pdf_file = Path("test.pdf")

        with patch("pathlib.Path.exists", return_value=True):
            with patch("src.pipelines.pdf.PDFPipeline.process") as mock_process:
                mock_process.return_value = [{"content": "pdf chunk"}]

                pipeline = create_pipeline(pdf_file, test_config)
                result = pipeline.process(pdf_file)

                assert len(result) == 1
                assert result[0]["content"] == "pdf chunk"

    def test_should_raise_file_not_found_when_file_missing(
        self,
        test_config: Config,
    ) -> None:
        """Test error handling for missing files."""
        with pytest.raises(FileNotFoundError, match="File not found"):
            create_pipeline(Path("nonexistent.pdf"), test_config)

    def test_should_raise_value_error_when_unsupported_format(
        self,
        test_config: Config,
    ) -> None:
        """Test error handling for unsupported file formats."""
        unsupported_file = Path("test.docx")

        with patch("pathlib.Path.exists", return_value=True):
            with pytest.raises(ValueError, match="Unsupported file format"):
                create_pipeline(unsupported_file, test_config)
