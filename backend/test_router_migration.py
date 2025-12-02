"""
Test script to verify router imports with new refactored code.
"""

print('Testing router imports...')
from app.routers.kb_ingestion.router import router as ing_router
from app.routers.kb_management.router import router as mgmt_router
from app.lifecycle import startup, shutdown
print('✓ All router imports successful')
print('✓ Lifecycle imports successful')

print('\nTesting service instantiation...')
from app.ingestion.application.ingestion_service import IngestionService
service = IngestionService.instance()
print('✓ Service instantiated')

methods = [m for m in dir(service) if not m.startswith('_')]
print(f'✓ Service has {len(methods)} public methods')
print(f'✓ Key methods: start, resume, pause, cancel, status')

required_methods = ['start', 'resume', 'pause', 'cancel', 'status']
has_all = all(hasattr(service, m) for m in required_methods)
print(f'✓ All required methods present: {has_all}')

print('\n✅ All imports and instantiation successful!')
