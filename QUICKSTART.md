# Quick Start Guide - Unified Python Backend (v4.0)

## ✅ Modern Architecture with uv!

You now have a **unified Python FastAPI backend** with uv for blazing-fast dependency management.

## 🚀 Quick Start (3 Steps)

### 1. Install uv (if not already installed)
```powershell
# Windows
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# Linux/macOS
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Restart your terminal after installation.

### 2. Install Dependencies
```bash
# Install all dependencies (Python + Node.js)
npm run installAll

# OR install Python dependencies only
uv sync
```

This will:
- Create a `.venv` virtual environment automatically
- Install all Python dependencies from `pyproject.toml`
- Generate a `uv.lock` file for reproducible builds
- Install frontend dependencies

**⚡ uv is 10-100x faster than pip!**

### 3. Configure Environment
```bash
# Copy and edit root .env
cp .env.example .env
# Edit .env and set your OPENAI_API_KEY
```

### 4. Run the Application
```bash
# Start both backend and frontend
npm run backend    # Terminal 1 (uses uv run automatically)
npm run frontend   # Terminal 2
```

This starts:
- **Python FastAPI Backend** on http://localhost:8000 (managed by uv)
- **React Frontend** on http://localhost:5173

## 🧪 Test the Setup

### 1. Test Python Service
```bash
# Health check
curl http://localhost:8000/health

# Interactive docs (Swagger UI)
open http://localhost:8000/docs
```

### 2. Test in Browser
1. Open http://localhost:5173
2. Create a project or query knowledge bases
3. Everything works through the unified Python backend!

## 📋 What's New in v4.0

### Before (v3.x) ❌
```
Express (TypeScript) → HTTP → Python Service → LlamaIndex
```

### After (v4.0) ✅
```
React → FastAPI (Python) → LlamaIndex
```

## 🎯 Benefits

✅ **Simpler architecture** - One backend instead of two  
✅ **Faster development** - Direct Python-to-LlamaIndex integration  
✅ **10-100x faster installs** - uv vs pip  
✅ **Better type safety** - SQLAlchemy models + TypeScript  
✅ **Modern Python** - pyproject.toml, lockfiles, dependency groups  
✅ **Zero activation needed** - `uv run` handles venv automatically  

## 📁 New Structure

```
project/
├── pyproject.toml        # Python dependencies & project config ⭐ NEW
├── uv.lock              # Lockfile for reproducible builds ⭐ NEW
├── .python-version      # Python version (3.10) ⭐ NEW
├── backend/             # Python FastAPI :8000
│   ├── app/
│   │   ├── main.py     # FastAPI app
│   │   └── routers/    # API endpoints
│   └── tests/
└── frontend/           # React (Vite) :5173
```

## 🛠️ Development Commands

### Running Services

```bash
# Python backend (with uv - no venv activation needed!)
uv run uvicorn app.main:app --reload --port 8000

# OR use npm scripts
npm run backend   # Uses uv run internally
npm run frontend
```

### Managing Dependencies

```bash
# Add a new Python package
uv add package-name

# Add a dev dependency
uv add --dev pytest

# Remove a package
uv remove package-name

# Update all dependencies
uv sync --upgrade

# Run Python scripts
uv run python script.py

# Run tests
uv run pytest
```

## 📚 API Documentation

Once running:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🐛 Troubleshooting

**"uv: command not found"**
- Install uv: `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`
- Restart your terminal
- Add to PATH: `~/.local/bin` (Linux/macOS) or `%USERPROFILE%\.local\bin` (Windows)

**"Connection refused to localhost:8000"**
- Make sure Python backend is running: `npm run backend`
- Check that port 8000 is not in use: `netstat -ano | findstr :8000`

**"Module not found" or dependency issues**
- Reinstall dependencies: `uv sync`
- Remove lockfile and resync: `rm uv.lock && uv sync`

**"OpenAI API key not found"**
- Create `.env` file in project root
- Set `OPENAI_API_KEY=your-key-here`

## 📖 More Documentation

- `README.md` - Complete project documentation
- `docs/REFACTORING_SUMMARY.md` - Architecture evolution
- `backend/README.md` - Backend service details

---

**Ready to go with uv!** 🚀⚡

