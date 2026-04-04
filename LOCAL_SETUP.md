# Local Development Setup

This guide sets up Cerebrum AI Platform entirely on your local machine using Docker. No cloud services required.

## Quick Start

```bash
# 1. Clone and enter the repo
git clone https://github.com/bopoadz-del/Cerebrum.git
cd Cerebrum

# 2. Create data directory for documents
mkdir -p data/diriyah_docs

# 3. Start all services
docker-compose -f docker-compose.local.yml up --build

# 4. Open in browser:
# Frontend: http://localhost:5173
# API Docs: http://localhost:8000/api/docs
# Health:   http://localhost:8000/health
```

## Services

| Service | Port | Description |
|---------|------|-------------|
| API | 8000 | FastAPI backend with auto-reload |
| Frontend | 5173 | React + Vite dev server |
| PostgreSQL | 5432 | Local database (data persists in Docker volume) |
| Redis | 6379 | Cache and task queue |
| Celery Workers | - | Background task processing |

## Auto-Processing Documents

Drop files into the `data/diriyah_docs/` folder and they are automatically processed:

```bash
# Copy a PDF
cp ~/Downloads/project-specs.pdf data/diriyah_docs/

# The file will be:
# 1. Detected by the local filesystem watcher
# 2. Hashed to prevent duplicates
# 3. Emitted as FILE_UPLOADED event
# 4. Processed by existing trigger system (OCR, classification, etc.)
```

Supported file types:
- **Documents**: PDF, DOC, DOCX, TXT, HTML
- **Spreadsheets**: XLS, XLSX  
- **BIM/CAD**: IFC, DWG, DXF
- **Images**: PNG, JPG, JPEG, GIF, BMP

## Environment Variables

Key variables in `docker-compose.local.yml`:

| Variable | Default | Description |
|----------|---------|-------------|
| `WATCH_LOCAL_FILES` | `true` | Enable local file watching |
| `LOCAL_DATA_PATH` | `/data/diriyah_docs` | Path to watch for files |
| `USE_STUB_CONNECTORS` | `true` | Use stub implementations (safe for local dev) |
| `USE_STUB_ML` | `true` | Use stub ML models |
| `DEBUG` | `true` | Enable debug mode |

## Useful Commands

```bash
# View logs
docker-compose -f docker-compose.local.yml logs -f api

# Restart just the API
docker-compose -f docker-compose.local.yml restart api

# Run database migrations (inside container)
docker-compose -f docker-compose.local.yml exec api alembic upgrade head

# Access PostgreSQL
docker-compose -f docker-compose.local.yml exec postgres psql -U cerebrum -d cerebrum_local

# Stop everything
docker-compose -f docker-compose.local.yml down

# Stop and remove volumes (DELETES ALL DATA)
docker-compose -f docker-compose.local.yml down -v
```

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Frontend      │────▶│   FastAPI       │────▶│   PostgreSQL    │
│   (React/Vite)  │◀────│   (Python)      │◀────│   (Local DB)    │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                               │
                               ▼
                        ┌─────────────────┐
                        │   Redis         │
                        │   (Cache/Queue) │
                        └─────────────────┘
                               │
                               ▼
                        ┌─────────────────┐
                        │   Celery        │
                        │   (Workers)     │
                        └─────────────────┘
                               ▲
                               │
┌─────────────────┐     ┌─────────────────┐
│  data/diriyah_  │────▶│  Local File     │
│     docs/       │     │  Watcher        │
└─────────────────┘     └─────────────────┘
```

## Troubleshooting

### Port Already in Use
```bash
# Find what's using port 8000
lsof -i :8000

# Or use different ports in docker-compose.local.yml
```

### Database Connection Issues
```bash
# Reset everything (DELETES DATA)
docker-compose -f docker-compose.local.yml down -v
docker-compose -f docker-compose.local.yml up --build
```

### File Watching Not Working
```bash
# Check watcher is enabled
docker-compose -f docker-compose.local.yml exec api env | grep WATCH

# Should show: WATCH_LOCAL_FILES=true
```

### Hot Reload Not Working
The API and frontend both have hot reload enabled. If changes aren't detected:
```bash
# Restart the service
docker-compose -f docker-compose.local.yml restart api
```

## Production vs Local

| Feature | Local (docker-compose.local.yml) | Production (Render) |
|---------|----------------------------------|---------------------|
| Database | PostgreSQL in Docker | Managed PostgreSQL |
| File Storage | Local filesystem | Cloud storage |
| File Watching | Local filesystem watcher | Google Drive webhooks |
| ML Models | Stubs (safe) | Real models (if available) |
| Workers | Local Celery | Cloud task queues |
| Authentication | Stub connectors | Real OAuth |

## Moving to New Laptop

1. **Push code to GitHub**: Already done if you cloned from there
2. **Copy data folder** (optional): `scp -r data/ new-laptop:Cerebrum/`
3. **Run the Quick Start commands above**

That's it! The entire stack is containerized.
