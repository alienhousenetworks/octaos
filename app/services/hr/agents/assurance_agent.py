import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import Session

from app.models.hr import SalaryBand, JobRequisition
from app.models.verticals import Candidate
from app.schemas.hr_documents import (
    VerificationFinding,
    VerificationReport,
    FindingSeverity,
    FindingStatus,
)
from app.services.hr.template_engine import TOKEN_REGEX


class HRDocumentPreparationAgent:
    """Agent 1 (Preparation): Maps candidate, requisition, and compensation data into a verified snapshot."""

    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

    def build_snapshot(
        self,
        candidate_id: str,
        requisition_id: Optional[str] = None,
        custom_vars: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        candidate = self.db.query(Candidate).filter_by(id=candidate_id, tenant_id=self.tenant_id).first()
        if not candidate:
            raise ValueError(f"Candidate {candidate_id} not found for tenant {self.tenant_id}")

        req = None
        if requisition_id:
            req = self.db.query(JobRequisition).filter_by(id=requisition_id, tenant_id=self.tenant_id).first()

        today_str = datetime.now().strftime("%B %d, %Y")
        overrides = custom_vars or {}

        # Default fallback extraction from candidate profile
        name = overrides.get("candidate_name") or candidate.name or "Candidate"
        email = overrides.get("candidate_email") or candidate.email or ""
        role = overrides.get("job_title") or overrides.get("role") or (req.title if req else candidate.role) or "Associate"
        salary = overrides.get("salary_amount") or overrides.get("salary") or "120000"
        currency = overrides.get("salary_currency") or "USD"
        address = overrides.get("candidate_address") or "Address on file"
        company_name = overrides.get("company_name") or "OctaOS Technologies Inc."
        company_address = overrides.get("company_address") or "100 Innovation Way, Suite 400"
        joining_date = overrides.get("start_date") or overrides.get("joining_date") or today_str
        reporting_manager = overrides.get("reporting_manager") or "Director of Engineering"

        snapshot = {
            "candidate_id": candidate.id,
            "requisition_id": req.id if req else None,
            "candidate_name": name,
            "candidate_legal_name": overrides.get("candidate_legal_name") or name,
            "candidate_email": email,
            "candidate_address": address,
            "job_title": role,
            "designation": role,
            "department": overrides.get("department") or "Engineering & Operations",
            "company_name": company_name,
            "company_address": company_address,
            "salary_amount": salary,
            "salary_currency": currency,
            "annual_ctc": f"{currency} {salary}",
            "start_date": joining_date,
            "joining_date": joining_date,
            "current_date": today_str,
            "reporting_manager": reporting_manager,
            "work_mode": overrides.get("work_mode") or "Hybrid",
            "employment_type": overrides.get("employment_type") or "Full-Time Permanent",
            "probation_months": str(overrides.get("probation_months") or "3"),
            "notice_period_days": str(overrides.get("notice_period_days") or "30"),
            "benefits_summary": overrides.get("benefits_summary") or "Comprehensive medical, dental, and health coverage.",
            "stock_options": overrides.get("stock_options") or "Stock options vesting over 4 years with a 1-year standard cliff.",
            "signatory_name": overrides.get("signatory_name") or "Chief Executive Officer",
            "signatory_title": overrides.get("signatory_title") or "Managing Director",
            **overrides,
        }
        return snapshot



class HRDocumentAssuranceAgent:
    """Agent 2 (Assurance & Verification): Audits rendered documents against policies, salary bands, and integrity gates."""

    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

    def audit_document_packet(
        self,
        packet_id: str,
        artifact_sha256: str,
        rendered_content: str,
        snapshot: Dict[str, Any],
        requisition_id: Optional[str] = None
    ) -> VerificationReport:
        findings: List[VerificationFinding] = []

        # Gate 1: Check for unresolved template placeholders
        unresolved_tokens = TOKEN_REGEX.findall(rendered_content)
        if unresolved_tokens:
            findings.append(VerificationFinding(
                finding_id=str(uuid.uuid4()),
                rule_id="RULE-TOKEN-001",
                category="schema_tokens",
                severity=FindingSeverity.CRITICAL,
                status=FindingStatus.FAIL,
                explanation=f"Found {len(unresolved_tokens)} unresolved template placeholders: {', '.join(unresolved_tokens[:5])}",
                expected_value="0 unresolved tokens",
                observed_value=f"{len(unresolved_tokens)} tokens remaining",
                source_references=["rendered_artifact"],
                remediation="Provide values for all required variables before requesting approval."
            ))
        else:
            findings.append(VerificationFinding(
                finding_id=str(uuid.uuid4()),
                rule_id="RULE-TOKEN-001",
                category="schema_tokens",
                severity=FindingSeverity.INFO,
                status=FindingStatus.PASS,
                explanation="All template placeholders successfully substituted. Zero raw tokens detected.",
                expected_value="0 unresolved tokens",
                observed_value="0 unresolved tokens",
                source_references=["rendered_artifact"]
            ))

        # Gate 2: Salary Band Policy Verification
        salary_str = str(snapshot.get("salary_amount", "0")).replace(",", "")
        currency = str(snapshot.get("salary_currency", "USD"))
        try:
            salary_val = Decimal(salary_str)
        except Exception:
            salary_val = Decimal("0")

        if requisition_id:
            active_band = self.db.query(SalaryBand).filter_by(
                tenant_id=self.tenant_id,
                requisition_id=requisition_id,
                currency=currency
            ).first()

            if active_band:
                min_amt = Decimal(str(active_band.min_amount))
                max_amt = Decimal(str(active_band.max_amount))
                if min_amt <= salary_val <= max_amt:
                    findings.append(VerificationFinding(
                        finding_id=str(uuid.uuid4()),
                        rule_id="RULE-SALARY-001",
                        category="salary_band",
                        severity=FindingSeverity.INFO,
                        status=FindingStatus.PASS,
                        explanation=f"Offered base compensation {currency} {salary_val:,.2f} is within authorized band ({min_amt:,.2f} - {max_amt:,.2f}).",
                        expected_value=f"{min_amt} - {max_amt}",
                        observed_value=str(salary_val),
                        source_references=[f"salary_band:{active_band.id}", f"requisition:{requisition_id}"]
                    ))
                else:
                    findings.append(VerificationFinding(
                        finding_id=str(uuid.uuid4()),
                        rule_id="RULE-SALARY-001",
                        category="salary_band",
                        severity=FindingSeverity.CRITICAL,
                        status=FindingStatus.FAIL,
                        explanation=f"Offered base compensation {currency} {salary_val:,.2f} is OUTSIDE authorized band ({min_amt:,.2f} - {max_amt:,.2f}).",
                        expected_value=f"{min_amt} - {max_amt}",
                        observed_value=str(salary_val),
                        source_references=[f"salary_band:{active_band.id}", f"requisition:{requisition_id}"],
                        remediation="Adjust compensation within the authorized range or obtain an executive R4 financial waiver."
                    ))
            else:
                findings.append(VerificationFinding(
                    finding_id=str(uuid.uuid4()),
                    rule_id="RULE-SALARY-001",
                    category="salary_band",
                    severity=FindingSeverity.MEDIUM,
                    status=FindingStatus.REVIEW_REQUIRED,
                    explanation=f"No explicit salary band configured for requisition {requisition_id} in {currency}. Manual compensation review required.",
                    expected_value="Configured SalaryBand",
                    observed_value="None",
                    source_references=[f"requisition:{requisition_id}"],
                    remediation="Configure a salary band or record approval rationale."
                ))
        else:
            findings.append(VerificationFinding(
                finding_id=str(uuid.uuid4()),
                rule_id="RULE-SALARY-001",
                category="salary_band",
                severity=FindingSeverity.LOW,
                status=FindingStatus.REVIEW_REQUIRED,
                explanation="No requisition ID linked; salary band verification skipped.",
                expected_value="Linked requisition",
                observed_value="Unlinked",
                source_references=["candidate_record"]
            ))

        # Gate 3: Critical Legal Clauses Check
        lower_content = rendered_content.lower()
        required_clauses = [
            ("confidential", "Confidentiality & Non-Disclosure Clause"),
            ("intellectual property", "IP Ownership & Work-for-Hire Clause"),
            ("notice period", "Termination & Notice Period Clause")
        ]

        for keyword, clause_name in required_clauses:
            if keyword in lower_content:
                findings.append(VerificationFinding(
                    finding_id=str(uuid.uuid4()),
                    rule_id=f"RULE-CLAUSE-{keyword[:4].upper()}",
                    category="clause_integrity",
                    severity=FindingSeverity.INFO,
                    status=FindingStatus.PASS,
                    explanation=f"{clause_name} is present in document body.",
                    expected_value="Present",
                    observed_value="Present",
                    source_references=["rendered_body"]
                ))
            else:
                findings.append(VerificationFinding(
                    finding_id=str(uuid.uuid4()),
                    rule_id=f"RULE-CLAUSE-{keyword[:4].upper()}",
                    category="clause_integrity",
                    severity=FindingSeverity.MEDIUM,
                    status=FindingStatus.REVIEW_REQUIRED,
                    explanation=f"Standard {clause_name} appears to be missing or worded non-standardly.",
                    expected_value=f"Keyword '{keyword}'",
                    observed_value="Missing",
                    source_references=["rendered_body"],
                    remediation="Verify whether this document type requires the clause or append corporate standard."
                ))

        # Gate 4: Cross-Document Consistency (Dates & Identity)
        candidate_name = snapshot.get("candidate_name", "")
        if candidate_name and candidate_name in rendered_content:
            findings.append(VerificationFinding(
                finding_id=str(uuid.uuid4()),
                rule_id="RULE-IDENTITY-001",
                category="cross_document",
                severity=FindingSeverity.INFO,
                status=FindingStatus.PASS,
                explanation=f"Candidate legal identity '{candidate_name}' verified in rendered artifact.",
                expected_value=candidate_name,
                observed_value=candidate_name,
                source_references=["snapshot:candidate_name"]
            ))
        else:
            findings.append(VerificationFinding(
                finding_id=str(uuid.uuid4()),
                rule_id="RULE-IDENTITY-001",
                category="cross_document",
                severity=FindingSeverity.CRITICAL,
                status=FindingStatus.FAIL,
                explanation="Candidate name missing or does not match snapshot in rendered document.",
                expected_value=candidate_name,
                observed_value="Not matched",
                source_references=["snapshot:candidate_name"]
            ))

        # Compute overall release eligibility
        has_critical = any(f.severity == FindingSeverity.CRITICAL and f.status == FindingStatus.FAIL for f in findings)
        has_review = any(f.status == FindingStatus.REVIEW_REQUIRED for f in findings)

        if has_critical:
            eligibility = "BLOCKED"
        elif has_review:
            eligibility = "REVIEW_REQUIRED"
        else:
            eligibility = "ELIGIBLE_FOR_APPROVAL"

        return VerificationReport(
            packet_id=packet_id,
            artifact_sha256=artifact_sha256,
            overall_eligibility=eligibility,
            findings=findings,
            engine_metadata={
                "assurance_agent_version": "2.0-deterministic-governed",
                "evaluated_at": datetime.utcnow().isoformat()
            }
        )
