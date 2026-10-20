"""Public Candidate Portal Endpoints: Secure, Tokenized Candidate Onboarding."""
import hashlib
from datetime import datetime, timezone
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session

from app.api import deps
from app.models.hr import (
    HRWorkflowInstance,
    CandidateEvidence,
    CandidateFieldValue,
)
from app.schemas.hr_workflow import (
    CandidatePortalSessionResponse,
    CandidateIntakeSubmitRequest,
)
from app.services.hr.candidate_portal.service import CandidatePortalService
from app.services.hr.extraction.reconciliation import EvidenceReconciliationService
from app.services.hr.document_store import DocumentStore


router = APIRouter()


@router.get("/session/{token}", response_model=CandidatePortalSessionResponse)
def get_candidate_session(
    token: str,
    db: Session = Depends(deps.get_db),
):
    """Public endpoint resolving candidate onboarding session, synthesized fields, and checklist."""
    session_data = CandidatePortalService.resolve_session(db, token)
    if not session_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid, expired, or revoked candidate access token.",
        )
    return session_data


@router.post("/session/{token}/upload")
async def upload_candidate_evidence(
    token: str,
    category: str = Form(...),  # 'passport', 'national_id', 'resume', 'tax_form', 'degree_certificate'
    file: UploadFile = File(...),
    db: Session = Depends(deps.get_db),
):
    """Secure document upload for candidate proofs with simulated OCR extraction & provenance."""
    token_hash = CandidatePortalService.hash_token(token)
    instance = db.query(HRWorkflowInstance).filter_by(
        candidate_token_hash=token_hash,
        token_revoked=False,
    ).first()
    if not instance:
        raise HTTPException(status_code=401, detail="Invalid candidate token")

    content_bytes = await file.read()
    filename = file.filename or f"{category}.pdf"
    file_sha = hashlib.sha256(content_bytes).hexdigest()

    # Save to isolated tenant document store
    storage_key = DocumentStore.save(
        tenant_id=instance.tenant_id,
        filename=filename,
        content=content_bytes,
        prefix="candidate_evidence",
    )

    # Perform OCR evidence extraction
    extracted_fields = EvidenceReconciliationService.simulate_document_ocr_extraction(
        document_category=category,
        filename=filename,
        content_bytes=content_bytes,
    )

    evidence = CandidateEvidence(
        tenant_id=instance.tenant_id,
        instance_id=instance.id,
        document_name=filename,
        document_category=category,
        storage_key=storage_key,
        file_sha256=file_sha,
        mime_type=file.content_type or "application/octet-stream",
        extracted_data=extracted_fields,
    )
    db.add(evidence)
    db.commit()
    db.refresh(evidence)

    return {
        "status": "uploaded",
        "evidence_id": evidence.id,
        "extracted_fields": extracted_fields,
    }


@router.post("/session/{token}/submit")
def submit_candidate_questionnaire(
    token: str,
    req: CandidateIntakeSubmitRequest,
    db: Session = Depends(deps.get_db),
):
    """Submits candidate-provided intake form data and marks instance status ready for extraction."""
    token_hash = CandidatePortalService.hash_token(token)
    instance = db.query(HRWorkflowInstance).filter_by(
        candidate_token_hash=token_hash,
        token_revoked=False,
    ).first()
    if not instance:
        raise HTTPException(status_code=401, detail="Invalid candidate token")

    # Save candidate field values
    for canonical_key, val in req.field_values.items():
        field_rec = db.query(CandidateFieldValue).filter_by(
            instance_id=instance.id,
            canonical_key=canonical_key,
        ).first()

        if not field_rec:
            field_rec = CandidateFieldValue(
                tenant_id=instance.tenant_id,
                instance_id=instance.id,
                canonical_key=canonical_key,
                candidate_provided_value=val,
            )
            db.add(field_rec)
        else:
            field_rec.candidate_provided_value = val

    instance.current_state = "intake_submitted"
    db.commit()

    # Automatically trigger evidence reconciliation
    summary = EvidenceReconciliationService.reconcile_instance_data(db, instance.id)
    if not summary.is_blocked:
        instance.current_state = "review_ready"
        db.commit()

    return {
        "status": "submitted",
        "next_state": instance.current_state,
        "conflicts_detected": summary.conflict_count,
    }
