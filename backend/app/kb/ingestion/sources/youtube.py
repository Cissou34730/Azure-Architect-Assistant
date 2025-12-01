"""
YouTube Source Handler
Handles YouTube transcript ingestion with LLM-powered distillation.
"""

import re
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from llama_index.core import Document
from llama_index.readers.youtube_transcript import YoutubeTranscriptReader
from llama_index.llms.openai import OpenAI
from pydantic import BaseModel, Field

from .base import BaseSourceHandler

logger = logging.getLogger(__name__)


# ============================================================================
# Structured Output Models
# ============================================================================

class KeyConcept(BaseModel):
    """Extracted key concept from transcript"""
    name: str = Field(description="Name of the concept or technical term")
    definition: str = Field(description="Definition, rule, or constraint")


class TechnicalQA(BaseModel):
    """Question/Answer pair for better retrieval"""
    question: str = Field(description="Question an architect would ask")
    answer: str = Field(description="Precise technical answer")


class DistilledTranscript(BaseModel):
    """Complete distilled transcript output"""
    key_concepts: List[KeyConcept] = Field(default_factory=list, description="Key concepts and facts")
    technical_qa: List[TechnicalQA] = Field(default_factory=list, description="Technical Q&A pairs")
    summary: str = Field(description="One-paragraph summary of main topics")


# ============================================================================
# Distillation Prompt
# ============================================================================

YOUTUBE_DISTILLATION_PROMPT = """### ROLE
You are a Senior Technical Writer at Microsoft, specializing in Azure Architecture. 
Your mission is to convert raw spoken transcripts into dense, structured technical documentation for a Knowledge Base (RAG).

### INSTRUCTIONS
Analyze the provided transcript and extract two types of structured information:

1. **FACTS & RULES**: 
   - Indisputable technical statements
   - Limits (quotas, latencies, constraints)
   - Firm recommendations (Do/Don't patterns)
   - Key concept definitions
   - Best practices and patterns

2. **TECHNICAL Q&A**: 
   - Transform narrative explanations into clear Question/Answer pairs
   - The question must reflect what an architect would ask
   - The answer must be the specific technical solution from the text
   - Critical for retrieval: write questions an architect would naturally search for

### CLEANING RULES
- **IGNORE**: 
  - Oral fillers ("um", "so", "you see", "basically")
  - Jokes and personal anecdotes
  - Introductions and marketing fluff
  - Greetings ("Hello everyone", "Thanks for watching")
  
- **SYNTHESIZE**: 
  - If the speaker takes 5 sentences to say something, extract the essence
  - Example: "So like, what happens is, you know, the SLA is actually 99.9%" → "SLA = 99.9%"
  
- **CONTEXT**: 
  - Define acronyms at first mention (e.g., "App Service Environment (ASE)")
  - Use full technical names for Azure services
  
- **LANGUAGE**: 
  - Keep Azure technical terms in English
  - Write explanations in clear, professional language

### INPUT TRANSCRIPT
{transcript}

### OUTPUT
Extract the information and format according to the DistilledTranscript schema.
"""


# ============================================================================
# YouTube Source Handler
# ============================================================================

class YouTubeSourceHandler(BaseSourceHandler):
    """
    Handle YouTube transcript ingestion with LLM-powered distillation.
    Converts raw transcripts into structured knowledge (concepts + Q&A).
    """
    
    def __init__(self, kb_id: str, job=None, state=None):
        super().__init__(kb_id, job=job, state=state)
        self.reader = YoutubeTranscriptReader()
        self.llm = OpenAI(model="gpt-4o-mini", temperature=0.1)
        logger.info(f"YouTubeSourceHandler initialized for KB: {kb_id}")
    
    def ingest(self, config: Dict[str, Any]) -> List[Document]:
        """
        Ingest YouTube videos from config.
        
        Args:
            config: Must contain 'video_urls' list
            
        Returns:
            List of Documents
        """
        video_urls = config.get('video_urls', [])
        metadata = config.get('metadata', {})
        
        all_docs = []
        for url in video_urls:
            # Cooperative pause/cancel check
            if self.state:
                if self.state.cancel_requested:
                    logger.info(f"YouTube ingestion cancelled at {len(all_docs)} videos")
                    return all_docs
                if self.state.paused:
                    logger.info(f"YouTube ingestion paused at {len(all_docs)} videos")
                    return all_docs
            
            docs = self.ingest_video(url, metadata)
            all_docs.extend(docs)
        
        return all_docs
    
    def ingest_video(self, video_url: str, metadata: Optional[Dict[str, Any]] = None) -> List[Document]:
        """
        Ingest YouTube video transcript with distillation.
        
        Args:
            video_url: YouTube video URL
            metadata: Optional metadata (title, channel, etc.)
            
        Returns:
            List of Documents (summary + concepts + Q&A pairs)
        """
        try:
            video_id = self._extract_video_id(video_url)
            logger.info(f"Ingesting YouTube video: {video_id}")
            
            # Load transcript
            transcript_docs = self.reader.load_data(ytlinks=[video_url])
            
            if not transcript_docs:
                logger.warning(f"No transcript found for {video_url}")
                return []
            
            transcript_text = transcript_docs[0].get_content()
            
            # Distill transcript using LLM
            distilled = self._distill_transcript(transcript_text)
            
            # Create documents for better retrieval
            documents = []
            base_metadata = {
                'source_type': 'youtube',
                'video_url': video_url,
                'video_id': video_id,
                'kb_id': self.kb_id,
                'date_ingested': datetime.now().isoformat(),
                **(metadata or {})
            }
            
            # 1. Summary document
            summary_doc = Document(
                text=f"# Video Summary\n\n{distilled.summary}",
                metadata={**base_metadata, 'content_type': 'summary'}
            )
            documents.append(summary_doc)
            
            # 2. Concept documents (one per concept)
            for concept in distilled.key_concepts:
                concept_doc = Document(
                    text=f"**{concept.name}**: {concept.definition}",
                    metadata={
                        **base_metadata,
                        'content_type': 'concept',
                        'concept_name': concept.name
                    }
                )
                documents.append(concept_doc)
            
            # 3. Q&A documents (one per Q&A pair)
            for qa in distilled.technical_qa:
                qa_doc = Document(
                    text=f"**Q: {qa.question}**\n\nA: {qa.answer}",
                    metadata={
                        **base_metadata,
                        'content_type': 'qa',
                        'question': qa.question
                    }
                )
                documents.append(qa_doc)
            
            logger.info(f"Distilled {video_id}: {len(distilled.key_concepts)} concepts, "
                       f"{len(distilled.technical_qa)} Q&A pairs")
            return documents
            
        except Exception as e:
            logger.error(f"Failed to ingest YouTube video {video_url}: {e}", exc_info=True)
            return []
    
    def _distill_transcript(self, transcript: str) -> DistilledTranscript:
        """Use LLM to distill transcript into structured format"""
        
        prompt = YOUTUBE_DISTILLATION_PROMPT.format(transcript=transcript)
        
        try:
            response = self.llm.structured_predict(
                output_cls=DistilledTranscript,
                prompt=prompt
            )
            return response
            
        except Exception as e:
            logger.error(f"Distillation failed: {e}")
            # Return minimal structure
            return DistilledTranscript(
                key_concepts=[],
                technical_qa=[],
                summary="Failed to distill transcript"
            )
    
    def _extract_video_id(self, url: str) -> str:
        """Extract video ID from YouTube URL"""
        patterns = [
            r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([^&]+)',
            r'(?:https?://)?(?:www\.)?youtu\.be/([^?]+)',
            r'(?:https?://)?(?:www\.)?youtube\.com/embed/([^?]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        raise ValueError(f"Could not extract video ID from {url}")
    
    def ingest_playlist(self, playlist_url: str) -> List[Document]:
        """
        Ingest entire YouTube playlist.
        
        Args:
            playlist_url: YouTube playlist URL
            
        Returns:
            List of Documents from all videos
        """
        # TODO: Implement playlist parsing
        logger.warning("Playlist ingestion not yet implemented")
        return []
