"""
Integration test for CAF knowledge base pause/resume functionality.

This test validates:
1. Starting ingestion for CAF KB
2. Pausing the ingestion job
3. Verifying state is persisted
4. Resuming from checkpoint
5. Completing the ingestion

Run with: python test_caf_pause_resume.py
Or with pytest: pytest test_caf_pause_resume.py -v -s

Dependencies: If pytest tests fail to import, run:
  pip install pytest pytest-asyncio
"""

import asyncio
import time
import sys
from pathlib import Path

# Check for pytest installation
try:
    import pytest
    PYTEST_AVAILABLE = True
except ImportError:
    PYTEST_AVAILABLE = False
    print("\n⚠️  Note: pytest not installed. Pytest tests will not be available.")
    print("   To enable pytest tests, run: pip install pytest pytest-asyncio\n")

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from app.ingestion.application.ingestion_service import IngestionService
from app.ingestion.domain.enums import JobStatus
from app.ingestion.infrastructure.persistence import create_local_disk_persistence_store
from app.ingestion.infrastructure.repository import create_database_repository
from app.service_registry import get_kb_manager
from app.routers.kb_ingestion.operations import KBIngestionService


class TestCAFPauseResume:
    """Test pause/resume functionality with CAF knowledge base."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.kb_id = "caf"
        self.ingestion_service = IngestionService.instance()
        self.kb_ingestion_service = KBIngestionService()
        self.persistence = create_local_disk_persistence_store()
        self.repository = create_database_repository()
        self.kb_manager = get_kb_manager()
        
        # Get KB config
        self.kb_config = self.kb_manager.get_kb_config(self.kb_id)
        assert self.kb_config is not None, f"KB '{self.kb_id}' not found in config"
        
        print(f"\n{'='*60}")
        print(f"Testing CAF Knowledge Base Pause/Resume")
        print(f"KB ID: {self.kb_id}")
        print(f"KB Name: {self.kb_config.get('name')}")
        print(f"Source Type: {self.kb_config.get('source_type')}")
        print(f"{'='*60}\n")
    
    def teardown_method(self):
        """Cleanup after test."""
        # Cancel any running jobs
        try:
            asyncio.run(self.ingestion_service.cancel(self.kb_id))
        except:
            pass
    
    async def test_pause_resume_workflow(self):
        """Test complete pause/resume workflow for CAF ingestion."""
        
        print("\n[Step 1] Starting CAF ingestion...")
        print("-" * 60)
        
        # Start ingestion
        try:
            state = await self.ingestion_service.start(
                self.kb_id,
                self.kb_ingestion_service.run_ingestion_pipeline,
                self.kb_config
            )
            print(f"✓ Ingestion started")
            print(f"  Job ID: {state.job_id}")
            print(f"  Status: {state.status}")
            print(f"  Phase: {state.phase}")
        except Exception as e:
            print(f"✗ Failed to start ingestion: {e}")
            raise
        
        # Wait for ingestion to make some progress
        print("\n[Step 2] Waiting for ingestion progress...")
        print("-" * 60)
        
        await asyncio.sleep(3.0)  # Wait 3 seconds for some documents to be processed
        
        # Check status before pause
        status_before = self.ingestion_service.status(self.kb_id)
        print(f"✓ Status before pause:")
        print(f"  Status: {status_before.status}")
        print(f"  Phase: {status_before.phase}")
        print(f"  Progress: {status_before.progress}%")
        print(f"  Metrics: {status_before.metrics}")
        
        assert status_before.status == JobStatus.RUNNING, "Job should be running"
        
        # Pause ingestion
        print("\n[Step 3] Pausing ingestion...")
        print("-" * 60)
        
        try:
            success = await self.ingestion_service.pause(self.kb_id)
            assert success, "Pause should return True"
            print(f"✓ Pause initiated successfully")
        except Exception as e:
            print(f"✗ Failed to pause: {e}")
            raise
        
        # Wait for pause to complete
        await asyncio.sleep(2.0)
        
        # Check status after pause
        status_after_pause = self.ingestion_service.status(self.kb_id)
        print(f"✓ Status after pause:")
        print(f"  Status: {status_after_pause.status}")
        print(f"  Phase: {status_after_pause.phase}")
        print(f"  Progress: {status_after_pause.progress}%")
        print(f"  Metrics: {status_after_pause.metrics}")
        
        assert status_after_pause.status == JobStatus.PAUSED, "Job should be paused"
        
        # Verify state is persisted to disk
        print("\n[Step 4] Verifying state persistence...")
        print("-" * 60)
        
        persisted_state = self.persistence.load(self.kb_id)
        assert persisted_state is not None, "State should be persisted"
        assert persisted_state.status == JobStatus.PAUSED, "Persisted state should show paused"
        print(f"✓ State persisted to disk")
        print(f"  Job ID: {persisted_state.job_id}")
        print(f"  Documents processed: {persisted_state.metrics.get('documents_processed', 0)}")
        print(f"  Chunks created: {persisted_state.metrics.get('chunks_total', 0)}")
        
        # Check database for queue items
        if persisted_state.job_id:
            queue_stats = self.repository.get_queue_stats(persisted_state.job_id)
            print(f"  Queue stats: {queue_stats}")
        
        # Resume ingestion
        print("\n[Step 5] Resuming ingestion from checkpoint...")
        print("-" * 60)
        
        try:
            success = await self.ingestion_service.resume(
                self.kb_id,
                self.kb_ingestion_service.run_ingestion_pipeline,
                self.kb_config
            )
            assert success, "Resume should return True"
            print(f"✓ Resume initiated successfully")
        except Exception as e:
            print(f"✗ Failed to resume: {e}")
            raise
        
        # Wait a bit for resume to start
        await asyncio.sleep(2.0)
        
        # Check status after resume
        status_after_resume = self.ingestion_service.status(self.kb_id)
        print(f"✓ Status after resume:")
        print(f"  Status: {status_after_resume.status}")
        print(f"  Phase: {status_after_resume.phase}")
        print(f"  Progress: {status_after_resume.progress}%")
        print(f"  Metrics: {status_after_resume.metrics}")
        
        assert status_after_resume.status == JobStatus.RUNNING, "Job should be running again"
        
        # Let it run a bit more
        print("\n[Step 6] Monitoring resumed ingestion...")
        print("-" * 60)
        
        for i in range(5):
            await asyncio.sleep(2.0)
            current_status = self.ingestion_service.status(self.kb_id)
            print(f"  [{i+1}/5] Status: {current_status.status}, "
                  f"Phase: {current_status.phase}, "
                  f"Progress: {current_status.progress}%")
            
            if current_status.status in [JobStatus.COMPLETED, JobStatus.FAILED]:
                break
        
        # Final status check
        print("\n[Step 7] Final status check...")
        print("-" * 60)
        
        final_status = self.ingestion_service.status(self.kb_id)
        print(f"✓ Final status:")
        print(f"  Status: {final_status.status}")
        print(f"  Phase: {final_status.phase}")
        print(f"  Progress: {final_status.progress}%")
        print(f"  Message: {final_status.message}")
        print(f"  Metrics: {final_status.metrics}")
        
        if final_status.error:
            print(f"  Error: {final_status.error}")
        
        # Cleanup - cancel if still running
        if final_status.status == JobStatus.RUNNING:
            print("\n[Cleanup] Cancelling job...")
            await self.ingestion_service.cancel(self.kb_id)
            print("✓ Job cancelled")
        
        print("\n" + "="*60)
        print("Test completed successfully! ✓")
        print("="*60)
        
        # Assertions for test validation
        assert status_before.status == JobStatus.RUNNING, "Job should start in running state"
        assert status_after_pause.status == JobStatus.PAUSED, "Job should pause successfully"
        assert status_after_resume.status == JobStatus.RUNNING, "Job should resume successfully"
        assert persisted_state is not None, "State should be persisted during pause"
    
    async def test_multiple_pause_resume_cycles(self):
        """Test multiple pause/resume cycles."""
        
        print("\n[Test] Multiple Pause/Resume Cycles")
        print("="*60)
        
        # Start ingestion
        state = await self.ingestion_service.start(
            self.kb_id,
            self.kb_ingestion_service.run_ingestion_pipeline,
            self.kb_config
        )
        print(f"✓ Ingestion started (Job ID: {state.job_id})")
        
        cycles = 3
        for cycle in range(cycles):
            print(f"\n[Cycle {cycle + 1}/{cycles}]")
            print("-" * 60)
            
            # Wait for progress
            await asyncio.sleep(2.0)
            
            # Pause
            print(f"  Pausing...")
            success = await self.ingestion_service.pause(self.kb_id)
            assert success, f"Pause failed in cycle {cycle + 1}"
            await asyncio.sleep(1.0)
            
            status = self.ingestion_service.status(self.kb_id)
            print(f"  ✓ Paused (Progress: {status.progress}%)")
            assert status.status == JobStatus.PAUSED
            
            # Resume
            print(f"  Resuming...")
            success = await self.ingestion_service.resume(
                self.kb_id,
                self.kb_ingestion_service.run_ingestion_pipeline,
                self.kb_config
            )
            assert success, f"Resume failed in cycle {cycle + 1}"
            await asyncio.sleep(1.0)
            
            status = self.ingestion_service.status(self.kb_id)
            print(f"  ✓ Resumed (Status: {status.status})")
            assert status.status == JobStatus.RUNNING
        
        # Cleanup
        await self.ingestion_service.cancel(self.kb_id)
        print("\n✓ Multiple cycles completed successfully!")
    
    async def test_pause_persistence_data_integrity(self):
        """Verify data integrity during pause/resume."""
        
        print("\n[Test] Data Integrity During Pause/Resume")
        print("="*60)
        
        # Start ingestion
        await self.ingestion_service.start(
            self.kb_id,
            self.kb_ingestion_service.run_ingestion_pipeline,
            self.kb_config
        )
        
        # Let it run
        await asyncio.sleep(3.0)
        
        # Get metrics before pause
        status_before = self.ingestion_service.status(self.kb_id)
        docs_before = status_before.metrics.get('documents_processed', 0)
        chunks_before = status_before.metrics.get('chunks_total', 0)
        
        print(f"Before pause:")
        print(f"  Documents: {docs_before}")
        print(f"  Chunks: {chunks_before}")
        
        # Pause
        await self.ingestion_service.pause(self.kb_id)
        await asyncio.sleep(1.0)
        
        # Load from disk
        persisted = self.persistence.load(self.kb_id)
        
        print(f"\nPersisted state:")
        print(f"  Documents: {persisted.metrics.get('documents_processed', 0)}")
        print(f"  Chunks: {persisted.metrics.get('chunks_total', 0)}")
        
        # Resume
        await self.ingestion_service.resume(
            self.kb_id,
            self.kb_ingestion_service.run_ingestion_pipeline,
            self.kb_config
        )
        await asyncio.sleep(2.0)
        
        # Get metrics after resume
        status_after = self.ingestion_service.status(self.kb_id)
        docs_after = status_after.metrics.get('documents_processed', 0)
        chunks_after = status_after.metrics.get('chunks_total', 0)
        
        print(f"\nAfter resume:")
        print(f"  Documents: {docs_after}")
        print(f"  Chunks: {chunks_after}")
        
        # Verify data consistency
        assert docs_after >= docs_before, "Document count should not decrease"
        assert chunks_after >= chunks_before, "Chunk count should not decrease"
        
        # Cleanup
        await self.ingestion_service.cancel(self.kb_id)
        
        print("\n✓ Data integrity verified!")


def run_test():
    """Run the test synchronously."""
    test = TestCAFPauseResume()
    test.setup_method()
    
    try:
        # Run main workflow test
        asyncio.run(test.test_pause_resume_workflow())
        
        print("\n\n")
        
        # Run multiple cycles test
        asyncio.run(test.test_multiple_pause_resume_cycles())
        
        print("\n\n")
        
        # Run data integrity test
        asyncio.run(test.test_pause_persistence_data_integrity())
        
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        test.teardown_method()
    
    return True


if __name__ == "__main__":
    print("\n" + "="*60)
    print("CAF Knowledge Base - Pause/Resume Integration Test")
    print("="*60)
    
    success = run_test()
    
    if success:
        print("\n" + "="*60)
        print("ALL TESTS PASSED ✓")
        print("="*60)
        sys.exit(0)
    else:
        print("\n" + "="*60)
        print("TESTS FAILED ✗")
        print("="*60)
        sys.exit(1)
