# Quick Start Guide - Two Backend Architecture

## ✅ Refactoring Complete!

You now have **two separate backend services** communicating via HTTP (no more spawn!).

## 🚀 Quick Start (3 Steps)

### 1. Install Dependencies
```bash
npm run install:all
```

### 2. Configure Environment
```bash
# Copy and edit root .env (shared by both backend services)
cp .env.example .env
# Edit .env and set your OPENAI_API_KEY
```

**Note**: Both Express backend and Python service now share the same `.env` file at the project root. This eliminates duplication and keeps configuration in sync.

### 3. Run All Services
```bash
npm run dev
```

This starts:
- **Python RAG Service** on http://localhost:8000
- **Express Backend** on http://localhost:3000
- **React Frontend** on http://localhost:5173

## 🧪 Test the Setup

### 1. Test Python Service Directly
```bash
# Health check
curl http://localhost:8000/health

# Interactive docs
open http://localhost:8000/docs
```

### 2. Test Through Express Backend
```bash
curl -X POST http://localhost:3000/api/waf/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What are the five pillars of WAF?", "topK": 5}'
```

### 3. Test in Browser
1. Open http://localhost:5173
2. Click "WAF Query" tab
3. Ask a question

## 📋 What Changed

### Before ❌
```
Express → spawn(python) → stdin/stdout → messy error handling
```

### After ✅
```
Express → HTTP → FastAPI → clean REST API
```

## 🎯 Benefits

✅ No more process spawning overhead  
✅ Clean HTTP boundaries  
✅ Proper error handling (HTTP status codes)  
✅ Self-documenting API (Swagger at /docs)  
✅ Independent scaling  
✅ Industry-standard architecture  

## 📁 New Structure

```
project/
├── backend/              # Express API (TypeScript) :3000
├── python-service/       # FastAPI RAG (Python) :8000  ⭐ NEW
│   ├── app/
│   │   ├── main.py      # FastAPI endpoints
│   │   └── rag/         # RAG modules
│   └── requirements.txt
└── frontend/            # React (Vite) :5173
```

## 🛠️ Individual Service Commands

If you prefer separate terminals:

```bash
# Terminal 1: Python Service
cd python-service
uvicorn app.main:app --reload --port 8000

# Terminal 2: Express Backend  
cd backend
npm run dev

# Terminal 3: Frontend
cd frontend
npm run dev
```

## 📚 API Documentation

Once running:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🐛 Troubleshooting

**"Connection refused to localhost:8000"**
- Make sure Python service is running
- Check `PYTHON_SERVICE_URL` in backend/.env

**"Module not found"**
- Run `pip install -r python-service/requirements.txt`
- Activate virtual environment if using one

**"OpenAI API key not found"**
- Set `OPENAI_API_KEY` in both backend/.env and python-service/.env

## 📖 More Documentation

- `ARCHITECTURE.md` - Detailed architecture explanation
- `REFACTORING_COMPLETE.md` - Full refactoring details
- `python-service/README.md` - Python service documentation

---

**Ready to go!** 🎉
