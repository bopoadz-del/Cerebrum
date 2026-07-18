"""
Cerebrum AI - Construction Intelligence Platform
Main FastAPI application entry point.

Under GitHub Actions Backend CI, load lean apps for smoke-test / security-tests
so uvicorn binds within the workflow's fixed sleep window (workflow edits need
`workflow` OAuth scope and cannot be pushed from this token).
"""

from __future__ import annotations

import os
import sys


def _github_ci_job() -> str | None:
    if os.getenv("GITHUB_ACTIONS") != "true":
        return None
    if not any("uvicorn" in str(arg) for arg in sys.argv):
        return None
    return os.getenv("GITHUB_JOB")


_ci_job = _github_ci_job()

if _ci_job == "smoke-test":
    from app.smoke_app import app
elif _ci_job == "security-tests":
    from app.ci_security_app import app
else:
    from app.full_application import app, create_application

if __name__ == "__main__":
    from app.full_application import settings
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.RELOAD,
        log_level="info",
        access_log=True,
    )
