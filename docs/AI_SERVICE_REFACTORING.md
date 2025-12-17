# AI Service Layer Refactoring

## Overview

This refactoring centralizes all AI operations (LLM and Embeddings) behind a unified interface, making the codebase provider-agnostic and easier to maintain.

## Architecture

```
┌─────────────────────────────────────────┐
│   Application Layer (Routes/Services)  │
└─────────────────┬───────────────────────┘
                  │
         ┌────────▼────────┐
         │   AIService     │  ← Single entry point
         │   Singleton     │
         └────────┬────────┘
                  │
    ┌─────────────┴─────────────┐
    │                           │
┌───▼──────────┐       ┌───────▼────────┐
│ LLMProvider  │       │ EmbeddingProvider│
│ Interface    │       │ Interface        │
└───┬──────────┘       └───────┬──────────┘
    │                          │
    ├── OpenAILLMProvider      ├── OpenAIEmbeddingProvider
    ├── AzureOpenAIProvider    ├── AzureEmbedding
    └── AnthropicProvider      └── LocalEmbedder (future)
```

## Components

### 1. **AIConfig** (`config.py`)
Centralized configuration for all AI providers.

**Environment Variables:**
```bash
# Provider selection
AI_LLM_PROVIDER=openai  # openai|azure|anthropic
AI_EMBEDDING_PROVIDER=openai

# OpenAI
OPENAI_API_KEY=sk-...
AI_OPENAI_LLM_MODEL=gpt-4o-mini
AI_OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# Azure (optional)
AI_AZURE_OPENAI_ENDPOINT=https://...
AI_AZURE_OPENAI_API_KEY=...
AI_AZURE_LLM_DEPLOYMENT=gpt-4
```

### 2. **Interfaces** (`interfaces.py`)
- `LLMProvider` - Abstract base for LLM providers
- `EmbeddingProvider` - Abstract base for embedding providers
- Standardized request/response formats

### 3. **Providers** (`providers/`)
- `OpenAILLMProvider` - OpenAI chat completions
- `OpenAIEmbeddingProvider` - OpenAI embeddings
- Future: Azure, Anthropic, Local models

### 4. **AIService** (`ai_service.py`)
Unified service with convenience methods.

## Usage Examples

### Basic Setup

```python
from app.services.ai import get_ai_service, ChatMessage

# Get singleton instance
ai_service = get_ai_service()
```

### Chat Completion

```python
# Simple completion
response = await ai_service.complete("Explain Azure Well-Architected Framework")
print(response)

# Chat with history
messages = [
    ChatMessage(role="system", content="You are a helpful Azure architect."),
    ChatMessage(role="user", content="How do I design for high availability?")
]
response = await ai_service.chat(messages, temperature=0.7)
print(response.content)
print(f"Used {response.usage['total_tokens']} tokens")

# Streaming chat
messages = [ChatMessage(role="user", content="Tell me about Azure")]
async for chunk in await ai_service.chat(messages, stream=True):
    print(chunk, end='', flush=True)
```

### Embeddings

```python
# Single text
embedding = await ai_service.embed_text("Azure Well-Architected Framework")
print(f"Dimension: {len(embedding)}")

# Batch processing
texts = ["text1", "text2", "text3"]
embeddings = await ai_service.embed_batch(texts, batch_size=100)
print(f"Generated {len(embeddings)} embeddings")
```

### Model Information

```python
print(f"LLM Model: {ai_service.get_llm_model()}")
print(f"Embedding Model: {ai_service.get_embedding_model()}")
print(f"Embedding Dimension: {ai_service.get_embedding_dimension()}")
```

## Migration Guide

### Before (Old Code)

```python
# llm_service.py - Multiple OpenAI clients
from openai import AsyncOpenAI
import os

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
response = await client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": prompt}],
    temperature=0.7
)
content = response.choices[0].message.content

# kb/service.py - Global Settings mutation
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding
Settings.llm = OpenAI(model="gpt-4o-mini")
Settings.embed_model = OpenAIEmbedding(model="text-embedding-3-small")
```

### After (New Code)

```python
# Anywhere in the application
from app.services.ai import get_ai_service, ChatMessage

ai_service = get_ai_service()

# Chat
messages = [ChatMessage(role="user", content=prompt)]
response = await ai_service.chat(messages, temperature=0.7)
content = response.content

# Embeddings
embeddings = await ai_service.embed_batch(texts)
```

## Benefits

✅ **Single Source of Truth** - One place for API keys and config  
✅ **Provider Agnostic** - Switch providers via env var  
✅ **Testable** - Mock AIService instead of OpenAI directly  
✅ **No Global State** - Dependency injection friendly  
✅ **Type Safe** - Full typing support  
✅ **Cost Tracking** - Centralized usage logging  
✅ **Rate Limiting** - Unified retry/backoff logic  

## Testing

```python
from app.services.ai import AIService, AIConfig
from app.services.ai.interfaces import ChatMessage

# Custom config for testing
config = AIConfig(
    llm_provider="openai",
    openai_api_key="test-key",
    openai_llm_model="gpt-4o-mini"
)
ai_service = AIService(config)

# Mock for unit tests
from unittest.mock import AsyncMock
ai_service._llm_provider.chat = AsyncMock(return_value=LLMResponse(...))
```

## Migration Phases

### Phase 1: ✅ Foundation (Completed)
- [x] Create interfaces and config
- [x] Implement OpenAI providers (LLM and Embedding)
- [x] Create AIService singleton with factory pattern
- [x] Write initial documentation
- **Files Created:**
  - `app/services/ai/interfaces.py`
  - `app/services/ai/config.py`
  - `app/services/ai/ai_service.py`
  - `app/services/ai/providers/openai_llm.py`
  - `app/services/ai/providers/openai_embedding.py`

### Phase 2: ✅ LLM Service Migration (Completed)
- [x] Updated `llm_service.py` to use AIService
- [x] Removed `get_openai_client()` function
- [x] Migrated chat methods to use `ai_service.chat()`
- [x] Updated exports in `services/__init__.py`
- [x] Tested integration
- **Files Modified:**
  - `app/services/llm_service.py`
  - `app/services/__init__.py`
  - `app/services/ai/__init__.py`

### Phase 3: ✅ Ingestion Embedding Migration (Completed)
- [x] Updated OpenAIEmbedder to use AIService
- [x] Uses `ai_service.embed_batch()` for efficient processing
- [x] Added asyncio handling for sync method calling async service
- [x] Removed direct LlamaIndex OpenAIEmbedding import
- [x] Maintained interface compatibility with ingestion pipeline
- **Files Modified:**
  - `app/ingestion/infrastructure/embedding/openai_embedder.py`

### Phase 4: ✅ KB Service & LlamaIndex Adapter (Completed)
- [x] Created LlamaIndex-compatible adapters
  - `AIServiceLLM` - Implements CustomLLM interface
  - `AIServiceEmbedding` - Implements BaseEmbedding interface
- [x] Updated kb/service.py to use adapters
- [x] Updated vector index builder to use adapters
- [x] Zero breaking changes to LlamaIndex functionality
- [x] All existing indices remain compatible
- **Files Created:**
  - `app/services/ai/adapters/__init__.py`
  - `app/services/ai/adapters/llamaindex.py`
- **Files Modified:**
  - `app/kb/service.py`
  - `app/ingestion/infrastructure/indexing/vector.py`

### Phase 5: ✅ Cleanup (Completed)
- [x] Updated YouTube source handler to use AIService adapter
- [x] Verified no remaining direct OpenAI imports (except in providers)
- [x] Updated documentation with all phases
- [x] Import validation tests passed
- **Files Modified:**
  - `app/ingestion/domain/sources/youtube.py`
  - `docs/AI_SERVICE_REFACTORING.md`

## Refactoring Summary

**All phases complete!** The codebase now uses the unified AIService throughout:

✅ **LLM Service** - Chat and document analysis  
✅ **Ingestion** - Embedding generation  
✅ **KB Queries** - LlamaIndex integration via adapters  
✅ **Vector Indexing** - LlamaIndex integration via adapters  
✅ **YouTube Ingestion** - Transcript distillation  

**Eliminated Redundancy:**
- ❌ 4+ places reading `OPENAI_API_KEY`
- ❌ Multiple AsyncOpenAI client instances
- ❌ Global Settings mutations in LlamaIndex
- ❌ Direct OpenAI imports scattered across codebase

**New Architecture:**
- ✅ Single AIService singleton
- ✅ Centralized configuration
- ✅ Provider abstraction (easy to add Azure/Anthropic)
- ✅ LlamaIndex compatibility via adapters
- ✅ Type-safe interfaces

## Future Enhancements

- [ ] Azure OpenAI provider
- [ ] Anthropic Claude provider
- [ ] Local model support (Ollama)
- [ ] Response caching
- [ ] Token usage tracking/reporting
- [ ] Rate limiting per user/project
- [ ] Cost estimation
