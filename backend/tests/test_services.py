import pytest

@pytest.mark.asyncio
async def test_service_wrappers_import_and_run():
    from backend.services import analytics_engine, rag_engine, google_drive

    assert analytics_engine.available() is True
    r = await analytics_engine.run(1, a=2)
    assert r["ok"] is True
    assert r["service"] == "analytics_engine"

    r2 = await rag_engine.run("q")
    assert r2["ok"] is True

    r3 = await google_drive.run()
    assert r3["ok"] is True


def test_compat_routers_import():
    from backend.api import get_compat_router
    router = get_compat_router()
    assert router is not None
