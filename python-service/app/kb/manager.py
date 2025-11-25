"""
Knowledge Base Manager
Loads and manages multiple knowledge base configurations.
"""

import json
import os
import logging
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class KBConfig:
    """Knowledge base configuration."""
    
    def __init__(self, config_dict: dict):
        self.id: str = config_dict['id']
        self.name: str = config_dict['name']
        self.description: str = config_dict.get('description', '')
        self.status: str = config_dict.get('status', 'active')
        self.embedding_model: str = config_dict.get('embedding_model', 'text-embedding-3-small')
        self.generation_model: str = config_dict.get('generation_model', 'gpt-4o-mini')
        self.chunk_size: int = config_dict.get('chunk_size', 800)
        self.chunk_overlap: int = config_dict.get('chunk_overlap', 120)
        self.source_url: str = config_dict.get('source_url', '')
        self.paths: dict = config_dict.get('paths', {})
        
        # Profile configuration
        self.profiles: List[str] = config_dict.get('profiles', ['chat', 'proposal'])
        self.priority: int = config_dict.get('priority', 5)
        
    @property
    def index_path(self) -> str:
        """Get full path to index directory."""
        if 'index' in self.paths:
            # Check if absolute path
            index_path = self.paths['index']
            if os.path.isabs(index_path):
                return index_path
            # Relative to project root
            project_root = Path(__file__).parent.parent.parent.parent
            return str(project_root / index_path)
        return ""
    
    @property
    def is_active(self) -> bool:
        """Check if KB is active."""
        return self.status == 'active'
    
    def supports_profile(self, profile: str) -> bool:
        """Check if KB supports given profile."""
        return profile in self.profiles


class KBManager:
    """Manages multiple knowledge bases."""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize KB manager.
        
        Args:
            config_path: Path to config.json. If None, uses default location.
        """
        if config_path is None:
            project_root = Path(__file__).parent.parent.parent.parent
            config_path = project_root / "data" / "knowledge_bases" / "config.json"
        
        self.config_path = Path(config_path)
        self.knowledge_bases: Dict[str, KBConfig] = {}
        self._load_config()
    
    def _load_config(self):
        """Load knowledge base configurations from config.json."""
        try:
            if not self.config_path.exists():
                logger.warning(f"Config file not found: {self.config_path}")
                return
            
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            for kb_dict in config.get('knowledge_bases', []):
                kb = KBConfig(kb_dict)
                self.knowledge_bases[kb.id] = kb
                logger.info(f"Loaded KB: {kb.id} ({kb.name}) - Status: {kb.status}")
        
        except Exception as e:
            logger.error(f"Failed to load KB config: {e}")
    
    def get_kb(self, kb_id: str) -> Optional[KBConfig]:
        """Get KB configuration by ID."""
        return self.knowledge_bases.get(kb_id)
    
    def get_active_kbs(self) -> List[KBConfig]:
        """Get all active knowledge bases."""
        return [kb for kb in self.knowledge_bases.values() if kb.is_active]
    
    def get_kbs_for_profile(self, profile: str) -> List[KBConfig]:
        """
        Get knowledge bases that support given profile.
        
        Args:
            profile: 'chat' or 'proposal'
            
        Returns:
            List of KB configs supporting the profile, sorted by priority
        """
        kbs = [
            kb for kb in self.knowledge_bases.values()
            if kb.is_active and kb.supports_profile(profile)
        ]
        # Sort by priority (lower number = higher priority)
        return sorted(kbs, key=lambda kb: kb.priority)
    
    def list_kbs(self) -> List[Dict]:
        """List all knowledge bases with basic info."""
        return [
            {
                'id': kb.id,
                'name': kb.name,
                'status': kb.status,
                'profiles': kb.profiles,
                'priority': kb.priority
            }
            for kb in self.knowledge_bases.values()
        ]
