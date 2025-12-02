"""
Pytest integration tests for CAF pause/resume functionality.

Run with:
  pytest backend/app/ingestion/tests/test_caf_integration.py -v -s
  pytest backend/app/ingestion/tests/test_caf_integration.py::test_caf_pause_resume_workflow -v -s
"""

import asyncio
import pytest
from pathlib import Path

from app.ingestion.application.ingestion_service import IngestionService
from app.ingestion.domain.enums import JobStatus
from app.ingestion.infrastructure.persistence import create_local_disk_persistence_store
from app.ingestion.infrastructure.repository import create_database_repository
from app.service_registry import get_kb_manager
from app.routers.kb_ingestion.operations import KBIngestionService


@pytest.fixture
def kb_id():
    """CAF knowledge base ID."""
    return "caf"


@pytest.fixture
def ingestion_service():
    """Get ingestion service instance."""
    return IngestionService.instance()


@pytest.fixture
def kb_ingestion_service():
    """Get KB ingestion service."""
    return KBIngestionService()


@pytest.fixture
def persistence():
    """Get persistence store."""
    return create_local_disk_persistence_store()


@pytest.fixture
def repository():
    """Get database repository."""
    return create_database_repository()


@pytest.fixture
def kb_config(kb_id):
    """Get KB configuration."""
    kb_manager = get_kb_manager()
    config = kb_manager.get_kb_config(kb_id)
    assert config is not None, f"KB '{kb_id}' not found in config"
    return config


@pytest.fixture(autouse=True)
async def cleanup_after_test(kb_id, ingestion_service):
    """Cleanup fixture that runs after each test."""
    yield
    # Cancel any running jobs after test
    try:
        await ingestion_service.cancel(kb_id)
    except:
        pass


@pytest.mark.asyncio
async def test_caf_pause_resume_workflow(
    kb_id,
    ingestion_service,
    kb_ingestion_service,
    persistence,
    kb_config
):
    """Test complete pause/resume workflow for CAF ingestion."""
    
    print(f"\n{'='*60}")
    print(f"Testing CAF Pause/Resume Workflow")
    print(f"{'='*60}")
    
    # Step 1: Start ingestion
    print("\n[1] Starting ingestion...")
    state = await ingestion_service.start(
        kb_id,
        kb_ingestion_service.run_ingestion_pipeline,
        kb_config
    )
    
    assert state.status == JobStatus.PENDING or state.status == JobStatus.RUNNING
    print(f"✓ Started (Job ID: {state.job_id})")
    
    # Step 2: Wait for progress
    print("\n[2] Waiting for ingestion progress...")
    await asyncio.sleep(3.0)
    
    status_before = ingestion_service.status(kb_id)
    print(f"✓ Status: {status_before.status}, Progress: {status_before.progress}%")
    assert status_before.status == JobStatus.RUNNING
    
    # Step 3: Pause
    print("\n[3] Pausing ingestion...")
    success = await ingestion_service.pause(kb_id)
    assert success, "Pause should succeed"
    
    await asyncio.sleep(2.0)
    
    status_paused = ingestion_service.status(kb_id)
    print(f"✓ Paused (Status: {status_paused.status})")
    assert status_paused.status == JobStatus.PAUSED
    
    # Step 4: Verify persistence
    print("\n[4] Verifying persistence...")
    persisted = persistence.load(kb_id)
    assert persisted is not None, "State should be persisted"
    assert persisted.status == JobStatus.PAUSED
    print(f"✓ State persisted (Documents: {persisted.metrics.get('documents_processed', 0)})")
    
    # Step 5: Resume
    print("\n[5] Resuming ingestion...")
    success = await ingestion_service.resume(
        kb_id,
        kb_ingestion_service.run_ingestion_pipeline,
        kb_config
    )
    assert success, "Resume should succeed"
    
    await asyncio.sleep(2.0)
    
    status_resumed = ingestion_service.status(kb_id)
    print(f"✓ Resumed (Status: {status_resumed.status})")
    assert status_resumed.status == JobStatus.RUNNING
    
    # Step 6: Monitor
    print("\n[6] Monitoring for 5 seconds...")
    for i in range(3):
        await asyncio.sleep(2.0)
        current = ingestion_service.status(kb_id)
        print(f"  [{i+1}] Status: {current.status}, Progress: {current.progress}%")
    
    print(f"\n{'='*60}")
    print("✓ Workflow test completed successfully!")
    print(f"{'='*60}")


@pytest.mark.asyncio
async def test_caf_multiple_pause_resume_cycles(
    kb_id,
    ingestion_service,
    kb_ingestion_service,
    kb_config
):
    """Test multiple pause/resume cycles."""
    
    print(f"\n{'='*60}")
    print(f"Testing Multiple Pause/Resume Cycles")
    print(f"{'='*60}")
    
    # Start
    await ingestion_service.start(
        kb_id,
        kb_ingestion_service.run_ingestion_pipeline,
        kb_config
    )
    print("✓ Ingestion started")
    
    cycles = 3
    for cycle in range(cycles):
        print(f"\n[Cycle {cycle + 1}/{cycles}]")
        
        # Wait and pause
        await asyncio.sleep(2.0)
        await ingestion_service.pause(kb_id)
        await asyncio.sleep(1.0)
        
        status = ingestion_service.status(kb_id)
        assert status.status == JobStatus.PAUSED
        print(f"  ✓ Paused (Progress: {status.progress}%)")
        
        # Resume
        await ingestion_service.resume(
            kb_id,
            kb_ingestion_service.run_ingestion_pipeline,
            kb_config
        )
        await asyncio.sleep(1.0)
        
        status = ingestion_service.status(kb_id)
        assert status.status == JobStatus.RUNNING
        print(f"  ✓ Resumed")
    
    print(f"\n{'='*60}")
    print("✓ Multiple cycles completed successfully!")
    print(f"{'='*60}")


@pytest.mark.asyncio
async def test_caf_data_integrity_during_pause_resume(
    kb_id,
    ingestion_service,
    kb_ingestion_service,
    persistence,
    kb_config
):
    """Verify data integrity is maintained during pause/resume."""
    
    print(f"\n{'='*60}")
    print(f"Testing Data Integrity")
    print(f"{'='*60}")
    
    # Start
    await ingestion_service.start(
        kb_id,
        kb_ingestion_service.run_ingestion_pipeline,
        kb_config
    )
    
    # Get initial metrics
    await asyncio.sleep(3.0)
    status_before = ingestion_service.status(kb_id)
    docs_before = status_before.metrics.get('documents_processed', 0)
    chunks_before = status_before.metrics.get('chunks_total', 0)
    
    print(f"\nBefore pause:")
    print(f"  Documents: {docs_before}")
    print(f"  Chunks: {chunks_before}")
    
    # Pause and verify persistence
    await ingestion_service.pause(kb_id)
    await asyncio.sleep(1.0)
    
    persisted = persistence.load(kb_id)
    docs_persisted = persisted.metrics.get('documents_processed', 0)
    chunks_persisted = persisted.metrics.get('chunks_total', 0)
    
    print(f"\nPersisted state:")
    print(f"  Documents: {docs_persisted}")
    print(f"  Chunks: {chunks_persisted}")
    
    # Resume and verify counts don't decrease
    await ingestion_service.resume(
        kb_id,
        kb_ingestion_service.run_ingestion_pipeline,
        kb_config
    )
    await asyncio.sleep(2.0)
    
    status_after = ingestion_service.status(kb_id)
    docs_after = status_after.metrics.get('documents_processed', 0)
    chunks_after = status_after.metrics.get('chunks_total', 0)
    
    print(f"\nAfter resume:")
    print(f"  Documents: {docs_after}")
    print(f"  Chunks: {chunks_after}")
    
    # Assertions
    assert docs_after >= docs_before, "Documents should not decrease"
    assert chunks_after >= chunks_before, "Chunks should not decrease"
    assert docs_persisted == docs_before, "Persisted docs should match pre-pause"
    assert chunks_persisted == chunks_before, "Persisted chunks should match pre-pause"
    
    print(f"\n{'='*60}")
    print("✓ Data integrity verified!")
    print(f"{'='*60}")


@pytest.mark.asyncio
async def test_caf_pause_without_running_job(kb_id, ingestion_service):
    """Test pausing when no job is running."""
    
    print(f"\n{'='*60}")
    print(f"Testing Pause Without Running Job")
    print(f"{'='*60}")
    
    # Try to pause when nothing is running
    success = await ingestion_service.pause(kb_id)
    
    # Should return False since there's no job to pause
    assert success == False, "Pause should return False when no job is running"
    
    print("✓ Correctly handled pause with no running job")


@pytest.mark.asyncio
async def test_caf_resume_without_checkpoint(
    kb_id,
    ingestion_service,
    kb_ingestion_service,
    kb_config,
    persistence
):
    """Test resuming when no checkpoint exists."""
    
    print(f"\n{'='*60}")
    print(f"Testing Resume Without Checkpoint")
    print(f"{'='*60}")
    
    # Delete any existing checkpoint
    persistence.delete(kb_id)
    
    # Try to resume
    success = await ingestion_service.resume(
        kb_id,
        kb_ingestion_service.run_ingestion_pipeline,
        kb_config
    )
    
    # Should return False since there's no checkpoint
    assert success == False, "Resume should return False when no checkpoint exists"
    
    print("✓ Correctly handled resume without checkpoint")


@pytest.mark.asyncio
async def test_caf_state_transitions(
    kb_id,
    ingestion_service,
    kb_ingestion_service,
    kb_config
):
    """Test state transitions are valid."""
    
    print(f"\n{'='*60}")
    print(f"Testing State Transitions")
    print(f"{'='*60}")
    
    # Start: pending -> running
    state = await ingestion_service.start(
        kb_id,
        kb_ingestion_service.run_ingestion_pipeline,
        kb_config
    )
    await asyncio.sleep(2.0)
    
    status = ingestion_service.status(kb_id)
    assert status.status == JobStatus.RUNNING
    print("✓ Transition: pending -> running")
    
    # Pause: running -> paused
    await ingestion_service.pause(kb_id)
    await asyncio.sleep(1.0)
    
    status = ingestion_service.status(kb_id)
    assert status.status == JobStatus.PAUSED
    print("✓ Transition: running -> paused")
    
    # Resume: paused -> running
    await ingestion_service.resume(
        kb_id,
        kb_ingestion_service.run_ingestion_pipeline,
        kb_config
    )
    await asyncio.sleep(1.0)
    
    status = ingestion_service.status(kb_id)
    assert status.status == JobStatus.RUNNING
    print("✓ Transition: paused -> running")
    
    # Cancel: running -> cancelled
    await ingestion_service.cancel(kb_id)
    await asyncio.sleep(1.0)
    
    status = ingestion_service.status(kb_id)
    assert status.status == JobStatus.CANCELED
    print("✓ Transition: running -> cancelled")
    
    print(f"\n{'='*60}")
    print("✓ All state transitions valid!")
    print(f"{'='*60}")
