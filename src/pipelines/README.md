# LLMarkable Pipelines Documentation

## Overview

The `src/pipelines/` package provides a comprehensive document conversion system that transforms various file formats into LLM-friendly Markdown chunks. Built on [Docling](https://github.com/docling-project/docling) with extensive optimizations for performance, accuracy, and reliability.

## 🏗️ Architecture

### Design Patterns

- **Abstract Factory Pattern**: Centralized pipeline creation via `factory.py`
- **Strategy Pattern**: Format-specific processing strategies per pipeline  
- **Template Method**: Common interface with format-specific implementations
- **Registry Pattern**: Dynamic pipeline registration and discovery

### Core Components

```
src/pipelines/
├── base.py          # Abstract base class defining pipeline interface
├── factory.py       # Pipeline factory with format detection and creation
├── pdf.py           # PDF processing with advanced table extraction
├── html.py          # HTML processing with structure preservation 
├── docx.py          # Microsoft Word document processing
├── pptx.py          # Microsoft PowerPoint presentation processing
├── image.py         # Image OCR processing (PNG, JPEG, TIFF, BMP, GIF)
└── __init__.py      # Package exports and public API
```

## 📋 Supported Formats

### Document Formats
- **PDF** (`.pdf`) - Advanced table extraction, OCR, structure preservation
- **HTML** (`.html`, `.htm`) - Structure-aware conversion with paragraph chunking
- **DOCX** (`.docx`) - Microsoft Word with metadata preservation
- **PPTX** (`.pptx`) - Microsoft PowerPoint with slide structure analysis

### Image Formats (OCR-enabled)
- **PNG** (`.png`) - High-quality OCR with layout detection
- **JPEG** (`.jpg`, `.jpeg`) - Compressed image OCR processing
- **TIFF** (`.tif`, `.tiff`) - Multi-page and high-resolution support
- **BMP** (`.bmp`) - Bitmap image OCR processing
- **GIF** (`.gif`) - Animated and static GIF OCR

**Total**: 12 file extensions supported across 5 specialized pipelines.

## 🔧 Pipeline Implementations

### PDF Pipeline (`pdf.py`) 

**Advanced Optimization**: State-of-the-art PDF processing with Docling v1.16.0+ features.

**Optimization Features**:
- **TableFormer ACCURATE Mode**: Superior table extraction quality
- **Smart Cell Matching**: Prevents column merging errors  
- **Multi-language OCR**: Configurable language support
- **Hybrid Chunking**: `HybridChunker` with `HierarchicalChunker` fallback
- **Memory Management**: File size limits (20MB) and page limits (1000 pages)

### HTML Pipeline (`html.py`)

**Structure-Aware Processing**: Preserves HTML document structure while creating manageable chunks.

**Features**:
- **Document Structure Preservation**: Maintains HTML hierarchy
- **Paragraph-Based Chunking**: Natural text boundaries  
- **Content Filtering**: Configurable minimum paragraph length
- **Markdown Export**: Clean conversion to LLM-friendly format

### DOCX Pipeline (`docx.py`)

**Microsoft Word Processing**: Comprehensive Word document support with metadata preservation.

**Capabilities**:
- **Metadata Preservation**: Document properties, styles, structure
- **Intelligent Chunking**: Hybrid strategy with hierarchical fallback
- **Content Analysis**: Document complexity assessment
- **Memory Optimization**: Large document handling (>10MB threshold)

### PPTX Pipeline (`pptx.py`)

**PowerPoint Processing**: Slide-aware processing with presentation structure analysis.

**Features**:
- **Slide Structure Analysis**: Maintains presentation flow
- **Content Density Analysis**: Slide complexity assessment
- **Media Integration**: Handles embedded content
- **Large Presentation Support**: 15MB threshold for media-rich files

### Image Pipeline (`image.py`)

**OCR Processing**: Advanced optical character recognition for 7 image formats.

**Capabilities**:
- **Multi-Format Support**: PNG, JPEG, TIFF, BMP, GIF
- **High-Quality OCR**: Docling's advanced text extraction
- **Layout Detection**: Preserves document structure from images
- **Large Image Handling**: 25MB threshold for high-resolution files

## 🏭 Factory System (`factory.py`)

**Centralized Pipeline Management**: Single source of truth for format detection and pipeline creation.

### Registry Pattern

```python
_PIPELINE_REGISTRY: dict[str, type[BasePipeline]] = {
    ".pdf": PDFPipeline,
    ".html": HTMLPipeline, ".htm": HTMLPipeline,
    ".docx": DocxPipeline,
    ".pptx": PPTXPipeline,
    ".png": ImagePipeline, ".jpg": ImagePipeline, # ... other image formats
}
```

### Factory Functions

```python
# Core factory operations
create_pipeline(file_path: Path, config: Config) -> BasePipeline
get_supported_formats() -> list[str]
is_supported_format(file_path: Path) -> bool

# Advanced registry management  
register_pipeline(extension: str, pipeline_class: type[BasePipeline]) -> None
```

## ⚙️ Configuration Integration

### Pipeline-Specific Parameters

Each pipeline leverages centralized configuration from `src/config.py`:

```python
@dataclass
class Config:
    # Core chunking parameters
    chunk_size: int = 2048               # Target chunk size
    min_tokens: int = 330                # Minimum useful chunk size
    
    # Memory management
    max_file_size_mb: int = 20           # Standard file size limit
    large_image_threshold_mb: int = 25   # Image-specific threshold
    
    # Pipeline-specific tuning
    pdf_complex_table_min_rows: int = 10
    html_min_paragraph_length: int = 50
    preserve_tables: bool = True         # Advanced table extraction
```

## 🔄 Chunking Strategies

### Hybrid Chunking Architecture

All pipelines implement intelligent chunking with fallback mechanisms:

```python
def _chunk_document(self, docling_doc: DoclingDocument) -> list[BaseChunk]:
    try:
        # Primary: HybridChunker (optimal for most documents)
        chunks = list(self.hybrid_chunker.chunk(dl_doc=docling_doc))
        return chunks
    except Exception as err:
        # Fallback: HierarchicalChunker (robust alternative)
        chunks = list(self.hierarchical_chunker.chunk(docling_doc))
        return chunks
```

## 🎯 Performance Optimizations

### Memory Management

```
File size limits per format:
- PDF/DOCX/PPTX: 20MB (20,971,520 bytes)
- Images: 25MB (26,214,400 bytes)

Processing limits:
- PDF Pages: 1000 pages maximum
- Batch Size: 50 chunks per batch
```

### Quality Enhancements

- **Content Density Filtering**: Removes low-information chunks
- **Trailing Chunk Consolidation**: Merges small end chunks
- **Token-Based Validation**: Ensures chunks meet minimum requirements
- **Metadata Enrichment**: Comprehensive chunk metadata for downstream processing

## 🧪 Testing Strategy

### Test Coverage

**140 comprehensive tests** covering:
- Unit tests for each pipeline class
- Factory pattern functionality
- Error handling scenarios  
- Configuration validation
- Integration test scenarios

### Quality Assurance

- **Mock-Based Testing**: No external dependencies in unit tests
- **Fast Execution**: All tests complete under 5 seconds  
- **100% Type Safety**: mypy strict mode compliance
- **100% Code Quality**: ruff linting compliance

## 📊 Usage Examples

### Basic Pipeline Usage

```python
from pathlib import Path
from src.config import Config
from src.pipelines.factory import create_pipeline

# Initialize configuration
config = Config(chunk_size=2048, preserve_tables=True, verbose=True)

# Create pipeline for file
file_path = Path("document.pdf")
pipeline = create_pipeline(file_path, config)

# Process document
chunks = pipeline.process(file_path)

# Access results
for chunk in chunks:
    content = chunk["content"]
    metadata = chunk["metadata"]
    print(f"Chunk {metadata['chunk_id']}: {metadata['token_count']} tokens")
```

### Advanced Factory Usage

```python
from src.pipelines.factory import get_supported_formats, is_supported_format

# Check format support
supported = get_supported_formats()
print(f"Supported formats: {supported}")

# Check specific file
if is_supported_format(Path("doc.pdf")):
    print("PDF format is supported")
```

## 🔍 Best Practices

### Configuration Management

1. **Use Config Dataclass**: Centralized, validated configuration
2. **Parameter Validation**: Comprehensive validation with informative errors
3. **Memory Limits**: Set appropriate thresholds per format type

### Error Handling

1. **Specific Exceptions**: Use custom exception hierarchy
2. **Error Context**: Include file paths and processing stages
3. **Graceful Fallbacks**: Implement chunking strategy fallbacks

### Performance Optimization

1. **Token-Based Chunking**: Use precise token counting for LLM compatibility
2. **Memory Management**: Monitor and limit resource usage
3. **Quality Filtering**: Remove low-value chunks early in pipeline

## 🏆 Quality Metrics

### Code Quality
- **Type Safety**: 100% mypy strict compliance
- **Code Style**: 100% ruff compliance  
- **Test Coverage**: 140 tests, 100% pass rate

### Feature Completeness
- **Format Coverage**: 12 file extensions across 5 pipelines
- **Processing Quality**: Advanced table extraction, OCR, structure preservation
- **Error Handling**: Comprehensive exception hierarchy

---

**Built with**: Python 3.12, Docling, HuggingFace Transformers, Rich  
**Quality**: mypy strict, ruff compliant, 140 tests passing  
**Status**: Production-ready, actively maintained 