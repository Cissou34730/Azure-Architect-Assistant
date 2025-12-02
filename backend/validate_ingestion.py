"""Validation script for refactored ingestion module."""

import sys
from pathlib import Path

# Add backend to path
backend_root = Path(__file__).parent.parent
sys.path.insert(0, str(backend_root))


def validate_imports():
    """Validate all key imports work."""
    print("Validating imports...")
    
    try:
        # Domain imports
        from app.ingestion.domain.models import IngestionState, JobRuntime
        from app.ingestion.domain.enums import JobStatus, JobPhase, validate_transition
        from app.ingestion.domain.errors import DuplicateChunkError, QueueEmptyError
        print("✓ Domain imports OK")
        
        # Infrastructure imports
        from app.ingestion.infrastructure.repository import DatabaseRepository
        from app.ingestion.infrastructure.persistence import LocalDiskPersistenceStore
        print("✓ Infrastructure imports OK")
        
        # Application imports
        from app.ingestion.application.ingestion_service import IngestionService
        from app.ingestion.application.lifecycle import LifecycleManager
        from app.ingestion.application.executor import safe_run
        print("✓ Application imports OK")
        
        # Workers imports
        from app.ingestion.workers import ProducerWorker, ConsumerWorker
        print("✓ Workers imports OK")
        
        # Config imports
        from app.ingestion.config import get_settings, IngestionSettings
        print("✓ Config imports OK")
        
        # Observability imports
        from app.ingestion.observability.logging import set_correlation_context
        from app.ingestion.observability.metrics import get_metrics_collector
        print("✓ Observability imports OK")
        
        # Package-level imports
        from app.ingestion import IngestionService as ServiceAlias
        print("✓ Package imports OK")
        
        return True
    except Exception as exc:
        print(f"✗ Import failed: {exc}")
        return False


def validate_state_machine():
    """Validate state machine transitions."""
    print("\nValidating state machine...")
    
    try:
        from app.ingestion.domain.enums import JobStatus, validate_transition, StateTransitionError
        
        # Valid transitions
        assert validate_transition(JobStatus.PENDING, JobStatus.RUNNING)
        assert validate_transition(JobStatus.RUNNING, JobStatus.PAUSED)
        assert validate_transition(JobStatus.PAUSED, JobStatus.RUNNING)
        
        # Invalid transitions
        assert not validate_transition(JobStatus.COMPLETED, JobStatus.RUNNING)
        assert not validate_transition(JobStatus.PENDING, JobStatus.PAUSED)
        
        print("✓ State machine transitions validated")
        return True
    except Exception as exc:
        print(f"✗ State machine validation failed: {exc}")
        return False


def validate_configuration():
    """Validate configuration system."""
    print("\nValidating configuration...")
    
    try:
        from app.ingestion.config import get_settings
        
        settings = get_settings()
        assert settings.batch_size > 0
        assert settings.thread_join_timeout > 0
        assert isinstance(settings.enable_metrics, bool)
        
        print(f"✓ Configuration loaded: batch_size={settings.batch_size}")
        return True
    except Exception as exc:
        print(f"✗ Configuration validation failed: {exc}")
        return False


def validate_service_creation():
    """Validate service can be instantiated."""
    print("\nValidating service creation...")
    
    try:
        from app.ingestion.application.ingestion_service import IngestionService
        
        # Note: This creates singleton instance
        service = IngestionService.instance()
        assert service is not None
        assert hasattr(service, 'start')
        assert hasattr(service, 'pause')
        assert hasattr(service, 'resume')
        assert hasattr(service, 'cancel')
        assert hasattr(service, 'status')
        
        print("✓ Service instance created successfully")
        return True
    except Exception as exc:
        print(f"✗ Service creation failed: {exc}")
        return False


def main():
    """Run all validations."""
    print("=" * 60)
    print("Ingestion Module Validation")
    print("=" * 60)
    
    results = []
    
    results.append(("Imports", validate_imports()))
    results.append(("State Machine", validate_state_machine()))
    results.append(("Configuration", validate_configuration()))
    results.append(("Service Creation", validate_service_creation()))
    
    print("\n" + "=" * 60)
    print("Validation Summary")
    print("=" * 60)
    
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{name:.<40} {status}")
    
    all_passed = all(r[1] for r in results)
    
    print("=" * 60)
    if all_passed:
        print("✓ All validations passed!")
        return 0
    else:
        print("✗ Some validations failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
