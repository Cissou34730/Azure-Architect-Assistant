# WAF Query System - Quick Start Guide

## What is it?

A RAG (Retrieval-Augmented Generation) system that lets you query Azure Well-Architected Framework documentation using natural language questions. Get accurate, source-grounded answers backed by official Microsoft documentation.

## Quick Start (5 steps)

### 1. Install Dependencies

```bash
# Node.js dependencies
npm run install:all

# Python dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

Create `backend/.env`:
```bash
OPENAI_API_KEY=your-key-here
PORT=3000
```

### 3. Run Ingestion (One-Time, ~20 minutes)

```bash
python run_waf_ingestion.py
```

### 4. Start the Application

Terminal 1:
```bash
cd backend
npm run dev
```

Terminal 2:
```bash
cd frontend
npm run dev
```

### 5. Use the System

1. Open http://localhost:5173
2. Click "WAF Query" tab
3. Ask questions like:
   - "What are the security best practices for Azure Storage?"
   - "How do I design a highly available architecture?"
   - "What are the cost optimization recommendations?"

## API Usage

### Query Endpoint

```bash
POST http://localhost:3000/api/waf/query
Content-Type: application/json

{
  "question": "What are the five pillars of the Well-Architected Framework?",
  "topK": 5
}
```

### Response

```json
{
  "answer": "The Azure Well-Architected Framework is built on five pillars...",
  "sources": [
    {
      "url": "https://learn.microsoft.com/azure/well-architected/pillars",
      "title": "Azure Well-Architected Framework pillars",
      "section": "pillar",
      "score": 0.92
    }
  ],
  "hasResults": true,
  "suggestedFollowUps": ["Tell me more about the reliability pillar"]
}
```

## Common Tasks

### Re-run Ingestion

```bash
cd backend/src/python
rm -rf waf_storage_clean waf_*.txt waf_*.jsonl chunks_*.* 
cd ../../..
python run_waf_ingestion.py
```

### Test Query from CLI

```bash
cd backend/src/python
python query_service.py "What is the cost optimization pillar?"
```

### Check Index Status

```bash
curl http://localhost:3000/api/waf/ready
```

## Architecture Overview

```
User Question
    ↓
Frontend (React)
    ↓
Backend (TypeScript) → WAFService
    ↓
Python Query Service
    ↓
Vector Index (LlamaIndex) ← Embeddings (OpenAI)
    ↓
Retrieved Chunks
    ↓
LLM (GPT-4) → Answer + Sources
```

## Customization

### Adjust Retrieval Parameters

Edit `backend/src/services/WAFService.ts`:
```typescript
const result = await wafService.query({
  question,
  topK: 10,  // Retrieve more chunks
  metadataFilters: {
    section: 'pillar'  // Filter by section
  }
});
```

### Change Similarity Threshold

Edit `backend/src/python/query_service.py`:
```python
service = WAFQueryService(
    similarity_threshold=0.8  # Higher = stricter matching
)
```

### Use Different Models

Edit `backend/src/python/indexer.py` and `query_service.py`:
```python
WAFIndexer(
    embedding_model="text-embedding-3-large",  # Better quality
    llm_model="gpt-4o"  # More capable model
)
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Index not found" | Run `python run_waf_ingestion.py` |
| "OPENAI_API_KEY not found" | Set in `backend/.env` |
| Slow queries | Normal for first query (loading index) |
| Port conflicts | Change PORT in `backend/.env` |
| Python not found | Set PYTHON_PATH in `backend/.env` |

## File Locations

| Purpose | Path |
|---------|------|
| Vector Index | `backend/src/python/waf_storage_clean/` |
| Crawled URLs | `backend/src/python/waf_urls.txt` |
| Processed Docs | `backend/src/python/waf_documents.jsonl` |
| Chunks for Review | `backend/src/python/chunks_review.csv` |
| Python Logs | Terminal output |

## Performance Tips

1. **First Query**: Takes 5-10 seconds (loading index)
2. **Subsequent Queries**: 1-3 seconds
3. **Ingestion Time**: 15-30 minutes (depends on network and API rate limits)
4. **Disk Space**: ~200MB for index storage
5. **API Costs**: ~$2-5 for full ingestion (embeddings), ~$0.01 per query

## Next Steps

1. ✅ Basic setup working
2. Try different question types
3. Explore metadata filtering
4. Review and validate chunks manually
5. Integrate with your architecture projects
6. Extend to other documentation sources

## Support

- GitHub Issues: Report bugs and feature requests
- README.md: Comprehensive documentation
- Code Comments: Detailed inline documentation
