# PRD: Advanced Document Conversion & Synthesis Pipeline

## 1. Vision & Mission

To build an advanced, modular, and extensible document conversion pipeline that transforms source files (PDF, HTML, etc.) into high-quality, LLM-friendly Markdown. The system will prioritize information fidelity and leverage format-specific optimizations. It will be designed with a forward-looking architecture to optionally incorporate a local Large Language Model (LLM) for intelligent content synthesis and refinement.

## 2. Core Principles

- **Maximal Information Fidelity**: The system must be architected to prevent the loss of information. Small or fragmented content will be intelligently consolidated, not discarded.
- **Format-Specific Optimization**: The pipeline will not use a one-size-fits-all approach. It will detect the input file type and dynamically dispatch a dedicated, optimized processing pipeline to extract the best possible structured output from each source format.
- **Scalable & Maintainable Architecture**: The codebase will be refactored from a single script into a professional, modular Python package. This ensures maintainability and makes it easy to add support for new file formats or processing steps in the future.

## 3. Proposed Project Structure

To support our goals, the project will be reorganized as follows:

```
research/
├── input/                  # Source documents (PDFs, HTML, etc.)
├── output/                 # Processed markdown files
├── docling_converter/      # Main application package
│   ├── __init__.py
│   ├── main.py             # CLI entry point (using Typer/Click)
│   ├── config.py           # Centralized configuration (chunk sizes, model IDs)
│   ├── pipelines/
│   │   ├── __init__.py
│   │   ├── base_pipeline.py  # Abstract base class for all pipelines
│   │   ├── pdf_pipeline.py   # PDF-specific logic and optimizations
│   │   ├── html_pipeline.py  # HTML-specific logic
│   │   └── ...             # Future pipelines for other formats
│   ├── utils.py            # Shared helper functions (e.g., advanced chunk merging)
│   └── llm_refiner.py      # (Phase 2) Logic for interacting with the local LLM
├── pyproject.toml          # Project dependencies
├── README.md
└── ...
```

---

## 4. Phase 1: Foundational Refactoring & Optimization

This phase focuses on building a robust, non-LLM pipeline that corrects the shortcomings of the current script.

### 4.1. Intelligent Chunk Consolidation

The current filtering of small chunks is too aggressive and leads to data loss. The new strategy will be:

1.  Perform an initial chunking pass using Docling's `HybridChunker`.
2.  Implement a `consolidate_chunks` function in `utils.py`. This function will iterate through the chunks:
    - If a chunk is below `MIN_TOKENS`, it will be marked for merging.
    - It will be merged with its adjacent neighbor (previous or next), prioritizing the merge that results in a more balanced final chunk size, without exceeding `MAX_TOKENS`.
    - This ensures that short but important content (prompts, short answers, list items) is preserved by being attached to a neighbor.

### 4.2. Format-Specific Pipeline Implementation

The core of the refactoring is the move to a pipeline-based architecture.

1.  **`base_pipeline.py`**: An abstract base class `BasePipeline` will define the required interface, e.g., a `process()` method.
2.  **`pdf_pipeline.py`**: The `PdfPipeline` will be implemented to properly use `PdfFormatOption`, re-enabling optimizations for table structure recognition and other PDF-specific features.
3.  **`html_pipeline.py`**: The `HtmlPipeline` will handle HTML files. Initially, it can use the default Docling converter settings, which are already well-optimized for HTML.
4.  **`main.py`**: The main CLI entry point will:
    - Accept a file path as an argument.
    - Detect the file's extension (`.pdf`, `.html`, etc.).
    - Instantiate the corresponding pipeline class (`PdfPipeline`, `HtmlPipeline`).
    - Call the `process()` method on the instantiated pipeline object.

---

## 5. Phase 2: AI-Augmented Content Synthesis

This phase introduces an optional, powerful refinement step using a local LLM. It assumes Phase 1 is complete. The goal is to transform a set of chunks into a single, coherent, and beautifully formatted Markdown document.

### 5.1. The Role of the LLM & Impact on Chunking

With an LLM for refinement, the purpose of the initial "chunking" shifts. It's no longer about producing human-readable final chunks, but about creating logically-grouped "information blocks" for the LLM. We can likely relax the chunking rules slightly, as the LLM's job is to stitch them together perfectly. The `HybridChunker` remains an excellent choice for this task as it respects semantic boundaries.

### 5.2. Recommended Model & Integration Strategy

- **Model**: **Mistral-7B-Instruct** (or a similar high-performing 7B model). It offers an excellent balance of performance and resource requirements and can be effectively run with 8-bit quantization on a 12GB VRAM GPU. It excels at following complex instructions for formatting and synthesis.
- **Integration**: We will use the **`langchain-docling`** and **`langchain`** libraries. As you noted, this is the documented, best-practice approach within the Docling ecosystem. The LLM can be exposed via any OpenAI-compatible local server (like Ollama, vLLM, or TGW), and we will use LangChain's `ChatOpenAI` or a similar client to interact with it, simply by pointing the client to the local server's URL. This decouples our code from the specific server implementation.

### 5.3. The `--refine` Workflow

A new `--refine` flag will be added to the CLI. When active:

1.  The appropriate file pipeline (e.g., `PdfPipeline`) runs its conversion and chunking process as normal.
2.  Instead of saving the individual chunks, the pipeline gathers the text content of all generated chunks.
3.  This list of text content is passed to a new function: `refine_document(content: list[str])` in `llm_refiner.py`.
4.  `refine_document` uses LangChain to:
    - Construct a detailed prompt using the content.
    - Send the request to the local LLM endpoint.
    - Receive the single, synthesized Markdown string.
5.  The `main.py` script saves this final string to a single file, e.g., `output/my_document/document_refined.md`.

### 5.4. Proposed System Prompt for LLM Refinement

```markdown
You are an expert technical writer and document synthesist. Your task is to transform a series of raw text chunks, extracted from a source document, into a single, clean, coherent, and well-structured Markdown document.

**Your Instructions:**

1.  **Synthesize, Don't Summarize**: Combine all provided chunks into a single narrative. Do not leave out any information, especially code blocks, user questions, or specific details. The goal is a complete and faithful reconstruction.
2.  **Impose Logical Structure**: Analyze the content and apply appropriate Markdown formatting. Use headings (`#`, `##`), subheadings, bullet points (`-`), numbered lists, and bold text to create a clear and readable hierarchy.
3.  **Maintain Original Intent**: Preserve the original tone and logical flow of the content. If the source is a conversation, maintain the turn-by-turn structure.
4.  **Clean Up Artifacts**: Remove any repetitive headers, footers, or conversion artifacts that may appear in the chunks. Ensure seamless transitions between what were originally separate chunks.
5.  **Format Code Correctly**: Identify any code snippets and format them in properly fenced Markdown code blocks with language identifiers if possible.

**Source Content Chunks:**

---
{chunk_content}
---

**Final Markdown Document:**
