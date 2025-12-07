"""
Producer Pipeline - Crawl, Chunk, and Enqueue
Handles the producer phase of ingestion: document crawling, chunking, and enqueueing for the consumer.
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional
from pathlib import Path
from hashlib import sha256
import json
import re
from urllib.parse import urlparse

from llama_index.core import Document
from config import get_kb_defaults

from app.ingestion.domain.phase_tracker import PhaseTracker, IngestionPhase, PhaseStatus
from app.ingestion.domain.sources import SourceHandlerFactory
from app.ingestion.domain.chunking import ChunkerFactory
from app.ingestion.infrastructure.persistence import create_local_disk_persistence_store
from app.ingestion.infrastructure.repository import create_database_repository
from app.ingestion.core.orchestrator import IngestionOrchestrator
from app.ingestion.core.state_manager import aggregate_job_status
from app.ingestion.core.phase import PhaseStatus

logger = logging.getLogger(__name__)


class ProducerPipeline:
    """
    Producer pipeline: Crawl → Save → Chunk → Enqueue
    Runs in producer thread, feeds work to consumer via DB queue.
    """
    
    def __init__(self, kb_config: Dict[str, Any], state=None):
        """
        Initialize producer pipeline.
        
        Args:
            kb_config: Knowledge base configuration
            state: IngestionState for progress tracking and cancellation
        """
        # Merge KB config with defaults
        defaults = get_kb_defaults()
        self.kb_config = defaults.merge_with_kb_config(kb_config)
        self.state = state
        self.kb_id = self.kb_config['id'] if 'id' in self.kb_config else self.kb_config['kb_id']
        self.source_type = self.kb_config['source_type']
        self.source_config = self.kb_config.get('source_config', {})
        
        # Configuration
        self.chunk_size = self.kb_config['chunk_size']
        self.chunk_overlap = self.kb_config['chunk_overlap']
        self.chunking_strategy = self.kb_config['chunking_strategy']
        
        # Metrics
        self.all_documents = []
        self.total_chunks_enqueued = 0
        self.batch_num = 0
        
        # Phase tracking
        self.phase_tracker: Optional[PhaseTracker] = None
        if state and state.job_id:
            self.phase_tracker = PhaseTracker(state.job_id, self.kb_id)
            if state.phase_status:
                self.phase_tracker.load_from_dict(state.phase_status)
        
    async def run(self):
        """
        Execute the producer pipeline.
        Crawls documents, chunks them, and enqueues for consumer.
        """
        logger.info(f"=== Producer Pipeline Start: KB {self.kb_id} ===")
        logger.info(f"  Source type: {self.source_type}")
        
        try:
            # Check if cancelled before starting
            if await self._check_cancel("pipeline start"):
                if self.phase_tracker:
                    current_phase = self.phase_tracker.get_current_phase()
                    if current_phase:
                        self.phase_tracker.cancel_phase(current_phase)
                    self._persist_phase_tracker()
                return
            
            # Check if this is a resume with existing work in queue
            if await self._check_resume_scenario():
                logger.info("Resume scenario detected - skipping document loading, consumer will process existing queue")
                # Mark loading/chunking as completed if not already
                if self.phase_tracker:
                    for phase in [IngestionPhase.LOADING, IngestionPhase.CHUNKING]:
                        if not self.phase_tracker.is_phase_completed(phase):
                            self.phase_tracker.complete_phase(phase)
                    self._persist_phase_tracker()
                return
            
            # Initialize components
            handler = SourceHandlerFactory.create_handler(
                self.source_type,
                self.kb_id,
                state=self.state
            )
            
            chunker = ChunkerFactory.create_chunker(
                strategy=self.chunking_strategy,
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap
            )
            
            # Process batches with phase tracking
            await self._process_batches(handler, chunker)
            
            # Verify we got work done
            await self._verify_completion()
            
            # Mark chunking phase as completed
            if self.phase_tracker:
                self.phase_tracker.complete_phase(IngestionPhase.CHUNKING, self.total_chunks_enqueued)
                self._persist_phase_tracker()
            
            logger.info(f"=== Producer Pipeline Complete: KB {self.kb_id} ===")
            logger.info(f"  Documents: {len(self.all_documents)}")
            logger.info(f"  Chunks enqueued: {self.total_chunks_enqueued}")
            
        except Exception as e:
            logger.error(f"Producer pipeline failed for KB {self.kb_id}: {e}", exc_info=True)
            if self.state:
                # Route failure through service helper to enforce invariants
                try:
                    from app.ingestion.application.ingestion_service import IngestionService
                    IngestionService.instance()._set_failed(self.state, error_message=str(e))
                except Exception:
                    # Fallback if service not available
                    from app.ingestion.domain.enums import JobStatus
                    self.state.status = JobStatus.FAILED.value
                    self.state.error = str(e)
            
            # Mark current phase as failed
            if self.phase_tracker:
                current_phase = self.phase_tracker.get_current_phase()
                if current_phase:
                    self.phase_tracker.fail_phase(current_phase, str(e))
                self._persist_phase_tracker()
            
            raise
    
    async def _process_batches(self, handler, chunker):
        """Process document batches from source."""
        # ===== PHASE 1: LOADING (formerly CRAWLING) =====
        # Check if LOADING phase needs to run
        if self.phase_tracker and not self.phase_tracker.should_run_phase(IngestionPhase.LOADING):
            logger.info("LOADING phase already complete, skipping document loading")
        else:
            # Start LOADING phase
            if self.phase_tracker:
                self.phase_tracker.start_phase(IngestionPhase.LOADING)
                self._persist_phase_tracker()
            
            self._update_progress(IngestionPhase.LOADING, 0, "Loading documents from source...")
        
        try:
            for document_batch in self._load_documents_from_source(handler):
                self.batch_num += 1
                batch_size = len(document_batch)
                
                logger.info(f"\n=== Processing Batch {self.batch_num} ({batch_size} documents) ===")
                
                # Check cancellation
                if await self._check_cancel(f"batch {self.batch_num} start"):
                    logger.info(f"Stopped at batch {self.batch_num}: {len(self.all_documents)} docs, {self.total_chunks_enqueued} chunks")
                    if self.phase_tracker:
                        current_phase = self.phase_tracker.get_current_phase()
                        if current_phase:
                            self.phase_tracker.pause_phase(current_phase)
                        self._persist_phase_tracker()
                    return
                
                # Save documents to disk
                self._save_documents_to_disk(document_batch)
                self.all_documents.extend(document_batch)
                
                # Update metrics and phase progress
                if self.state:
                    self.state.metrics['documents_crawled'] = len(self.all_documents)
                
                if self.phase_tracker:
                    crawl_progress = min(100, (self.batch_num * 10))
                    self.phase_tracker.update_phase_progress(
                        IngestionPhase.LOADING, 
                        crawl_progress,
                        items_processed=len(self.all_documents)
                    )
                
                await asyncio.sleep(0)  # Yield control
                
                # Update progress
                self._update_progress(
                    IngestionPhase.LOADING,
                    min(30, 10 + self.batch_num),
                    f"Loaded batch {self.batch_num} ({len(self.all_documents)} documents)",
                    {"documents_loaded": len(self.all_documents), "batch_num": self.batch_num}
                )
                
                # Check cancellation after save
                if await self._check_cancel(f"batch {self.batch_num} after save"):
                    if self.phase_tracker:
                        self.phase_tracker.pause_phase(IngestionPhase.LOADING)
                        self._persist_phase_tracker()
                    return
                
            # Complete LOADING phase
            if self.phase_tracker:
                self.phase_tracker.complete_phase(IngestionPhase.LOADING, len(self.all_documents))
                self._persist_phase_tracker()
        
        except GeneratorExit:
            logger.info(f"Generator closed at batch {self.batch_num}")
        except asyncio.CancelledError:
            logger.info(f"KB {self.kb_id} cancelled by system")
            if self.phase_tracker:
                current_phase = self.phase_tracker.get_current_phase()
                if current_phase:
                    self.phase_tracker.pause_phase(current_phase)
                self._persist_phase_tracker()
            raise
        
        # ===== PHASE 2: CHUNKING =====
        # Check if CHUNKING phase needs to run
        if self.phase_tracker and not self.phase_tracker.should_run_phase(IngestionPhase.CHUNKING):
            logger.info("CHUNKING phase already complete, skipping")
            return
        
        # Start CHUNKING phase
        if self.phase_tracker and self.phase_tracker.should_run_phase(IngestionPhase.CHUNKING):
            self.phase_tracker.start_phase(IngestionPhase.CHUNKING)
            self._persist_phase_tracker()
        
        # Chunk all documents
        logger.info(f"Chunking {len(self.all_documents)} documents...")
        self._update_progress(
            IngestionPhase.CHUNKING,
            40,
            f"Chunking {len(self.all_documents)} documents..."
        )
        
        documents_dict = self._convert_documents_to_dict(self.all_documents)
        all_chunks = chunker.chunk_documents(documents_dict, state=self.state)
        
        await asyncio.sleep(0)  # Yield control
        
        logger.info(f"✓ Created {len(all_chunks)} chunks")
        
        # Complete CHUNKING phase
        if self.phase_tracker:
            self.phase_tracker.complete_phase(IngestionPhase.CHUNKING, len(self.all_documents))
            self._persist_phase_tracker()
            
            # Check cancellation after chunking
            if await self._check_cancel(f"after chunking"):
                if self.phase_tracker:
                    self.phase_tracker.pause_phase(IngestionPhase.CHUNKING)
                    self._persist_phase_tracker()
                return
            
            # Start CHUNKING phase (enqueueing)
            if self.phase_tracker:
                self.phase_tracker.start_phase(IngestionPhase.CHUNKING)
                self._persist_phase_tracker()
            
            # Enqueue chunks for consumer
            logger.info(f"Enqueuing {len(all_chunks)} chunks...")
            self._update_progress(
                IngestionPhase.EMBEDDING,
                60,
                f"Queuing chunks for embedding"
            )
            
            enqueued = self._enqueue_chunks(all_chunks)
            self.total_chunks_enqueued += enqueued
            
            await asyncio.sleep(0)  # Yield control
            
            logger.info(f"✓ Total: {len(self.all_documents)} docs, {self.total_chunks_enqueued} chunks queued")
            
            # Persist state
            if self.state:
                self.state.metrics['batches_processed'] = self.batch_num
                self.state.metrics['chunks_queued'] = self.total_chunks_enqueued
                self.state.metrics['documents_processed'] = len(self.all_documents)
                
                persistence = create_local_disk_persistence_store()
                persistence.save(self.state)
                    
    async def _verify_completion(self):
        """Verify that work was done (or already complete)."""
        # If we have no documents but phases show as complete, that's OK (resume scenario)
        if not self.all_documents:
            if self.phase_tracker:
                if self.phase_tracker.is_phase_completed(IngestionPhase.LOADING):
                    logger.info("No documents loaded but LOADING phase complete (resume scenario)")
                    return
            # Only fail if we truly didn't do any work
            raise ValueError("No documents loaded from source")
    
    def _load_documents_from_source(self, handler):
        """Load documents from source handler (generator)."""
        logger.info(f"Loading documents from {self.source_type}")
        
        try:
            result = handler.ingest(self.source_config)
            
            # If generator, yield batches
            if hasattr(result, '__iter__') and not isinstance(result, (list, tuple)):
                logger.info("Handler returned generator for batch processing")
                for batch in result:
                    logger.info(f"Yielding batch of {len(batch)} documents")
                    yield batch
            else:
                # Legacy: handler returned list
                logger.info(f"Handler returned {len(result)} documents")
                yield result
        except Exception as e:
            logger.error(f"Failed to load documents: {e}", exc_info=True)
            raise
    
    def _save_documents_to_disk(self, documents: List[Document]):
        """Save documents to disk with ID-based naming."""
        backend_root = Path(__file__).parent.parent.parent.parent
        doc_dir = backend_root / "data" / "knowledge_bases" / self.kb_id / "documents"
        doc_dir.mkdir(parents=True, exist_ok=True)
        
        for doc in documents:
            meta = doc.metadata or {}
            doc_id = meta.get('doc_id', 0)
            url = meta.get('url', '')
            
            # Extract page name from URL
            if url:
                parsed = urlparse(url)
                path = parsed.path.rstrip('/')
                page_name = path.split('/')[-1] if path else 'index'
                page_name = re.sub(r'\.(html?|php|asp)$', '', page_name)
            else:
                page_name = 'document'
            
            # Sanitize for Windows
            page_name = re.sub(r'[<>:"/\\|?*]', '_', page_name)
            page_name = re.sub(r'\s+', '_', page_name)
            page_name = page_name.strip('._')
            
            if not page_name or page_name == '_':
                page_name = 'document'
            
            if len(page_name) > 100:
                page_name = page_name[:100]
            
            # Format: {id:04d}_{page-name}.md
            filename = f"{doc_id:04d}_{page_name}.md"
            doc_path = doc_dir / filename
            
            try:
                with open(doc_path, 'w', encoding='utf-8') as f:
                    f.write(f"# Doc ID: {doc_id}\n")
                    f.write(f"# URL: {url}\n\n")
                    f.write(doc.text or "")
            except Exception as e:
                logger.error(f"Failed to save document {doc_id}: {e}")
    
    def _convert_documents_to_dict(self, documents: List[Document]) -> List[Dict[str, Any]]:
        """Convert Documents to dict format for chunker."""
        return [
            {
                'content': doc.get_content(),
                'metadata': doc.metadata
            }
            for doc in documents
        ]
    
    def _enqueue_chunks(self, chunks: List[Dict[str, Any]]) -> int:
        """Enqueue chunks to DB queue for consumer."""
        chunk_rows = []
        
        for ch in chunks:
            text = ch.get('content', '')
            meta = ch.get('metadata', {})
            
            # Warn if empty content
            if not text or not text.strip():
                logger.warning(f"Empty content in chunk: metadata={meta}")
            
            # Compute hash
            try:
                meta_s = json.dumps(meta, sort_keys=True, ensure_ascii=False)
            except Exception:
                meta_s = str(meta)
            
            h = sha256((text + meta_s).encode('utf-8')).hexdigest()
            
            chunk_rows.append({
                'doc_hash': h,
                'content': text,
                'metadata': meta,
            })
        
        # Enqueue to DB
        if self.state and self.state.job_id:
            repo = create_database_repository()
            inserted = repo.enqueue_chunks(self.state.job_id, chunk_rows)
            logger.info(f"✓ Enqueued {inserted}/{len(chunk_rows)} chunks for job {self.state.job_id}")
            return inserted
        
        return 0
    
    def _update_progress(self, phase: IngestionPhase, progress: int, message: str, metrics: Dict[str, Any] = None):
        """Update state with progress."""
        if not self.state:
            return
        
        self.state.progress = progress
        self.state.message = message
        
        if metrics:
            self.state.metrics.update(metrics)
        
        # Persist state
        persistence = create_local_disk_persistence_store()
        persistence.save(self.state)
    
    async def _check_cancel(self, checkpoint_name: str) -> bool:
        """Check if cancelled."""
        if not self.state:
            return False
        orchestrator = IngestionOrchestrator.instance()
        desired = orchestrator.get_desired_state(self.state.job_id) if self.state.job_id else "idle"

        if self.state.cancel_requested or desired in ("canceled", "shutdown"):
            logger.info(f"KB {self.kb_id} cancelled at {checkpoint_name}")
            persistence = create_local_disk_persistence_store()
            persistence.save(self.state)
            return True
        # Pause handling: honor orchestrator desired state
        if desired == "paused":
            logger.info(f"KB {self.kb_id} paused at {checkpoint_name}")
            persistence = create_local_disk_persistence_store()
            persistence.save(self.state)
            return True
        return False
    
    async def _check_resume_scenario(self) -> bool:
        """
        Check if this is a resume with existing work in queue.
        Returns True if producer should skip document loading.
        """
        if not self.state or not self.state.job_id:
            return False
        
        try:
            repo = create_database_repository()
            queue_stats = repo.get_queue_stats(self.state.job_id)
            total_in_queue = queue_stats['pending'] + queue_stats['processing']
            
            if total_in_queue > 0:
                logger.info(f"Resume scenario detected: {total_in_queue} chunks already in queue")
                logger.info(f"  Pending: {queue_stats['pending']}, Processing: {queue_stats['processing']}")
                logger.info(f"  Done: {queue_stats['done']}, Error: {queue_stats['error']}")
                return True
        except Exception as e:
            logger.warning(f"Could not check queue stats: {e}")
        
        return False
    
    def _persist_phase_tracker(self) -> None:
        """Persist phase tracker to database and state."""
        if not self.phase_tracker or not self.state or not self.state.job_id:
            return
        
        try:
            # Update state with phase info
            phase_data = self.phase_tracker.to_dict()
            self.state.phase_status = phase_data
            
            current_phase = self.phase_tracker.get_current_phase()
            if current_phase:
                self.state.phase = current_phase.value
            
            # Calculate overall progress
            self.state.progress = self.phase_tracker.get_overall_progress()

            # Aggregate overall job status from per-phase statuses
            try:
                overall = aggregate_job_status({
                    k: {"status": v.get("status", PhaseStatus.IDLE.value)}
                    for k, v in phase_data.items()
                })
                self.state.status = overall
            except Exception:
                pass
            
            # Persist to database
            repo = create_database_repository()
            repo.update_phase_progress(
                self.state.job_id,
                current_phase.value if current_phase else "unknown",
                phase_data
            )
            
            # Persist to local storage
            persistence = create_local_disk_persistence_store()
            persistence.save(self.state)
            
        except Exception as e:
            logger.warning(f"Failed to persist phase tracker: {e}")
