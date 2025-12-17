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
- [x] Implement OpenAI providers
- [x] Create AIService singleton
- [x] Write documentation

### Phase 2: Migrate LLM Service
- [ ] Update `llm_service.py` to use AIService
- [ ] Update chat_service.py
- [ ] Update document_service.py
- [ ] Test chat functionality

### Phase 3: Migrate Ingestion
- [ ] Create adapter for ingestion pipeline
- [ ] Update OpenAIEmbedder to use AIService
- [ ] Test ingestion end-to-end

### Phase 4: Migrate KB Service
- [ ] Create LlamaIndex adapter
- [ ] Update kb/service.py to use AIService
- [ ] Remove global Settings mutations
- [ ] Test KB queries

### Phase 5: Cleanup
- [ ] Remove old OpenAI client code
- [ ] Update tests
- [ ] Update documentation

## Future Enhancements

- [ ] Azure OpenAI provider
- [ ] Anthropic Claude provider
- [ ] Local model support (Ollama)
- [ ] Response caching
- [ ] Token usage tracking/reporting
- [ ] Rate limiting per user/project
- [ ] Cost estimation
