# Frontend Agent Instructions

## Scope

This directory contains the Cerebrum frontend: **React 18 + TypeScript** dashboards, **Tailwind CSS + shadcn/ui** components, **Vite** builds, and client-facing portals.

## Applicable Skill

| Skill | Path | Relevant Sections |
|-------|------|-------------------|
| **cerebrum** | `.kimi/skills/cerebrum/SKILL.md` | §8 Webapp Sub-Skill, §10.3 Progress → Dashboard Pipeline, §13 Forbidden Patterns |

## Rules for This Directory

1. **Read the skill before building new dashboard modules.** Follow the component patterns (Progress Tracker, QA/QC Log, Drone Gallery, BIM Viewer, Document Library).
2. **Build must pass with zero errors** (`npm run build`).
3. **No ESLint warnings** (`npm run lint`).
4. **Container builds successfully** (`docker build`).
5. **Offline-first** — core dashboards must function with local SQLite backend when cloud is unavailable.
