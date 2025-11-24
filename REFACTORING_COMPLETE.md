# ✅ Refactoring Complete: Two Separate Backend Services

## What Changed

### Before (Problematic)
```
Express Backend (TypeScript)
    ↓ child_process.spawn()
Python Scripts (query_service.py, etc.)
    ↓ stdin/stdout JSON
OpenAI API
```
❌ Process overhead, error handling issues, debugging nightmare

### After (Clean)
```
Express Backend (TypeScript) : Port 3000
    ↓ HTTP fetch()
Python FastAPI Service : Port 8000
    ↓ Standard REST API
OpenAI API + LlamaIndex
```
✅ Clean HTTP boundaries, proper error handling, industry standard

## New Structure

```
Azure-Architect-Assistant/
├── backend/                    # Express API (TypeScript)
│   ├── src/
│   │   ├── api/
│   │   │   └── waf.ts         # WAF routes (proxies to Python)
│   │   └── services/
│   │       └── WAFService.ts  # NEW: HTTP client (no more spawn!)
│   └── package.json
│
├── python-service/             # NEW: FastAPI RAG Service
│   ├── app/
│   │   ├── main.py            # FastAPI app with endpoints
│   │   └── rag/               # RAG modules (copied from backend/src/rag)
│   │       ├── query.py
│   │       ├── crawler.py
│   │       ├── cleaner.py
│   │       └── indexer.py
│   ├── requirements.txt
│   ├── .env
│   └── README.md
│
├── frontend/                   # React (Vite)
└── package.json               # Updated with dev:python script
```

## How to Run

### Option 1: All Services Together
```bash
npm run dev
```
This starts:
- Python service on port 8000
- Express backend on port 3000
- React frontend on port 5173

### Option 2: Individual Terminals

**Terminal 1: Python Service**
```bash
cd python-service
uvicorn app.main:app --reload --port 8000
```

**Terminal 2: Express Backend**
```bash
cd backend
npm run dev
```

**Terminal 3: Frontend**
```bash
cd frontend
npm run dev
```

## Key Changes to Files

### 1. New Python Service (`python-service/app/main.py`)
- FastAPI application with proper endpoints
- Pydantic models for request/response validation
- Health check endpoint
- Query endpoint
- Ingestion endpoints (Phase 1 & 2)
- Automatic Swagger docs at `/docs`

### 2. Updated WAFService (`backend/src/services/WAFService.ts`)
**Before (718 lines with spawn logic)**:
```typescript
const pythonProcess = spawn(this.pythonPath, ["query_service.py"]);
pythonProcess.stdin.write(JSON.stringify(query));
pythonProcess.stdout.on("data", (data) => { ... });
// Complex error handling, process management, etc.
```

**After (230 lines with clean HTTP)**:
```typescript
async query(request: WAFQueryRequest): Promise<WAFQueryResponse> {
  const response = await fetch(`${this.pythonServiceUrl}/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request)
  });
  return await response.json();
}
```

### 3. Updated Configuration
- `backend/.env`: Added `PYTHON_SERVICE_URL=http://localhost:8000`
- `python-service/.env`: Python service configuration
- `package.json`: Added `dev:python` and updated `install:all`

## API Endpoints

### Python Service (http://localhost:8000)

```bash
# Health Check
GET /health

# Query WAF
POST /query
{
  "question": "What are the five pillars?",
  "topK": 5
}

# Ingestion Phase 1
POST /ingest/phase1

# Ingestion Phase 2
POST /ingest/phase2

# Interactive API Docs
GET /docs
```

### Express Backend (http://localhost:3000)

```bash
# WAF Query (proxies to Python service)
POST /api/waf/query
{
  "question": "What are the five pillars?",
  "topK": 5
}

# Other project endpoints remain unchanged
```

## Benefits

✅ **Clean Architecture**: HTTP-based microservices  
✅ **Better Error Handling**: Standard HTTP status codes  
✅ **Easier Debugging**: No process boundary issues  
✅ **Type Safety**: Pydantic models in Python, TypeScript interfaces  
✅ **Self-Documenting**: FastAPI auto-generates Swagger docs  
✅ **Independent Scaling**: Can scale Python service separately  
✅ **Standard Testing**: Mock HTTP calls, not process spawning  
✅ **Production Ready**: Docker-compatible, cloud-native  

## Testing the New Setup

1. **Start Python service**:
   ```bash
   cd python-service
   uvicorn app.main:app --reload --port 8000
   ```

2. **Test directly**:
   ```bash
   curl http://localhost:8000/health
   ```

3. **Start Express backend**:
   ```bash
   cd backend
   npm run dev
   ```

4. **Test through Express**:
   ```bash
   curl -X POST http://localhost:3000/api/waf/query \
     -H "Content-Type: application/json" \
     -d '{"question": "What are the five pillars?"}'
   ```

5. **Start frontend and test in browser**

## Next Steps

- [ ] Test all endpoints work correctly
- [ ] Run ingestion to populate index
- [ ] Update deployment documentation
- [ ] Add Docker Compose configuration
- [ ] Consider adding API authentication between services
- [ ] Add monitoring/health checks

## Files to Delete (Old Spawn-Based Code)

```bash
# Backend - old Python wrappers no longer needed
backend/src/rag/query_service.py
backend/src/rag/query_wrapper.py
backend/src/rag/query_stream_wrapper.py
backend/src/services/WAFService.old.ts
```

These are now replaced by FastAPI endpoints in `python-service/`.

---

**Status**: ✅ **Refactoring Complete - Ready to Test**
