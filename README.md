# LLMarkable

**Transform documents into LLM-friendly, remarkable outputs**

## 1. Overview

LLMarkable provides a sophisticated, modular pipeline for converting various source documents (such as PDF and HTML) into high-quality, LLM-friendly Markdown. It moves beyond simple conversion by employing a format-specific architecture to maximize quality and an intelligent chunking strategy to ensure no information is lost.

The core objective is to produce structured, coherent, and semantically rich Markdown files that are optimized for Retrieval-Augmented Generation (RAG) and other LLM-based applications.

## 2. Core Features

- **Modular & Scalable Architecture**: The codebase is organized into a clean Python package, making it easy to maintain and extend with new file formats or processing capabilities.
- **Format-Specific Pipelines**: The system auto-detects the input file type and dispatches a dedicated, optimized pipeline (e.g., for PDF, HTML) to ensure the highest quality conversion by leveraging format-specific features like `PdfFormatOption`.
- **Intelligent Chunk Consolidation**: To prevent information loss, the pipeline avoids simply discarding small chunks. Instead, it intelligently merges them with adjacent chunks, ensuring that short but important pieces of content are preserved.
- **Type-Safe Development**: Full type annotation coverage with mypy static type checking ensures code reliability and maintainability.
- **Comprehensive Testing**: Pytest-based testing strategy with fixtures, parametrization, and comprehensive coverage reporting.

## 3. Project Structure

The project is organized into a modular package structure:

```
llmarkable/
├── input/                  # Source documents (PDFs, HTML, etc.)
├── output/                 # Processed markdown files
├── src/                    # Main application package
│   ├── __init__.py
│   ├── config.py          # Configuration dataclasses
│   ├── pipelines/
│   │   ├── __init__.py
│   │   ├── base.py        # Abstract base pipeline
│   │   ├── pdf.py         # PDF processing pipeline
│   │   └── html.py        # HTML processing pipeline (planned)
│   └── utils.py           # Utility functions
├── tests/                  # Comprehensive test suite
│   ├── test_pdf_pipeline_unit.py
│   ├── test_chunk_utilities.py
│   └── conftest.py        # Pytest configuration and fixtures
├── main.py                 # CLI entry point (using Typer)
├── pyproject.toml          # Project dependencies and 
└── README.md
```

## 4. Installation & Usage

### Installation

This project uses `uv` for package management and requires Python 3.12+.

1.  Clone the repository.
2.  Install the dependencies:
    ```bash
    uv sync
    ```

### Usage

1.  Place your source documents (`.pdf`, `.html`, etc.) into the `input/` directory.
2.  Run the conversion from the command line, specifying the file to process:
    ```bash
    python main.py input/your_document.pdf
    ```
3.  The processed Markdown files will be saved in a dedicated subdirectory within the `output/` folder.

## 5. Development Guidelines

### Testing Strategy

This project follows comprehensive testing best practices:

- **Unit Testing**: All components have dedicated unit tests using pytest
- **Test Organization**: Tests are organized in the `tests/` directory with clear naming conventions
- **Fixtures**: Reusable test fixtures for common setup scenarios
- **Mocking**: Strategic use of mocks to isolate components and avoid external dependencies
- **Coverage**: Minimum 80% test coverage requirement with pytest-cov
- **Parametrization**: Use of pytest.mark.parametrize for testing multiple scenarios efficiently

#### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_pdf_pipeline_unit.py

# Run with verbose output
pytest -v
```

### Data Handling & Type Safety

#### Dataclasses for Configuration

We use Python's built-in `dataclasses` for configuration and data structures:

```python
from dataclasses import dataclass

@dataclass
class Config:
    chunk_size: int = 2048
    min_tokens: int = 200
    chunk_overlap: int = 100
```

**Why dataclasses over Pydantic:**
- **Simplicity**: No external dependencies for basic data structures
- **Performance**: Minimal overhead for internal configuration
- **Type Safety**: Full mypy compatibility out of the box
- **Standard Library**: Part of Python 3.7+ standard library

#### Type Checking with mypy

All code must pass mypy type checking:

```bash
# Run type checking
mypy src/

# Check specific file
mypy src/pipelines/pdf.py
```

**Type annotation requirements:**
- All public functions must have type annotations
- All class attributes must be typed
- Use `typing` module for complex types (Union, Optional, List, etc.)
- Prefer explicit types over `Any`

### Code Quality Standards

#### Pre-commit Hooks

The project uses pre-commit hooks to enforce code quality:

```bash
# Install pre-commit hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

#### Linting and Formatting

- **ruff**: For linting and code formatting
- **mypy**: For static type checking
- **pytest**: For running tests

#### Development Workflow

1. **Write tests first**: Follow TDD principles where appropriate
2. **Type annotations**: Add type hints to all new code
3. **Run tests**: Ensure all tests pass before committing
4. **Type checking**: Verify mypy passes without errors
5. **Documentation**: Update docstrings and documentation

## 6. Architecture Decisions

### Data Validation Strategy

For this project, we chose **dataclasses over Pydantic** based on:

1. **Scope**: Internal configuration doesn't require runtime validation
2. **Dependencies**: Avoiding external dependencies for simple data structures
3. **Performance**: Minimal overhead for configuration objects
4. **Type Safety**: mypy provides compile-time type checking

**When to use Pydantic:**
- External API data validation
- Complex validation rules
- JSON serialization/deserialization requirements
- Runtime data validation needs

### Testing Philosophy

Our testing approach prioritizes:

1. **Fast Tests**: Unit tests run quickly to encourage frequent execution
2. **Isolated Tests**: Each test is independent and can run in any order
3. **Clear Intent**: Test names clearly describe what is being tested
4. **Comprehensive Coverage**: All public interfaces and edge cases covered
5. **Maintainable**: Tests are easy to understand and modify

## 7. Roadmap: Future Development

The next major phase of this project is to implement an AI-augmented synthesis layer.

-   **Phase 2: AI-Powered Content Refinement**: A `--refine` flag will be added to the CLI. When used, the pipeline will feed the generated chunks to a local LLM (e.g., Mistral-7B). The LLM will be tasked with intelligently rewriting and reformatting the chunks into a single, perfectly structured, and coherent Markdown document, effectively creating a final "golden copy" of the source material.

## 8. Contributing

### Development Setup

1. Clone the repository
2. Install dependencies: `uv sync`
3. Install pre-commit hooks: `pre-commit install`
4. Run tests to verify setup: `pytest`
5. Run type checking: `mypy src/`

### Pull Request Guidelines

1. All tests must pass
2. Code must pass mypy type checking
3. Maintain or improve test coverage
4. Follow existing code style and patterns
5. Update documentation for new features

For detailed development guidelines, see [development.md](development.md).



