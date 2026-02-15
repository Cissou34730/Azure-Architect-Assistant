# System Architecture (Agent)

## Purpose

Concise architecture reference for agents performing coding and documentation tasks.

## Current State

- Runtime topology: frontend (React/Vite) -> backend (FastAPI) -> external AI/knowledge services.
- Backend layers:
  - API routers in `backend/app/routers`
  - service logic in `backend/app/services` and feature service modules
  - domain/persistence in `backend/app/models`, `backend/app/ingestion`, `backend/app/kb`
- Startup lifecycle initializes DBs and key services; KB index loading is lazy.
- Persistent storage includes project, ingestion, and diagram SQLite databases plus file-based KB indices.

## Do / Don't

### Do

- Keep feature changes within layer boundaries.
- Update this document for architecture-level behavior changes.
- Use human docs only when deeper implementation detail is required by maintainers.

### Don't

- Mix detailed historical migration narratives into this file.
- Record transient implementation status updates here.

## Decision Summary

- Maintain backend-centric architecture and modular feature boundaries.
- Keep this file as stable architecture snapshot, not project log.

## Update Triggers

Update this file when:

- runtime topology changes
- layering or module ownership changes
- persistence model changes materially

## Metadata

- Status: Active
- Last Updated: 2026-02-15
- Owner: Engineering
