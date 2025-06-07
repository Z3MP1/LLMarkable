# Project: PDF to LLM-friendly Markdown Converter

## 0. Overview

This project is a Python script that converts documents from the `input/` directory into chunked, LLM-friendly Markdown files in the `output/` directory using the `docling` library.

## 1. Objective

The goal is to process a directory of potentially large and diverse files and convert them into a format optimized for consumption by Large Language Models (LLMs). This involves not just format conversion but also intelligent chunking to respect semantic boundaries and fit within typical LLM context window limits.

## 2. Requirements

- Python 3.12+
- `docling` library
- `rich` library
- `transformers` library

