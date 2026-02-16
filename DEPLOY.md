# Cerebrum AI - Deployment Guide

This guide covers deploying Cerebrum AI to various platforms.

## Quick Start - Local Development

```bash
# 1. Clone and navigate
cd /mnt/okcomputer/output

# 2. Copy environment file
cp backend/.env.example backend/.env
# Edit backend/.env with your values

# 3. Start all services
docker-compose up -d

# 4. Run migrations
docker-compose exec backend alembic upgrade head

# 5. Access the application
# Frontend: http://localhost:5173
# API: http://localhost:8000
# API Docs: http://localhost:8000/api/docs
# Flower: http://localhost:5555
```

## Deploy to Render (One-Click)

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy)

1. Fork this repository to your GitHub account
2. Click the "Deploy to Render" button above
3. Follow the prompts to connect your GitHub account
4. Render will automatically:
   - Create a PostgreSQL database
   - Create a Redis instance
   - Deploy the backend API
   - Deploy Celery workers
   - Deploy the frontend

### Manual Render Setup

If you prefer manual configuration:

1. **Create PostgreSQL Database**
   - Go to Render Dashboard → New → PostgreSQL
   - Name: `cerebrum-db`
   - Plan: Starter ($7/month)

2. **Create Redis Instance**
   - Go to Render Dashboard → New → Redis
   - Name: `cerebrum-redis`
   - Plan: Starter ($10/month)

3. **Deploy Backend**
   - New → Web Service
   - Connect your GitHub repo
   - Name: `cerebrum-api`
   - Root Directory: `backend`
   - Environment: `Python 3`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - Add environment variables from `.env.example`

4. **Deploy Workers**
   - New → Background Worker
   - Name: `cerebrum-worker-fast`
   - Root Directory: `backend`
   - Start Command: `celery -A app.workers.celery_config worker -Q celery_fast -n fast@%h`

   - New → Background Worker
   - Name: `cerebrum-worker-slow`
   - Root Directory: `backend`
   - Start Command: `celery -A app.workers.celery_config worker -Q celery_slow -n slow@%h`

5. **Deploy Frontend**
   - New → Static Site
   - Name: `cerebrum-frontend`
   - Root Directory: `frontend`
   - Build Command: `npm install && npm run build`
   - Publish Directory: `dist`

## Environment Variables

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+asyncpg://user:pass@host/db` |
| `REDIS_URL` | Redis connection string | `redis://host:6379/0` |
| `SECRET_KEY` | JWT signing key (min 32 chars) | Generate with `openssl rand -hex 32` |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DEBUG` | Enable debug mode | `false` |
| `CORS_ORIGINS` | Allowed CORS origins | `http://localhost:5173` |
| `SENTRY_DSN` | Sentry error tracking | - |
| `OPENAI_API_KEY` | OpenAI API access | - |

## Health Checks

The application exposes health endpoints:

- `GET /health` - Overall health status
- `GET /health/live` - Kubernetes liveness probe
- `GET /health/ready` - Kubernetes readiness probe
- `GET /health/startup` - Kubernetes startup probe

## Troubleshooting

### Database Connection Issues

```bash
# Check if PostgreSQL is running
docker-compose ps postgres

# Check logs
docker-compose logs postgres

# Test connection
docker-compose exec postgres psql -U cerebrum -d cerebrum -c "SELECT 1"
```

### Redis Connection Issues

```bash
# Check if Redis is running
docker-compose ps redis

# Test connection
docker-compose exec redis redis-cli ping
```

### Worker Issues

```bash
# Check worker logs
docker-compose logs worker-fast
docker-compose logs worker-slow

# Restart workers
docker-compose restart worker-fast worker-slow
```

### Migration Issues

```bash
# Reset migrations (WARNING: destroys data)
docker-compose exec backend alembic downgrade base
docker-compose exec backend alembic upgrade head

# Check current version
docker-compose exec backend alembic current
```

## Production Checklist

- [ ] Change default `SECRET_KEY`
- [ ] Set `DEBUG=false`
- [ ] Configure `CORS_ORIGINS` for your domain
- [ ] Enable Sentry error tracking
- [ ] Set up SSL/TLS certificates
- [ ] Configure backup strategy for database
- [ ] Set up monitoring and alerting
- [ ] Review and adjust rate limits
- [ ] Enable audit logging
- [ ] Configure log aggregation

## Support

For issues and questions:
- GitHub Issues: https://github.com/cerebrum-ai/cerebrum/issues
- Documentation: https://docs.cerebrum.ai
