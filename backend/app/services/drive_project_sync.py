from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from googleapiclient.discovery import build
from sqlalchemy.orm import Session

from app.models.google_drive_project import GoogleDriveProject
from app.models.integration import IntegrationProvider, IntegrationToken
from app.models.project import Project, ProjectType
from app.services.drive_project_detector import DetectedProjectType, FolderSummary, detect_project
from app.services.google_drive_service import GoogleDriveService


def _map_project_type(t: DetectedProjectType) -> ProjectType:
    try:
        return ProjectType(str(t))
    except Exception:
        return ProjectType.UNKNOWN


def _list_folders_root(drive) -> List[Dict[str, Any]]:
    q = "trashed=false and 'root' in parents and mimeType='application/vnd.google-apps.folder'"
    res = drive.files().list(
        pageSize=200,
        q=q,
        orderBy="modifiedTime desc",
        fields="files(id,name,modifiedTime)",
    ).execute()
    return res.get("files", [])


def _list_children(drive, folder_id: str, page_size: int = 250) -> List[Dict[str, Any]]:
    q = f"trashed=false and '{folder_id}' in parents"
    res = drive.files().list(
        pageSize=page_size,
        q=q,
        orderBy="modifiedTime desc",
        fields="files(id,name,mimeType,modifiedTime,size)",
    ).execute()
    return res.get("files", [])


def _indexable_drive_file(mime: str, name: str) -> bool:
    # Minimal demo filter: index documents that likely contain text.
    # (Your document_parser already handles Google Docs export + PDFs in memory.)
    if mime in (
        "application/pdf",
        "text/plain",
        "text/markdown",
        "application/vnd.google-apps.document",
        "application/vnd.google-apps.presentation",
        "application/vnd.google-apps.spreadsheet",
    ):
        return True
    lower = (name or "").lower()
    return lower.endswith((".md", ".txt", ".pdf", ".csv"))


def discover_and_upsert_drive_projects(
    db: Session,
    user_id: uuid.UUID,
    *,
    min_score: float = 2.0,
    max_root_folders: int = 200,
    max_children_per_folder: int = 250,
    index_now: bool = True,
    max_files_per_project: int = 50,
) -> Dict[str, Any]:
    """
    Folder-first metadata scan:
      - list root folders (My Drive)
      - shallow list children for anchors
      - run detector
      - upsert Project + GoogleDriveProject mapping

    If index_now=True:
      - select indexable child files (capped)
      - queue Celery batch indexing using existing process_drive_file_batch()

    Returns counts + ids for UI/debug.
    """
    # Use raw query to avoid column mismatch issues during migrations
    from sqlalchemy import text
    result = db.execute(
        text("""
            SELECT access_token, refresh_token, expiry, scopes, token_uri, client_id, client_secret
            FROM integration_tokens 
            WHERE user_id = :user_id 
            AND service = 'google_drive' 
            AND is_active = true
            LIMIT 1
        """),
        {"user_id": str(user_id)}
    )
    row = result.fetchone()
    
    if not row:
        return {"status": "error", "message": "Google Drive not connected", "detected": 0, "updated": 0}
    
    # Create a simple object to hold token data
    class SimpleToken:
        pass
    
    tok = SimpleToken()
    tok.access_token = row[0]
    tok.refresh_token = row[1]
    tok.expiry = row[2]
    tok.scopes = row[3]
    tok.token_uri = row[4] or "https://oauth2.googleapis.com/token"
    tok.client_id = row[5]
    tok.client_secret = row[6]

    svc = GoogleDriveService(db)
    creds = svc.get_credentials(user_id)
    if not creds:
        return {"status": "error", "message": "Google Drive credentials unavailable", "detected": 0, "updated": 0}

    drive = build("drive", "v3", credentials=creds, cache_discovery=False)

    root_folders = _list_folders_root(drive)[:max_root_folders]

    detected = 0
    created_projects = 0
    updated_mappings = 0
    created_mappings = 0
    queued_index_jobs = 0
    mapping_ids: List[str] = []
    project_ids: List[str] = []

    for folder in root_folders:
        folder_id = folder.get("id")
        folder_name = folder.get("name") or "Untitled"

        children = _list_children(drive, folder_id, page_size=max_children_per_folder)
        child_names = tuple(c.get("name", "") for c in children if c.get("name"))
        child_mimes = tuple(c.get("mimeType", "") for c in children if c.get("mimeType"))

        summary = FolderSummary(
            folder_id=folder_id,
            folder_name=folder_name,
            child_names=child_names,
            child_mime_types=child_mimes,
            modified_time_iso=folder.get("modifiedTime"),
        )
        dp = detect_project(summary)

        if dp.score < min_score:
            continue

        detected += 1
        ptype = _map_project_type(dp.project_type)

        mapping: Optional[GoogleDriveProject] = db.query(GoogleDriveProject).filter(
            GoogleDriveProject.user_id == user_id,
            GoogleDriveProject.root_folder_id == folder_id,
        ).first()

        reasons_payload = [{"signal": r.signal, "weight": r.weight, "detail": r.detail} for r in dp.reasons]

        if mapping is None:
            proj = Project(
                name=folder_name,
                type=ptype,
                tags=list(dp.tags),
                meta={
                    "source": "google_drive",
                    "root_folder_id": folder_id,
                    "confidence": dp.confidence,
                    "score": dp.score,
                    "reasons": reasons_payload,
                    "entry_points": list(dp.entry_points),
                },
            )
            db.add(proj)
            db.flush()  # assigns proj.id

            mapping = GoogleDriveProject(
                user_id=user_id,
                project_id=proj.id,
                root_folder_id=folder_id,
                root_folder_name=folder_name,
                score=float(dp.score),
                confidence=float(dp.confidence),
                reasons=reasons_payload,
                entry_points=list(dp.entry_points),
                tags=list(dp.tags),
                indexing_status="idle",
                indexing_progress={"indexed": 0, "total": 0},
                last_scanned_at=datetime.utcnow(),
                deleted=False,
            )
            db.add(mapping)

            created_projects += 1
            created_mappings += 1
            project_ids.append(str(proj.id))
        else:
            mapping.root_folder_name = folder_name
            mapping.score = float(dp.score)
            mapping.confidence = float(dp.confidence)
            mapping.reasons = reasons_payload
            mapping.entry_points = list(dp.entry_points)
            mapping.tags = list(dp.tags)
            mapping.last_scanned_at = datetime.utcnow()
            mapping.deleted = False

            proj = db.query(Project).filter(Project.id == mapping.project_id).first()
            if proj:
                proj.name = folder_name
                proj.type = ptype
                proj.tags = list(dp.tags)
                meta = dict(proj.meta or {})
                meta.update(
                    {
                        "source": "google_drive",
                        "root_folder_id": folder_id,
                        "confidence": dp.confidence,
                        "score": dp.score,
                        "reasons": reasons_payload,
                        "entry_points": list(dp.entry_points),
                    }
                )
                proj.meta = meta

            updated_mappings += 1
            project_ids.append(str(mapping.project_id))

        # --- MAGIC DEMO: queue indexing now ---
        if index_now:
            # only immediate child files (not folders), indexable types only, capped
            file_ids: List[str] = []
            for c in children:
                mime = c.get("mimeType") or ""
                if mime == "application/vnd.google-apps.folder":
                    continue
                if not _indexable_drive_file(mime, c.get("name") or ""):
                    continue
                fid = c.get("id")
                if fid:
                    file_ids.append(fid)
                if len(file_ids) >= max_files_per_project:
                    break

            if file_ids:
                # Update UI status before enqueue
                mapping.indexing_status = "queued"
                mapping.indexing_progress = {"indexed": 0, "total": len(file_ids)}

                # Defer import to avoid circular imports at module import time
                from app.tasks import process_drive_file_batch

                process_drive_file_batch.delay(
                    file_ids=file_ids,
                    user_id=str(user_id),
                    access_token=tok.access_token,
                )
                queued_index_jobs += 1

        mapping_ids.append(str(mapping.id))

    db.commit()

    return {
        "status": "success",
        "detected": detected,
        "created_projects": created_projects,
        "created_mappings": created_mappings,
        "updated_mappings": updated_mappings,
        "queued_index_jobs": queued_index_jobs,
        "mapping_ids": mapping_ids[:20],
        "project_ids": project_ids[:20],
    }
