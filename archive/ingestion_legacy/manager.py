"""
Knowledge Base Manager
Loads and manages multiple knowledge base configurations.
"""

import json
import os
import logging
from pathlib import Path
from typing import Dict, List, Optional
from config import get_openai_settings, get_kb_defaults

logger = logging.getLogger(__name__)


class KBConfig:
    """Knowledge base configuration."""
    
    def __init__(self, config_dict: dict):
        # Load defaults from config
        openai_settings = get_openai_settings()
        kb_defaults = get_kb_defaults()
        
        self.id: str = config_dict['id']
        self.name: str = config_dict['name']
        self.description: str = config_dict.get('description', '')
        self.status: str = config_dict.get('status', 'active')
        self.embedding_model: str = config_dict.get('embedding_model', openai_settings.embedding_model)
        self.generation_model: str = config_dict.get('generation_model', openai_settings.model)
        self.chunk_size: int = config_dict.get('chunk_size', kb_defaults.chunk_size)
        self.chunk_overlap: int = config_dict.get('chunk_overlap', kb_defaults.chunk_overlap)
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
            # Relative to backend root (backend/data/...)
            backend_root = Path(__file__).parent.parent.parent
            return str(backend_root / index_path)
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
            backend_root = Path(__file__).parent.parent.parent
            config_path = backend_root / "data" / "knowledge_bases" / "config.json"
        
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
    
    def kb_exists(self, kb_id: str) -> bool:
        """Check if a KB with given ID exists."""
        return kb_id in self.knowledge_bases
    
    def get_kb_config(self, kb_id: str) -> Dict:
        """Get raw KB configuration dictionary."""
        kb = self.get_kb(kb_id)
        if not kb:
            raise ValueError(f"KB '{kb_id}' not found")
        
        # Return full config dict
        with open(self.config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        for kb_dict in config.get('knowledge_bases', []):
            if kb_dict['id'] == kb_id:
                return kb_dict
        
        raise ValueError(f"KB '{kb_id}' not found in config")
    
    def get_kb_storage_path(self, kb_id: str) -> str:
        """Get storage directory path for a KB."""
        backend_root = Path(__file__).parent.parent.parent
        kb_root = os.getenv("KNOWLEDGE_BASES_ROOT", str(backend_root / "data" / "knowledge_bases"))
        
        # Handle relative paths
        if not Path(kb_root).is_absolute():
            kb_root = str(backend_root / kb_root)
        
        kb_dir = Path(kb_root) / kb_id
        return str(kb_dir / "index")
    
    def create_kb(self, kb_id: str, kb_config: Dict):
        """
        Create a new knowledge base.
        
        Args:
            kb_id: Unique KB identifier
            kb_config: KB configuration dictionary
        """
        if self.kb_exists(kb_id):
            raise ValueError(f"KB '{kb_id}' already exists")
        
        # Create KB directory structure
        backend_root = Path(__file__).parent.parent.parent
        kb_dir = backend_root / "data" / "knowledge_bases" / kb_id
        kb_dir.mkdir(parents=True, exist_ok=True)
        (kb_dir / "index").mkdir(exist_ok=True)
        (kb_dir / "documents").mkdir(exist_ok=True)
        
        # Update paths in config
        kb_config['paths'] = {
            'index': f"data/knowledge_bases/{kb_id}/index",
            'documents': f"data/knowledge_bases/{kb_id}/documents"
        }
        
        # Add to config.json
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except FileNotFoundError:
            config = {'knowledge_bases': []}
        
        config['knowledge_bases'].append(kb_config)
        
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)
        
        # Reload config
        self._load_config()
        
        logger.info(f"Created KB: {kb_id}")
    
    def update_kb_config(self, kb_id: str, kb_config: Dict):
        """
        Update KB configuration.
        
        Args:
            kb_id: KB identifier
            kb_config: Updated KB configuration
        """
        if not self.kb_exists(kb_id):
            raise ValueError(f"KB '{kb_id}' not found")
        
        # Load current config
        with open(self.config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # Update KB in list
        for i, kb_dict in enumerate(config['knowledge_bases']):
            if kb_dict['id'] == kb_id:
                config['knowledge_bases'][i] = kb_config
                break
        
        # Save config
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)
        
        # Reload config
        self._load_config()
        
        logger.info(f"Updated KB: {kb_id}")
    
    def delete_kb(self, kb_id: str):
        """
        Delete a knowledge base and all its data.
        
        Args:
            kb_id: KB identifier
        """
        if not self.kb_exists(kb_id):
            raise ValueError(f"KB '{kb_id}' not found")
        
        # Remove from config.json
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except FileNotFoundError:
            config = {'knowledge_bases': []}
        
        config['knowledge_bases'] = [
            kb for kb in config['knowledge_bases'] if kb['id'] != kb_id
        ]
        
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)
        
        # Delete KB directory and all its data
        backend_root = Path(__file__).parent.parent.parent
        kb_dir = backend_root / "data" / "knowledge_bases" / kb_id
        
        if kb_dir.exists():
            import shutil
            import time
            
            # Try to delete with retries (handles Windows file locking issues)
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    # On Windows, use onerror handler to handle permission issues
                    def handle_remove_readonly(func, path, exc):
                        """Handle readonly files on Windows"""
                        import stat
                        import os
                        os.chmod(path, stat.S_IWRITE)
                        func(path)
                    
                    shutil.rmtree(kb_dir, onerror=handle_remove_readonly)
                    logger.info(f"Deleted KB directory: {kb_dir}")
                    break
                except PermissionError as e:
                    if attempt < max_retries - 1:
                        logger.warning(f"Attempt {attempt + 1} failed to delete {kb_dir}: {e}. Retrying...")
                        time.sleep(0.5)  # Wait before retry
                    else:
                        logger.error(f"Failed to delete KB directory after {max_retries} attempts: {e}")
                        raise ValueError(f"Failed to delete KB data: {str(e)}. Files may be in use.")
        
        # Reload config
        self._load_config()
        
        logger.info(f"Deleted KB: {kb_id}")
