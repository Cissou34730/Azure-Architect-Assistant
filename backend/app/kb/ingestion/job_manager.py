"""
Ingestion Job Manager
Tracks and manages background ingestion jobs with progress reporting.
"""

import asyncio
from datetime import datetime
from enum import Enum
from typing import Dict, Optional, List, Any
import logging

from .base import IngestionPhase

logger = logging.getLogger(__name__)


class JobStatus(str, Enum):
    """Job execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class IngestionJob:
    """Represents a single ingestion job."""
    
    def __init__(self, kb_id: str, kb_name: str, source_type: str):
        """
        Initialize job.
        
        Args:
            kb_id: Knowledge base ID
            kb_name: Knowledge base name
            source_type: Source type (e.g., 'web-documentation', 'web-generic')
        """
        self.job_id = f"{kb_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.kb_id = kb_id
        self.kb_name = kb_name
        self.source_type = source_type
        
        # Status tracking
        self.status = JobStatus.PENDING
        self.phase = IngestionPhase.CRAWLING
        self.progress = 0  # 0-100
        self.message = "Job created"
        self.error: Optional[str] = None
        
        # Timing
        self.created_at = datetime.now()
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        
        # Metrics
        self.metrics: Dict[str, Any] = {
            'urls_crawled': 0,
            'documents_cleaned': 0,
            'chunks_created': 0,
            'documents_processed': 0
        }
        
        # Task reference for cancellation
        self._task: Optional[asyncio.Task] = None
    
    def start(self):
        """Mark job as started."""
        self.status = JobStatus.RUNNING
        self.started_at = datetime.now()
        self.message = "Job started"
        logger.info(f"[{self.job_id}] Job started")
    
    def update_progress(
        self,
        phase: IngestionPhase,
        progress: int,
        message: str,
        metrics: Optional[Dict[str, Any]] = None
    ):
        """
        Update job progress.
        
        Args:
            phase: Current ingestion phase
            progress: Progress percentage (0-100)
            message: Status message
            metrics: Optional metrics update
        """
        self.phase = phase
        self.progress = max(0, min(100, progress))  # Clamp 0-100
        self.message = message
        
        if metrics:
            self.metrics.update(metrics)
        
        logger.debug(f"[{self.job_id}] {phase.value}: {progress}% - {message}")
    
    def complete(self, metrics: Optional[Dict[str, Any]] = None):
        """Mark job as completed."""
        self.status = JobStatus.COMPLETED
        self.phase = IngestionPhase.COMPLETED
        self.progress = 100
        self.message = "Ingestion completed successfully"
        self.completed_at = datetime.now()
        
        if metrics:
            self.metrics.update(metrics)
        
        duration = (self.completed_at - self.started_at).total_seconds() if self.started_at else 0
        logger.info(f"[{self.job_id}] Job completed in {duration:.1f}s")
    
    def fail(self, error: str):
        """Mark job as failed."""
        self.status = JobStatus.FAILED
        self.phase = IngestionPhase.FAILED
        self.error = error
        self.message = f"Job failed: {error}"
        self.completed_at = datetime.now()
        
        logger.error(f"[{self.job_id}] Job failed: {error}")
    
    def cancel(self):
        """Cancel the job."""
        self.status = JobStatus.CANCELLED
        self.message = "Job cancelled by user"
        self.completed_at = datetime.now()
        
        if self._task and not self._task.done():
            self._task.cancel()
        
        logger.info(f"[{self.job_id}] Job cancelled")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert job to dictionary for API responses."""
        return {
            'job_id': self.job_id,
            'kb_id': self.kb_id,
            'kb_name': self.kb_name,
            'source_type': self.source_type,
            'status': self.status.value,
            'phase': self.phase.value,
            'progress': self.progress,
            'message': self.message,
            'error': self.error,
            'metrics': self.metrics,
            'created_at': self.created_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'duration_seconds': (
                (self.completed_at - self.started_at).total_seconds()
                if self.started_at and self.completed_at
                else None
            )
        }


class JobManager:
    """Manages all ingestion jobs."""
    
    _instance: Optional['JobManager'] = None
    _jobs: Dict[str, IngestionJob] = {}
    
    def __new__(cls):
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def create_job(
        self,
        kb_id: str,
        kb_name: str,
        source_type: str
    ) -> IngestionJob:
        """
        Create a new ingestion job.
        
        Args:
            kb_id: Knowledge base ID
            kb_name: Knowledge base name
            source_type: Source type
            
        Returns:
            Created job
        """
        job = IngestionJob(kb_id, kb_name, source_type)
        self._jobs[job.job_id] = job
        
        logger.info(f"Created job {job.job_id} for KB '{kb_name}' (type: {source_type})")
        return job
    
    def get_job(self, job_id: str) -> Optional[IngestionJob]:
        """
        Get job by ID.
        
        Args:
            job_id: Job ID
            
        Returns:
            Job or None if not found
        """
        return self._jobs.get(job_id)
    
    def get_jobs_for_kb(self, kb_id: str, limit: int = 50) -> List[IngestionJob]:
        """
        Get all jobs for a knowledge base.
        
        Args:
            kb_id: Knowledge base ID
            limit: Maximum number of jobs to return
            
        Returns:
            List of jobs, sorted by creation time (newest first)
        """
        jobs = [job for job in self._jobs.values() if job.kb_id == kb_id]
        jobs.sort(key=lambda j: j.created_at, reverse=True)
        return jobs[:limit]
    
    def get_latest_job_for_kb(self, kb_id: str) -> Optional[IngestionJob]:
        """
        Get the latest job for a KB.
        
        Args:
            kb_id: Knowledge base ID
            
        Returns:
            Latest job or None if no jobs found
        """
        jobs = self.get_jobs_for_kb(kb_id, limit=1)
        return jobs[0] if jobs else None
    
    def get_all_jobs(self, limit: int = 50) -> List[IngestionJob]:
        """
        Get all jobs across all KBs.
        
        Args:
            limit: Maximum number of jobs to return
            
        Returns:
            List of jobs, sorted by creation time (newest first)
        """
        jobs = list(self._jobs.values())
        jobs.sort(key=lambda j: j.created_at, reverse=True)
        return jobs[:limit]
    
    def list_jobs(
        self,
        status: Optional[JobStatus] = None,
        limit: int = 50
    ) -> List[IngestionJob]:
        """
        List jobs with optional filtering.
        
        Args:
            status: Filter by status
            limit: Maximum number of jobs to return
            
        Returns:
            List of jobs
        """
        jobs = list(self._jobs.values())
        
        # Filter by status
        if status:
            jobs = [job for job in jobs if job.status == status]
        
        # Sort by created time (newest first)
        jobs.sort(key=lambda j: j.created_at, reverse=True)
        
        return jobs[:limit]
    
    def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a running job.
        
        Args:
            job_id: Job ID
            
        Returns:
            True if cancelled, False if job not found or not cancellable
        """
        job = self.get_job(job_id)
        if not job:
            return False
        
        if job.status not in [JobStatus.PENDING, JobStatus.RUNNING]:
            logger.warning(f"Cannot cancel job {job_id}: status is {job.status}")
            return False
        
        job.cancel()
        return True
    
    def cleanup_old_jobs(self, max_age_hours: int = 24):
        """
        Remove old completed/failed jobs.
        
        Args:
            max_age_hours: Maximum age in hours for completed jobs
        """
        cutoff_time = datetime.now()
        cutoff_timestamp = cutoff_time.timestamp() - (max_age_hours * 3600)
        
        to_remove = []
        for job_id, job in self._jobs.items():
            if job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
                if job.completed_at and job.completed_at.timestamp() < cutoff_timestamp:
                    to_remove.append(job_id)
        
        for job_id in to_remove:
            del self._jobs[job_id]
            logger.info(f"Cleaned up old job {job_id}")
        
        if to_remove:
            logger.info(f"Cleaned up {len(to_remove)} old jobs")


# Global job manager instance
_job_manager = JobManager()


def get_job_manager() -> JobManager:
    """Get the global job manager instance."""
    return _job_manager
