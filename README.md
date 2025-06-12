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
- **AI-Powered Content Synthesis**: Optional LLM-powered chunk refinement and enhancement, with format-specific prompt templates and configurable synthesis levels (light, moderate, aggressive).
- **Provider-Agnostic Token Management**: TokenManager class for batching, caching, and cost estimation across LLM providers (OpenAI, Ollama, etc.).
- **Comprehensive LLM Integration Tests**: End-to-end tests with mock LLM providers, covering chunk refinement, metadata injection, error handling, and performance.
- **Dynamic Prompt Management**: All LLM synthesis uses dynamic, format/task/level-specific prompt loading from `/prompts` via PromptManager. No hardcoded prompts remain.
- **Prompt Coverage & Validation**: Automated tests ensure all required prompt templates (summarize, reformat, correct_grammar; light/moderate/aggressive) exist for every supported format. Prompt coverage is enforced and extensible.
- **Content Validation**: ContentValidator provides real readability scoring (Flesch Reading Ease) and stubs for future factual/structural/semantic checks.
- **OpenAIProvider**: Streaming, robust error handling, tiktoken-based token counting, async support, and comprehensive tests.
- **Type-Safe & Lint-Clean**: 100% mypy strict, ruff compliant, all tests pass. No unused ignores or type errors remain.
- **Extensible LLM Integration**: Ready for Anthropic and Gemini provider integration, as well as new input formats (EPUB, TXT, CSV, XML, JSON, etc.).

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
│       ├── engine.py               # Content synthesis engine
│       ├── token_manager.py        # Provider-agnostic token management
│       ├── prompt_manager.py       # Prompt templates and engineering
│       ├── providers/              # LLM provider implementations (OpenAI, Ollama, etc.)
│       └── ...
├── tests/                          # Comprehensive test suite
│   ├── conftest.py                 # Pytest configuration and fixtures
│   ├── test_config.py              # Configuration validation tests
│   ├── test_pdf_pipeline_unit.py   # PDF pipeline unit tests
│   ├── test_html_pipeline_unit.py  # HTML pipeline unit tests
│   ├── test_chunk_utilities.py     # Utility function tests
│   ├── test_exceptions.py          # Exception handling tests
│   ├── test_llm_integration.py     # End-to-end LLM synthesis and error tests
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
 - **Comprehensive Coverage**: 150+ tests covering all components, including LLM-powered synthesis and error scenarios
- **Test Organization**: Dedicated `tests/` directory with proper structure
- **Quality Standards**: Unit and integration tests only, fast execution, comprehensive mocking
- **Coverage Reporting**: HTML coverage reports with detailed metrics

#### LLM Integration (Phase 2, In Progress)
- **Synthesis Engine**: Optional LLM-powered chunk refinement, with format-specific prompt templates and configurable synthesis levels
- **TokenManager**: Provider-agnostic token counting, batching, caching, and cost estimation (OpenAI, Ollama, etc.)
- **Comprehensive LLM Integration Tests**: End-to-end tests with mock LLM providers, covering chunk refinement, metadata injection, error handling, and performance
- **OpenAIProvider**: Integration in progress (tiktoken-based token counting, robust error handling, async support)

## 6. Development Guidelines

### Testing Strategy

This project follows comprehensive testing best practices:

- **Unit & Integration Testing**: All tests use mocks to avoid external dependencies
- **Fast Execution**: Tests run in milliseconds (under 100ms each)
- **Test Organization**: Tests are organized in the `tests/` directory with clear naming conventions
- **Fixtures**: Reusable test fixtures for common setup scenarios in `conftest.py`
 - **Coverage**: Comprehensive test coverage with 150+ tests across all components
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

## 7. Roadmap: Future Development

### Phase 2: AI-Powered Content Refinement

The next major phase will implement an AI-augmented synthesis layer:

- **LLM Integration**: Local model support (Mistral-7B, Llama, etc.), OpenAI (complete), Anthropic and Gemini (planned)
- **Content Refinement**: `--refine` flag for intelligent rewriting
- **Coherent Output**: Single, perfectly structured Markdown document
- **Prompt Engineering**: Optimized prompts for different document types, enforced by automated tests
- **Validation**: Automated readability scoring and prompt coverage checks
- **OpenAIProvider**: Complete (streaming, error handling, token counting, async, tests)
- **AnthropicProvider & GeminiProvider**: Planned (API integration, prompt support, tests)

### Extensibility Plans

- **New File Formats**: DOCX, PPTX, images (complete); EPUB, TXT, CSV, XML, JSON (planned)
- **Configuration Files**: YAML/TOML support for complex configurations
- **Batch Processing**: Multiple file processing capabilities
- **API Interface**: REST API for programmatic usage

## 8. Technical Specifications

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

## 9. Advanced LLM Synthesis: Streaming, Performance, and Troubleshooting

### Streaming with OpenAIProvider

You can stream LLM responses token-by-token using the `stream_generate` method of `OpenAIProvider`:

```python
from src.synthesis.providers.openai import OpenAIProvider
from src.config import Config
import asyncio

async def stream_example():
    config = Config.default()
    config.openai_api_key = "sk-..."
    provider = OpenAIProvider(config)
    async for chunk in provider.stream_generate("Summarize this text."):
        print(chunk, end="", flush=True)

# Run the example
# asyncio.run(stream_example())
```

This is useful for large outputs or interactive applications.

### Performance Monitoring

The `ContentSynthesizer.refine_chunk` method now returns both the refined content and the time taken (in seconds):

```python
result, elapsed = await synthesizer.refine_chunk(chunk, config)
print(f"Synthesis took {elapsed:.2f} seconds")
```

This helps you monitor and optimize LLM usage.

### Best Practices for Large Documents
- Use token-based chunking (default: 2048 tokens) to avoid context overflows.
- For very large documents, process in batches and use streaming to avoid memory spikes.
- Monitor token usage and cost with the `TokenManager`.
- Adjust `max_tokens` and `temperature` in config for your use case.

### Migration Guide: Phase 1 → Phase 2
- **Config changes:** New fields for LLM provider, model, synthesis options (see `src/config.py`).
- **New features:** LLM-powered synthesis, streaming, token/cost tracking, advanced error handling.
- **CLI:** Use `--refine` and provider/model flags for synthesis.
- **Testing:** All LLM features are mock-tested for reliability.

### Troubleshooting LLM Issues
- **Timeouts:** Increase `max_retries` or check network/API status.
- **Rate limits:** Use exponential backoff (built-in), or reduce request frequency.
- **Memory errors:** Lower chunk size, use streaming, or process in smaller batches.
- **Authentication:** Ensure API keys are set and valid (see `validate_connection`).
- **Model errors:** Check model name/version and provider documentation.

### Benchmarks (Coming Soon)
Performance benchmarks for synthesis speed, memory usage, and cost will be published as more data is collected.



