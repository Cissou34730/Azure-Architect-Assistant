# Architecture: Two Separate Backend Services

This project now uses **two independent backend services**:

## 1. Express Backend (TypeScript) - Port 3000
**Location**: `backend/`

**Responsibilities**:
- Project management API
- Document upload and storage
- Chat conversation management
- Architecture proposal generation (LLMService)
- API gateway / orchestration layer

**Stack**: Express.js, TypeScript, SQLite

**Run**:
```bash
cd backend
npm run dev
```

## 2. Python RAG Service (FastAPI) - Port 8000
**Location**: `python-service/`

**Responsibilities**:
- WAF documentation queries (RAG)
- Vector search and embeddings
- Document crawling and ingestion
- LlamaIndex operations

**Stack**: FastAPI, Python, LlamaIndex, OpenAI

**Run**:
```bash
cd python-service
uvicorn app.main:app --reload --port 8000
```

## Communication Flow

```
Frontend (Port 5173)
    ↓ HTTP
Express Backend (Port 3000)
    ↓ HTTP (internal)
Python RAG Service (Port 8000)
    ↓
OpenAI API
```

## Quick Start

### 1. Install Dependencies
```bash
npm run install:all
```

### 2. Configure Environment

**backend/.env**:
```env
OPENAI_API_KEY=your-key-here
PORT=3000
PYTHON_SERVICE_URL=http://localhost:8000
```

**python-service/.env**:
```env
OPENAI_API_KEY=your-key-here
PORT=8000
```

### 3. Run All Services
```bash
# Terminal 1: Python service
cd python-service
uvicorn app.main:app --reload --port 8000

# Terminal 2: Express backend
cd backend
npm run dev

# Terminal 3: Frontend
cd frontend
npm run dev
```

**Or use concurrently (all in one terminal)**:
```bash
npm run dev
```

## API Endpoints

### Express Backend (3000)
- `POST /api/projects` - Create project
- `GET /api/projects` - List projects
- `POST /api/projects/:id/chat` - Chat with AI
- `POST /api/waf/query` - Query WAF (proxies to Python service)

### Python Service (8000)
- `GET /health` - Health check
- `POST /query` - Query WAF documentation
- `POST /ingest/phase1` - Start crawling
- `POST /ingest/phase2` - Build index
- `GET /docs` - Swagger API documentation

## Benefits of This Architecture

✅ **Clean Separation**: TypeScript for web, Python for ML/AI  
✅ **Independent Scaling**: Scale services separately  
✅ **Better Debugging**: Clear boundaries, proper error handling  
✅ **Type Safety**: HTTP contracts instead of spawn()  
✅ **Standard Pattern**: Industry-standard microservices  
✅ **Easier Testing**: Mock HTTP calls instead of processes  
✅ **Deployment Ready**: Docker-compatible architecture  

## Deployment

### Docker Compose (Recommended)
```yaml
version: '3.8'
services:
  frontend:
    build: ./frontend
    ports: ["80:80"]
  
  backend:
    build: ./backend
    ports: ["3000:3000"]
    environment:
      PYTHON_SERVICE_URL: http://python-service:8000
  
  python-service:
    build: ./python-service
    ports: ["8000:8000"]
```

### Manual Deployment
1. Deploy Python service to cloud (e.g., Azure Container Instances)
2. Set `PYTHON_SERVICE_URL` in Express backend env
3. Deploy Express backend
4. Deploy frontend with backend URL configured
