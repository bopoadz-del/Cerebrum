# Cerebrum AI - Construction Intelligence Platform

[![Version](https://img.shields.io/badge/version-2.0.0-blue.svg)](https://github.com/cerebrum-ai/cerebrum)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-61DAFB.svg)](https://reactjs.org/)

> **End-to-End Construction Intelligence: From Empty Directory to Production Platform**

Cerebrum AI is a comprehensive construction management platform featuring a 14-layer backend architecture built with FastAPI and a modern React frontend. The platform provides AI-powered insights, BIM/VDC capabilities, real-time collaboration, and enterprise-grade security.

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CEREBRUM AI PLATFORM                                 │
│                    14-Layer Backend Architecture                             │
├─────────────────────────────────────────────────────────────────────────────┤
│  Layer 14 │ Data Warehouse    │ Airflow ETL, BigQuery, Executive Dashboards │
│  Layer 13 │ Integration Hub   │ Webhooks, Procore/ACC, Zapier Connectors    │
│  Layer 12 │ Advanced VDC      │ Federated Models, Clash Detection, 4D/5D    │
│  Layer 11 │ Field Data        │ Daily Reports, Photos, Punch Lists, Offline │
│  Layer 10 │ Collaboration     │ Real-time Comments, Approvals, WebSocket    │
│  Layer 9  │ Tasks             │ Background Jobs, Celery Workers, Queues     │
│  Layer 8  │ API Management    │ Endpoint Management, Caching, Rate Limiting │
│  Layer 7  │ Pipelines         │ Workflow Orchestration, DAG Execution       │
│  Layer 6  │ Audit             │ Immutable Audit Logs, Compliance Reports    │
│  Layer 5  │ Sandbox           │ Isolated Execution Environments             │
│  Layer 4  │ ML                │ Model Training, Predictions, Feature Store  │
│  Layer 3  │ BIM               │ IFC Parsing, Element Management, 3D Viewer  │
│  Layer 2  │ Documents         │ Document AI, OCR, Transcription, Search     │
│  Layer 1  │ Core              │ Auth, RBAC, Multi-tenancy, Security         │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- PostgreSQL 15+
- Redis 7+

### Local Development

```bash
# Clone the repository
git clone https://github.com/cerebrum-ai/cerebrum.git
cd cerebrum

# Start all services with Docker Compose
docker-compose up -d

# Or start services individually:

# 1. Start PostgreSQL and Redis
docker-compose up -d postgres redis

# 2. Run database migrations
cd backend
alembic upgrade head

# 3. Seed the database
python scripts/seed.py

# 4. Start the backend
uvicorn app.main:app --reload

# 5. In a new terminal, start the frontend
cd ../frontend
npm install
npm run dev
```

The application will be available at:
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/api/docs
- Flower (Celery Monitoring): http://localhost:5555

## 📁 Project Structure

```
cerebrum/
├── backend/                    # FastAPI Backend
│   ├── app/
│   │   ├── api/               # API endpoints
│   │   │   └── v1/
│   │   │       └── endpoints/ # REST endpoints (auth, users, projects, etc.)
│   │   ├── core/              # Core utilities
│   │   │   ├── security/      # JWT, RBAC, MFA, encryption
│   │   │   ├── config.py      # Configuration
│   │   │   └── logging.py     # Structured logging
│   │   ├── db/                # Database
│   │   │   ├── session.py     # Connection pooling
│   │   │   └── base_class.py  # Soft delete mixin
│   │   ├── models/            # SQLAlchemy models (14 layers)
│   │   ├── schemas/           # Pydantic schemas
│   │   ├── services/          # Business logic
│   │   ├── integrations/      # External integrations
│   │   ├── pipelines/         # Data processing pipelines
│   │   ├── ml/                # Machine learning
│   │   ├── vdc/               # Virtual Design Construction
│   │   ├── edge/              # Edge computing
│   │   ├── enterprise/        # Enterprise features
│   │   ├── portal/            # Subcontractor portal
│   │   ├── monitoring/        # Observability
│   │   ├── warehouse/         # Data warehouse
│   │   ├── quality/           # Quality & safety
│   │   ├── iot/               # IoT & Digital Twin
│   │   ├── registry/          # Self-coding registry
│   │   ├── coding/            # Code generation
│   │   ├── validation/        # Validation pipeline
│   │   ├── hotswap/           # Hot deployment
│   │   ├── healing/           # Self-healing
│   │   └── prompts/           # Prompt registry
│   ├── tests/                 # Test suite
│   ├── scripts/               # Utility scripts
│   ├── alembic/               # Database migrations
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/                   # React Frontend
│   ├── src/
│   │   ├── components/        # React components
│   │   │   ├── layout/        # Sidebar, TopBar, MainLayout
│   │   │   ├── ui/            # UI components
│   │   │   ├── BIMViewer/     # 3D BIM viewer components
│   │   │   ├── vdc/           # VDC components
│   │   │   ├── quality/       # Quality components
│   │   │   └── iot/           # IoT components
│   │   ├── pages/             # Page components (20+ pages)
│   │   ├── contexts/          # React contexts
│   │   ├── hooks/             # Custom hooks
│   │   ├── lib/               # Utilities
│   │   ├── stores/            # Zustand stores
│   │   ├── router.tsx         # React Router
│   │   └── main.tsx           # Entry point
│   ├── public/
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml
└── README.md
```

## 🔑 Key Features

### Core Platform (Layer 1)
- ✅ JWT Authentication with MFA (TOTP)
- ✅ Role-Based Access Control (5 role levels)
- ✅ Multi-tenancy with subdomain support
- ✅ Soft delete pattern for data integrity
- ✅ Audit logging with hash chain integrity

### Document Intelligence (Layer 2)
- ✅ OCR with Tesseract
- ✅ Document classification with GPT-4 Vision
- ✅ Named entity extraction
- ✅ Action item extraction from meeting minutes
- ✅ Audio transcription with Whisper

### BIM & VDC (Layers 3, 12)
- ✅ IFC parsing with IfcOpenShell
- ✅ 3D viewer with Three.js / React Three Fiber
- ✅ Federated model management
- ✅ Clash detection (AABB collision)
- ✅ 4D/5D BIM (schedule + cost integration)
- ✅ COBie-compliant digital handover

### Machine Learning (Layer 4)
- ✅ MLflow experiment tracking
- ✅ Model registry with staging
- ✅ AutoML with Optuna/Ray Tune
- ✅ Feature store integration
- ✅ Model explainability (SHAP/LIME)

### Edge Computing
- ✅ Jetson device registry
- ✅ OTA model deployment
- ✅ Hybrid cloud-edge inference
- ✅ Real-time safety AI (YOLOv8)

### Enterprise Features
- ✅ SAML 2.0 / OIDC SSO
- ✅ SCIM directory sync
- ✅ White-labeling
- ✅ Data residency controls
- ✅ SOC 2 / GDPR compliance

### Self-Coding Registry (Meta-Cognition)
- ✅ Capability registry with lifecycle management
- ✅ AI-powered code generation
- ✅ Automated validation pipeline
- ✅ Hot deployment without restart
- ✅ Self-healing with automatic patches

### Formula Engine
- ✅ JSON-based formula library
- ✅ Safe evaluation with restricted builtins
- ✅ Domain-tagged formulas (construction, structural, financial)
- ✅ REST API for formula evaluation
- ✅ Input validation and error handling

## 📐 Formula API

The Formula Engine provides safe, sandboxed evaluation of mathematical formulas for construction calculations.

### Environment Variable
```bash
INITIAL_FORMULAS_PATH=data/formulas/initial_library.json  # Path to formulas JSON
```

### API Endpoints

**List all formulas:**
```bash
curl http://localhost:8000/api/v1/formulas
```

**Get specific formula:**
```bash
curl http://localhost:8000/api/v1/formulas/concrete_volume
```

**Evaluate a formula:**
```bash
curl -X POST http://localhost:8000/api/v1/formulas/eval \
  -H "Content-Type: application/json" \
  -d '{
    "formula_id": "concrete_volume",
    "inputs": {
      "length": 10.0,
      "width": 5.0,
      "height": 0.3
    }
  }'
# Response: {"formula_id":"concrete_volume","success":true,"output_values":{"result":15.0}}
```

**Evaluate by path:**
```bash
curl -X POST http://localhost:8000/api/v1/formulas/rebar_weight/eval \
  -H "Content-Type: application/json" \
  -d '{"diameter": 16, "length": 12}'
```

### Built-in Functions
Available in formula expressions: `abs`, `round`, `min`, `max`, `sum`, `pow`, `sqrt`, `pi`, `sin`, `cos`, `tan`, `log`, `exp`, and all `math` module functions.

### Security
- Dangerous builtins (`__import__`, `open`, `exec`, `eval`) are blocked
- Formulas run in restricted environment
- Invalid expressions return error messages, don't crash

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the backend directory:

```env
# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/cerebrum

# Redis
REDIS_URL=redis://localhost:6379/0

# Security
SECRET_KEY=your-super-secret-key
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# External APIs
OPENAI_API_KEY=sk-...
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
SENDGRID_API_KEY=...

# S3 / File Storage
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
S3_BUCKET=cerebrum-uploads

# Monitoring
SENTRY_DSN=https://...
```

## 🧪 Testing

```bash
# Backend tests
cd backend
pytest -v

# With coverage
pytest --cov=app --cov-report=html

# Frontend tests
cd frontend
npm test

# E2E tests
npm run test:e2e
```

## 📊 API Documentation

When running locally, access the interactive API documentation:

- Swagger UI: http://localhost:8000/api/docs
- ReDoc: http://localhost:8000/api/redoc

## 🚢 Deployment

### Render (One-Click Deploy)

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy)

The project includes a `render.yaml` file for one-click deployment.

### Docker Production

```bash
# Build production images
docker-compose -f docker-compose.prod.yml build

# Deploy
docker-compose -f docker-compose.prod.yml up -d
```

### Kubernetes

```bash
# Apply manifests
kubectl apply -f k8s/
```

## 📈 Monitoring

- **APM**: Datadog / New Relic integration
- **Error Tracking**: Sentry
- **Logs**: ELK Stack / Splunk
- **Metrics**: Prometheus + Grafana
- **Uptime**: Pingdom / UptimeRobot
- **Status Page**: status.cerebrum.ai

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- FastAPI team for the amazing framework
- React team for the frontend library
- The construction technology community for inspiration

---

<p align="center">
  Built with ❤️ by the Cerebrum AI Team
</p>
