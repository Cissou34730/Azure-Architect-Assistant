"""Quick validation script for test files."""
print('Validating test files...\n')

# Test 1: Standalone test
try:
    from test_caf_pause_resume import TestCAFPauseResume
    test = TestCAFPauseResume()
    methods = [m for m in dir(test) if m.startswith('test_') and callable(getattr(test, m))]
    print('✓ Standalone test (test_caf_pause_resume.py):')
    print(f'  - Class: TestCAFPauseResume')
    print(f'  - Test methods: {len(methods)}')
    for m in methods:
        print(f'    • {m}')
except Exception as e:
    print(f'✗ Standalone test failed: {e}')

print()

# Test 2: Pytest tests (if pytest available)
try:
    import pytest
    print('✓ pytest is installed')
    
    # Try importing pytest tests
    from app.ingestion.tests import test_caf_integration
    import inspect
    
    test_functions = [name for name, obj in inspect.getmembers(test_caf_integration) 
                     if inspect.iscoroutinefunction(obj) and name.startswith('test_')]
    
    print(f'✓ Pytest integration tests (test_caf_integration.py):')
    print(f'  - Test functions: {len(test_functions)}')
    for func in test_functions:
        print(f'    • {func}')
        
except ImportError as e:
    print(f'⚠ pytest not installed - pytest tests will not be available')
    print(f'  Install with: pip install pytest pytest-asyncio')
    print(f'  Or run: pip install -r requirements.txt')

print()

# Test 3: Check dependencies
print('✓ Required imports available:')
try:
    from app.ingestion.application.ingestion_service import IngestionService
    print('  • IngestionService')
    from app.ingestion.domain.enums import JobStatus
    print('  • JobStatus')
    from app.ingestion.infrastructure.persistence import create_local_disk_persistence_store
    print('  • Persistence')
    from app.ingestion.infrastructure.repository import create_database_repository
    print('  • Repository')
    from app.service_registry import get_kb_manager
    print('  • KBManager')
    from app.routers.kb_ingestion.operations import KBIngestionService
    print('  • KBIngestionService')
except Exception as e:
    print(f'✗ Import failed: {e}')

print()
print('='*60)
print('Test validation complete!')
print('='*60)
print()
print('To run standalone test:')
print('  python test_caf_pause_resume.py')
print()
print('To run pytest suite (requires pytest):')
print('  pytest app/ingestion/tests/test_caf_integration.py -v -s')
print()
print('To use test runner:')
print('  python run_caf_tests.py --help')
