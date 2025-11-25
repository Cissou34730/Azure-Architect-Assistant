# Multi-Source RAG Architecture

## Overview

The Azure Architect Assistant now supports a **profile-based multi-source RAG** (Retrieval-Augmented Generation) system. This architecture enables querying multiple knowledge bases with context-appropriate retrieval strategies.

## Architecture Layers

### 1. Python Service Layer (FastAPI)
**Location:** `python-service/app/`

#### Core Modules

**`app/kb/` - Knowledge Base Infrastructure**
- `manager.py` - Configuration management and KB selection
  - `KBManager`: Loads `config.json`, filters KBs by profile
  - `KBConfig`: Wrapper for KB configuration with properties
  
- `service.py` - Generic KB query service
  - `KnowledgeBaseService`: KB-agnostic wrapper around LlamaIndex
  - Global `_INDEX_CACHE` for cross-KB index caching
  - Attribution: Results tagged with `kb_id` and `kb_name`
  
- `multi_query.py` - Multi-source orchestration
  - `QueryProfile` enum: `CHAT` vs `PROPOSAL`
  - `MultiSourceQueryService`: Profile-based multi-KB querying
  - Profile strategies:
    - **CHAT**: Top 6 results (3 per KB), fast responses
    - **PROPOSAL**: Top 15 results (5 per KB), comprehensive context

**`app/main.py` - FastAPI Endpoints**
- `POST /query/chat` - Fast, targeted queries (chat profile)
- `POST /query/proposal` - Comprehensive queries (proposal profile)
- `GET /kb/list` - List all available knowledge bases
- `GET /kb/health` - Health status of all KBs
- `GET /health` - Overall service health

**Legacy Support**
- `app/rag/` - WAF-specific implementation (being phased out)
- `POST /query` - Legacy endpoint (redirects to chat profile)

### 2. TypeScript Service Layer
**Location:** `backend/src/services/`

#### Modular Service Architecture (v2.0)

**`types.ts` - Shared Types**
```typescript
// Generic KB source (not WAF-specific)
interface KBSource {
  url: string;
  title: string;
  kb_id?: string;
  kb_name?: string;  // Works with any KB
}

interface LLMResponse {
  assistantMessage?: string;
  projectState: ProjectState;
  sources?: KBSource[];
}
```

**`OpenAIClient.ts` - OpenAI API Wrapper**
```typescript
// Generic OpenAI/Azure OpenAI client
openaiClient.complete(systemPrompt, userPrompt)
openaiClient.getModel()
```

**`ChatService.ts` - Interactive Chat Logic**
```typescript
// Handles chat clarification with KB enrichment
chatService.processChatMessage(message, state, history)
  ├── detectArchitectureKeywords() - Generic cloud/arch detection
  ├── queryKnowledgeBases() - Uses RAGService
  ├── formatKBContext() - Generic KB formatting
  └── parseChatResponse() - Extract message + state
```

**`ProposalService.ts` - Proposal Generation Logic**
```typescript
// Generates comprehensive architecture proposals
proposalService.generateProposal(state, onProgress)
  ├── buildRelevantQueries() - Dynamic query generation
  │   ├── Core topics (security, reliability, cost, etc.)
  │   ├── Scenario-specific (IoT, data, microservices)
  │   └── NFR-specific (zero trust, compliance)
  ├── Uses RAGService.queryForProposal()
  └── formatKBContext() - Generic KB formatting
```

**`KBService.ts` - Generic KB HTTP Client**
```typescript
// HTTP client for Python KB service
kbService.queryChat(question, topKPerKB?)
kbService.queryProposal(question, topKPerKB?)
kbService.queryProfile({ question, profile, topKPerKB })
kbService.listKnowledgeBases()
kbService.checkKBHealth()

// Legacy compatibility
kbService.query({ question, topK })  // → redirects to queryChat
```

**`RAGService.ts` - High-Level RAG Operations**
```typescript
// Context-aware querying
ragService.queryForChat(question)           // Chat context (fast)
ragService.queryForAnalysis(question)       // Analysis context (moderate)
ragService.queryForProposal(questions[])    // Proposal context (comprehensive)

// Advanced operations
ragService.queryMultipleTopics([{ topic, profile }])
ragService.getKBHealth()
ragService.listKnowledgeBases()
```

**`LLMService.ts` - Thin Orchestration Layer** ⭐ NEW
```typescript
// Delegates to specialized services
llmService.analyzeDocuments(texts)                    // Uses OpenAIClient
llmService.processChatMessage(msg, state, history)    // → ChatService
llmService.generateArchitectureProposal(state, onProgress) // → ProposalService
```

**`index.ts` - Unified Exports**
```typescript
export { 
  llmService, chatService, proposalService, 
  openaiClient, storage, kbService, ragService 
};
export { kbService as wafService }; // Backward compatibility
```

**Architecture Benefits:**
- ✅ No WAF-specific hardcoding
- ✅ Each service 150-280 lines (manageable)
- ✅ Single Responsibility Principle
- ✅ Generic KB support
- ✅ Dynamic query generation based on context
- ✅ Easy to test and extend

### 3. API Layer
**Location:** `backend/src/api/projects.ts`

**New Endpoints**
- `GET /kb/list` - List knowledge bases
- `GET /kb/health` - KB health status

**Updated Endpoints**
- All chat/analysis/proposal operations now use RAGService
- Automatic profile selection based on context:
  - Chat messages → `queryForChat` (fast, 3 results/KB)
  - Document analysis → `queryForAnalysis` (moderate, 5 results/KB)
  - Proposal generation → `queryForProposal` (comprehensive, 5+ results/KB)

## Query Profiles

### CHAT Profile
**Use Case:** Interactive chat, quick Q&A

**Configuration:**
- Results per KB: 3
- Total results: ~6 (top from all KBs)
- Strategy: Fast, targeted
- Merging: Simple concatenation

**Endpoints:**
- Python: `POST /query/chat`
- TypeScript: `kbService.queryChat()` or `ragService.queryForChat()`

### PROPOSAL Profile
**Use Case:** Comprehensive architecture proposals

**Configuration:**
- Results per KB: 5
- Total results: ~15 (top from all KBs)
- Strategy: Comprehensive, detailed
- Merging: Structured by topic

**Endpoints:**
- Python: `POST /query/proposal`
- TypeScript: `kbService.queryProposal()` or `ragService.queryForProposal()`

## Configuration

### Knowledge Base Configuration
**File:** `data/knowledge_bases/config.json`

```json
{
  "knowledge_bases": [
    {
      "id": "waf",
      "name": "Azure Well-Architected Framework",
      "profiles": ["chat", "proposal"],
      "priority": 1,
      "status": "active",
      "embedding_model": "text-embedding-3-small",
      "generation_model": "gpt-4o-mini",
      "paths": {
        "documents": "data/knowledge_bases/waf/documents",
        "index": "data/knowledge_bases/waf/index",
        "manifest": "data/knowledge_bases/waf/manifest.json"
      }
    }
  ]
}
```

**Key Fields:**
- `profiles`: Array of supported profiles (`["chat", "proposal"]`)
- `priority`: Sort order (lower = higher priority)
- `status`: `"active"` or `"inactive"`

## Data Flow

### Chat Message Flow
```
User Message
  ↓
projects.ts: POST /projects/:id/chat
  ↓
LLMService.processChatMessage()
  ├─→ Detects Azure-related keywords
  ├─→ ragService.queryForChat(question)
  │     ├─→ kbService.queryChat(question, 3)
  │     │     └─→ Python: POST /query/chat
  │     │           ├─→ KBManager.get_kbs_for_profile("chat")
  │     │           ├─→ Query each KB (parallel)
  │     │           └─→ Merge top 6 results
  │     └─→ Format context with sources
  ├─→ Build prompt with KB context
  ├─→ Call OpenAI GPT-4
  └─→ Return answer + updated state + sources
```

### Proposal Generation Flow
```
User: Generate Proposal
  ↓
projects.ts: GET /projects/:id/architecture/proposal
  ↓
LLMService.generateArchitectureProposal()
  ├─→ Build 5 pillar questions
  ├─→ ragService.queryForProposal([questions])
  │     ├─→ kbService.queryProposal(q, 5) for each
  │     │     └─→ Python: POST /query/proposal
  │     │           ├─→ KBManager.get_kbs_for_profile("proposal")
  │     │           ├─→ Query each KB (parallel)
  │     │           └─→ Merge top 15 results
  │     └─→ Deduplicate sources
  ├─→ Build comprehensive prompt
  ├─→ Call OpenAI GPT-4
  └─→ Stream proposal with SSE
```

## Adding New Knowledge Bases

### Step 1: Prepare Data
```bash
# Create directory structure
mkdir -p data/knowledge_bases/my-kb/{documents,index}
```

### Step 2: Add to Configuration
Edit `data/knowledge_bases/config.json`:
```json
{
  "id": "my-kb",
  "name": "My Knowledge Base",
  "profiles": ["chat", "proposal"],
  "priority": 2,
  "status": "active",
  "embedding_model": "text-embedding-3-small",
  "generation_model": "gpt-4o-mini",
  "paths": {
    "documents": "data/knowledge_bases/my-kb/documents",
    "index": "data/knowledge_bases/my-kb/index",
    "manifest": "data/knowledge_bases/my-kb/manifest.json"
  }
}
```

### Step 3: Ingest Data
```bash
# Phase 1: Crawl and clean
python scripts/ingest/kb_phase1.py --kb-id my-kb --source-url https://...

# Phase 2: Build vector index
python scripts/ingest/kb_phase2.py --kb-id my-kb
```

### Step 4: Verify
```bash
# Check health
curl http://localhost:8000/kb/health

# List KBs
curl http://localhost:8000/kb/list

# Test query
curl -X POST http://localhost:8000/query/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "test question", "profile": "chat"}'
```

## Migration from WAFService

### Before (Legacy)
```typescript
import { wafService } from "./services/WAFService.js";

const result = await wafService.query({ question, topK: 5 });
```

### After (New)
```typescript
import { ragService } from "./services/RAGService.js";

// For chat
const result = await ragService.queryForChat(question);

// For proposals
const results = await ragService.queryForProposal([q1, q2, q3]);
```

### Backward Compatibility
```typescript
// Still works via index.ts export alias
import { wafService } from "./services/index.js";
const result = await wafService.query({ question, topK });
// → Redirects to kbService.queryChat()
```

## Performance Considerations

### Index Caching
- **Global Cache**: All KBs share `_INDEX_CACHE` dictionary
- **Cache Key**: Storage directory path
- **Benefit**: ~2-5s saved on subsequent queries per KB

### Parallel Queries
- **Multi-KB**: Queries run in parallel via `Promise.all()`
- **Proposal**: All pillar queries execute simultaneously
- **Benefit**: Linear scaling (5 queries take ~same time as 1)

### Profile Optimization
- **Chat**: 3 results/KB → faster embedding search
- **Proposal**: 5 results/KB → more comprehensive but slower
- **Auto-select**: Services choose appropriate profile per context

## Testing

### Unit Tests
```bash
# Python tests
cd python-service
pytest tests/

# TypeScript tests
npm test
```

### Integration Tests
```bash
# Test KB service
npm run test:integration

# Test full flow
curl -X POST http://localhost:3000/projects/:id/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is Azure reliability?"}'
```

### Load Testing
```bash
# Test parallel queries
for i in {1..10}; do
  curl -X POST http://localhost:8000/query/chat \
    -H "Content-Type: application/json" \
    -d "{\"question\": \"test $i\", \"profile\": \"chat\"}" &
done
wait
```

## Monitoring

### Logs
```typescript
// TypeScript services
logger.info("KB query", { profile, sourceCount, kbs });

// Python services
logger.info(f"[{kb_id}] Retrieved {len(nodes)} nodes")
```

### Health Checks
```bash
# Overall health
curl http://localhost:8000/health

# KB-specific health
curl http://localhost:8000/kb/health

# Via Express
curl http://localhost:3000/kb/health
```

### Metrics to Monitor
- Query latency per profile
- Index cache hit rate
- KB availability
- Source attribution accuracy
- Token usage per query type

## Troubleshooting

### "No KB results found"
- Check KB status: `curl http://localhost:8000/kb/list`
- Verify profile in KB config: `profiles: ["chat", "proposal"]`
- Check index exists: `ls data/knowledge_bases/*/index/`

### "Context length exceeded"
- Reduce `topKPerKB` parameter
- Use `chat` profile instead of `proposal`
- Check chunk size in KB config

### "Python service not available"
- Verify service running: `curl http://localhost:8000/health`
- Check `PYTHON_SERVICE_URL` in `.env`
- Review Python logs: `python-service/logs/`

## Future Enhancements

### Planned Features
1. **Dynamic KB Selection**: AI chooses relevant KBs per query
2. **Hybrid Search**: Combine keyword + semantic search
3. **KB Analytics**: Track query patterns, popular sources
4. **Incremental Updates**: Add documents without full reindex
5. **Multi-tenancy**: Project-specific KB configurations

### Extensibility Points
- `KBManager.get_kbs_for_profile()` - Custom selection logic
- `MultiSourceQueryService._merge_results()` - Custom merging strategies
- `RAGService.queryMultipleTopics()` - Advanced orchestration
- KB ingestion pipelines - Support more source types

## References

- **LlamaIndex**: https://docs.llamaindex.ai/
- **FastAPI**: https://fastapi.tiangolo.com/
- **OpenAI Embeddings**: https://platform.openai.com/docs/guides/embeddings
- **Azure WAF**: https://learn.microsoft.com/azure/well-architected/
