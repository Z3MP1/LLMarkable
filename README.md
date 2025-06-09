# LLMarkable

**Transform documents into LLM-friendly, remarkable outputs**

## 1. Overview

LLMarkable provides a sophisticated, modular pipeline for converting various source documents (such as PDF and HTML) into high-quality, LLM-friendly Markdown. It moves beyond simple conversion by employing a format-specific architecture to maximize quality and an intelligent chunking strategy to ensure no information is lost.

The core objective is to produce structured, coherent, and semantically rich Markdown files that are optimized for Retrieval-Augmented Generation (RAG) and other LLM-based applications.

## 2. Core Features

- **Modular & Scalable Architecture**: The codebase is organized into a clean Python package, making it easy to maintain and extend with new file formats or processing capabilities.
- **Format-Specific Pipelines**: The system auto-detects the input file type and dispatches a dedicated, optimized pipeline (e.g., for PDF, HTML) to ensure the highest quality conversion by leveraging format-specific features like `PdfFormatOption`.
- **Intelligent Chunk Consolidation**: To prevent information loss, the pipeline avoids simply discarding small chunks. Instead, it intelligently merges them with adjacent chunks, ensuring that short but important pieces of content are preserved.
- **Comprehensive Error Handling**: Robust exception handling with custom error types for different failure scenarios, ensuring graceful degradation and informative error messages.
- **Type-Safe Development**: Full type annotation coverage with mypy static type checking ensures code reliability and maintainability.
- **Comprehensive Testing**: Pytest-based testing strategy with fixtures, parametrization, and comprehensive coverage reporting.

## 3. Project Structure

The project is organized into a modular package structure:

```
llmarkable/
├── input/                          # Source documents (PDFs, HTML, etc.)
├── output/                         # Processed markdown files
├── src/                            # Main application package
│   ├── __init__.py
│   ├── config.py                   # Configuration dataclasses with validation
│   ├── exceptions.py               # Custom exception hierarchy
│   ├── serializers.py              # Chunking Serializers 
│   ├── utils.py                    # Chunk utilities and tokenization
│   ├── pipelines/
│   │   ├── __init__.py
│   │   ├── base.py                 # Abstract base pipeline
│   │   ├── factory.py              # Pipeline factory and format detection
│   │   ├── pdf.py                  # PDF processing pipeline
│   │   └── html.py                 # HTML processing pipeline
│   └── synthesis/
│       ├── __init__.py
│       ├── base.py                 # Abstract base synthesis provider
│       ├── openai.py               # OpenAI-based synthesis provider
│       ├── anthropic.py            # Anthropic-based synthesis provider
│       └── gemini.py               # Gemini-based synthesis provider
│
├── tests/                          # Comprehensive test suite
│   ├── conftest.py                 # Pytest configuration and fixtures
│   ├── test_config.py              # Configuration validation tests
│   ├── test_pdf_pipeline_unit.py   # PDF pipeline unit tests
│   ├── test_html_pipeline_unit.py  # HTML pipeline unit tests
│   ├── test_chunk_utilities.py     # Utility function tests
│   ├── test_exceptions.py          # Exception handling tests
│   └── htmlcov/                    # Coverage reports (generated)
├── main.py                         # CLI entry point (using Typer)
├── pyproject.toml                  # Project dependencies and configuration
└── README.md                       
```

## 4. Installation & Usage

### Installation

This project uses `uv` for package management and requires Python 3.12+.

1.  Clone the repository.
2.  Install `uv`:
    ```bash
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```
3.  Install the dependencies:
    ```bash
    uv sync
    ```

### Usage

#### Basic Conversion

Convert a document using default settings:
```bash
python main.py convert input/document.pdf
```

#### Advanced Options

```bash
# Convert with custom chunk size and output directory
python main.py convert document.pdf --output-dir results/ --chunk-size 1024

# Generate individual chunk files instead of consolidated output
python main.py convert document.html --individual-chunks

# Enable verbose output for detailed processing information
python main.py convert document.pdf --verbose

# Customize chunking parameters
python main.py convert document.pdf --min-tokens 100 --chunk-overlap 150
```

#### Supported Formats

Check supported file formats and current configuration:
```bash
python main.py info
```

## 5. Development Status

### ✅ Completed Components

#### Core Infrastructure
- **Project Structure**: Modern Python package with `src/` layout and `pipelines/` subdirectory
- **Dependencies**: Configured with `docling`, `typer`, `rich`, `transformers` via `uv`
- **Configuration**: Research-driven `Config` dataclass with comprehensive validation
- **Pipeline Factory**: Auto-detection and routing system for different file formats

#### Processing Pipelines
- **PDF Processing Pipeline**: Complete implementation with Docling integration
- **HTML Processing Pipeline**: Complete implementation with paragraph-based chunking
- **Chunking Strategy**: Intelligent chunking with token-based sizing and overlap handling
- **Quality Filtering**: Content filtering based on token count and content quality

#### Error Handling & Validation
- **Custom Exception Hierarchy**: Comprehensive error types for different failure scenarios
- **Input Validation**: File existence, format support, parameter range validation
- **Graceful Degradation**: Fallback mechanisms and informative error messages
- **Configuration Validation**: Comprehensive parameter validation with clear error messages

#### CLI Interface
- **Complete Implementation**: Typer-based CLI with Rich progress indicators
- **Commands**: `convert` (main processing) and `info` (format information)
- **Features**: Parameter overrides, verbose mode, comprehensive error handling
- **User Experience**: Rich formatting with emojis, colors, and structured output

#### Output Generation System
- **Dual Mode Support**: Individual chunk files or consolidated output
- **Rich Metadata**: YAML-style headers with token counts, timestamps, source info
- **Cross-Platform Compatibility**: Proper filename sanitization for all OSes
- **Directory Structure**: Clean organization with configurable output modes

#### Testing Infrastructure
 - **Comprehensive Coverage**: 104 tests covering all components
- **Test Organization**: Dedicated `tests/` directory with proper structure
- **Quality Standards**: Unit tests only, fast execution, comprehensive mocking
- **Coverage Reporting**: HTML coverage reports with detailed metrics

#### Quality Assurance
- **Type Safety**: mypy strict mode with full type annotations
- **Code Quality**: ruff linting with project-specific rules
- **Exception Testing**: Comprehensive error scenario testing

### 🎯 Feature Highlights

#### Intelligent Chunking
- **Token-Based Processing**: Configurable tokenizer model (default `BAAI/bge-small-en-v1.5`) for precise token counting
- **Research-Driven Defaults**: Chunk size (2048 tokens), min tokens (330), overlap (100)
- **Content Preservation**: Intelligent merging of small chunks to prevent information loss
- **Quality Filtering**: Automatic filtering of low-quality or minimal content

#### Robust Error Handling
- **Custom Exception Types**: Specific errors for validation, file access, conversion, chunking
- **Informative Messages**: Clear error descriptions with actionable guidance
- **Graceful Fallbacks**: Fallback chunking strategies when primary methods fail
- **Comprehensive Validation**: Input validation with detailed parameter checking

#### Professional Testing
 - **104 Passing Tests**: Complete coverage of all components and edge cases
- **Fast Execution**: All tests run in under 4 seconds
- **Proper Isolation**: Unit tests with comprehensive mocking
- **Realistic Scenarios**: Tests use actual tokenizer behavior and realistic data

## 6. Development Guidelines

### Testing Strategy

This project follows comprehensive testing best practices:

- **Unit Testing Only**: All tests use mocks to avoid external dependencies
- **Fast Execution**: Tests run in milliseconds (under 100ms each)
- **Test Organization**: Tests are organized in the `tests/` directory with clear naming conventions
- **Fixtures**: Reusable test fixtures for common setup scenarios in `conftest.py`
 - **Coverage**: Comprehensive test coverage with 104 tests across all components
- **Parametrization**: Use of pytest.mark.parametrize for testing multiple scenarios efficiently

#### Running Tests

```bash
# Run all tests
pytest

# Run with coverage (reports to tests/htmlcov/)
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
    min_tokens: int = 330
    chunk_overlap: int = 100
    
    def validate(self) -> None:
        """Comprehensive validation with specific error messages."""
        # ... validation logic
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

### Code Quality Standards

#### Development Tools

- **ruff**: For linting and code formatting
- **mypy**: For static type checking
- **pytest**: For running tests with coverage
- **uv**: For fast package management

#### Development Workflow

1. **Write tests first**: Follow TDD principles where appropriate
2. **Type annotations**: Add type hints to all new code
3. **Run tests**: Ensure all tests pass before committing
4. **Type checking**: Verify mypy passes without errors
5. **Documentation**: Update docstrings and documentation

## 7. Architecture Decisions

### Exception Handling Strategy

Comprehensive custom exception hierarchy:

```python
# Custom exception types for specific scenarios
class LLMarkableError(Exception): ...
class ValidationError(LLMarkableError): ...
class FileAccessError(LLMarkableError): ...
class ConversionError(LLMarkableError): ...
class ChunkingError(ConversionError): ...
class TokenizerError(LLMarkableError): ...
```

### Testing Philosophy

Our testing approach prioritizes:

1. **Fast Tests**: Unit tests run quickly to encourage frequent execution
2. **Isolated Tests**: Each test is independent and can run in any order
3. **Clear Intent**: Test names clearly describe what is being tested
4. **Comprehensive Coverage**: All public interfaces and edge cases covered
5. **Maintainable**: Tests are easy to understand and modify

## 8. Roadmap: Future Development

### Phase 2: AI-Powered Content Refinement

The next major phase will implement an AI-augmented synthesis layer:

- **LLM Integration**: Local model support (Mistral-7B, Llama, etc.)
- **Content Refinement**: `--refine` flag for intelligent rewriting
- **Coherent Output**: Single, perfectly structured Markdown document
- **Prompt Engineering**: Optimized prompts for different document types

### Extensibility Plans

- **New File Formats**: DOCX, PPTX, images via plugin architecture
- **Configuration Files**: YAML/TOML support for complex configurations
- **Batch Processing**: Multiple file processing capabilities
- **API Interface**: REST API for programmatic usage

## 9. Contributing

### Development Setup

1. Clone the repository
2. Install dependencies: `uv sync`
3. Run tests to verify setup: `pytest`
4. Run type checking: `mypy src/`

### Pull Request Guidelines

1. All tests must pass
2. Code must pass mypy type checking
3. Maintain or improve test coverage
4. Follow existing code style and patterns
5. Update documentation for new features

For detailed development guidelines, see [development.md](development.md).

## 10. Current Test Metrics

 - **Total Tests**: 104 passing
- **Execution Time**: Under 4 seconds for full suite
- **Components Covered**:
  - Configuration system (20 tests)
  - PDF pipeline (16 tests)
  - HTML pipeline (22 tests)
  - Chunk utilities (25 tests)
  - Exception handling (20 tests)
- **Type Safety**: 100% mypy compliance
- **Quality Standards**: All tests use proper mocking and isolation

## 11. Technical Specifications

### Tokenization
- **Default Model**: BAAI/bge-small-en-v1.5 (384 dimensions, 512 token limit)
- **Purpose**: Semantic embeddings optimized for retrieval tasks
- **Performance**: Fast inference with good semantic understanding

### Configuration Defaults
- **Chunk Size**: 2048 tokens (optimal for LLM context windows)
- **Min Tokens**: 330 tokens (research-backed threshold for meaningful chunks)
- **Chunk Overlap**: 100 tokens (context preservation between chunks)
- **Output Dir**: `output/` (organized by document name)

### Supported Formats
- **PDF**: Complete support via Docling with format-specific optimizations
- **HTML**: Complete support with paragraph-based chunking
- **Extensible**: Plugin architecture ready for additional formats



