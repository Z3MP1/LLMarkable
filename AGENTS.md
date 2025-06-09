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
