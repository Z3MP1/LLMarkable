"""Manage prompt templates for content synthesis."""

from pathlib import Path


class PromptManager:
    """
    Loads, caches, and formats prompt templates for content synthesis.

    Supports format-specific and refinement-level-specific template selection.
    Provides an interface to retrieve and format templates with dynamic data.
    """

    def __init__(self, prompts_dir: str | Path) -> None:
        """
        Initialize the PromptManager with the root directory for prompt templates.

        Args:
            prompts_dir (str | Path): Path to the root prompts directory.

        """
        self.prompts_dir = Path(prompts_dir)
        self._cache: dict[str, str] = {}

    def get_template(self, doc_format: str, task: str, refinement_level: str) -> str:
        """
        Retrieve the prompt template for the given document format, task, and refinement level.

        Args:
            doc_format (str): Document format (e.g., 'pdf', 'html', 'markdown').
            task (str): Synthesis task (e.g., 'summarize', 'reformat', 'correct_grammar').
            refinement_level (str): Refinement level (e.g., 'light', 'moderate', 'aggressive').

        Returns:
            str: The prompt template as a string.

        Raises:
            FileNotFoundError: If the template file does not exist.

        """
        key = f"{doc_format}/{task}_{refinement_level}.txt"
        if key in self._cache:
            return self._cache[key]
        path = self.prompts_dir / doc_format / f"{task}_{refinement_level}.txt"
        if not path.exists():
            msg = f"Prompt template not found: {path}"
            raise FileNotFoundError(msg)
        template = path.read_text(encoding="utf-8")
        self._cache[key] = template
        return template

    def format_template(self, template: str, **kwargs: object) -> str:
        """
        Format the template with dynamic data.

        Args:
            template (str): The prompt template string with placeholders.
            **kwargs: Dynamic data to fill in the template.

        Returns:
            str: The formatted prompt.

        Raises:
            KeyError: If a required variable is missing.

        """
        try:
            return template.format(**kwargs)
        except KeyError as err:
            msg = f"Missing variable for prompt template: {err}"
            raise KeyError(msg) from err
