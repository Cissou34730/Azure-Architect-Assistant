# Azure Architecture Assistant - POC

This is a proof-of-concept application that helps Azure Solution Architects analyze project documents, clarify requirements through interactive chat, and generate high-level Azure architecture proposals.

## Features

1. **Project Management**: Create and manage multiple architecture projects
2. **Document Upload**: Upload RFP, specifications, and other project documents (supports plain text, with placeholders for PDF/DOCX)
3. **Document Analysis**: AI-powered analysis to extract project context, requirements, and constraints
4. **Interactive Chat**: Clarify requirements and refine the architecture sheet through conversation
5. **Architecture Sheet**: Structured view of project requirements, NFRs, constraints, and open questions
6. **Architecture Proposal**: Generate comprehensive Azure architecture proposals based on gathered requirements

## Architecture

- **Backend**: Express + TypeScript REST API
- **Frontend**: React + Vite with Tailwind CSS
- **Storage**: In-memory (no persistence - resets on restart)
- **AI**: OpenAI / Azure OpenAI API for document analysis and architecture generation

## Prerequisites

- Node.js 18+ and npm
- OpenAI API key or Azure OpenAI credentials

## Setup

### 1. Clone and Install Dependencies

```bash
# Install backend dependencies
cd backend
npm install

# Install frontend dependencies
cd ../frontend
npm install
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

## API Endpoints

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

- **No Persistence**: All data stored in memory; resets on server restart
- **No Authentication**: Single-user, no access control
- **Limited Document Parsing**: Full text extraction only for plain text files; PDF/DOCX are placeholders
- **No Multi-tenancy**: Designed for single-user proof-of-concept
- **Basic Error Handling**: Minimal validation and error messages

## Future Enhancements

- Database persistence (MongoDB, PostgreSQL)
- User authentication and multi-tenancy
- Advanced document parsing (PDF, DOCX, Excel)
- Architecture diagram generation
- Export capabilities (Word, PDF)
- Version history for Architecture Sheets
- Collaborative editing
- Integration with Azure services for validation

## License

MIT

