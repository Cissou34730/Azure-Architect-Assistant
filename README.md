# Azure Architecture Assistant - POC

This is a proof-of-concept application that helps Azure Solution Architects analyze project documents, clarify requirements through interactive chat, generate high-level Azure architecture proposals, and query the Azure Well-Architected Framework (WAF) documentation.

## Features

### Architecture Project Management
1. **Project Management**: Create and manage multiple architecture projects
2. **Document Upload**: Upload RFP, specifications, and other project documents (supports plain text, with placeholders for PDF/DOCX)
3. **Document Analysis**: AI-powered analysis to extract project context, requirements, and constraints
4. **Interactive Chat**: Clarify requirements and refine the architecture sheet through conversation
5. **Architecture Sheet**: Structured view of project requirements, NFRs, constraints, and open questions
6. **Architecture Proposal**: Generate comprehensive Azure architecture proposals based on gathered requirements

### WAF Query System (New)
7. **WAF Documentation Ingestion**: Automated crawling and processing of Azure Well-Architected Framework documentation
8. **Vector Search**: Semantic search across WAF content using OpenAI embeddings
9. **Source-Grounded Answers**: Get accurate answers with citations to official WAF documentation
10. **Interactive Queries**: Ask questions about Azure best practices, architecture patterns, and recommendations

## Architecture

- **Backend**: Express + TypeScript REST API
- **Frontend**: React + Vite with Tailwind CSS
- **Storage**: In-memory (no persistence - resets on restart)
- **AI**: OpenAI / Azure OpenAI API for document analysis and architecture generation
- **WAF System**:
  - **Python**: LlamaIndex for document ingestion, chunking, embeddings, and vector indexing
  - **Vector Store**: Local persistent storage (no external database required)
  - **Embeddings**: OpenAI text-embedding-3-small
  - **Generation**: OpenAI gpt-4-turbo-preview
  - **Integration**: TypeScript backend orchestrates Python processes

## Prerequisites

- Node.js 18+ and npm
- Python 3.10+ (for WAF functionality)
- OpenAI API key or Azure OpenAI credentials

## Setup

### 1. Clone and Install Dependencies

```bash
# Install all dependencies (backend + frontend)
npm run install:all

# OR install individually

# Install backend dependencies
cd backend
npm install

# Install frontend dependencies
cd ../frontend
npm install

# Install Python dependencies (for WAF functionality)
pip install -r requirements.txt
```

### 2. Configure OpenAI API

Create a `.env` file in the `backend` directory:

```bash
# For OpenAI
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-4o

# OR for Azure OpenAI
AZURE_OPENAI_API_KEY=your-azure-openai-key
OPENAI_API_ENDPOINT=https://your-resource.openai.azure.com/openai/deployments/your-deployment/chat/completions?api-version=2024-02-15-preview
OPENAI_MODEL=gpt-4o
```

### 3. Run the Application

**Terminal 1 - Start Backend:**

```bash
cd backend
npm run dev
```

Backend runs on `http://localhost:3000`

**Terminal 2 - Start Frontend:**

```bash
cd frontend
npm run dev
```

Frontend runs on `http://localhost:5173`

## Usage Workflow

1. **Create a Project**
   - Enter a project name in the left sidebar
   - Click "Create Project"

2. **Upload Documents**
   - Select the project
   - Go to the "Documents" tab
   - Upload project files (RFP, specifications, etc.)
   - Click "Analyze Documents" to generate the initial Architecture Sheet

3. **Review Architecture Sheet**
   - Go to the "State" tab to see the extracted information:
     - Context & Objectives
     - Non-Functional Requirements (NFRs)
     - Application Structure
     - Data & Compliance
     - Technical Constraints
     - Open Questions

4. **Clarify Requirements**
   - Go to the "Chat" tab
   - Ask questions or provide additional information
   - The Architecture Sheet updates automatically based on the conversation

5. **Generate Architecture Proposal**
   - Go to the "Proposal" tab
   - Click "Generate Proposal"
   - Review the comprehensive Azure architecture recommendation

## WAF Query System

### Overview

The WAF Query System provides intelligent, source-grounded answers to questions about the Azure Well-Architected Framework. It uses advanced RAG (Retrieval-Augmented Generation) techniques to combine semantic search with LLM generation.

### Architecture

The system consists of four main components:

1. **Crawler** (`backend/src/python/crawler.py`)
   - BFS traversal of learn.microsoft.com/azure/well-architected/
   - Depth control and domain restriction
   - Deduplication and graceful error handling

2. **Ingestion Pipeline** (`backend/src/python/ingestion.py`)
   - HTML extraction using Readability
   - Content cleaning with BeautifulSoup
   - HTML-to-text conversion
   - Text normalization

3. **Chunking & Validation** (`backend/src/python/chunker.py`)
   - Token-based splitting (800 tokens, 120 overlap)
   - Manual validation workflow (CSV export)
   - Metadata preservation (URL, title, section)

4. **Vector Indexing** (`backend/src/python/indexer.py`)
   - Embedding generation (text-embedding-3-small)
   - LlamaIndex persistent vector store
   - Local storage (no external DB)

5. **Query Service** (`backend/src/python/query_service.py`)
   - Semantic retrieval (top-K chunks)
   - Similarity filtering (threshold: 0.75)
   - Answer generation (gpt-4-turbo-preview)
   - Source attribution with relevance scores

### Initial Setup

#### 1. Run WAF Ingestion (One-Time Setup)

The ingestion process must be run once to build the vector index. This can take 15-30 minutes.

**Option A: Via Web Interface**
1. Navigate to the "WAF Query" tab in the application
2. Click "Start WAF Ingestion"
3. Wait for the process to complete (monitor status via refresh)

**Option B: Via Python CLI (Complete Pipeline)**

```bash
# Run the complete pipeline with one command
python run_waf_ingestion.py
```

This script will:
- Crawl ~500 WAF documentation pages
- Extract and clean content
- Chunk documents into searchable pieces
- Auto-validate all chunks
- Generate embeddings and build vector index

**Option C: Via Python CLI (Step-by-Step)**

```bash
cd backend/src/python

# Step 1: Crawl WAF documentation
python crawler.py

# Step 2: Process and clean documents
python ingestion.py

# Step 3: Chunk documents
python chunker.py

# Step 4: (Optional) Manually validate chunks
# Edit chunks_review.csv - set status to KEEP or DROP for each chunk

# Step 5: Build vector index
python indexer.py
```

#### 2. Configuration

Ensure your `.env` file includes:

```bash
# Required for WAF functionality
OPENAI_API_KEY=your-openai-api-key

# Optional: Specify Python path if using virtual environment
PYTHON_PATH=python  # or /path/to/venv/bin/python
```

### Using the WAF Query System

1. **Access the Interface**
   - Click the "WAF Query" tab in the navigation bar
   - Ensure the index status shows "ready"

2. **Ask Questions**
   - Enter your question in natural language
   - Examples:
     - "What are the best practices for securing Azure SQL databases?"
     - "How should I design a highly available multi-region architecture?"
     - "What are the cost optimization recommendations for Azure Storage?"

3. **Review Answers**
   - Read the AI-generated answer
   - Check the source documents with relevance scores
   - Click source links to view original documentation
   - Use suggested follow-up questions for deeper exploration

### Technical Specifications

| Component | Technology | Configuration |
|-----------|-----------|---------------|
| Crawler | Python requests + BeautifulSoup | Max 500 pages, depth 3 |
| Text Extraction | readability-lxml + html2text | Removes nav, footer, sidebar |
| Chunking | LlamaIndex TokenTextSplitter | 800 tokens, 120 overlap |
| Embeddings | OpenAI text-embedding-3-small | 1536 dimensions |
| Vector Store | LlamaIndex Local Storage | `waf_storage_clean/` |
| Generation | OpenAI gpt-4-turbo-preview | Temperature: default |
| Retrieval | Similarity search | Top-5, threshold 0.75 |

### Extending the System

The WAF ingestion pipeline is designed to be extensible to other documentation sources:

1. **Add New Sources**: Modify `crawler.py` to accept different base URLs
2. **Custom Extractors**: Create source-specific extractors in `ingestion.py`
3. **Multiple Indexes**: Build separate indexes for different documentation sets
4. **Metadata Filtering**: Use `metadataFilters` in queries to scope searches

## API Endpoints

### Architecture Projects

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/projects` | Create a new project |
| GET | `/api/projects` | List all projects |
| POST | `/api/projects/:id/documents` | Upload documents |
| POST | `/api/projects/:id/analyze-docs` | Analyze documents and create Architecture Sheet |
| POST | `/api/projects/:id/chat` | Send chat message and update Architecture Sheet |
| GET | `/api/projects/:id/state` | Get current Architecture Sheet |
| POST | `/api/projects/:id/architecture/proposal` | Generate Azure architecture proposal |
| GET | `/api/projects/:id/messages` | Get conversation history |

### WAF Query System

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/waf/query` | Query WAF documentation |
| POST | `/api/waf/ingest` | Start WAF ingestion pipeline |
| GET | `/api/waf/status` | Get ingestion status |
| GET | `/api/waf/ready` | Check if index is ready |

#### WAF Query Request

```json
{
  "question": "What are the security best practices for Azure Storage?",
  "topK": 5,
  "metadataFilters": {
    "section": "pillar"
  }
}
```

#### WAF Query Response

```json
{
  "answer": "According to the Azure Well-Architected Framework...",
  "sources": [
    {
      "url": "https://learn.microsoft.com/azure/well-architected/...",
      "title": "Security pillar overview",
      "section": "pillar",
      "score": 0.89
    }
  ],
  "scores": [0.89, 0.85, 0.82],
  "hasResults": true,
  "discussionEnabled": true,
  "suggestedFollowUps": [
    "How do I implement encryption at rest?",
    "What about network security?",
    "How does this relate to compliance requirements?"
  ]
}
```

## Data Models

### ProjectState (Architecture Sheet)

```typescript
{
  projectId: string
  context: {
    summary: string
    objectives: string[]
    targetUsers: string
    scenarioType: string
  }
  nfrs: {
    availability: string
    security: string
    performance: string
    costConstraints: string
  }
  applicationStructure: {
    components: string[]
    integrations: string[]
  }
  dataCompliance: {
    dataTypes: string[]
    complianceRequirements: string[]
    dataResidency: string
  }
  technicalConstraints: {
    constraints: string[]
    assumptions: string[]
  }
  openQuestions: string[]
  lastUpdated: string
}
```

## Limitations (POC)

### Architecture Projects
- **No Persistence**: All data stored in memory; resets on server restart
- **No Authentication**: Single-user, no access control
- **Limited Document Parsing**: Full text extraction only for plain text files; PDF/DOCX are placeholders
- **No Multi-tenancy**: Designed for single-user proof-of-concept
- **Basic Error Handling**: Minimal validation and error messages

### WAF Query System
- **Local Storage Only**: Vector index stored locally; not suitable for distributed deployment
- **No Incremental Updates**: Full re-ingestion required to update documentation
- **OpenAI Dependency**: Requires OpenAI API access; no offline mode
- **Basic Validation**: Manual chunk validation workflow is optional
- **Single Language**: English only; no multilingual support

## Future Enhancements

### Architecture Projects
- Database persistence (MongoDB, PostgreSQL)
- User authentication and multi-tenancy
- Advanced document parsing (PDF, DOCX, Excel)
- Architecture diagram generation
- Export capabilities (Word, PDF)
- Version history for Architecture Sheets
- Collaborative editing
- Integration with Azure services for validation

### WAF Query System
- **Multi-Source Support**: Ingest additional documentation (Azure docs, whitepapers, blogs)
- **Incremental Updates**: Delta updates for changed documentation
- **Advanced Filtering**: Date ranges, content types, quality scores
- **Conversation Memory**: Multi-turn dialogue with context retention
- **Distributed Storage**: Support for vector databases (Pinecone, Weaviate, Azure AI Search)
- **Monitoring & Analytics**: Query logs, popular questions, answer quality metrics
- **Multilingual Support**: Query and retrieve in multiple languages
- **Custom Models**: Support for Azure OpenAI and other embedding/LLM providers

## Troubleshooting

### WAF Ingestion Issues

**Problem**: Python dependencies not found
```bash
# Solution: Ensure Python packages are installed
pip install -r requirements.txt

# Or use a virtual environment
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/Mac
source .venv/bin/activate
pip install -r requirements.txt
```

**Problem**: OPENAI_API_KEY not found
```bash
# Solution: Create .env file in backend directory with:
OPENAI_API_KEY=your-key-here
```

**Problem**: Ingestion timeout or failure
```bash
# Solution: Run steps individually to identify the issue
cd backend/src/python
python crawler.py      # Test crawling
python ingestion.py    # Test document processing
python chunker.py      # Test chunking
python indexer.py      # Test indexing
```

**Problem**: TypeScript can't find Python
```bash
# Solution: Set PYTHON_PATH in backend/.env
PYTHON_PATH=/path/to/python  # or python3, python, etc.
```

### Query Issues

**Problem**: "Index not found" error
- **Solution**: Run the ingestion pipeline first (see "Initial Setup" section)

**Problem**: Low-quality answers
- **Solution**: Adjust similarity threshold or top-K in query parameters
- **Alternative**: Manually validate chunks before indexing (edit `chunks_review.csv`)

**Problem**: Slow query response
- **Solution**: This is normal for first query (index loading). Subsequent queries are faster.

### General Issues

**Problem**: Port already in use
```bash
# Solution: Change port in backend/.env
PORT=3001
```

**Problem**: CORS errors
- **Solution**: Ensure both frontend and backend are running on expected ports
- Frontend: http://localhost:5173
- Backend: http://localhost:3000

## Project Structure

```
Azure-Architect-Assistant/
├── backend/
│   ├── src/
│   │   ├── api/            # REST API routes
│   │   │   ├── projects.ts # Architecture project endpoints
│   │   │   └── waf.ts      # WAF query endpoints
│   │   ├── services/       # Business logic
│   │   │   └── WAFService.ts
│   │   ├── python/         # WAF ingestion & query
│   │   │   ├── crawler.py
│   │   │   ├── ingestion.py
│   │   │   ├── chunker.py
│   │   │   ├── indexer.py
│   │   │   ├── query_service.py
│   │   │   └── query_wrapper.py
│   │   ├── db/             # Database (in-memory)
│   │   ├── models/         # Data models
│   │   └── index.ts        # Server entry point
│   ├── package.json
│   └── .env                # Environment variables
├── frontend/
│   ├── src/
│   │   ├── App.tsx         # Main application
│   │   └── WAFQueryInterface.tsx
│   ├── package.json
│   └── vite.config.ts
├── requirements.txt        # Python dependencies
├── run_waf_ingestion.py   # Complete ingestion script
├── package.json            # Workspace config
└── README.md
```

## License

MIT

