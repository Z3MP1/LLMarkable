# Environment Setup Instructions for LLMarkable

## Recommended: Using `uv` (Fast, Reproducible, Official Method)

1. Ensure you have Python 3.12+ installed.
2. Install `uv`:
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```
3. Create a virtual environment (optional but recommended):
   ```bash
   python3.12 -m venv .venv
   source .venv/bin/activate
   ```
4. Install all dependencies:
   ```bash
   uv sync
   ```

This will create a fast, reproducible environment using the dependencies specified in `pyproject.toml` and `uv.lock`.

---

## Alternative: Using pip and requirements.txt (Not Recommended)

Some tools or environments may require pip and a requirements.txt file. This is not the preferred method for this project, but is provided for compatibility:

1. Ensure you have Python 3.12+ installed.
2. Create and activate a virtual environment:
   ```bash
   python3.12 -m venv .venv
   source .venv/bin/activate
   ```
3. Install dependencies from requirements.txt:
   ```bash
   pip install -r requirements.txt
   ```

> **Note:** The pip/requirements.txt method is less reproducible and may not match the exact environment produced by `uv sync`. Use only if required by your tooling.

---

## Troubleshooting & Compatibility Notes

- If you still encounter problems with environment setup or package installation, experience has shown that running:
  - `uv pip install [package] --system`
  - or `pip install [package] --system`
  can sometimes resolve issues, especially in certain environments (e.g., IDEs, containers, or when using system Python).
- The `requirements.txt` file is provided **only** for compatibility with such tools and should not be referenced elsewhere in the project or documentation.

---

# Target Structure & Functionality for LLMarkable Agents

## Project Goals & Architecture
- LLMarkable is a modular, format-specific document conversion system. Each supported format (PDF, HTML, DOCX, PPTX, Image) has its own pipeline, leveraging format-specific features for optimal quality.
- The primary goal is to produce high-quality, LLM-friendly Markdown chunks, preserving all information and structure, and optimizing for RAG and AI-powered workflows.
- Token-based chunking, smart consolidation (merging small/low-info chunks), and research-backed parameters (chunk_size=2048, min_tokens=330, chunk_overlap=100) are required in all pipelines.
- The system is extensible: new file formats and LLM-powered synthesis (Phase 2) are supported via a plugin-ready architecture.
- Robust error handling, type safety (mypy strict), and comprehensive, fast, isolated testing are mandatory.

## Implementation & Workflow Rules
- Follow the architecture and requirements in [README.md](README.md) and [PRD.txt](.taskmaster/templates/PRD.txt) for all tasks and features.
- All code must:
  - Pass all tests in the `tests/` directory
  - Pass `ruff` linting (unless a well-reasoned ignore is added via `# noqa` or `pyproject.toml`)
  - Pass `mypy` type checking (strict mode)
- If ignoring a ruff lint error, the agent must document the reason (in code or commit message) and prefer project-wide consistency.
- Each task/PR must close with all tests, ruff, and mypy checks passing.

## References
- See [README.md](README.md) for project structure, usage, and development workflow.
- See [PRD.txt](.taskmaster/templates/PRD.txt) for detailed requirements, architecture, and roadmap.
