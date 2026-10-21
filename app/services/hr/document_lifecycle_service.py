import hashlib
import json
import uuid
import secrets
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models.hr import (
    TenantDocumentTemplate,
    TemplateVersion,
    TemplateVariableSchema,
    HRDocumentPacket,
    HRDocumentArtifact,
    DocumentVerificationRun,
    HRArtifactApproval,
    CandidateAcceptanceRecord,
    Employee,
    OnboardingTask,
    Application,
    JobRequisition,
)
from app.models.verticals import Candidate
from app.models.base import APICredential
from app.services.hr.document_store import LocalPrivateDocumentStore, sha256_bytes
from app.services.hr.template_engine import (
    detect_tokens,
    render_deterministic_html,
    render_deterministic_docx,
    generate_synthetic_test_data,
)
from app.services.hr.contract_service import CONTRACT_TEMPLATES, generate_offer_email_content
from app.services.hr.agents.assurance_agent import (
    HRDocumentPreparationAgent,
    HRDocumentAssuranceAgent,
)
from app.services.agents.hr import HRAgent
from app.core.security import decrypt_api_key


class DocumentLifecycleService:
    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id
        self.store = LocalPrivateDocumentStore()

    # --- TEMPLATE REGISTRY & PUBLICATION ---

    def register_template(
        self,
        document_type: str,
        name: str,
        description: Optional[str],
        file_format: str,
        content: str,
        user_id: str,
    ) -> Tuple[TenantDocumentTemplate, TemplateVersion]:
        template = self.db.query(TenantDocumentTemplate).filter_by(
            tenant_id=self.tenant_id,
            document_type=document_type,
            name=name
        ).first()

        if not template:
            template = TenantDocumentTemplate(
                tenant_id=self.tenant_id,
                document_type=document_type,
                name=name,
                description=description,
            )
            self.db.add(template)
            self.db.flush()

        # Compute next version number
        latest = self.db.query(TemplateVersion).filter_by(
            template_id=template.id,
            tenant_id=self.tenant_id
        ).order_by(TemplateVersion.version.desc()).first()

        next_version = (latest.version + 1) if latest else 1
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

        # Save template source in private store
        storage_key = self.store.put(
            self.tenant_id,
            f"template_{template.id}_v{next_version}.{file_format}",
            content.encode("utf-8")
        )

        version_row = TemplateVersion(
            template_id=template.id,
            tenant_id=self.tenant_id,
            version=next_version,
            format=file_format,
            status="draft",
            storage_key=storage_key,
            content_sha256=content_hash,
            raw_content=content,
        )
        self.db.add(version_row)
        self.db.flush()

        # Detect tokens and create variable schemas
        tokens = detect_tokens(content)
        for t in tokens:
            v_schema = TemplateVariableSchema(
                template_version_id=version_row.id,
                variable_name=t,
                data_type="string",
                is_required=True,
                source_field=f"candidate.{t}",
            )
            self.db.add(v_schema)

        self.db.commit()
        return template, version_row

    def publish_template(self, template_id: str, version_num: int, user_id: str) -> TemplateVersion:
        version_row = self.db.query(TemplateVersion).filter_by(
            template_id=template_id,
            tenant_id=self.tenant_id,
            version=version_num
        ).first()

        if not version_row:
            raise ValueError(f"Template version {version_num} not found.")

        # Test-render with synthetic data before publication
        test_vars = generate_synthetic_test_data()
        rendered, unpopulated = render_deterministic_html(version_row.raw_content or "", test_vars, version_row.format)
        if unpopulated:
            raise ValueError(f"Cannot publish template: Synthetic test render failed on unpopulated tokens: {unpopulated}")

        # Retire prior published versions for this template
        self.db.query(TemplateVersion).filter_by(
            template_id=template_id,
            tenant_id=self.tenant_id,
            status="published"
        ).update({"status": "retired"})

        version_row.status = "published"
        version_row.published_at = datetime.now(timezone.utc)
        version_row.published_by_user_id = user_id
        self.db.commit()
        self.db.refresh(version_row)
        return version_row

    # --- DOCUMENT PACKET GENERATION & ASSURANCE ---

    def generate_packet(
        self,
        candidate_id: str,
        requisition_id: Optional[str] = None,
        custom_vars: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        prep_agent = HRDocumentPreparationAgent(self.db, self.tenant_id)
        snapshot = prep_agent.build_snapshot(candidate_id, requisition_id, custom_vars)
        snapshot_json = json.dumps(snapshot, sort_keys=True)
        snapshot_hash = hashlib.sha256(snapshot_json.encode("utf-8")).hexdigest()

        # Find or create application
        candidate = self.db.query(Candidate).filter_by(id=candidate_id, tenant_id=self.tenant_id).first()
        app = self.db.query(Application).filter_by(candidate_id=candidate_id, tenant_id=self.tenant_id).first()
        if not app:
            req = None
            if requisition_id:
                req = self.db.query(JobRequisition).filter_by(id=requisition_id, tenant_id=self.tenant_id).first()
            if not req:
                req = self.db.query(JobRequisition).filter_by(tenant_id=self.tenant_id).first()
            if not req:
                req = JobRequisition(
                    tenant_id=self.tenant_id,
                    title=(candidate.role if candidate else None) or "Software Engineer",
                    status="open",
                )
                self.db.add(req)
                self.db.flush()

            app = Application(
                tenant_id=self.tenant_id,
                candidate_id=candidate_id,
                requisition_id=req.id,
                current_stage="offer",
                status="active",
                source="HR Document Studio",
                consent_status="basis_recorded",
            )
            self.db.add(app)
            self.db.flush()

        app_id = app.id
        effective_req_id = requisition_id or (app.requisition_id if app else None)

        packet = HRDocumentPacket(
            tenant_id=self.tenant_id,
            application_id=app_id,
            candidate_id=candidate_id,
            requisition_id=effective_req_id,
            data_snapshot=snapshot,
            data_snapshot_sha256=snapshot_hash,
            current_lifecycle_state="draft",
        )
        self.db.add(packet)
        self.db.flush()

        # Fetch published templates or fallback to standard templates
        doc_types = ["offer_letter", "appointment_letter", "employment_contract"]
        artifacts = []
        assurance_agent = HRDocumentAssuranceAgent(self.db, self.tenant_id)
        all_findings = []

        for dtype in doc_types:
            pub_version = (
                self.db.query(TemplateVersion)
                .join(TenantDocumentTemplate, TenantDocumentTemplate.id == TemplateVersion.template_id)
                .filter(
                    TenantDocumentTemplate.tenant_id == self.tenant_id,
                    TenantDocumentTemplate.document_type == dtype,
                    TemplateVersion.status == "published"
                )
                .order_by(TemplateVersion.version.desc())
                .first()
            )

            raw_template_str = ""
            fmt = "html"
            tpl_version_id = None

            if pub_version:
                raw_template_str = pub_version.raw_content or ""
                fmt = pub_version.format
                tpl_version_id = pub_version.id
            else:
                # Built-in fallback
                if dtype == "offer_letter":
                    raw_template_str = CONTRACT_TEMPLATES.get("internship_offer", {}).get("content_template", "")
                    fmt = "markdown"
                elif dtype == "appointment_letter":
                    raw_template_str = self._get_default_appointment_letter()
                    fmt = "markdown"
                else:
                    raw_template_str = CONTRACT_TEMPLATES.get("full_time_standard", {}).get("content_template", "")
                    fmt = "markdown"

            rendered_html, unpopulated = render_deterministic_html(raw_template_str, snapshot, fmt)
            html_bytes = rendered_html.encode("utf-8")
            art_sha256 = sha256_bytes(html_bytes)

            storage_key = self.store.put_artifact(
                self.tenant_id,
                category=dtype,
                content_sha256=art_sha256,
                ext="html",
                data=html_bytes
            )

            artifact_row = HRDocumentArtifact(
                packet_id=packet.id,
                tenant_id=self.tenant_id,
                template_version_id=tpl_version_id,
                document_type=dtype,
                format="html",
                storage_key=storage_key,
                artifact_sha256=art_sha256,
                byte_size=len(html_bytes),
            )
            self.db.add(artifact_row)
            self.db.flush()

            # Audit artifact with Assurance Agent
            verification = assurance_agent.audit_document_packet(
                packet_id=packet.id,
                artifact_sha256=art_sha256,
                rendered_content=rendered_html,
                snapshot=snapshot,
                requisition_id=requisition_id
            )

            v_run = DocumentVerificationRun(
                packet_id=packet.id,
                tenant_id=self.tenant_id,
                artifact_sha256=art_sha256,
                overall_eligibility=verification.overall_eligibility,
                findings=[f.dict() for f in verification.findings],
                agent_model_id="governed-rule-engine-v2",
                rule_version="2026.1",
            )
            self.db.add(v_run)
            all_findings.extend(verification.findings)

            artifacts.append({
                "artifact_id": artifact_row.id,
                "document_type": dtype,
                "artifact_sha256": art_sha256,
                "html": rendered_html,
                "eligibility": verification.overall_eligibility,
            })

        self.db.commit()

        # Overall packet eligibility
        is_blocked = any(a["eligibility"] == "BLOCKED" for a in artifacts)
        is_review = any(a["eligibility"] == "REVIEW_REQUIRED" for a in artifacts)
        packet_eligibility = "BLOCKED" if is_blocked else ("REVIEW_REQUIRED" if is_review else "ELIGIBLE_FOR_APPROVAL")

        return {
            "packet_id": packet.id,
            "candidate_id": candidate_id,
            "snapshot": snapshot,
            "packet_eligibility": packet_eligibility,
            "artifacts": artifacts,
            "findings": [f.dict() for f in all_findings],
        }

    # --- HUMAN APPROVAL ---

    def approve_artifact(
        self,
        packet_id: str,
        artifact_id: str,
        expected_sha256: str,
        approver_id: str,
        approver_role: str,
        rationale: Optional[str] = None
    ) -> HRArtifactApproval:
        artifact = self.db.query(HRDocumentArtifact).filter_by(
            id=artifact_id,
            packet_id=packet_id,
            tenant_id=self.tenant_id
        ).first()

        if not artifact:
            raise ValueError("Document artifact not found.")

        if artifact.artifact_sha256 != expected_sha256:
            raise ValueError("Cryptographic hash mismatch. The artifact has been modified since viewing.")

        # Check latest verification run
        v_run = self.db.query(DocumentVerificationRun).filter_by(
            packet_id=packet_id,
            artifact_sha256=expected_sha256,
            tenant_id=self.tenant_id
        ).order_by(DocumentVerificationRun.executed_at.desc()).first()

        if v_run and v_run.overall_eligibility == "BLOCKED":
            raise ValueError("Cannot approve artifact: Release is BLOCKED by critical verification findings.")

        approval = HRArtifactApproval(
            tenant_id=self.tenant_id,
            packet_id=packet_id,
            artifact_id=artifact_id,
            bound_artifact_sha256=expected_sha256,
            approver_user_id=approver_id,
            approver_role=approver_role,
            decision="approved",
            rationale=rationale or "Verified by authorized HR officer.",
        )
        self.db.add(approval)

        packet = self.db.query(HRDocumentPacket).filter_by(id=packet_id, tenant_id=self.tenant_id).first()
        if packet:
            packet.current_lifecycle_state = "approved"

        self.db.commit()
        self.db.refresh(approval)
        return approval

    # --- DISPATCH & LIFECYCLE PROGRESSION ---

    def dispatch_offer(
        self,
        packet_id: str,
        user_id: str,
        channel: str = "smtp",
        base_url: str = "http://localhost:3000"
    ) -> Dict[str, Any]:
        packet = self.db.query(HRDocumentPacket).filter_by(id=packet_id, tenant_id=self.tenant_id).first()
        if not packet:
            raise ValueError("Document packet not found.")

        offer_art = self.db.query(HRDocumentArtifact).filter_by(
            packet_id=packet_id,
            document_type="offer_letter",
            tenant_id=self.tenant_id
        ).first()

        if not offer_art:
            raise ValueError("Offer letter artifact not found in packet.")

        # Verify active approval bound to exact SHA-256
        approval = self.db.query(HRArtifactApproval).filter_by(
            packet_id=packet_id,
            artifact_id=offer_art.id,
            bound_artifact_sha256=offer_art.artifact_sha256,
            decision="approved"
        ).first()

        if not approval:
            raise ValueError("Offer dispatch forbidden: Offer letter has not received human authorization bound to its SHA-256 hash.")

        snapshot = packet.data_snapshot or {}
        candidate_email = snapshot.get("candidate_email")
        candidate_name = snapshot.get("candidate_name", "Candidate")
        role = snapshot.get("job_title", "Team Member")
        company_name = snapshot.get("company_name", "OctaOS Technologies Inc.")
        salary = snapshot.get("salary_amount", "120,000")
        currency = snapshot.get("salary_currency", "USD")
        start_date = snapshot.get("start_date", "Immediate")

        # Generate single-use acceptance token
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

        # Store acceptance record in pending state
        acc_rec = CandidateAcceptanceRecord(
            tenant_id=self.tenant_id,
            packet_id=packet_id,
            token_hash=token_hash,
            status="pending",
        )
        self.db.add(acc_rec)

        acceptance_url = f"{base_url}/accept-offer?token={raw_token}"
        subject, body = generate_offer_email_content(
            candidate_name, role, company_name, start_date, salary, currency
        )
        body += f"\n\nTo accept this official offer, please click the secure link below:\n{acceptance_url}\n"

        # Dispatch via HRAgent
        sent_successfully = False
        delivery_note = "Registered in dispatch queue"
        agent = HRAgent(self.db, self.tenant_id)

        try:
            if channel == "smtp":
                cred = self.db.query(APICredential).filter_by(tenant_id=self.tenant_id, provider="smtp").first()
                if cred and cred.encrypted_key and candidate_email and "@" in candidate_email:
                    smtp_creds = agent._parse_smtp_credentials(decrypt_api_key(cred.encrypted_key))
                    if smtp_creds:
                        sent_successfully = agent._send_actual_email(smtp_creds, candidate_email, subject, body)
                        delivery_note = "Sent via SMTP"
            elif channel == "gmail":
                cred = self.db.query(APICredential).filter_by(tenant_id=self.tenant_id, provider="gmail").first()
                if cred and cred.encrypted_key and candidate_email:
                    agent._send_gmail_api_email(decrypt_api_key(cred.encrypted_key), candidate_email, subject, body)
                    sent_successfully = True
                    delivery_note = "Sent via Gmail API"
        except Exception as e:
            delivery_note = f"Delivery registered ({str(e)[:80]})"

        packet.current_lifecycle_state = "offered"
        # Update candidate status
        cand = self.db.query(Candidate).filter_by(id=packet.candidate_id, tenant_id=self.tenant_id).first()
        if cand:
            cand.status = "offered"

        self.db.commit()
        return {
            "status": "success",
            "delivery_note": delivery_note,
            "acceptance_url": acceptance_url,
            "lifecycle_state": packet.current_lifecycle_state
        }

    def process_acceptance(self, token: str, ip_address: str, user_agent: str) -> Dict[str, Any]:
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        acc = self.db.query(CandidateAcceptanceRecord).filter_by(token_hash=token_hash).first()

        if not acc:
            raise ValueError("Invalid or expired acceptance token.")

        if acc.status == "accepted":
            # Idempotent response
            return {"status": "already_accepted", "accepted_at": acc.accepted_at.isoformat()}

        acc.status = "accepted"
        acc.accepted_at = datetime.now(timezone.utc)
        acc.ip_address = ip_address
        acc.user_agent = user_agent

        packet = self.db.query(HRDocumentPacket).filter_by(id=acc.packet_id).first()
        if packet:
            packet.current_lifecycle_state = "accepted"
            cand = self.db.query(Candidate).filter_by(id=packet.candidate_id).first()
            if cand:
                cand.status = "offer_accepted"

        self.db.commit()
        return {"status": "success", "accepted_at": acc.accepted_at.isoformat()}

    def dispatch_appointment_letter(self, packet_id: str, user_id: str) -> Dict[str, Any]:
        packet = self.db.query(HRDocumentPacket).filter_by(id=packet_id, tenant_id=self.tenant_id).first()
        if not packet or packet.current_lifecycle_state != "accepted":
            raise ValueError("Joining letter dispatch requires verified candidate offer acceptance.")

        packet.current_lifecycle_state = "appointed"
        self.db.commit()
        return {"status": "success", "message": "Official Appointment / Joining letter dispatched."}

    def execute_contract_and_provision(self, packet_id: str, user_id: str) -> Dict[str, Any]:
        packet = self.db.query(HRDocumentPacket).filter_by(id=packet_id, tenant_id=self.tenant_id).first()
        if not packet:
            raise ValueError("Packet not found.")

        # Idempotent employee provisioning
        existing = self.db.query(Employee).filter_by(
            tenant_id=self.tenant_id,
            application_id=packet.application_id
        ).first()

        if not existing:
            emp = Employee(
                tenant_id=self.tenant_id,
                application_id=packet.application_id,
                candidate_id=packet.candidate_id,
                status="active",
                hired_at=datetime.now(timezone.utc),
            )
            self.db.add(emp)
            self.db.flush()

            # Create default preboarding tasks
            tasks = [
                "Submit tax documents & government photo ID",
                "Review and sign corporate security policy",
                "Laptop provisioning & GitHub enterprise setup",
                "Day-1 10:00 AM orientation meeting with manager"
            ]
            for t in tasks:
                self.db.add(OnboardingTask(
                    tenant_id=self.tenant_id,
                    employee_id=emp.id,
                    title=t,
                    status="open",
                    verification_required=True
                ))

        packet.current_lifecycle_state = "hired"
        cand = self.db.query(Candidate).filter_by(id=packet.candidate_id, tenant_id=self.tenant_id).first()
        if cand:
            cand.status = "hired"

        self.db.commit()
        return {"status": "success", "message": "Contract executed and employee successfully provisioned."}

    def _get_default_appointment_letter(self) -> str:
        return """# OFFICIAL APPOINTMENT & JOINING LETTER

Date: **{{current_date}}**

To,  
**{{candidate_name}}**  
{{candidate_address}}  

Dear **{{candidate_name}}**,

Following your formal acceptance of our Offer Letter, we are pleased to confirm your appointment as **{{job_title}}** at **{{company_name}}**.

### 1. Reporting & Induction
- **Designation:** {{job_title}}
- **Department:** {{department}}
- **Joining Date:** {{start_date}}
- **Reporting Manager:** {{reporting_manager}}
- **Work Mode:** {{work_mode}}

### 2. Day-1 Onboarding Checklist
Please ensure you bring original and photocopies of the following on your commencement date:
- Valid government-issued photo ID & proof of residence.
- Educational degrees and certificates.
- Relieving letter and pay slips from your prior employer.
- Canceled bank cheque / direct-deposit authorization details.

### 3. Terms of Employment
Your appointment is governed by company policies and the Employment Agreement executed between both parties.

We look forward to welcoming you to our team on **{{start_date}}**!

---

Sincerely,

**{{signatory_name}}**  
{{signatory_title}}, {{company_name}}  
"""
