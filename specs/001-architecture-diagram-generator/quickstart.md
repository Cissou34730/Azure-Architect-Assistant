# Quickstart: Architecture Diagram Generator

**Target Audience**: Developers setting up the Architecture Diagram Generator service for the first time.

**Time to Complete**: ~15 minutes

---

## Prerequisites

Ensure you have the following installed:

- **Python 3.10+** (verify: `python --version`)
- **Java Runtime Environment (JRE) 11+** (for PlantUML rendering, verify: `java --version`)
- **Git** (for cloning repository)
- **SQLite 3+** (bundled with Python, no separate install needed)
- **OpenAI API Key** (obtain from [OpenAI Platform](https://platform.openai.com/api-keys))

Optional:
- **Docker** (for containerized deployment)
- **VS Code** with Python extension (recommended IDE)

---

## Step 1: Clone Repository

```bash
git clone <repository-url>
cd Azure-Architect-Assistant-speckit
git checkout 001-architecture-diagram-generator
```

---

## Step 2: Set Up Python Environment

### Create Virtual Environment
```bash
python -m venv .venv
```

### Activate Virtual Environment
**Windows (PowerShell)**:
```powershell
.\.venv\Scripts\Activate.ps1
```

**Linux/macOS**:
```bash
source .venv/bin/activate
```

### Install Dependencies
```bash
pip install --upgrade pip
pip install -r backend/requirements.txt
```

**Key Dependencies** (auto-installed):
- `fastapi>=0.115.0` - Async web framework
- `uvicorn>=0.32.0` - ASGI server
- `openai>=1.0.0` - OpenAI API client
- `sqlalchemy>=2.0.0` - ORM with async support
- `aiosqlite>=0.20.0` - Async SQLite driver
- `plantuml>=0.3.0` - PlantUML Python wrapper
- `pyproject-mermaid>=0.1.0` - Mermaid validation
- `alembic>=1.13.0` - Database migrations
- `pydantic>=2.0.0` - Request/response validation

---

## Step 3: Download PlantUML JAR

PlantUML requires a local JAR file for rendering diagrams with Azure icons.

```bash
# Create lib directory
mkdir -p backend/lib

# Download latest PlantUML JAR
curl -L https://github.com/plantuml/plantuml/releases/download/v1.2024.7/plantuml-1.2024.7.jar -o backend/lib/plantuml.jar

# Verify Java can execute it
java -jar backend/lib/plantuml.jar -version
```

**Expected Output**: `PlantUML version 1.2024.7`

---

## Step 4: Configure Environment Variables

Create `.env` file in project root:

```bash
# .env
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxx
OPENAI_MODEL=gpt-4-turbo-2024-04-09
PLANTUML_JAR_PATH=./backend/lib/plantuml.jar
PROJECTS_DATABASE=./backend/data/projects.db
DIAGRAMS_DATABASE=./backend/data/diagrams.db
LOG_LEVEL=INFO
LOCK_TIMEOUT_MINUTES=10
MAX_GENERATION_RETRIES=3
```

**Security Note**: Never commit `.env` to Git. Add to `.gitignore`:
```bash
echo ".env" >> .gitignore
```

---

## Step 5: Initialize Database

Run Alembic migrations to create schema:

```bash
cd backend
alembic upgrade head
```

**Expected Output**:
```
INFO  [alembic.runtime.migration] Running upgrade -> 001_create_diagram_sets
INFO  [alembic.runtime.migration] Running upgrade 001 -> 002_create_diagrams
INFO  [alembic.runtime.migration] Running upgrade 002 -> 003_create_ambiguity_reports
INFO  [alembic.runtime.migration] Running upgrade 003 -> 004_create_locks
```

**Verify Database Created**:
```bash
ls backend/data/diagrams.db
```

---

## Step 6: Start Development Server

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Expected Output**:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [12345]
INFO:     Started server process [12346]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

---

## Step 7: Verify API is Running

Open browser or use `curl`:

```bash
curl http://localhost:8000/health
```

**Expected Response**:
```json
{
  "status": "healthy",
  "database": "connected",
  "plantuml": "available",
  "openai": "configured"
}
```

---

## Step 8: Test Diagram Generation

### Create Test Diagram Set

```bash
curl -X POST http://localhost:8000/api/v1/diagram-sets \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-key-12345" \
  -d '{
    "input_description": "User uploads document to Azure Blob Storage. Azure Function processes document and stores metadata in Cosmos DB. User queries documents via API Gateway.",
    "adr_id": "ADR-2024-TEST-001"
  }'
```

**Expected Response** (within 30 seconds):
```json
{
  "id": 1,
  "adr_id": "ADR-2024-TEST-001",
  "input_description": "User uploads document...",
  "created_at": "2025-12-17T10:00:00Z",
  "updated_at": "2025-12-17T10:00:00Z",
  "diagrams": [
    {
      "id": 1,
      "diagram_type": "mermaid_functional",
      "source_code": "flowchart TD\n    A[User] --> B[Azure Blob Storage]...",
      "version": "1.0.0"
    },
    {
      "id": 2,
      "diagram_type": "c4_context",
      "source_code": "C4Context\n    title System Context...",
      "version": "1.0.0"
    }
  ],
  "ambiguities": [
    {
      "id": 1,
      "ambiguous_text": "processes document",
      "suggested_clarification": "Specify: OCR, NLP, or text extraction?",
      "resolved": false
    }
  ]
}
```

### Retrieve Diagram

```bash
curl http://localhost:8000/api/v1/diagram-sets/1
```

### Export PlantUML as SVG

```bash
curl http://localhost:8000/api/v1/diagram-sets/1/diagrams/4/export?format=svg \
  -o test-diagram.svg
```

---

## Step 9: Explore API Documentation

FastAPI auto-generates interactive API docs:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

Use these to test endpoints interactively with auto-validation.

---

## Step 10: Run Tests (Optional)

```bash
cd backend
pytest tests/ -v
```

**Expected Output**:
```
tests/test_diagram_generation.py::test_create_diagram_set PASSED
tests/test_ambiguity_detection.py::test_detect_ambiguities PASSED
tests/test_locking.py::test_acquire_release_lock PASSED
================================ 15 passed in 12.34s ================================
```

---

## Project Structure Overview

```
backend/
├── app/
│   ├── main.py                    # FastAPI application entry point
│   ├── routers/
│   │   ├── diagram_sets.py        # Diagram CRUD endpoints
│   │   ├── ambiguities.py         # Ambiguity resolution endpoints
│   │   └── locks.py               # Locking endpoints
│   ├── services/
│   │   ├── diagram_generator.py   # LLM-powered generation logic
│   │   ├── ambiguity_detector.py  # Ambiguity detection service
│   │   ├── plantuml_renderer.py   # PlantUML rendering service
│   │   └── mermaid_validator.py   # Mermaid validation service
│   ├── models/
│   │   ├── diagram_set.py         # SQLAlchemy ORM models
│   │   ├── diagram.py
│   │   ├── ambiguity_report.py
│   │   └── lock.py
│   ├── schemas/
│   │   └── requests.py            # Pydantic request/response schemas
│   └── config.py                  # Configuration management
├── data/
│   └── diagrams.db                # SQLite database file
├── lib/
│   └── plantuml.jar               # PlantUML JAR (not in Git)
├── migrations/
│   └── versions/                  # Alembic migration scripts
├── tests/
│   ├── test_diagram_generation.py
│   ├── test_ambiguity_detection.py
│   └── test_locking.py
└── requirements.txt               # Python dependencies
```

---

## Common Issues & Troubleshooting

### Issue 1: `ModuleNotFoundError: No module named 'openai'`
**Solution**: Ensure virtual environment is activated and dependencies installed:
```bash
.\.venv\Scripts\Activate.ps1  # Windows
pip install -r backend/requirements.txt
```

### Issue 2: `java.lang.NoClassDefFoundError` when rendering PlantUML
**Solution**: Verify PlantUML JAR path in `.env` and Java installation:
```bash
java -jar backend/lib/plantuml.jar -version
```

### Issue 3: `RateLimitError` from OpenAI API
**Solution**: OpenAI rate limits apply. Wait 60 seconds or upgrade API plan. Check usage: https://platform.openai.com/usage

### Issue 4: Database locked error (SQLite)
**Solution**: SQLite allows single writer. Ensure no other process has database open:
```bash
# Kill any stale Python processes
taskkill /F /IM python.exe  # Windows
pkill -9 python             # Linux/macOS
```

### Issue 5: Port 8000 already in use
**Solution**: Change port or kill existing process:
```bash
# Use different port
uvicorn app.main:app --port 8001

# Or kill process on port 8000 (Windows)
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

---

## Next Steps

1. **Integrate with Main Project**: Update main Azure Architect Assistant to call this API service
2. **Add Frontend UI**: Build React component for diagram display (Mermaid client-side rendering)
3. **Deploy to Azure**: Containerize with Docker and deploy to Azure Container Apps
4. **Monitor Performance**: Add Application Insights for telemetry (SC-001 compliance)
5. **Implement Versioning UI**: Enable users to browse diagram version history (FR-020)

---

## Development Workflow

### Making Changes
1. Create feature branch: `git checkout -b feature/your-feature`
2. Make code changes following constitution principles (SRP, Zero Duplication, Explicit Naming)
3. Add tests: `pytest tests/test_your_feature.py`
4. Run linter: `ruff check backend/`
5. Run type checker: `mypy backend/`
6. Commit: `git commit -m "Add: Your feature description"`

### Database Migrations
```bash
# Create new migration after model changes
alembic revision --autogenerate -m "Add new field"

# Apply migration
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

### Running in Production Mode
```bash
# Install production dependencies
pip install -r backend/requirements-prod.txt

# Run with Gunicorn (production WSGI server)
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

---

## Docker Deployment (Optional)

### Build Image
```dockerfile
# backend/Dockerfile
FROM python:3.10-slim

# Install Java for PlantUML
RUN apt-get update && apt-get install -y openjdk-11-jre-headless && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Download PlantUML JAR
RUN mkdir -p lib && \
    wget https://github.com/plantuml/plantuml/releases/download/v1.2024.7/plantuml-1.2024.7.jar -O lib/plantuml.jar

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Build and Run
```bash
docker build -t diagram-generator:latest backend/
docker run -d -p 8000:8000 --env-file .env diagram-generator:latest
```

---

## Constitution Compliance Checklist

Before committing code, verify:

- [ ] **SRP**: Each class/function has single responsibility
- [ ] **Auto-Deploy**: No manual configuration steps required
- [ ] **Explicit Naming**: Variables/functions clearly named (no `d`, `tmp`, `data`)
- [ ] **Zero Duplication**: Shared logic extracted to utility functions
- [ ] **YAGNI**: No speculative features implemented

---

## Resources

- **OpenAPI Spec**: `specs/001-architecture-diagram-generator/contracts/openapi.yaml`
- **Data Model**: `specs/001-architecture-diagram-generator/data-model.md`
- **Feature Spec**: `specs/001-architecture-diagram-generator/spec.md`
- **Research Notes**: `specs/001-architecture-diagram-generator/research.md`
- **Implementation Plan**: `specs/001-architecture-diagram-generator/plan.md`

---

## Support

For issues or questions:
1. Check troubleshooting section above
2. Review API docs at http://localhost:8000/docs
3. Consult constitution at `.specify/memory/constitution.md`
4. Open issue in project repository

**Happy coding! 🚀**
