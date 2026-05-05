# Backend Agent Instructions

## Scope

This directory contains the Cerebrum backend: **FastAPI** APIs, **PostgreSQL/SQLite** databases, **Alembic** migrations, and data ingestion pipelines.

## Applicable Skill

| Skill | Path | Relevant Sections |
|-------|------|-------------------|
| **cerebrum** | `.kimi/skills/cerebrum/SKILL.md` | §9 Backend Sub-Skill, §10.3 Progress → Dashboard Pipeline, §13 Forbidden Patterns |

## Rules for This Directory

1. **Read the skill before modifying APIs or DB schemas.** Follow the tech stack (FastAPI + Pydantic v2 + SQLAlchemy 2.0 / Drizzle) and validation rules (pytest, alembic check, docker-compose up, `/health` returns 200).
2. **No hardcoded secrets** — use `.env` + GitHub Secrets only.
3. **All tests must pass** before any commit (`pytest`).
4. **Migrations must be in sync** — run `alembic check` after schema changes.
5. **Offline-first compatibility** — SQLite fallback must work for Jetson/Termux deployments.
