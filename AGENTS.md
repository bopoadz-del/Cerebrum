# Cerebrum — Agent Instructions

## Project Scope

This is the **Cerebrum** project — a construction-tech stack covering BOQ, QA/QC, BIM, drone analytics, and universal artifact production (xlsx, pdf, docx, pptx, webapp, backend).

## Available Skills

| Skill | Path | Description |
|-------|------|-------------|
| **cerebrum** | `.kimi/skills/cerebrum/SKILL.md` | Universal Construction & Deliverable Agent skill. Covers deliverable matrix, validation layers, and domain-specific workflows for construction + software artifacts. |

## How to Use

When working on any deliverable (Excel BOQ, PDF report, DOCX contract, PPTX pitch, webapp dashboard, or backend API), **read the `cerebrum` skill first** to follow the project's standardized validation loops, style systems, and forbidden patterns.

## Quick Reference

- **Validation is mandatory** — every artifact must pass its domain-specific checks before commit.
- **Excel formulas only** — no static values for derived outputs.
- **Commit before deploy** — Render filesystem is ephemeral; GitHub is the source of truth.
- **Offline-first** — core workflows must run on Jetson Orin/Nano, Termux, and Windows.
