Step-by-Step Implementation Plan for Phase Status Management
Phase 1: Backend Domain Model Enhancement
Step 1.1: Create Phase Status Enum
Create a new enum PhaseStatus in enums.py
Define statuses: NOT_STARTED, RUNNING, PAUSED, COMPLETED, FAILED
Keep it simple, no complex state machine initially
Step 1.2: Create Phase State Model
Create new file backend/app/ingestion/domain/models/phase_state.py
Define PhaseState dataclass with:
phase_name: string (loading, chunking, embedding, indexing)
status: PhaseStatus enum
progress: int (0-100)
items_processed: int
items_total: Optional[int]
started_at: Optional[datetime]
completed_at: Optional[datetime]
error: Optional[string]
Step 1.3: Enhance IngestionState Model
Update state.py
Add field phases: Dict[str, PhaseState] to track all four phases
Add method get_overall_status() to consolidate phase statuses into overall job status
Add method get_current_phase() to determine which phase is active
Phase 2: Database Schema Updates
Step 2.1: Create Database Migration
Add new table ingestion_phase_status with columns:
id: primary key
job_id: foreign key to ingestion_jobs
phase_name: string
status: string
progress: integer
items_processed: integer
items_total: integer (nullable)
started_at: datetime (nullable)
completed_at: datetime (nullable)
error: text (nullable)
created_at, updated_at: timestamps
Step 2.2: Update SQLAlchemy Models
Create new model class IngestionPhaseStatus in models.py
Add relationship from IngestionJob to IngestionPhaseStatus
Phase 3: Infrastructure Layer Updates
Step 3.1: Extend Repository Interface
Update repository.py
Add methods:
update_phase_status(job_id, phase_name, status, progress, ...)
get_phase_status(job_id, phase_name)
get_all_phases_status(job_id)
Step 3.2: Implement Repository Methods
Update repository.py
Implement the new phase status CRUD operations
Ensure transactional consistency
Phase 4: Application Layer - Phase Tracker Service
Step 4.1: Create Phase Tracker Service
Create new file backend/app/ingestion/application/phase_tracker.py
Implement PhaseTracker class with methods:
initialize_phases(job_id): Create all 4 phases with NOT_STARTED status
start_phase(job_id, phase_name): Mark phase as RUNNING
pause_phase(job_id, phase_name): Mark phase as PAUSED
complete_phase(job_id, phase_name): Mark phase as COMPLETED
fail_phase(job_id, phase_name, error): Mark phase as FAILED
update_progress(job_id, phase_name, progress, items_processed): Update metrics
get_consolidated_status(job_id): Calculate overall job status from all phases
Step 4.2: Integrate with Ingestion Service
Update ingestion_service.py
Inject PhaseTracker instance
Call phase tracker methods during ingestion lifecycle
Phase 5: Worker Integration
Step 5.1: Update Producer Worker
Modify producer.py
Add phase tracking calls:
Start loading phase when beginning file crawl
Update progress during loading
Complete loading phase when done
Start chunking phase
Update progress during chunking
Complete chunking phase when done
Step 5.2: Update Consumer Worker
Modify consumer.py
Add phase tracking calls:
Start embedding phase when first item dequeued
Update progress during embedding
Complete embedding phase
Start indexing phase
Update progress during indexing
Complete indexing phase
Phase 6: Control Flow - Pause/Resume/Cancel
Step 6.1: Enhance Lifecycle Manager
Update lifecycle.py
Add pause handling that:
Sets pause flag
Waits for current batch to finish
Marks current phase as PAUSED
Persists state
Step 6.2: Implement Resume Logic
Update resume method to:
Load phase status from database
Resume from the last PAUSED phase
Change phase status from PAUSED to RUNNING
Continue processing
Step 6.3: Implement Cancel Logic
Add cancel method:
Set stop flag
Mark current phase as FAILED with "Canceled by user"
Mark remaining phases as NOT_STARTED
Clean up resources
Phase 7: API Endpoints
Step 7.1: Update Status Response Model
Update ingestion_models.py
Enhance JobStatusResponse to include:
phases: List of PhaseStatusDetail
Create PhaseStatusDetail model with all phase information
Step 7.2: Add Control Endpoints
Update ingestion_router.py
Add/enhance endpoints:
POST /kb/{kb_id}/start: Already exists, ensure it initializes phases
POST /kb/{kb_id}/pause: New endpoint to pause ingestion
POST /kb/{kb_id}/resume: New endpoint to resume ingestion
POST /kb/{kb_id}/cancel: New endpoint to cancel ingestion
GET /kb/{kb_id}/status: Enhance to return phase details
Phase 8: Frontend Implementation
Step 8.1: Update TypeScript Types
Update ingestion.ts
Add PhaseStatus type
Add PhaseDetail interface
Update IngestionJob interface to include phases array
Step 8.2: Update API Service
Update ingestionApi.ts
Add functions:
pauseIngestion(kbId: string)
resumeIngestion(kbId: string)
cancelIngestion(kbId: string)
Step 8.3: Create Phase Status Component
Create frontend/src/components/ingestion/PhaseStatus.tsx
Display visual representation of all 4 phases
Show status icon/color for each phase (not started, running, paused, completed)
Show progress bar for each phase
Keep it simple: just status indicators and progress
Step 8.4: Update KBListItem Component
Update KBListItem.tsx
Add control buttons:
"Start Ingestion" (when not started)
"Pause" (when running)
"Resume" (when paused)
"Cancel" (when running or paused)
Show current phase and overall progress
Integrate PhaseStatus component
Step 8.5: Add Phase Detail View (Optional)
Create expandable section to show detailed phase information
Display items processed, errors, timestamps per phase
Keep UI clean and simple
Phase 9: Testing
Step 9.1: Unit Tests
Test PhaseStatus enum and transitions
Test PhaseState model
Test PhaseTracker service methods
Test repository phase operations
Step 9.2: Integration Tests
Test complete start → pause → resume flow
Test start → cancel flow
Test phase progression through all 4 phases
Test error handling in phases
Step 9.3: Manual Testing
Test frontend controls work correctly
Verify status updates in real-time
Test edge cases (pause during phase transition, etc.)
Phase 10: Documentation
Step 10.1: Update Architecture Documentation
Document phase status management in ARCHITECTURE.md
Add state diagram showing phase transitions
Step 10.2: Update API Documentation
Document new endpoints in INGESTION_API.md
Add request/response examples
Step 10.3: Update User Guide
Create simple guide for using pause/resume/cancel features