from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple


# Keep this independent from SQLAlchemy models.
# We'll map to your ProjectType enum in Step 2.
class DetectedProjectType(str):
    SOFTWARE_REPO = "software_repo"
    CLIENT_CONSULTING = "client_consulting"
    JOB_APPLICATION = "job_application"
    LEGAL_FINANCE = "legal_finance"
    RESEARCH_NOTES = "research_notes"
    DESIGN_MEDIA = "design_media"
    GENERAL_PROJECT = "general_project"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class Evidence:
    signal: str
    weight: float
    detail: Optional[str] = None


@dataclass(frozen=True)
class FolderSummary:
    """
    Metadata-only summary of a folder plus (optional) shallow children listing.
    """
    folder_id: str
    folder_name: str
    child_names: Tuple[str, ...] = ()
    child_mime_types: Tuple[str, ...] = ()
    modified_time_iso: Optional[str] = None


@dataclass(frozen=True)
class DetectedProject:
    folder_id: str
    folder_name: str
    score: float
    confidence: float
    project_type: DetectedProjectType
    reasons: Tuple[Evidence, ...]
    entry_points: Tuple[str, ...]
    tags: Tuple[str, ...]


# ----------------------------
# Heuristics (tunable constants)
# ----------------------------

FOLDER_HINTS: Tuple[Tuple[str, float], ...] = (
    ("project", 1.0),
    ("client", 1.2),
    ("proposal", 1.2),
    ("contract", 1.2),
    ("sow", 1.1),
    ("invoice", 0.9),
    ("repo", 1.0),
    ("src", 0.6),
    ("docs", 0.5),
    ("design", 0.7),
    ("research", 0.6),
    ("notes", 0.4),
)

ANCHOR_PATTERNS: Tuple[Tuple[re.Pattern, float, str], ...] = (
    (re.compile(r"^readme(\..*)?$", re.I), 2.0, "README"),
    (re.compile(r"^package\.json$", re.I), 2.0, "Node project"),
    (re.compile(r"^pyproject\.toml$", re.I), 2.0, "Python project"),
    (re.compile(r"^requirements(\.txt)?$", re.I), 1.5, "Python deps"),
    (re.compile(r"^dockerfile$", re.I), 1.5, "Docker"),
    (re.compile(r"^\.github$", re.I), 0.8, "GitHub config"),
    (re.compile(r".*proposal.*\.(docx|pdf)$", re.I), 1.8, "Proposal"),
    (re.compile(r".*\b(sow|statement of work)\b.*\.(docx|pdf)$", re.I), 2.0, "SOW"),
    (re.compile(r".*\bcontract\b.*\.(docx|pdf)$", re.I), 2.0, "Contract"),
    (re.compile(r".*\binvoice\b.*\.(pdf|xlsx|csv)$", re.I), 1.3, "Invoice"),
    (re.compile(r".*\.ipynb$", re.I), 1.0, "Notebook"),
)


def _sigmoid(x: float) -> float:
    # stable sigmoid for mapping scores to (0,1)
    import math
    if x >= 0:
        z = math.exp(-x)
        return 1.0 / (1.0 + z)
    z = math.exp(x)
    return z / (1.0 + z)


def detect_project(summary: FolderSummary) -> DetectedProject:
    """
    Returns a DetectedProject with:
      - score: raw heuristic sum
      - confidence: sigmoid(score - 2.0) so score≈2 => ~0.5
      - reasons: explainable evidence
      - entry_points: likely key files
    """
    name_l = (summary.folder_name or "").lower()

    score = 0.0
    reasons: List[Evidence] = []
    entry_points: List[str] = []
    tags: List[str] = []

    # folder name hints
    for kw, w in FOLDER_HINTS:
        if kw in name_l:
            score += w
            reasons.append(Evidence("folder_name_hint", w, f"matched '{kw}'"))

    # anchor files
    for child in summary.child_names:
        for pat, w, label in ANCHOR_PATTERNS:
            if pat.match(child) or pat.search(child):
                score += w
                reasons.append(Evidence("anchor_file", w, f"{label}: {child}"))
                entry_points.append(child)

    # type inference (lightweight)
    child_join = " ".join(summary.child_names).lower()

    ptype = DetectedProjectType.UNKNOWN
    if any(x in child_join for x in ("pyproject.toml", "requirements.txt", "setup.py", "package.json", ".ipynb", "src")) or "repo" in name_l:
        ptype = DetectedProjectType.SOFTWARE_REPO
        tags.append("code")
    elif any(x in child_join for x in ("proposal", "sow", "contract", "invoice")) or "client" in name_l:
        ptype = DetectedProjectType.CLIENT_CONSULTING
        tags.append("client")
    elif any(x in child_join for x in ("resume", "cv", "cover letter")) or "job" in name_l:
        ptype = DetectedProjectType.JOB_APPLICATION
        tags.append("career")
    elif any(x in child_join for x in ("tax", "bank", "statement", "receipt")) or "finance" in name_l:
        ptype = DetectedProjectType.LEGAL_FINANCE
        tags.append("finance")
    elif any(x in child_join for x in ("paper", "literature", "notes", "bib")) or "research" in name_l:
        ptype = DetectedProjectType.RESEARCH_NOTES
        tags.append("research")
    elif any(x in child_join for x in ("figma", "psd", "sketch", ".ai", ".png", ".jpg", ".jpeg")) or "design" in name_l:
        ptype = DetectedProjectType.DESIGN_MEDIA
        tags.append("design")
    else:
        # If it has enough project-ish signals, call it a general project
        ptype = DetectedProjectType.GENERAL_PROJECT if score >= 2.0 else DetectedProjectType.UNKNOWN

    confidence = max(0.0, min(1.0, _sigmoid(score - 2.0)))

    # de-dupe while keeping order
    def _dedupe(xs: Sequence[str]) -> Tuple[str, ...]:
        seen = set()
        out: List[str] = []
        for x in xs:
            if x not in seen:
                seen.add(x)
                out.append(x)
        return tuple(out)

    return DetectedProject(
        folder_id=summary.folder_id,
        folder_name=summary.folder_name,
        score=score,
        confidence=confidence,
        project_type=ptype,
        reasons=tuple(reasons),
        entry_points=_dedupe(entry_points),
        tags=_dedupe(tags),
    )
