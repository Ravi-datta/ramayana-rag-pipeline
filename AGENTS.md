# Project Implementation Guide

## Project

ramayana-rag-pipeline

## Objective

Build a reproducible data preparation pipeline that converts a Telugu Ramayana quiz PDF into clean English RAG-ready chunks.

Input:

data/raw/ramayana.pdf

Final outputs:

data/processed/final_chunks.jsonl
data/processed/final_chunks.json
data/processed/final_chunks_preview.md
data/processed/chapter_index.csv
data/processed/validation_report.json

## Compliance Requirements

Translation and content generation must use DeepSeek only.

Do not use OpenAI, Claude, Gemini, or any other LLM API for:

- Telugu-to-English translation
- content rewriting
- chapter summaries
- content refinement
- LLM-based entity extraction
- LLM-based theme extraction

No API keys may be hardcoded. Use environment variables only.

## Source Document Assumptions

The source PDF is a Telugu Ramayana quiz compendium organized into six Kandas:

1. Bala Kanda: chapters 1 to 13
2. Ayodhya Kanda: chapters 14 to 32
3. Aranya Kanda: chapters 33 to 46
4. Kishkindha Kanda: chapters 47 to 58
5. Sundara Kanda: chapters 59 to 73
6. Yuddha Kanda: chapters 74 to 99

Expected total chapters: 99

Each chapter generally contains five questions.

Expected approximate total questions: 495

## Pipeline Stages

1. PDF extraction
2. Page cleaning
3. Chapter parsing
4. QA parsing
5. DeepSeek chapter translation
6. Entity alias normalization
7. Semantic chunk generation
8. Validation report generation
9. Markdown preview generation

## Extraction Requirements

Use PyMuPDF as the primary extractor.

Write extracted pages to:

data/extracted/pages.jsonl

Each page record must include:

- pdf_page_index
- printed_page_number
- raw_text
- extraction_method

OCR is not used by default. It should only be considered if a page has no extractable text.

## Cleaning Requirements

Write cleaned pages to:

data/extracted/pages_clean.jsonl

Cleaning must be conservative.

Preserve:

- Telugu content
- question numbers
- answer choices
- answer keys
- Kanda names
- chapter names
- Sarga ranges

Do not rewrite Telugu before translation.

## Parsing Requirements

Write parsed Telugu chapters to:

data/intermediate/chapters_telugu.json

Each chapter object must include:

- chapter_number
- chapter_id
- kanda_telugu
- kanda_english
- kanda_order
- sarga_range
- chapter_title_telugu
- source_pdf_pages
- printed_page_numbers
- raw_telugu_text
- questions
- parser_warnings
- needs_review

Parser fallback rules:

- If chapter detection fails, use Kanda ranges and nearby heading patterns to recover candidate chapters.
- If a chapter does not contain five detected questions, mark it as needs_review: true.
- If answer options cannot be separated confidently, preserve the raw block and attach a parser warning.
- Never discard raw Telugu text during parsing.

## Translation Requirements

Translate one parsed chapter per DeepSeek call.

Do not translate:

- the whole PDF in one call
- page by page
- small isolated fragments without chapter context

Cache translated chapters in:

data/intermediate/translated_chapters/

Write combined translated output to:

data/intermediate/chapters_english.json

Write translation audit logs to:

data/intermediate/translation_audit.jsonl

The DeepSeek client must support:

- environment variable based API key loading
- retries with exponential backoff
- timeout handling
- JSON response parsing
- markdown fence stripping
- per-chapter failure reporting
- cached chapter reuse unless forced

## Entity Normalization Requirements

Use:

configs/entity_aliases.yaml

Visible translated text should preserve meaningful epithets.

Metadata should normalize aliases to canonical entities.

Example:

Visible text may preserve:

Raghunandana, Rama of the Raghu lineage

Metadata should include:

Rama

## Chunking Requirements

Use semantic chunking based on the source structure.

Allowed chunk types:

- preface
- table_of_contents
- chapter_summary
- qa_multiple_choice
- qa_direct_answer
- qa_narrative
- qa_narrative_part

Every QA chunk must be self-contained and include:

- Kanda
- chapter number
- Sarga range
- primary entities
- question
- answer
- source page metadata

Do not create answer-only chunks.

## Validation Requirements

Write:

data/processed/validation_report.json

The validation report must include:

- detected chapter count
- detected question count
- missing chapters
- chapters with question count issues
- translation failures
- JSON parse failures
- chunk counts by type
- entity normalization warnings
- output file checks

The pipeline should not silently pass bad output.

## Required Commands

Sample run:

python scripts/run_pipeline.py --pdf data/raw/ramayana.pdf --output-dir data/processed --chapters 1 14 99

Full run:

python scripts/run_pipeline.py --pdf data/raw/ramayana.pdf --output-dir data/processed

Validation:

python scripts/validate_output.py --output-dir data/processed

## Git Security Rules

Do not commit:

- .env
- API keys
- raw PDFs
- extracted page text
- intermediate translated cache files

Commit final processed outputs:

- data/processed/final_chunks.jsonl
- data/processed/final_chunks.json
- data/processed/final_chunks_preview.md
- data/processed/chapter_index.csv
- data/processed/validation_report.json
