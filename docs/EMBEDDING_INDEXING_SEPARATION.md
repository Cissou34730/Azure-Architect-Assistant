# Embedding and Indexing Separation

## Overview

The ingestion pipeline now properly separates **embedding generation** and **index building** into distinct modules, following the Single Responsibility Principle (SRP).

## Architecture

### 4-Phase Pipeline

```
LOADING → CHUNKING → EMBEDDING → INDEXING
   ↓          ↓          ↓          ↓
Sources   Chunking   Embedding  Indexing
(domain)  (domain)  (infra)    (infra)
```

### Module Structure

```
app/ingestion/
├── domain/
│   ├── sources/           # Document loading (PDF, markdown, YouTube, website)
│   └── chunking/          # Document splitting strategies
│
└── infrastructure/
    ├── embedding/         # NEW: Embedding generation
    │   ├── embedder_base.py      # Abstract embedder interface
    │   ├── openai_embedder.py    # OpenAI implementation
    │   └── factory.py            # EmbedderFactory
    │
    └── indexing/          # REFACTORED: Index building only
        ├── builder_base.py       # Abstract builder interface
        ├── vector.py             # Accepts PRE-EMBEDDED documents
        └── factory.py            # IndexBuilderFactory
```

## Changes Made

### 1. Created `infrastructure/embedding/`

**`embedder_base.py`** - Abstract base class:
```python
class BaseEmbedder(ABC):
    @abstractmethod
    def embed_documents(self, documents: List[Dict]) -> List[LlamaDocument]:
        """Generate embeddings for documents"""
        pass
```

**`openai_embedder.py`** - OpenAI implementation:
```python
class OpenAIEmbedder(BaseEmbedder):
    def __init__(self, model_name: str = "text-embedding-3-small"):
        self.embedder = OpenAIEmbedding(model=model_name)
    
    def embed_documents(self, documents, progress_callback=None):
        # Convert to LlamaIndex documents
        # Generate embeddings using OpenAI
        # Return documents WITH embeddings set
        return llama_docs
```

**`factory.py`** - Factory pattern:
```python
class EmbedderFactory:
    EMBEDDERS = {
        'openai': OpenAIEmbedder,
        'default': OpenAIEmbedder
    }
    
    @classmethod
    def create_embedder(cls, embedder_type='openai', model_name='text-embedding-3-small'):
        return cls.EMBEDDERS[embedder_type](model_name=model_name)
```

### 2. Refactored `infrastructure/indexing/vector.py`

**Before (God Class - SRP Violation):**
```python
class VectorIndexBuilder:
    def build_index(self, documents: List[Dict]):
        # 1. Convert to LlamaIndex docs
        # 2. Generate embeddings (EMBEDDING phase) ❌
        # 3. Build index (INDEXING phase) ❌
        # 4. Persist to disk
        index = VectorStoreIndex.from_documents(llama_docs)  # Embedding + Indexing mixed!
```

**After (Single Responsibility):**
```python
class VectorIndexBuilder:
    def build_index(self, embedded_documents: List[LlamaDocument]):
        # Validate documents HAVE embeddings
        # Build index from PRE-EMBEDDED documents ✅
        # Persist to disk
        index = VectorStoreIndex(embedded_documents)  # Only indexing!
```

### 3. Updated `consumer_pipeline.py`

**Before:**
```python
class ConsumerPipeline:
    def __init__(self, runtime):
        self.index_builder = self._create_index_builder()  # Does everything
    
    def _index_documents(self, docs):
        # Calls build_index() which does BOTH embedding and indexing
        self.index_builder.build_index(docs)
```

**After:**
```python
class ConsumerPipeline:
    def __init__(self, runtime):
        self.embedder = self._create_embedder()           # Separate concerns
        self.index_builder = self._create_index_builder()  # Separate concerns
    
    def _index_documents(self, docs):
        # PHASE 1: EMBEDDING
        embedded_docs = self.embedder.embed_documents(docs, progress_callback)
        
        # PHASE 2: INDEXING
        self.index_builder.build_index(embedded_docs, progress_callback)
```

## Benefits

### 1. Single Responsibility Principle ✅
- **Embedder**: Generate vector embeddings
- **IndexBuilder**: Store embeddings in searchable structure
- Each class has ONE reason to change

### 2. Proper Phase Separation ✅
- EMBEDDING phase explicitly handled by embedder
- INDEXING phase explicitly handled by index builder
- Matches the 4-phase architecture (LOADING, CHUNKING, EMBEDDING, INDEXING)

### 3. Flexibility ✅
**Swap embedders independently:**
```python
# Use OpenAI
embedder = EmbedderFactory.create_embedder('openai', 'text-embedding-3-small')

# Use Azure OpenAI (future)
embedder = EmbedderFactory.create_embedder('azure', 'text-embedding-3-small')

# Use local model (future)
embedder = EmbedderFactory.create_embedder('local', 'sentence-transformers/all-MiniLM-L6-v2')
```

**Swap index storage independently:**
```python
# Use LlamaIndex
builder = IndexBuilderFactory.create_builder('vector', kb_id, storage_dir)

# Use Pinecone (future)
builder = IndexBuilderFactory.create_builder('pinecone', kb_id, api_key=...)

# Use Weaviate (future)
builder = IndexBuilderFactory.create_builder('weaviate', kb_id, url=...)
```

### 4. Testability ✅
- Can test embedding generation without index building
- Can test index building with mock embedded documents
- Can swap implementations for testing (mock embedder, in-memory index)

## Future Extensions

### Add Azure OpenAI Embedder
```python
# backend/app/ingestion/infrastructure/embedding/azure_embedder.py
class AzureEmbedder(BaseEmbedder):
    def __init__(self, deployment_name, api_key, endpoint):
        self.embedder = AzureOpenAIEmbedding(...)
```

### Add Local Model Embedder
```python
# backend/app/ingestion/infrastructure/embedding/local_embedder.py
class LocalEmbedder(BaseEmbedder):
    def __init__(self, model_name):
        self.embedder = HuggingFaceEmbedding(model_name)
```

### Add Pinecone Index Builder
```python
# backend/app/ingestion/infrastructure/indexing/pinecone_builder.py
class PineconeIndexBuilder(BaseIndexBuilder):
    def build_index(self, embedded_documents):
        # Store in Pinecone vector database
```

## Litmus Test

**Question:** "If I change the embedding provider, does the index storage change?"

**Answer:** **NO** - They are now completely independent!

- Switch embedder: OpenAI → Azure → Local model (IndexBuilder unchanged)
- Switch storage: LlamaIndex → Pinecone → Weaviate (Embedder unchanged)

This is the hallmark of proper separation of concerns.

## Migration Notes

### No Breaking Changes
- Old code archived in `archive/legacy_kb_ingestion/`
- New code is backward compatible
- Configuration still uses same fields (`embedding_model`, `index_type`)

### Configuration
No changes required to existing KB config files:
```json
{
  "embedding_model": "text-embedding-3-small",
  "generation_model": "gpt-4o-mini",
  "index_type": "vector"
}
```

New optional field for future flexibility:
```json
{
  "embedder_type": "openai",  // NEW: can be "openai", "azure", "local"
  "embedding_model": "text-embedding-3-small",
  "index_type": "vector"
}
```

## Summary

✅ **SRP Compliance**: Embedding and indexing are separate responsibilities  
✅ **4-Phase Architecture**: Matches LOADING → CHUNKING → EMBEDDING → INDEXING  
✅ **Flexibility**: Can swap embedders and storage independently  
✅ **Testability**: Each component can be tested in isolation  
✅ **Zero Breaking Changes**: Backward compatible with existing code  

The refactoring transforms a "God Class" (VectorIndexBuilder doing everything) into two focused classes with clear responsibilities.
