"""Domain-specific exceptions for ingestion."""

from __future__ import annotations


class IngestionError(Exception):
    """Base exception for ingestion errors."""

    pass


class DuplicateChunkError(IngestionError):
    """Raised when attempting to enqueue a duplicate chunk (by doc_hash)."""

    def __init__(self, job_id: str, doc_hash: str):
        self.job_id = job_id
        self.doc_hash = doc_hash
        super().__init__(f'Duplicate chunk: job_id={job_id}, doc_hash={doc_hash}')


class QueueEmptyError(IngestionError):
    """Raised when attempting to dequeue from an empty queue."""

    def __init__(self, job_id: str):
        self.job_id = job_id
        super().__init__(f'Queue empty for job_id={job_id}')


class JobNotFoundError(IngestionError):
    """Raised when job record not found."""

    def __init__(self, job_id: str):
        self.job_id = job_id
        super().__init__(f'Job not found: {job_id}')


class InvalidJobStateError(IngestionError):
    """Raised when job is in an invalid state for the requested operation."""

    def __init__(self, job_id: str, current_status: str, operation: str):
        self.job_id = job_id
        self.current_status = current_status
        self.operation = operation
        super().__init__(f'Cannot {operation} job {job_id} in status {current_status}')


class RuntimeNotFoundError(IngestionError):
    """Raised when runtime not found in manager."""

    def __init__(self, kb_id: str):
        self.kb_id = kb_id
        super().__init__(f'Runtime not found for KB: {kb_id}')


class PersistenceError(IngestionError):
    """Raised when state persistence fails."""

    def __init__(self, kb_id: str, reason: str):
        self.kb_id = kb_id
        self.reason = reason
        super().__init__(f'Persistence failed for KB {kb_id}: {reason}')


class PhaseNotFoundError(IngestionError):
    """Raised when a phase status row is expected but missing."""

    def __init__(self, job_id: str, phase_name: str):
        self.job_id = job_id
        self.phase_name = phase_name
        super().__init__(f'Phase not found: job_id={job_id}, phase_name={phase_name}')


class PhaseRepositoryError(IngestionError):
    """Raised when phase repository operations fail."""

    def __init__(self, job_id: str, phase_name: str, operation: str, reason: str):
        self.job_id = job_id
        self.phase_name = phase_name
        self.operation = operation
        self.reason = reason
        super().__init__(
            f'Phase repository error: op={operation}, job_id={job_id}, phase={phase_name}, reason={reason}'
        )


class NonCriticalPhaseError(IngestionError):
    """Raised for phase tracking failures that should not fail the ingestion job."""

    def __init__(self, job_id: str, phase_name: str, operation: str, reason: str):
        self.job_id = job_id
        self.phase_name = phase_name
        self.operation = operation
        self.reason = reason
        super().__init__(
            f'Non-critical phase tracking failure: op={operation}, job_id={job_id}, phase={phase_name}, reason={reason}'
        )
