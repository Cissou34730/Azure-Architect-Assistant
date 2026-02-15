# Project Overview (Agent)

## Purpose

Fast, low-token orientation for agents working in this repository.

## Current State

- Monorepo with React + TypeScript frontend and FastAPI + Python backend.
- Main product workflows: project authoring, architecture assistant chat, KB ingest/query, and diagram generation.
- Backend remains the system of record for project state, ingestion state, and diagram persistence.
- Core backend domains: project management, agents system (LangGraph), ingestion, KB query, diagram services.

## Do / Don't

### Do

- Use this file first for repo orientation.
- Follow domain boundaries when navigating code.
- Update this file when high-level workflows or core domains change.

### Don't

- Add detailed implementation narratives.
- Duplicate comprehensive architecture explanations from human docs.

## Decision Summary

- Keep a strict split: concise agent docs in `/docs/agents`, comprehensive docs in domain folders.
- Use backend as orchestration boundary and persistence owner.

## Update Triggers

Update this file when:

- new top-level feature workflows are added or removed
- major repo/domain boundaries change
- frontend/backend responsibility boundary changes

## Metadata

- Status: Active
- Last Updated: 2026-02-15
- Owner: Engineering
