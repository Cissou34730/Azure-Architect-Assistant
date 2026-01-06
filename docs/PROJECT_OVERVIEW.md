# Project Overview

Azure Architecture Assistant is a full-stack app that helps architects analyze project requirements, query Azure knowledge bases, and generate architecture guidance and diagrams.

## Core workflows

- Architecture projects: capture requirements, upload documents, analyze them into a structured state, chat to refine, and generate a proposal.
- Knowledge bases: create a KB, ingest sources into a vector index, and query across one or more KBs.
- Agent chat: a ReAct-style agent that searches Microsoft documentation via MCP and answers questions with citations.
- Diagram generation: generate Mermaid-based functional, C4 context, and C4 container diagrams from a text description.

## Key components

- Backend: FastAPI service with modular routers for projects, KB management, ingestion, queries, agents, and diagram generation.
- Frontend: React + Vite UI with project workspace, KB management/query, agent chat, and diagrams.
- Storage: SQLite databases for projects, ingestion state, and diagrams; file-based KB indices on disk.

## Repository layout

- backend/ - FastAPI app, services, ingestion pipeline, agent system, diagram generation.
- frontend/ - React UI, hooks, and API clients.
- data/ - SQLite DBs and KB indices (runtime).
- scripts/ - helper scripts (optional).
- docs/ - reference docs for the current codebase.

For architecture, setup, and API details see the docs in this folder.
