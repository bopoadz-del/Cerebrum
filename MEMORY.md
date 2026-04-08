# Cerebrum AI Platform - Memory Documentation

> **Last Updated:** April 2025  
> **Platform Version:** Cerebrum AI v1.0  
> **Purpose:** Baseline documentation for the Cerebrum AI construction intelligence platform

---

## Table of Contents

1. [What is Cerebrum](#what-is-cerebrum)
2. [Available Layers](#available-layers)
3. [Chat Interface](#chat-interface)
4. [Common Commands](#common-commands)
5. [Cost Estimation Features](#cost-estimation-features)
6. [Architecture Overview](#architecture-overview)
7. [Quick Reference](#quick-reference)

---

## What is Cerebrum

**Cerebrum** is an AI-powered construction intelligence platform designed for construction management, cost estimation, and building information modeling (BIM). It combines traditional construction industry knowledge with modern AI capabilities.

### Core Capabilities

| Capability | Description |
|------------|-------------|
| **Cost Estimation** | RSMeans integration for accurate construction cost calculations |
| **BIM Analysis** | IFC model processing, clash detection, and quantity takeoff |
| **Document Processing** | Invoice extraction, contract analysis, and report generation |
| **Autonomous Agent** | Self-coding, self-healing AI with 14 specialized layers |
| **Voice Interface** | Real-time voice chat for hands-free operation |
| **Project Management** | Google Drive integration with cascaded folder structure |

### Platform Components

```
┌─────────────────────────────────────────────────────────────┐
│                    CEREBRUM AI PLATFORM                     │
├─────────────┬─────────────┬─────────────┬───────────────────┤
│  Frontend   │   Backend   │   Agent     │   Integrations    │
│   (React)   │  (FastAPI)  │   System    │                   │
├─────────────┼─────────────┼─────────────┼───────────────────┤
│ Chat UI     │ REST API    │ 14 Layers   │ Google Drive      │
│ Voice Chat  │ WebSocket   │ Self-coding │ Procore           │
│ Mobile App  │ PostgreSQL  │ Self-healing│ Microsoft 365     │
│ 3-Panel     │ Redis       │ Planning    │ Slack             │
│   Layout    │ Celery      │ Scheduling  │ Zapier            │
└─────────────┴─────────────┴─────────────┴───────────────────┘
```

---

## Available Layers

Cerebrum implements a **14-layer architecture** where each layer represents a specialized domain. The autonomous agent can navigate between these layers based on task requirements.

### Layer Inventory

| # | Layer | Code | Purpose | Key Features |
|---|-------|------|---------|--------------|
| 1 | **Coding** | `coding` | Self-coding generation | FastAPI endpoints, React components, DB models |
| 2 | **Registry** | `registry` | Capability registry | Tool registration, version control, dependencies |
| 3 | **Validation** | `validation` | Security & testing | Code validation, security scanning, sandbox execution |
| 4 | **Hotswap** | `hotswap` | Dynamic deployment | Zero-downtime updates, rollback capabilities |
| 5 | **Healing** | `healing` | Self-healing | Error detection, root cause analysis, auto-patching |
| 6 | **Prompts** | `prompts` | Prompt management | A/B testing, dynamic loading, optimization |
| 7 | **Triggers** | `triggers` | Event triggers | File triggers, audit triggers, ML triggers, safety triggers |
| 8 | **Economics** | `economics` | Cost estimation | RSMeans data, building estimates, formulas |
| 9 | **VDC** | `vdc` | Virtual Design & Construction | BIM coordination, clash detection, 4D/5D modeling |
| 10 | **Edge** | `edge` | Edge inference | On-device AI, hybrid inference, safety monitoring |
| 11 | **Portal** | `portal` | User portal | RFI management, submittals, daily reports |
| 12 | **Enterprise** | `enterprise` | Security/auth | SSO/SAML, RBAC, audit logging, compliance |
| 13 | **Connectors** | `connectors` | External integrations | ERP, CRM, accounting, e-signature |
| 14 | **Monitoring** | `monitoring` | Observability | APM, logging, alerting, status pages |

### Layer Navigation

**API Endpoint:** `POST /api/v1/agent/layer/move`

```json
{
  "layer": "economics"
}
```

**List all layers:**
```bash
curl http://localhost:8000/api/v1/agent/layers
```

**Get current layer:**
```bash
curl http://localhost:8000/api/v1/agent/status
```

---

## Chat Interface

Cerebrum provides a **dual-mode chat interface** that adapts to user needs.

### Standard Mode

Quick commands for common construction tasks:

```
┌──────────────────────────────────────────────────────┐
│  Project: Downtown Office Building          [Agent]  │
├──────────────────────────────────────────────────────┤
│                                                      │
│  👤 User: /cost concrete foundation                  │
│                                                      │
│  🤖 Assistant:                                       │
│  Found 5 RSMeans items for "concrete foundation":   │
│                                                      │
│  • 03-100-100: Concrete Footing - $125.00/cy        │
│  • 03-200-150: Foundation Wall - $85.00/sf          │
│  ...                                                 │
│                                                      │
├──────────────────────────────────────────────────────┤
│  [+] Type a message...                    [Send]     │
└──────────────────────────────────────────────────────┘
```

### Agent Mode

For complex, multi-step tasks requiring AI reasoning:

```
┌──────────────────────────────────────────────────────┐
│  🧠 Agent Mode Active - Layer: Economics             │
├──────────────────────────────────────────────────────┤
│                                                      │
│  👤 User: Analyze this PDF and extract all          │
│           material quantities, then calculate        │
│           costs using RSMeans data                   │
│                                                      │
│  🤖 Agent: Processing...                             │
│  [░░░░░░░░░░░░░░░░░░] 45%                           │
│  Step 1: Extracting text from PDF...                 │
│  Step 2: Identifying material categories...          │
│                                                      │
└──────────────────────────────────────────────────────┘
```

### Interface Layout

**Desktop (3-Panel):**
```
┌─────────────┬──────────────────┬─────────────┐
│  Projects   │   Chat Header    │  Outcomes   │
│  Sidebar    │   - Project name │   Panel     │
│             │                  │             │
│ ▼ Project 1 │ Chat Messages    │ [Reports]   │
│   Chat 1    │ - Copy/Share     │ [Previews]  │
│   Chat 2    │ - Timestamp      │ [Steps]     │
│ ▶ Project 2 │                  │             │
│             │ Input [+] [Send] │ Outcome 1   │
│ Settings    │                  │             │
└─────────────┴──────────────────┴─────────────┘
```

**Mobile (Tab-based):**
```
┌─────────────────────────┐
│  Header - Project Name  │
├─────────────────────────┤
│  [Chat] [Outcomes]      │
├─────────────────────────┤
│     Chat Content        │
├─────────────────────────┤
│  [+] Type message...    │
├─────────────────────────┤
│  [Projects][Settings]   │
└─────────────────────────┘
```

### Chat Features

| Feature | Description |
|---------|-------------|
| **Smart Context** | Auto-brief + handoff at 90% capacity |
| **File Attachments** | Upload PDFs, images, CAD files |
| **Voice Input** | Real-time speech-to-text |
| **Web Search** | Internet search for current pricing |
| **Copy/Share** | One-click message sharing |
| **Timestamps** | Full date/time for all items |

---

## Common Commands

### Slash Commands (Standard Mode)

| Command | Description | Example |
|---------|-------------|---------|
| `/help` | Show all available commands | `/help` |
| `/cost <item>` | Search RSMeans cost database | `/cost concrete` |
| `/estimate <type> <size>` | Quick building estimate | `/estimate warehouse 50000` |
| `/formula <query>` | Find construction formulas | `/formula beam moment` |
| `/search <query>` | Search documents and memory | `/search foundation specs` |
| `/layer <name>` | Switch to specific layer | `/layer economics` |
| `/status` | Show agent status | `/status` |
| `/plan <goal>` | Create execution plan | `/plan analyze all BIM models` |

### Building Type Codes for Estimates

| Code | Building Type | Typical Cost/sf |
|------|---------------|-----------------|
| `office` | Office Building | $150-250 |
| `warehouse` | Warehouse/Distribution | $75-125 |
| `retail` | Retail/Shopping | $120-200 |
| `hospital` | Hospital/Medical | $400-600 |
| `school` | School/Educational | $200-300 |
| `apartment` | Multi-family Residential | $180-280 |
| `hotel` | Hotel/Hospitality | $250-400 |

### API Endpoints Reference

```bash
# Authentication
POST   /api/v1/auth/login
POST   /api/v1/auth/register

# Chat
POST   /api/v1/chat/completions
GET    /api/v1/chat/models

# Agent
POST   /api/v1/agent/execute
GET    /api/v1/agent/status
GET    /api/v1/agent/layers
POST   /api/v1/agent/layer/move
POST   /api/v1/agent/memory/search
POST   /api/v1/agent/memory/write

# Economics/Cost
GET    /api/v1/economics/rsmeans/search?q=concrete
GET    /api/v1/economics/csi-divisions
GET    /api/v1/economics/building-types
POST   /api/v1/economics/estimate
POST   /api/v1/economics/estimate/quick

# Documents
POST   /api/v1/documents/upload
GET    /api/v1/documents/{id}
POST   /api/v1/documents/{id}/search

# Projects
GET    /api/v1/projects
POST   /api/v1/projects
GET    /api/v1/projects/{id}/chats
```

---

## Cost Estimation Features

Cerebrum provides comprehensive **construction cost estimation** powered by RSMeans data and location-based adjustments.

### RSMeans Integration

**CSI MasterFormat Divisions:**

| Division | Name | Description |
|----------|------|-------------|
| 01 | General Requirements | Project management, mobilization, permits |
| 02 | Existing Conditions | Demolition, site clearing, remediation |
| 03 | Concrete | Cast-in-place, precast, masonry |
| 04 | Masonry | Brick, block, stone |
| 05 | Metals | Structural steel, metal decking |
| 06 | Wood, Plastics, Composites | Framing, millwork, plastics |
| 07 | Thermal & Moisture | Roofing, insulation, waterproofing |
| 08 | Openings | Doors, windows, glazing |
| 09 | Finishes | Drywall, flooring, painting |
| 10 | Specialties | Signage, lockers, window treatments |
| 11 | Equipment | Appliances, lab equipment |
| 12 | Furnishings | Furniture, window coverings |
| 13 | Special Construction | Swimming pools, greenhouses |
| 14 | Conveying Systems | Elevators, escalators |
| 15-19 | Reserved | Future expansion |
| 21-28 | Fire Suppression | Fire protection, plumbing, HVAC |
| 31 | Earthwork | Excavation, grading, fill |
| 32 | Exterior Improvements | Paving, fencing, landscaping |
| 33 | Utilities | Water, sewer, electrical distribution |

### Cost Calculation Formula

```
Total Cost = Σ(Line Item Costs) + Contingency + Location Adjustment

Where:
  Line Item Cost = Unit Cost × Quantity × City Cost Index
  Contingency = Subtotal × (Contingency% / 100)
```

### Location Cost Indices

| Region | Sample Cities | Index Range |
|--------|---------------|-------------|
| Northeast | New York, Boston, Philadelphia | 1.15-1.40 |
| West | Los Angeles, San Francisco, Seattle | 1.20-1.50 |
| Midwest | Chicago, Detroit, Minneapolis | 0.95-1.15 |
| South | Atlanta, Dallas, Miami | 0.85-1.05 |
| Mountain | Denver, Phoenix, Salt Lake | 0.90-1.10 |

### API Examples

**Quick Building Estimate:**
```bash
curl -X POST "http://localhost:8000/api/v1/economics/estimate/quick?building_type=office&size_sf=50000&city=Los%20Angeles"
```

**Detailed Cost Estimate:**
```bash
curl -X POST http://localhost:8000/api/v1/economics/estimate \
  -H "Content-Type: application/json" \
  -d '{
    "items": [
      {"rsmeans_id": "03-100-100", "quantity": 100},
      {"rsmeans_id": "04-200-150", "quantity": 500}
    ],
    "zip_code": "90210",
    "contingency_percent": 10
  }'
```

**Search RSMeans Database:**
```bash
curl "http://localhost:8000/api/v1/economics/rsmeans/search?q=concrete%20foundation&limit=10"
```

### Construction Formulas

Available calculation formulas:

| Formula ID | Name | Category |
|------------|------|----------|
| `concrete-volume` | Concrete Volume | Concrete |
| `rebar-weight` | Rebar Weight | Structural |
| `beam-moment` | Beam Bending Moment | Structural |
| `cost-per-sf` | Cost per Square Foot | Cost |
| `evm-cpi` | Earned Value CPI | Financial |
| `evm-spi` | Earned Value SPI | Financial |
| `downtime-cost` | Equipment Downtime Cost | Construction |
| `trench-volume` | Excavation Volume | Infrastructure |

**Calculate Formula:**
```bash
curl -X POST http://localhost:8000/api/v1/economics/formulas/concrete-volume/calculate \
  -H "Content-Type: application/json" \
  -d '{"length": 20, "width": 10, "depth": 0.5}'
```

---

## Architecture Overview

### Technology Stack

```
┌─────────────────────────────────────────────────────────────┐
│                         FRONTEND                            │
│  React 18 + TypeScript + Vite + Tailwind CSS + shadcn/ui   │
│  Framer Motion (animations) + Recharts (charts)            │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                         BACKEND                             │
│  FastAPI + Python 3.11 + SQLAlchemy (async)                │
│  PostgreSQL 15 + Redis 7 (4 instances) + Celery            │
│  PgBouncer (connection pooling) + Alembic (migrations)     │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                     AI / ML SERVICES                        │
│  Kimi API (LLM) + ChromaDB (vector store)                  │
│  Self-coding + Self-healing agents                         │
│  BIM/IFC processing pipelines                              │
└─────────────────────────────────────────────────────────────┘
```

### Security Features

- JWT Authentication (15-min access, 7-day refresh)
- bcrypt Password Hashing (salt rounds 12)
- Multi-Factor Authentication (TOTP)
- Role-Based Access Control (RBAC)
- Field-Level Encryption (AES-256-GCM)
- Rate Limiting (Redis-backed)
- Security Headers (HSTS, CSP, X-Frame-Options)
- Audit Logging with hash chain integrity

---

## Quick Reference

### Getting Started

1. **Access the platform:** `http://localhost:8000` (backend) or frontend URL
2. **Login/Register:** Create account or use existing credentials
3. **Connect Google Drive:** Link your Drive for project management
4. **Start chatting:** Use `/help` to see commands

### Common Workflows

**Estimate a Project:**
```
1. /estimate warehouse 100000
2. Upload blueprints
3. "Extract quantities from these drawings"
4. /cost [extracted items]
```

**Analyze Documents:**
```
1. Upload PDF (drag-drop or + menu)
2. "Summarize this contract"
3. "Extract all payment terms"
4. "Calculate total value"
```

**Generate Code:**
```
1. Switch to Agent Mode
2. "Generate an API endpoint for tracking materials"
3. Review generated code
4. "Deploy to test environment"
```

### Support

- **Documentation:** https://docs.cerebrum.ai
- **API Reference:** http://localhost:8000/docs
- **Health Check:** http://localhost:8000/health
- **Email:** support@cerebrum.ai

---

## Tags

#cerebrum #documentation #overview #layers #chat #commands #cost-estimation #construction #AI #bim

## Related Files

- `README.md` - Platform overview
- `TechSpec.md` - Technical specifications
- `Design_v2.md` - UI/UX design documentation
- `backend/README.md` - Backend API documentation
- `RUNBOOK.md` - Operations and troubleshooting
