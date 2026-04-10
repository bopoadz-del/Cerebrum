# OpenClaw Local/Self-Hosted Setup Guide

## What is OpenClaw?

OpenClaw is an open-source AI coding assistant that can be run locally or self-hosted. It provides an AI-powered development environment similar to GitHub Copilot but with full control over your data.

---

## 🚀 Installation Options

### Option 1: Quick Install (npm)

```bash
# Via official installer (curl)
curl -fsSL https://openclaw.ai/install.cmd -o install.cmd && install.cmd

# Or via npm
npm i -g openclaw

# Start the onboarding
openclaw onboard
```

### Option 2: Docker Deploy (Recommended for Codespaces)

Since we're in a disk-space-constrained environment, Docker deployment is recommended:

```bash
# Clone the repository
git clone https://github.com/openclaw/openclaw.git
cd openclaw

# Copy environment template
cp .env.example .env

# Edit .env with your API keys
# Required: OPENAI_API_KEY or ANTHROPIC_API_KEY
nano .env

# Start the services
docker compose up -d

# Access at
open http://localhost:18789
```

### Option 3: Local Development Setup

```bash
# Clone repository
git clone https://github.com/openclaw/openclaw.git
cd openclaw

# Install dependencies
npm install

# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Run development server
npm run dev

# Access at http://localhost:18789
```

---

## 🔧 Environment Configuration

Edit `.env` file with the following:

```env
# Required: API Keys for AI models
OPENAI_API_KEY=sk-your-openai-key
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key

# Optional: Database (defaults to SQLite)
DATABASE_URL=postgresql://user:pass@localhost:5432/openclaw

# Optional: Redis for caching
REDIS_URL=redis://localhost:6379/0

# Server configuration
PORT=18789
HOST=0.0.0.0

# Feature flags
ENABLE_WEB_SEARCH=true
ENABLE_CODE_EXECUTION=true
```

---

## 🐳 Docker Compose Configuration

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  openclaw:
    image: openclaw/openclaw:latest
    ports:
      - "18789:18789"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - DATABASE_URL=${DATABASE_URL:-sqlite:///data/openclaw.db}
      - REDIS_URL=${REDIS_URL}
    volumes:
      - ./data:/data
    restart: unless-stopped
    
  # Optional: PostgreSQL database
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: openclaw
      POSTGRES_PASSWORD: openclaw_pass
      POSTGRES_DB: openclaw
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped
    
  # Optional: Redis cache
  redis:
    image: redis:7-alpine
    restart: unless-stopped

volumes:
  postgres_data:
```

---

## 🔗 Integration with Cerebrum

To use OpenClaw alongside Cerebrum:

### 1. Run OpenClaw on a different port

```bash
# In openclaw .env
PORT=18789  # Different from Cerebrum's 8000/5173
```

### 2. Configure Cerebrum to use OpenClaw

Add to Cerebrum backend `.env`:

```env
# OpenClaw Integration
OPENCLAW_URL=http://localhost:18789
OPENCLAW_API_KEY=your-openclaw-api-key
```

### 3. Frontend Proxy Configuration

Add to `frontend/vite.config.ts`:

```typescript
export default defineConfig({
  server: {
    proxy: {
      '/openclaw': {
        target: 'http://localhost:18789',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/openclaw/, '')
      }
    }
  }
})
```

---

## 🎯 Using OpenClaw

Once running, OpenClaw provides:

1. **AI Chat Interface** - Natural language coding assistance
2. **Code Completion** - Intelligent autocomplete
3. **Code Review** - AI-powered code review
4. **Documentation** - Auto-generate documentation
5. **Refactoring** - AI-assisted code refactoring

---

## 📚 Resources

- [OpenClaw GitHub](https://github.com/openclaw/openclaw)
- [Documentation](https://docs.openclaw.ai)
- [Discord Community](https://discord.gg/openclaw)

---

## ⚠️ Current Codespace Limitation

Due to disk space constraints in this codespace (we freed up ~4.3GB but still limited), we recommend:

1. **Local Installation**: Install OpenClaw on your local machine
2. **Cloud VM**: Deploy to a cloud VM with more disk space
3. **Wait for Cleanup**: Run after completing Firebase deployment to free more space

---

## 🔄 Alternative: Use OpenClaw Cloud

If self-hosting is not feasible, you can use the managed OpenClaw Cloud service:

1. Sign up at [openclaw.ai](https://openclaw.ai)
2. Get your API key
3. Configure Cerebrum to use the cloud API
