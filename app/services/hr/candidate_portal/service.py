"""Candidate Portal Service: Token Security, Dynamic Intake Synthesis, and Session Resolution."""
import hashlib
import secrets
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session

from app.models.base import Tenant
from app.models.verticals import Candidate
from app.models.hr import (
    HRWorkflowInstance,
    HRWorkflowDefinition,
    CandidateEvidence,
    CandidateFieldValue,
    Application,
    JobRequisition,
)
from app.schemas.hr_workflow import (
    SynthesizedIntakeField,
    RequiredDocumentItem,
    CandidatePortalSessionResponse,
    WorkflowGraphSchema,
)
from app.services.hr.workflow.engine import DynamicWorkflowEngine


FRIENDLY_LABELS = {
    "candidate.full_name": ("Full Legal Name", "As it appears on your official government identification", "Jane Doe"),
    "candidate.email": ("Email Address", "We will send your onboarding pack here", "jane.doe@example.com"),
    "candidate.phone": ("Phone Number", "With country code", "+1 555-0199"),
    "candidate.current_address": ("Residential Address", "Your permanent or current primary residence", "123 Market St, Apt 4B"),
    "candidate.date_of_birth": ("Date of Birth", "Required for statutory benefits and tax compliance", "YYYY-MM-DD"),
    "candidate.pan_number": ("PAN / Tax ID Number", "Government issued tax identification number", "ABCDE1234F"),
    "candidate.national_id": ("National Identity Number", "Aadhaar, SSN, or National ID", "1234-5678-9012"),
    "candidate.emergency_contact_name": ("Emergency Contact Name", "Primary contact in case of emergency", "John Doe"),
    "candidate.emergency_contact_phone": ("Emergency Contact Phone", "Contact number", "+1 555-0188"),
}


class CandidatePortalService:
    """Manages tokenized candidate onboarding sessions and dynamic intake synthesis."""

    @staticmethod
    def generate_token_pair(expires_in_days: int = 7) -> Tuple[str, str, datetime]:
        """Generates high-entropy raw token, SHA-256 hash, and expiration timestamp."""
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        expires_at = datetime.now(timezone.utc) + timedelta(days=expires_in_days)
        return raw_token, token_hash, expires_at

    @staticmethod
    def hash_token(raw_token: str) -> str:
        return hashlib.sha256(raw_token.strip().encode("utf-8")).hexdigest()

    @classmethod
    def synthesize_intake_questionnaire(
        cls,
        required_canonical_keys: List[str],
    ) -> List[SynthesizedIntakeField]:
        """Deduplicates and enriches canonical fields required across all documents on the path."""
        synthesized: List[SynthesizedIntakeField] = []
        seen = set()

        for key in required_canonical_keys:
            if key in seen:
                continue
            seen.add(key)
            label, desc, placeholder = FRIENDLY_LABELS.get(
                key,
                (key.split(".")[-1].replace("_", " ").title(), "Required for your onboarding documents", "")
            )
            data_type = "date" if "date" in key or "dob" in key else "string"
            synthesized.append(
                SynthesizedIntakeField(
                    canonical_key=key,
                    label=label,
                    data_type=data_type,
                    is_required=True,
                    description=desc,
                    sample_placeholder=placeholder,
                )
            )

        # Ensure minimal required fields if none extracted
        if not synthesized:
            for default_key in ["candidate.full_name", "candidate.email", "candidate.phone", "candidate.current_address"]:
                label, desc, placeholder = FRIENDLY_LABELS[default_key]
                synthesized.append(
                    SynthesizedIntakeField(
                        canonical_key=default_key,
                        label=label,
                        data_type="string",
                        is_required=True,
                        description=desc,
                        sample_placeholder=placeholder,
                    )
                )

        return synthesized

    @classmethod
    def get_required_documents(cls, context: Dict[str, Any]) -> List[RequiredDocumentItem]:
        """Determines mandatory document evidence items based on role & context."""
        items = [
            RequiredDocumentItem(
                document_category="passport",
                title="Government Photo ID",
                description="Upload a clear scan of your Passport, Aadhaar, or Driver's License",
                is_mandatory=True,
            ),
            RequiredDocumentItem(
                document_category="tax_form",
                title="Tax / Social Security Proof",
                description="Upload PAN Card or National Tax Document",
                is_mandatory=True,
            ),
            RequiredDocumentItem(
                document_category="resume",
                title="Updated Curriculum Vitae (CV)",
                description="Your latest professional résumé",
                is_mandatory=False,
            ),
            RequiredDocumentItem(
                document_category="degree_certificate",
                title="Highest Educational Certificate",
                description="Graduation certificate or degree transcript",
                is_mandatory=False,
            ),
        ]
        return items

    @classmethod
    def resolve_session(
        cls,
        db: Session,
        raw_token: str,
    ) -> Optional[CandidatePortalSessionResponse]:
        """Resolves active candidate onboarding session by high-entropy token hash."""
        token_hash = cls.hash_token(raw_token)
        instance = db.query(HRWorkflowInstance).filter_by(
            candidate_token_hash=token_hash,
            token_revoked=False,
        ).first()

        if not instance:
            return None

        # Check expiration
        now = datetime.now(timezone.utc)
        if instance.token_expires_at.replace(tzinfo=timezone.utc) < now:
            return None

        # Fetch candidate, tenant, and application info
        candidate = db.query(Candidate).filter_by(id=instance.candidate_id).first()
        app = db.query(Application).filter_by(id=instance.application_id).first()
        tenant = db.query(Tenant).filter_by(id=instance.tenant_id).first()
        req = db.query(JobRequisition).filter_by(id=app.requisition_id).first() if app else None

        workflow_def = db.query(HRWorkflowDefinition).filter_by(id=instance.workflow_definition_id).first()
        required_keys = []
        if workflow_def and workflow_def.graph_schema:
            try:
                graph = WorkflowGraphSchema(**workflow_def.graph_schema)
                eval_res = DynamicWorkflowEngine.evaluate_traversal(graph, instance.context_data or {})
                required_keys = eval_res.required_candidate_fields
            except Exception:
                pass

        synthesized_fields = cls.synthesize_intake_questionnaire(required_keys)
        req_docs = cls.get_required_documents(instance.context_data or {})

        # Fetch uploaded evidence
        evidence_records = db.query(CandidateEvidence).filter_by(instance_id=instance.id).all()
        uploaded_evidence = [
            {
                "id": e.id,
                "document_name": e.document_name,
                "document_category": e.document_category,
                "file_sha256": e.file_sha256,
                "uploaded_at": e.uploaded_at.isoformat() if e.uploaded_at else "",
            }
            for e in evidence_records
        ]

        # Fetch existing field values
        field_records = db.query(CandidateFieldValue).filter_by(instance_id=instance.id).all()
        field_values = {f.canonical_key: f.resolved_value or f.candidate_provided_value for f in field_records}

        return CandidatePortalSessionResponse(
            instance_id=instance.id,
            candidate_name=candidate.name if candidate else "Candidate",
            role_title=req.title if req else "Role",
            company_name=tenant.name if tenant else "Company",
            status=instance.current_state,
            expires_at=instance.token_expires_at,
            synthesized_fields=synthesized_fields,
            required_documents=req_docs,
            uploaded_evidence=uploaded_evidence,
            field_values=field_values,
        )
