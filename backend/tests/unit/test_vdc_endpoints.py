"""
Unit tests for VDC endpoints.

Tests cover: in-memory create/get round-trips, BCF export,
clash report export, COBie JSON/zip export, and /me JWT wiring.
"""
import json
import zipfile
import io
import inspect
import pytest
from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI

from app.api.v1.endpoints import vdc as vdc_module


# ─── Minimal FastAPI app with vdc router ──────────────────────────────────────

def _make_app() -> FastAPI:
    app = FastAPI()
    from app.api.v1.endpoints.vdc import router as vdc_router
    app.include_router(vdc_router)
    return app


@pytest.fixture
def app():
    # Clear in-memory stores before each test
    vdc_module._federated_models.clear()
    vdc_module._clash_results.clear()
    vdc_module._validations.clear()
    return _make_app()


@pytest.fixture
async def client(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


# ─── Federated Models ─────────────────────────────────────────────────────────

class TestFederatedModels:
    @pytest.mark.asyncio
    async def test_create_federated_model(self, client):
        resp = await client.post("/vdc/federated-models", json={
            "name": "Tower A", "project_id": "proj-1",
            "discipline_model_ids": ["arch-1", "str-2"],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Tower A"
        assert "id" in data

    @pytest.mark.asyncio
    async def test_get_federated_model_after_create(self, client):
        create = await client.post("/vdc/federated-models", json={
            "name": "Block B", "project_id": "p2", "discipline_model_ids": [],
        })
        model_id = create.json()["id"]
        get = await client.get(f"/vdc/federated-models/{model_id}")
        assert get.status_code == 200
        assert get.json()["id"] == model_id

    @pytest.mark.asyncio
    async def test_get_federated_model_not_found(self, client):
        resp = await client.get("/vdc/federated-models/non-existent-id")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_export_federated_model(self, client):
        create = await client.post("/vdc/federated-models", json={
            "name": "Export Test", "project_id": "p3", "discipline_model_ids": [],
        })
        model_id = create.json()["id"]
        export = await client.post(f"/vdc/federated-models/{model_id}/export/json")
        assert export.status_code == 200
        payload = json.loads(export.content)
        assert payload["model_id"] == model_id

    @pytest.mark.asyncio
    async def test_export_unknown_model_404(self, client):
        resp = await client.post("/vdc/federated-models/bad-id/export/ifc")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_statistics_endpoint(self, client):
        create = await client.post("/vdc/federated-models", json={
            "name": "Stats", "project_id": "p4", "discipline_model_ids": [],
        })
        model_id = create.json()["id"]
        resp = await client.get(f"/vdc/federated-models/{model_id}/statistics")
        assert resp.status_code == 200
        assert resp.json()["model_id"] == model_id


# ─── Clash Detection ──────────────────────────────────────────────────────────

class TestClashDetection:
    @pytest.mark.asyncio
    async def test_run_clash_detection(self, client):
        resp = await client.post("/vdc/clash-detection/run", json={
            "federated_model_id": "fm-1", "tolerance": 0.001,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data
        assert data["clash_count"] == 0

    @pytest.mark.asyncio
    async def test_get_clash_result_round_trip(self, client):
        run = await client.post("/vdc/clash-detection/run", json={"federated_model_id": "fm-2"})
        result_id = run.json()["id"]
        get = await client.get(f"/vdc/clash-detection/results/{result_id}")
        assert get.status_code == 200
        assert get.json()["id"] == result_id

    @pytest.mark.asyncio
    async def test_get_clash_result_not_found(self, client):
        resp = await client.get("/vdc/clash-detection/results/bad-id")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_export_clash_report_html(self, client):
        run = await client.post("/vdc/clash-detection/run", json={"federated_model_id": "fm-3"})
        result_id = run.json()["id"]
        resp = await client.post(f"/vdc/clash-detection/export-report/html?result_id={result_id}")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]

    @pytest.mark.asyncio
    async def test_export_clash_report_csv(self, client):
        run = await client.post("/vdc/clash-detection/run", json={"federated_model_id": "fm-4"})
        result_id = run.json()["id"]
        resp = await client.post(f"/vdc/clash-detection/export-report/excel?result_id={result_id}")
        assert resp.status_code == 200
        assert "text/csv" in resp.headers["content-type"]

    @pytest.mark.asyncio
    async def test_export_clash_report_json(self, client):
        run = await client.post("/vdc/clash-detection/run", json={"federated_model_id": "fm-5"})
        result_id = run.json()["id"]
        resp = await client.post(f"/vdc/clash-detection/export-report/json?result_id={result_id}")
        assert resp.status_code == 200
        payload = json.loads(resp.content)
        assert "id" in payload

    @pytest.mark.asyncio
    async def test_export_bcf_produces_valid_zip(self, client):
        resp = await client.post("/vdc/clash-detection/export-bcf", json={
            "clash_ids": [], "author": "Test", "project_name": "Proj",
        })
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/zip"
        buf = io.BytesIO(resp.content)
        with zipfile.ZipFile(buf) as zf:
            assert "bcf.version" in zf.namelist()

    @pytest.mark.asyncio
    async def test_export_bcf_with_unknown_clash_ids(self, client):
        resp = await client.post("/vdc/clash-detection/export-bcf", json={
            "clash_ids": ["non-existent-clash"],
        })
        assert resp.status_code == 200


# ─── Model Quality ────────────────────────────────────────────────────────────

class TestModelQuality:
    @pytest.mark.asyncio
    async def test_validate_model(self, client):
        resp = await client.post("/vdc/model-quality/validate", json={"model_id": "m-1"})
        assert resp.status_code == 200
        data = resp.json()
        assert "validation_id" in data
        assert data["is_valid"] is True

    @pytest.mark.asyncio
    async def test_get_validation_round_trip(self, client):
        val = await client.post("/vdc/model-quality/validate", json={"model_id": "m-2"})
        vid = val.json()["validation_id"]
        get = await client.get(f"/vdc/model-quality/validations/{vid}")
        assert get.status_code == 200
        assert get.json()["validation_id"] == vid

    @pytest.mark.asyncio
    async def test_get_validation_not_found(self, client):
        resp = await client.get("/vdc/model-quality/validations/bad-id")
        assert resp.status_code == 404


# ─── Digital Handover ─────────────────────────────────────────────────────────

class TestDigitalHandover:
    @pytest.mark.asyncio
    async def test_export_cobie_json(self, client):
        resp = await client.post("/vdc/digital-handover/cobie", json={
            "federated_model_id": "fm-99",
            "project_info": {"name": "Tower X", "project_name": "TX", "site_name": "Riyadh"},
        })
        assert resp.status_code == 200
        data = json.loads(resp.content)
        assert "version" in data
        assert "Facility" in data

    @pytest.mark.asyncio
    async def test_export_cobie_excel_zip(self, client):
        resp = await client.post("/vdc/digital-handover/cobie/excel", json={
            "federated_model_id": "fm-100",
            "project_info": {"name": "Test", "project_name": "TP", "site_name": "Site"},
        })
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/zip"


# ─── stub_users /me with JWT dependency ──────────────────────────────────────

class TestStubUsersMeEndpoint:
    """Verify /me delegates to get_current_user instead of first-user query."""

    def test_me_endpoint_uses_current_user_dependency(self):
        from app.api.v1.endpoints.stub_users import get_current_user_profile
        sig = inspect.signature(get_current_user_profile)
        param_names = list(sig.parameters.keys())
        # After fix: uses current_user from get_current_user, no raw db session
        assert "current_user" in param_names

    def test_me_endpoint_no_longer_needs_db_param(self):
        from app.api.v1.endpoints.stub_users import get_current_user_profile
        sig = inspect.signature(get_current_user_profile)
        assert "db" not in sig.parameters

    def test_me_docstring_no_longer_says_placeholder(self):
        from app.api.v1.endpoints.stub_users import get_current_user_profile
        doc = (get_current_user_profile.__doc__ or "").lower()
        assert "placeholder" not in doc
