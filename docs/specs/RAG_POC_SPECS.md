Retrieval-Augmented Generation over Azure Well-Architected Framework (WAF)
Workflow Updated: Full-Document Validation Before Chunking

0. Scope

This document defines the functional and technical specifications for a Retrieval-Augmented Generation (RAG) Proof of Concept.

The goal is to ingest and structure the Azure Well-Architected Framework (WAF) documentation, clean it, validate the cleaned text manually, then construct a vector index and a query mechanism to generate grounded answers through OpenAI models.

The POC uses:

Python for ingestion, cleaning, document-level validation export, chunking, embeddings, and index generation

TypeScript for orchestrating ingestion steps and exposing a query endpoint

OpenAI models for embeddings and generation

Local persistent storage for the vector index

1. Technology Choices (Fixed)
1.1 Python Libraries

Chosen and fixed for the ingestion pipeline:

LlamaIndex – for chunking, embeddings, vector store, retrieval.

readability-lxml – for extracting main article content from HTML.

BeautifulSoup4 – for structural cleanup of HTML.

html2text – for converting cleaned HTML → normalized plain text.

requests – for HTML fetching and crawling.

This ingestion/cleaning stack maximizes text quality and reduces embedding cost.

1.2 OpenAI Models

Embedding model: text-embedding-3-small
(Excellent quality/cost ratio for technical documentation.)

Generation model: gpt-4.1-mini
(Efficient and sufficient for RAG when retrieval quality is high.)

1.3 Vector Index Backend

LlamaIndex Persistent Local Vector Store

Folder: waf_storage_clean/

Stores: embeddings, node metadata, index configuration

No external vector DB required for the POC.

1.4 TypeScript Environment

TypeScript will:

Trigger Python ingestion steps (two-phase workflow)

Expose the query API

Integrate with the front-end UI

No specific TS backend framework is mandated.

2. High-Level Architecture

The system is composed of:

Crawler (Python) → discovers WAF URLs

Ingestion Pipeline (Python)

HTML extraction

Cleaning

Text normalization

Export cleaned documents for manual validation

Chunking + Embeddings + Indexing (Python)

Executed only after manual approval

Query Service (Python callable from TS)

Loads the vector index

Performs retrieval + generation

TypeScript Frontend & Backend

Frontend sends questions and displays answers

Backend triggers ingestion and calls the query module

The process is two-phase ingestion, with a mandatory human validation step.

3. Functional Requirements
3.1 Two-Step Ingestion Workflow
STEP 1 — Document Cleaning & Human Validation

The ingestion pipeline must:

Crawl WAF URLs

BFS with domain restriction to /azure/well-architected/

Depth and page limits

Deduplication of URLs

Fetch raw HTML

Extract main content

Use Readability to remove layout elements (menus, navbars, footers, sidebars)

Structural cleanup

Remove residual noisy elements via BeautifulSoup

Remove feedback widgets, related links, TOC containers, etc.

Convert to plain text

html2text to produce readable, normalized text

Text normalization

Remove noisy sections (“Next steps”, “Feedback”, “See also”, navigation blocks)

Normalize whitespace and paragraph splits

Preserve meaningful structure

Export full cleaned documents

Each document saved as .md or .txt

Include metadata: URL, section (pillar, workload, service-guide, general), title

Include a manifest file listing all documents

Human Validation Step (mandatory)

Developer manually inspects and approves or rejects each cleaned document

Each document receives a status: APPROVED or REJECTED

Only approved documents proceed to chunking

Status stored in a JSON manifest (e.g., validation_manifest.json)

No chunking or embeddings occur before this validation.

STEP 2 — Chunking, Embeddings, Indexing

After document approval:

Load approved documents only

Chunking

Token-based chunking

chunk_size ≈ 800 tokens

chunk_overlap ≈ 120 tokens (10–15%)

Each chunk inherits metadata from its parent document

Embedding

Generate embeddings using text-embedding-3-small

Only for approved chunks

Vector Index Construction

Build vector index with LlamaIndex

Persist everything in waf_storage_clean/

Index Ready for Query

Retrieval and generation use this persisted index

3.2 Query Workflow

The query pipeline must:

Receive the question (from TS backend)

Load the persisted vector index (cache in-memory after first load)

Embed the question

Retrieve relevant chunks (top_k = 5 by default)

Optionally filter on metadata (e.g., section = "pillar")

Apply optional similarity threshold (0.75) to block low-confidence results

Build the generation prompt with:

system instructions

selected chunks

the user query

Call gpt-4.1-mini for generation

Return:

answer

list of source URLs

similarity scores

4. Technical Specifications
4.1 Python Ingestion Pipeline (Phase 1)
4.1.1 Crawler

BFS with deduplication

Domain restriction: learn.microsoft.com

Path restriction: /azure/well-architected/

Depth limit and max page limit

Graceful handling of errors/timeouts

4.1.2 HTML Extraction

Fetch HTML with requests

Extract main article content using readability-lxml

Remove leftover elements via BeautifulSoup selectors

4.1.3 Text Normalization

Convert cleaned HTML → text using html2text

Strip noisy sections (“Next steps”, “Feedback”, “See also”)

Normalize whitespace, remove duplicates, fix paragraphs

Produce a clean plain-text document per URL

4.1.4 Export for Manual Review

Write each cleaned document into a directory

Export a manifest.json with:

URL

section

title

path to cleaned text file

initial status = PENDING_REVIEW

Developer edits the manifest to set:

APPROVED

or REJECTED

No chunking or embedding occurs at this stage.

4.2 Python Chunking + Indexing Pipeline (Phase 2)

Triggered only after manual validation.

4.2.1 Load Approved Documents

Read manifest

Load only APPROVED documents

4.2.2 Chunking

Use LlamaIndex TokenTextSplitter

chunk_size ≈ 800 tokens

overlap ≈ 120 tokens

Each chunk has metadata:

url

section

title

document_id

4.2.3 Embeddings

Call text-embedding-3-small for each chunk

Embedding cost minimized thanks to prior document-level validation

4.2.4 Index Construction

Use LlamaIndex to build a persistent vector index

Persist to folder: waf_storage_clean/

Store:

embeddings

chunks

metadata

index configuration

4.3 Query Service (Python + TypeScript Integration)
4.3.1 Python Query Module

Must implement:

answer_question(question, top_k = 5, metadata_filters = None)

Responsibilities:

Load index (cache on first use)

Embed question

Run similarity search

Apply filters

Build prompt

Execute OpenAI LLM

Return structured JSON:

answer

source list

scores

4.3.2 TypeScript Backend Integration

The TS backend must:

Provide commands to trigger Phase 1 and Phase 2 Python scripts

Expose a /query endpoint

Forward the Python query module output directly to front-end

Never generate embeddings itself (Python is authoritative)

4.3.3 Front-End

Minimal UI:

Text input for queries

Display answer

Show source citations

