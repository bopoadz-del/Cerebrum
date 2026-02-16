"""Slack webhook wrapper stub."""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI(title="Slack Webhook Stub")

@app.post("/slack/events")
async def slack_events(req: Request):
    body = await req.json()
    if body.get("type") == "url_verification" and "challenge" in body:
        return JSONResponse({"challenge": body["challenge"]})
    return JSONResponse({"ok": True})
