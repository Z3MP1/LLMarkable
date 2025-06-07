# LLMarkable

**Transform documents into LLM-friendly, remarkable outputs**

## 1. Overview

LLMarkable provides a sophisticated, modular pipeline for converting various source documents (such as PDF and HTML) into high-quality, LLM-friendly Markdown. It moves beyond simple conversion by employing a format-specific architecture to maximize quality and an intelligent chunking strategy to ensure no information is lost.

The core objective is to produce structured, coherent, and semantically rich Markdown files that are optimized for Retrieval-Augmented Generation (RAG) and other LLM-based applications.

## 2. Core Features

- **Modular & Scalable Architecture**: The codebase is organized into a clean Python package, making it easy to maintain and extend with new file formats or processing capabilities.
- **Format-Specific Pipelines**: The system auto-detects the input file type and dispatches a dedicated, optimized pipeline (e.g., for PDF, HTML) to ensure the highest quality conversion by leveraging format-specific features like `PdfFormatOption`.
- **Intelligent Chunk Consolidation**: To prevent information loss, the pipeline avoids simply discarding small chunks. Instead, it intelligently merges them with adjacent chunks, ensuring that short but important pieces of content are preserved.

## 3. Project Structure

The project is organized into a modular package structure:

```
llmarkable/
├── input/                  # Source documents (PDFs, HTML, etc.)
├── output/                 # Processed markdown files
├── src/                    # Main application package
│   ├── __init__.py
│   ├── pipelines/
│   │   ├── __init__.py
│   │   ├── base_pipeline.py
│   │   ├── pdf_pipeline.py
│   │   └── html_pipeline.py
│   └── utils.py
├── main.py                 # CLI entry point (using Typer)
├── pyproject.toml          # Project dependencies
└── README.md
```

## 4. Installation & Usage

### Installation

This project uses `uv` for package management.

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

## 5. Roadmap: Future Development

The next major phase of this project is to implement an AI-augmented synthesis layer.

-   **Phase 2: AI-Powered Content Refinement**: A `--refine` flag will be added to the CLI. When used, the pipeline will feed the generated chunks to a local LLM (e.g., Mistral-7B). The LLM will be tasked with intelligently rewriting and reformatting the chunks into a single, perfectly structured, and coherent Markdown document, effectively creating a final "golden copy" of the source material.



