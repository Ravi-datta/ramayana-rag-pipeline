# Ramayana RAG Pipeline

## Objective

This repository contains a reproducible data preparation pipeline for converting a Telugu Ramayana quiz PDF into clean English chunks suitable for Retrieval-Augmented Generation ingestion.

The pipeline starts from:

data/raw/ramayana.pdf

and produces:

data/processed/final_chunks.jsonl
data/processed/final_chunks.json
data/processed/final_chunks_preview.md
data/processed/chapter_index.csv
data/processed/validation_report.json

## Source Document

The source document is a Telugu Ramayana quiz compendium organized across six Kandas:

1. Bala Kanda
2. Ayodhya Kanda
3. Aranya Kanda
4. Kishkindha Kanda
5. Sundara Kanda
6. Yuddha Kanda

The expected structure contains 99 chapters, with approximately five questions per chapter.

## Pipeline Overview

The pipeline has eight main stages:

1. PDF extraction using PyMuPDF
2. Conservative page cleaning
3. Chapter and question-answer parsing
4. DeepSeek-based Telugu-to-English chapter translation
5. Entity alias normalization
6. Semantic RAG chunk generation
7. Validation report generation
8. Human-readable Markdown preview generation

## Translation Compliance

Translation and content generation are performed only through DeepSeek.

No OpenAI, Claude, Gemini, or other LLM API is used for:

- Telugu-to-English translation
- content rewriting
- chapter summaries
- content refinement
- LLM-based entity extraction
- LLM-based theme extraction

Other tools may be used only for deterministic processing, code development, debugging, and validation.

## Chunking Strategy

The pipeline does not use blind fixed-size chunking as the primary strategy.

Chunks are generated from the document's semantic structure:

- chapter summaries
- multiple-choice QA entries
- direct-answer QA entries
- narrative-answer QA entries
- split narrative parts when needed

Each QA chunk is self-contained and includes the Kanda, chapter number, Sarga range, question, answer, entities, and source metadata.

## Entity Normalization

Ramayana names and epithets are normalized in metadata while preserving meaningful wording in the visible translated text.

For example, an epithet such as Raghunandana may remain visible in the translated passage, while the metadata records the canonical entity as Rama.

Entity aliases are configured in:

configs/entity_aliases.yaml

## Setup

Create a Python virtual environment:

python -m venv .venv

Activate it on Windows:

.venv\Scripts\activate

Install dependencies:

pip install -r requirements.txt

## Input Files

Place the source PDF here:

data/raw/ramayana.pdf

Raw PDFs are intentionally excluded from Git.

## Sample Run

Use the sample run first:

python scripts/run_pipeline.py --pdf data/raw/ramayana.pdf --output-dir data/processed --chapters 1 14 99

Inspect:

data/processed/final_chunks_preview.md
data/processed/validation_report.json

## Full Run

After the sample chapters are validated, run:

python scripts/run_pipeline.py --pdf data/raw/ramayana.pdf --output-dir data/processed

## Validation

Run:

python scripts/validate_output.py --output-dir data/processed

The validation report checks:

- detected chapters
- detected questions
- missing chapters
- chapters needing review
- translation failures
- JSON parsing failures
- chunk counts
- metadata completeness
- entity normalization warnings
- expected output files

## Output Files

final_chunks.jsonl

Primary RAG ingestion format. One JSON object per chunk.

final_chunks.json

Array-form version for easier inspection.

final_chunks_preview.md

Human-readable preview of processed content.

chapter_index.csv

Chapter-level summary with Kanda, page range, question count, and chunk count.

validation_report.json

Machine-readable quality report for parsing, translation, chunking, and metadata checks.
