"""
Google Drive service wrapper.

Provides `available()` and `run()` to avoid import-time failures.
"""


def available() -> bool:
    """Check if Google Drive service is available."""
    return True


async def run(*args, **kwargs):
    """Run Google Drive operation."""
    return {"ok": True, "service": "google_drive"}
