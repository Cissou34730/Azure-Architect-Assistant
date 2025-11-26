# Quick Start Guide - KB Ingestion System

## Prerequisites
- Backend server running on `http://localhost:8000`
- Frontend dev server running on `http://localhost:5173`
- OpenAI API key configured in `.env`

## Starting the Application

### 1. Start Backend
```powershell
cd backend
python -m uvicorn app.main:app --reload --port 8000
```

### 2. Start Frontend
```powershell
cd frontend
npm run dev
```

### 3. Open Browser
Navigate to: `http://localhost:5173`

## Creating Your First KB

### Step 1: Navigate to KB Management
1. Click **"KB Management"** tab in the navigation bar
2. You'll see the KB list (may be empty initially)

### Step 2: Create New KB
1. Click **"Create Knowledge Base"** button (top right)
2. **Wizard Step 1 - Basic Info**:
   - Name: `Azure Architecture`
   - KB ID: `azure-arch` (auto-generated)
   - Description: `Azure architecture patterns and best practices`
   - Click **Next**

3. **Wizard Step 2 - Source Type**:
   - Select **"Web Documentation"** (for structured docs)
   - Click **Next**

4. **Wizard Step 3 - Configuration**:
   - Start URLs: `https://learn.microsoft.com/en-us/azure/architecture/`
   - Allowed Domains: `learn.microsoft.com`
   - Path Prefix: `/en-us/azure/architecture/`
   - Max Pages: `50` (for quick testing)
   - Follow links: ✓ (checked)
   - Click **Next**

5. **Wizard Step 4 - Review**:
   - Review all settings
   - Click **"Create & Start"**

### Step 3: Monitor Progress
- You'll be redirected to the progress view
- Watch real-time updates:
  - Phase indicator (CRAWLING → CLEANING → EMBEDDING → INDEXING)
  - Progress bar (0% → 100%)
  - Metrics (pages crawled, documents cleaned, chunks created)
- Ingestion typically takes 5-15 minutes depending on size

### Step 4: Cancel (Optional)
- Click **"Cancel Job"** if you want to stop
- Confirm in the dialog
- Job status will update to CANCELLED

## Testing Different Source Types

### Web Documentation (Microsoft Learn)
```
Name: Azure Well-Architected Framework
Start URL: https://learn.microsoft.com/en-us/azure/well-architected/
Allowed Domains: learn.microsoft.com
Path Prefix: /en-us/azure/well-architected/
Max Pages: 100
```

### Generic Web (Any Website)
```
Name: Company Blog
Source Type: Generic Web
URLs:
  - https://example.com/blog/post1
  - https://example.com/blog/post2
Follow Links: No
```

## Monitoring Multiple KBs

1. Go back to KB list (click "Back to List")
2. You'll see all KBs with their job statuses
3. Click "View Progress" on any running job
4. Click "Start Ingestion" to re-index an existing KB

## API Testing (Optional)

### Using curl
```bash
# Create KB
curl -X POST http://localhost:8000/api/ingestion/kb/create \
  -H "Content-Type: application/json" \
  -d '{
    "kb_id": "test-kb",
    "name": "Test KB",
    "source_type": "web_generic",
    "source_config": {
      "urls": ["https://example.com"],
      "follow_links": false
    }
  }'

# Start ingestion
curl -X POST http://localhost:8000/api/ingestion/kb/test-kb/start

# Check status
curl http://localhost:8000/api/ingestion/kb/test-kb/status

# List all jobs
curl http://localhost:8000/api/ingestion/jobs

# Cancel job
curl -X POST http://localhost:8000/api/ingestion/kb/test-kb/cancel
```

### Using Python Test Script
```bash
cd backend
python test_ingestion_api.py
```

## Troubleshooting

### Backend not starting
```powershell
# Check if port 8000 is in use
Get-NetTCPConnection -LocalPort 8000

# Check Python environment
python --version  # Should be 3.10+

# Install dependencies
pip install -r requirements.txt
```

### Frontend not connecting to backend
- Verify backend is running: `http://localhost:8000/health`
- Check browser console for CORS errors
- Verify API base URL in `frontend/src/services/ingestionApi.ts`

### Ingestion fails immediately
- Check OpenAI API key in `.env`
- Check backend logs for errors
- Verify URLs are accessible
- Check network connectivity

### No KBs showing in list
- Check backend endpoint: `http://localhost:8000/api/kb/list`
- Verify `backend/data/knowledge_bases/config.json` exists
- Check browser console for errors

## Expected Behavior

### Successful Ingestion
1. Status: RUNNING → COMPLETED
2. Phase: CRAWLING → CLEANING → EMBEDDING → INDEXING → COMPLETED
3. Progress: 0% → 100%
4. Metrics populate progressively
5. KB status changes to "Indexed"

### Failed Ingestion
1. Status: RUNNING → FAILED
2. Error message displayed in red box
3. Check backend logs for details
4. Common causes:
   - Invalid URLs
   - Network errors
   - OpenAI API rate limits
   - Insufficient permissions

## Next Steps After Successful Ingestion

1. **Test Queries**:
   - Go to "Knowledge Base Query" tab
   - Select your new KB from the dropdown
   - Ask questions about the ingested content

2. **Multi-KB Queries**:
   - Create multiple KBs
   - Use "KB Query" profile to query all at once
   - Compare results across knowledge bases

3. **Re-Index**:
   - Click "Start Ingestion" on an existing KB
   - Updates the index with latest content
   - Useful for documentation that changes frequently

## Performance Tips

### For Quick Testing
- Set Max Pages to 10-50
- Use specific path prefixes
- Disable "Follow Links" for generic web

### For Production
- Set Max Pages to 1000+
- Use broad path prefixes
- Enable "Follow Links" for comprehensive coverage
- Schedule re-indexing periodically

## Monitoring Tips

### Check Backend Logs
```powershell
# Watch logs in real-time
cd backend
python -m uvicorn app.main:app --reload --log-level info
```

### Watch Network Tab
- Open browser DevTools (F12)
- Go to Network tab
- Filter: XHR
- Watch API calls every 2 seconds during ingestion

### Database Inspection
```bash
# Check KB configurations
cat backend/data/knowledge_bases/config.json

# Check vector indices
ls -la backend/data/knowledge_bases/*/index/
```

## Support

For issues or questions:
1. Check backend logs for errors
2. Review browser console for frontend errors
3. Verify API endpoints with curl/Postman
4. Check documentation in `docs/` folder:
   - `INGESTION_API.md` - API reference
   - `FRONTEND_INGESTION_IMPLEMENTATION.md` - Frontend details
   - `KB_INGESTION_PROGRESS.md` - Implementation progress

## Advanced Usage

### Custom Source Types
Extend `backend/app/kb/ingestion/sources/` with:
- PDF crawler
- Git repository crawler
- Database crawler
- API crawler

### Custom Embeddings
Modify `embedding_model` in KB creation:
- `text-embedding-3-small` (default)
- `text-embedding-3-large` (higher quality)
- `text-embedding-ada-002` (legacy)

### Custom Chunking
Adjust in KB creation:
- `chunk_size`: 500-2000 (default: 800)
- `chunk_overlap`: 50-200 (default: 120)

## Summary

You now have a fully functional KB ingestion system with:
- ✅ Multi-source support (web docs, generic web)
- ✅ Real-time progress tracking
- ✅ Job management (start/cancel/monitor)
- ✅ Beautiful UI with responsive design
- ✅ Error handling and validation
- ✅ RESTful API for automation

Happy knowledge base building! 🚀
