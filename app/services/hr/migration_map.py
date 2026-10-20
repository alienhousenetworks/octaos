"""Backfill people, requisitions, and applications from the flat candidates table.

Does not rewrite a source row's id, name, email, or scorecard.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

STAGE_RANK = {
    "sourced": 0,
    "screened": 1,
    "interviewing": 2,
    "interviewed": 2,
    "offer": 3,
    "offered": 3,
    "accepted": 3,
    "hired": 4,
}
STAGE_NAME = {
    0: "sourced",
    1: "screened",
    2: "interviewing",
    3: "offer",
    4: "hired",
}


def is_real_email(email: Optional[str]) -> bool:
    if email is None:
        return False
    text = email.strip()
    if not text or text.lower() == "n/a":
        return False
    return True


def normalize_role(role: Optional[str]) -> str:
    text = (role or "").strip()
    if not text:
        return "Unspecified role"
    return " ".join(text.split())


def map_stage(status: Optional[str]) -> str:
    key = (status or "sourced").strip().lower()
    rank = STAGE_RANK.get(key, 0)
    return STAGE_NAME[rank]


def backfill_candidates(db: Session) -> Dict[str, int]:
    from app.models.hr import (
        Application,
        ApplicationLegacySource,
        Assessment,
        EvidenceFact,
        HRDocument,
        Inference,
        Interview,
        JobRequisition,
    )
    from sqlalchemy import text

    class CandidateRecord:
        def __init__(self, d: dict):
            self.id = d.get("id")
            self.tenant_id = d.get("tenant_id")
            self.organization_id = d.get("organization_id")
            self.name = d.get("name")
            self.email = d.get("email")
            self.phone = d.get("phone")
            self.role = d.get("role")
            card = d.get("scorecard")
            if isinstance(card, str):
                try:
                    import json
                    card = json.loads(card)
                except Exception:
                    pass
            self.scorecard = card
            self.status = d.get("status")
            self.merged_into_candidate_id = d.get("merged_into_candidate_id")
            self.created_at = d.get("created_at")

    try:
        raw_rows = db.execute(text("""
            SELECT id, tenant_id, organization_id, name, email, phone, role, scorecard, status, merged_into_candidate_id, created_at
            FROM candidates
            ORDER BY created_at ASC NULLS LAST, id ASC
        """)).mappings().all()
    except Exception:
        return {"applications": 0, "assessments": 0, "people": 0}

    if not raw_rows:
        return {"applications": 0, "assessments": 0, "people": 0}

    rows: List[CandidateRecord] = [CandidateRecord(dict(r)) for r in raw_rows]
    created_apps = 0
    created_assessments = 0

    groups: Dict[tuple, List[CandidateRecord]] = defaultdict(list)
    for row in rows:
        if is_real_email(row.email):
            key = (row.tenant_id, row.email.strip().lower())
        else:
            key = (row.tenant_id, f"row:{row.id}")
        groups[key].append(row)

    for members in groups.values():
        survivor = members[0]
        for other in members[1:]:
            if other.merged_into_candidate_id != survivor.id:
                other.merged_into_candidate_id = survivor.id
                db.execute(
                    text("UPDATE candidates SET merged_into_candidate_id = :sid WHERE id = :oid"),
                    {"sid": survivor.id, "oid": other.id}
                )
            if (other.name or "") and other.name != survivor.name:
                pass  # alias fact is written with the assessment below

        by_role: Dict[tuple, List[CandidateRecord]] = defaultdict(list)
        for member in members:
            title = normalize_role(member.role)
            by_role[(member.tenant_id, member.organization_id, title.lower())].append(member)

        for (tenant_id, organization_id, _title_key), sources in by_role.items():
            title = normalize_role(sources[0].role)
            legacy_missing = not (sources[0].role or "").strip()
            opened = min((s.created_at for s in sources if s.created_at), default=datetime.now(timezone.utc))
            salary_text = None
            for source in sources:
                card = source.scorecard or {}
                if isinstance(card, dict) and card.get("salary_expectation") and not salary_text:
                    salary_text = str(card.get("salary_expectation"))

            requisition = (
                db.query(JobRequisition)
                .filter_by(tenant_id=tenant_id, organization_id=organization_id, title=title)
                .first()
            )
            if requisition is None:
                requisition = JobRequisition(
                    tenant_id=tenant_id,
                    organization_id=organization_id,
                    title=title,
                    status="open",
                    headcount_approved=1,
                    opened_at=opened,
                    opened_at_confirmed=False,
                    legacy_opened_at_is_first_candidate=True,
                    legacy_role_missing=legacy_missing,
                    legacy_salary_text=salary_text,
                )
                db.add(requisition)
                db.flush()

            application = (
                db.query(Application)
                .filter_by(tenant_id=tenant_id, candidate_id=survivor.id, requisition_id=requisition.id)
                .first()
            )
            furthest = max(STAGE_RANK.get((s.status or "sourced").strip().lower(), 0) for s in sources)
            stage = STAGE_NAME[furthest]
            hired = any((s.status or "").strip().lower() == "hired" for s in sources)
            if application is None:
                application = Application(
                    tenant_id=tenant_id,
                    candidate_id=survivor.id,
                    requisition_id=requisition.id,
                    current_stage=stage,
                    status="hired" if hired else "active",
                    source="legacy",
                    applied_at=opened,
                    applied_at_confirmed=False,
                    consent_status="unknown_legacy",
                )
                db.add(application)
                db.flush()
                created_apps += 1
            elif STAGE_RANK.get(application.current_stage, 0) < furthest:
                application.current_stage = stage
                if hired:
                    application.status = "hired"

            for source in sources:
                if db.query(ApplicationLegacySource).filter_by(legacy_candidate_id=source.id).first():
                    continue
                db.add(ApplicationLegacySource(
                    application_id=application.id,
                    legacy_candidate_id=source.id,
                    legacy_status=source.status,
                    source_email=source.email,
                ))
                version = (
                    db.query(Assessment)
                    .filter_by(application_id=application.id, kind="resume_screen")
                    .count()
                ) + 1
                assessment = Assessment(
                    tenant_id=tenant_id,
                    application_id=application.id,
                    requisition_id=requisition.id,
                    kind="resume_screen",
                    version=version,
                    status="current" if version == 1 else "superseded",
                )
                if version > 1:
                    current = (
                        db.query(Assessment)
                        .filter_by(application_id=application.id, kind="resume_screen", status="current")
                        .first()
                    )
                    if current:
                        current.status = "superseded"
                    assessment.status = "current"
                db.add(assessment)
                db.flush()
                created_assessments += 1
                _copy_scorecard(db, tenant_id, application.id, assessment.id, source, survivor)
                _copy_interview(db, tenant_id, application, requisition.id, source.scorecard or {})
                _copy_document(db, tenant_id, application.id, source)

            if (sources[-1].name or "") and sources[-1].name != survivor.name:
                latest = (
                    db.query(Assessment)
                    .filter_by(application_id=application.id, kind="resume_screen")
                    .order_by(Assessment.version.desc())
                    .first()
                )
                if latest and not db.query(EvidenceFact).filter_by(assessment_id=latest.id, fact_type="alias").first():
                    db.add(EvidenceFact(
                        tenant_id=tenant_id,
                        assessment_id=latest.id,
                        application_id=application.id,
                        source="legacy_scorecard",
                        fact_type="alias",
                        value=sources[-1].name,
                        evaluative=False,
                        extracted_at=datetime.now(timezone.utc),
                    ))

    db.flush()
    return {"applications": created_apps, "assessments": created_assessments, "people": len(groups)}


def _copy_scorecard(db: Session, tenant_id: str, application_id: str, assessment_id: str, source, survivor) -> None:
    from app.models.hr import EvidenceFact, Inference

    card: Dict[str, Any] = source.scorecard if isinstance(source.scorecard, dict) else {}
    now = source.created_at or datetime.now(timezone.utc)
    facts = []
    skills = card.get("skills") or []
    if isinstance(skills, list):
        for skill in skills:
            facts.append(("skill", str(skill), True))
    for key, fact_type in (
        ("phone", "phone"),
        ("links", "link"),
        ("years", "years_experience"),
        ("experience_years", "years_experience"),
    ):
        if card.get(key):
            facts.append((fact_type, str(card.get(key)), True))
    if source.name and source.id != survivor.id and source.name != survivor.name:
        facts.append(("alias", str(source.name), False))
    for fact_type, value, evaluative in facts:
        db.add(EvidenceFact(
            tenant_id=tenant_id,
            assessment_id=assessment_id,
            application_id=application_id,
            source="legacy_scorecard",
            fact_type=fact_type,
            value=value,
            evaluative=evaluative,
            extracted_at=now,
        ))
    narrative_bits = []
    for key in ("semantic_score", "fit_verdict", "recommendation", "strengths", "gaps", "match_score", "requirements_match"):
        if card.get(key) not in (None, ""):
            narrative_bits.append(f"{key}={card.get(key)}")
    if narrative_bits:
        db.add(Inference(
            assessment_id=assessment_id,
            label="legacy_scorecard",
            narrative="; ".join(narrative_bits)[:4000],
            heuristic_id="legacy_scorecard",
            prompt_version="legacy_scorecard_v1",
            supporting_fact_ids=[],
            model_output_untrusted=True,
        ))


def _copy_interview(db: Session, tenant_id: str, application, requisition_id: str, card: Dict[str, Any]) -> None:
    from app.models.hr import Interview

    if not any(card.get(k) for k in ("meeting_time", "meeting_link", "interview_round", "interviewer_name")):
        return
    link = str(card.get("meeting_link") or "")
    db.add(Interview(
        tenant_id=tenant_id,
        application_id=application.id,
        requisition_id=requisition_id,
        status="legacy_unconfirmed",
        tz="UTC",
        meeting_url=link or None,
        unconfirmed_legacy_link="meet.google.com/octa-" in link,
        round_name=card.get("interview_round"),
    ))


def _copy_document(db: Session, tenant_id: str, application_id: str, source) -> None:
    from app.models.hr import HRDocument

    card = source.scorecard if isinstance(source.scorecard, dict) else {}
    path = card.get("resume_link") or card.get("filename")
    if not path:
        return
    if db.query(HRDocument).filter_by(application_id=application_id, source_path=str(path)).first():
        return
    db.add(HRDocument(
        tenant_id=tenant_id,
        application_id=application_id,
        candidate_id=source.id,
        classification="recruiting",
        source_path=str(path),
        copy_status="pending",
    ))
