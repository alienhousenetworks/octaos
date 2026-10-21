"""Automated Unit Tests for Signed Document Verification & Idempotent Employee Provisioning."""

import pytest
from unittest.mock import MagicMock
from app.services.hr.document_verification_service import DocumentVerificationService
from app.services.hr.template_hub.intelligence import TemplateIntelligenceAnalyzer


def test_template_evidence_deduction():
    """Verify that template intelligence deduces required evidence without hardcoding."""
    # Placeholders referencing PAN, passport, degree, and confidentiality clause
    placeholders = ["candidate.pan_number", "candidate.current_address", "education.degree"]
    paragraphs = [
        "The employee agrees to confidentiality and proprietary information secrecy.",
        "Please provide bank account and cancelled cheque for monthly payroll direct deposit.",
    ]
    clauses = ["confidentiality"]

    reqs = TemplateIntelligenceAnalyzer.deduce_required_candidate_documents(
        placeholders=placeholders,
        paragraphs_text=paragraphs,
        detected_clauses=clauses,
    )

    categories = {r["document_category"] for r in reqs}
    assert "passport" in categories
    assert "tax_form" in categories
    assert "degree_certificate" in categories
    assert "bank_proof" in categories
    assert "signed_nda" in categories


def test_document_verification_corrupt_file():
    """Verify corrupt or non-PDF files are BLOCKED."""
    corrupt_bytes = b"not a real pdf file at all"
    report = DocumentVerificationService.verify_document_bytes(corrupt_bytes, "corrupt.pdf")
    assert report["status"] == "BLOCKED"
    assert "MISSING_PDF_HEADER" in report["tamper_flags"]


def test_document_verification_digital_pki():
    """Verify cryptographic PKI signatures are detected and graded ELIGIBLE_FOR_APPROVAL."""
    # Synthetic PDF payload with /ByteRange and /Contents
    pki_pdf = (
        b"%PDF-1.7\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R >>\nendobj\n"
        b"4 0 obj\n<< /Type /Sig /Filter /Adobe.PPKLite /SubFilter /adbe.pkcs7.detached "
        b"/ByteRange [0 100 200 300] /Contents <0123456789ABCDEF> >>\nendobj\n"
        b"%%EOF\n"
    )

    report = DocumentVerificationService.verify_document_bytes(pki_pdf, "signed_agreement.pdf")
    assert report["checks"]["valid_pdf_header"] is True
    assert report["checks"]["digital_pki_detected"] is True
    assert report["has_digital_signature"] is True
    assert report["status"] == "ELIGIBLE_FOR_APPROVAL"
    assert len(report["pki_details"]) == 1


def test_document_verification_electronic_signature_widget():
    """Verify visual/electronic widget signatures are detected."""
    visual_pdf = (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Annot /Subtype /Widget /FT /Sig /T (CandidateSignature) >>\nendobj\n"
        b"%%EOF\n"
    )

    report = DocumentVerificationService.verify_document_bytes(visual_pdf, "offer_signed.pdf")
    assert report["checks"]["valid_pdf_header"] is True
    assert report["checks"]["visual_signature_detected"] is True
    assert report["has_visual_signature"] is True
    assert report["status"] in ("ELIGIBLE_FOR_APPROVAL", "REVIEW_REQUIRED")


def test_document_verification_tamper_detection():
    """Verify when key contract terms are missing or altered, document is flagged."""
    sample_pdf = (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /FT /Sig /T (SignatureField) >>\nendobj\n"
        b"stream\nCandidate: John Doe. Role: Janitor. Salary: $10\nendstream\n"
        b"%%EOF\n"
    )
    expected_snippets = ["Senior Lead Architect", "$250,000"]
    report = DocumentVerificationService.verify_document_bytes(
        sample_pdf,
        "tampered.pdf",
        expected_text_snippets=expected_snippets,
    )
    assert report["status"] == "BLOCKED"
    assert "KEY_CONTRACT_TERMS_ALTERED_OR_MISSING" in report["tamper_flags"]


def test_employee_provisioning_idempotency():
    """Verify that provisioning an employee twice returns existing profile without duplicate records."""
    from datetime import datetime, timezone
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.models.base import Base
    from app.models.hr import TenantEmployeeSequence, HRWorkflowInstance, Application, HROutboxEvent
    from app.models.verticals import Candidate
    from app.models.hr_core import EmployeeProfile, Department
    from app.services.hr.employee_provisioning_service import EmployeeProvisioningService

    engine = create_engine("sqlite:///:memory:")
    # Create minimal tables
    TenantEmployeeSequence.__table__.create(engine)
    Application.__table__.create(engine)
    HRWorkflowInstance.__table__.create(engine)
    Candidate.__table__.create(engine)
    EmployeeProfile.__table__.create(engine)
    Department.__table__.create(engine)
    HROutboxEvent.__table__.create(engine)

    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    tenant_id = "tenant-test-123"
    instance_id = "inst-test-456"
    candidate_id = "cand-test-789"
    app_id = "app-test-1"

    # Seed candidate
    cand = Candidate(
        id=candidate_id,
        tenant_id=tenant_id,
        name="Ada Lovelace",
        email="ada@example.com",
        phone="+1234567890",
    )
    db.add(cand)

    app = Application(
        id=app_id,
        tenant_id=tenant_id,
        candidate_id=candidate_id,
        requisition_id="req-test-1",
        status="offered",
        current_stage="offered",
    )
    db.add(app)

    # Seed instance
    inst = HRWorkflowInstance(
        id=instance_id,
        tenant_id=tenant_id,
        application_id=app_id,
        candidate_id=candidate_id,
        workflow_definition_id="wf-1",
        current_state="signed_documents_received",
        candidate_token_hash="hash-abc-123",
        token_expires_at=datetime.now(timezone.utc),
        context_data={
            "company_fields": {
                "department": "Engineering",
                "role_title": "Principal Architect",
            }
        },
    )
    db.add(inst)
    db.commit()

    # 1st Provisioning call
    res1 = EmployeeProvisioningService.provision_employee_from_onboarding(
        db=db,
        tenant_id=tenant_id,
        instance_id=instance_id,
    )
    assert res1["idempotent"] is False
    assert res1["employee_number"] == "EMP-0001"
    assert res1["full_name"] == "Ada Lovelace"
    assert res1["department"] == "Engineering"

    # 2nd Provisioning call (should be idempotent)
    res2 = EmployeeProvisioningService.provision_employee_from_onboarding(
        db=db,
        tenant_id=tenant_id,
        instance_id=instance_id,
    )
    assert res2["idempotent"] is True
    assert res2["employee_id"] == res1["employee_id"]
    assert res2["employee_number"] == "EMP-0001"

    # Verify database has exactly 1 employee profile
    total_profiles = db.query(EmployeeProfile).filter_by(tenant_id=tenant_id).count()
    assert total_profiles == 1
