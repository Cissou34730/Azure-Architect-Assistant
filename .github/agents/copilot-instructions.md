# Azure-Architect-Assistant-speckit Development Guidelines

Auto-generated from all feature plans. Last updated: 2025-12-17

## Active Technologies
- Python 3.10+ (FastAPI async); TypeScript 5+ with React 19 and TailwindCSS 4.1; Vite + FastAPI, Pydantic, SQLAlchemy async, aiosqlite; pytest; existing MCP client under `backend/app/services/mcp/`; existing Agent System under `backend/app/agents_system/` (002-azure-architect-assistant)

- Python 3.10+ (backend), TypeScript 5+ (frontend integration) + FastAPI (async API), NEEDS CLARIFICATION: LLM client library (OpenAI SDK vs Anthropic SDK vs unified LangChain), NEEDS CLARIFICATION: PlantUML rendering library, NEEDS CLARIFICATION: Mermaid validation library (001-architecture-diagram-generator)

## Project Structure

```text
src/
tests/
```

## Commands

cd src; pytest; ruff check .

## Code Style

Python 3.10+ (backend), TypeScript 5+ (frontend integration): Follow standard conventions

## Recent Changes
- 002-azure-architect-assistant: Added Python 3.10+ (FastAPI async); TypeScript 5+ with React 19 and TailwindCSS 4.1; Vite + FastAPI, Pydantic, SQLAlchemy async, aiosqlite; pytest; existing MCP client under `backend/app/services/mcp/`; existing Agent System under `backend/app/agents_system/`

- 001-architecture-diagram-generator: Added Python 3.10+ (backend), TypeScript 5+ (frontend integration) + FastAPI (async API), NEEDS CLARIFICATION: LLM client library (OpenAI SDK vs Anthropic SDK vs unified LangChain), NEEDS CLARIFICATION: PlantUML rendering library, NEEDS CLARIFICATION: Mermaid validation library

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
