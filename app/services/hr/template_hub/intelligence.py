"""AI-Assisted Template Intelligence for OctaOS Template Hub."""
import re
from typing import List, Dict, Any, Tuple
from app.schemas.hr_workflow import (
    DetectedPlaceholder,
    ProposedFieldMapping,
    DetectedClause,
)


CANONICAL_SYNONYM_MAP: Dict[str, Tuple[str, str, str, float]] = {
    # key fragment -> (canonical_key, data_type, source_requirement, confidence)
    "name": ("candidate.full_name", "string", "candidate", 0.95),
    "full_name": ("candidate.full_name", "string", "candidate", 0.98),
    "candidate_name": ("candidate.full_name", "string", "candidate", 0.99),
    "employee_name": ("candidate.full_name", "string", "candidate", 0.95),
    "appointee": ("candidate.full_name", "string", "candidate", 0.90),
    
    "email": ("candidate.email", "string", "candidate", 0.98),
    "phone": ("candidate.phone", "string", "candidate", 0.95),
    "mobile": ("candidate.phone", "string", "candidate", 0.95),
    "contact_number": ("candidate.phone", "string", "candidate", 0.92),
    "address": ("candidate.current_address", "string", "candidate", 0.92),
    "residential_address": ("candidate.current_address", "string", "candidate", 0.96),
    "pan": ("candidate.pan_number", "string", "candidate", 0.95),
    "national_id": ("candidate.national_id", "string", "candidate", 0.95),
    "ssn": ("candidate.ssn", "string", "candidate", 0.95),
    "dob": ("candidate.date_of_birth", "date", "candidate", 0.95),
    "date_of_birth": ("candidate.date_of_birth", "date", "candidate", 0.98),
    
    "role": ("role.title", "string", "hr_input", 0.92),
    "designation": ("role.title", "string", "hr_input", 0.95),
    "job_title": ("role.title", "string", "hr_input", 0.98),
    "position": ("role.title", "string", "hr_input", 0.92),
    "department": ("role.department", "string", "hr_input", 0.95),
    "reporting_manager": ("role.reporting_manager", "string", "hr_input", 0.92),
    "start_date": ("role.start_date", "date", "hr_input", 0.95),
    "joining_date": ("role.start_date", "date", "hr_input", 0.98),
    "effective_date": ("role.start_date", "date", "hr_input", 0.90),
    
    "salary": ("compensation.annual_ctc", "money", "hr_input", 0.92),
    "compensation": ("compensation.annual_ctc", "money", "hr_input", 0.95),
    "ctc": ("compensation.annual_ctc", "money", "hr_input", 0.98),
    "annual_ctc": ("compensation.annual_ctc", "money", "hr_input", 0.99),
    "base_salary": ("compensation.base_amount", "money", "hr_input", 0.98),
    "fixed_salary": ("compensation.base_amount", "money", "hr_input", 0.95),
    
    "company": ("company.legal_name", "string", "company_policy", 0.95),
    "company_name": ("company.legal_name", "string", "company_policy", 0.98),
    "signatory": ("company.signatory_name", "string", "company_policy", 0.95),
    "signatory_title": ("company.signatory_title", "string", "company_policy", 0.95),
}


CLAUSE_PATTERNS = [
    ("confidentiality", re.compile(r"(confidential|proprietary information|non-disclosure|secrecy)", re.IGNORECASE)),
    ("non_compete", re.compile(r"(non-compete|restraint of trade|solicit|solicitation)", re.IGNORECASE)),
    ("governing_law", re.compile(r"(governing law|jurisdiction|courts of|arbitration)", re.IGNORECASE)),
    ("clawback", re.compile(r"(clawback|recovery of joining bonus|liquidated damages|notice period buyout)", re.IGNORECASE)),
    ("probation", re.compile(r"(probationary period|probation period|confirmation of employment)", re.IGNORECASE)),
    ("termination", re.compile(r"(termination of employment|notice period|summary dismissal)", re.IGNORECASE)),
]


class TemplateIntelligenceAnalyzer:
    """Proposes canonical field mappings and detects sensitive/legal clauses."""

    @staticmethod
    def analyze_template(
        placeholders: List[DetectedPlaceholder],
        paragraphs_text: List[str],
    ) -> Tuple[List[ProposedFieldMapping], List[DetectedClause]]:
        """Maps discovered placeholders to canonical schema and scans for clauses."""
        proposed_mappings: List[ProposedFieldMapping] = []

        for p in placeholders:
            token = p.inferred_key.lower()
            matched = False

            # Check direct or substring matches in synonym map
            for frag, (canonical, d_type, req_source, conf) in CANONICAL_SYNONYM_MAP.items():
                if frag in token:
                    proposed_mappings.append(
                        ProposedFieldMapping(
                            template_expression=p.expression,
                            canonical_key=canonical,
                            data_type=d_type,
                            source_requirement=req_source,
                            is_required=True,
                            confidence=conf,
                            validation_rule="standard",
                        )
                    )
                    matched = True
                    break

            if not matched:
                # Fallback heuristic mapping
                is_num = "amount" in token or "price" in token or "rate" in token
                proposed_mappings.append(
                    ProposedFieldMapping(
                        template_expression=p.expression,
                        canonical_key=f"custom.{token}",
                        data_type="money" if is_num else "string",
                        source_requirement="candidate" if "candidate" in token else "hr_input",
                        is_required=True,
                        confidence=0.75,
                        validation_rule=None,
                    )
                )

        # Detect clauses in paragraph texts
        detected_clauses: List[DetectedClause] = []
        for idx, text in enumerate(paragraphs_text):
            if len(text.strip()) < 30:
                continue
            for clause_type, pat in CLAUSE_PATTERNS:
                if pat.search(text):
                    title = text.split("\n")[0][:60].strip()
                    if not title or len(title) < 5:
                        title = f"{clause_type.replace('_', ' ').title()} Clause"
                    detected_clauses.append(
                        DetectedClause(
                            clause_type=clause_type,
                            title=title,
                            paragraph_index=idx,
                            is_standard=True,
                            summary=text[:160] + ("..." if len(text) > 160 else ""),
                        )
                    )
                    break

        return proposed_mappings, detected_clauses

    @classmethod
    def deduce_required_candidate_documents(
        cls,
        placeholders: List[Any],
        paragraphs_text: List[str] = None,
        detected_clauses: List[Any] = None,
    ) -> List[Dict[str, Any]]:
        """
        Deduces required proof documents from placeholders, paragraph context, and detected legal clauses.
        Returns serialized dicts compatible with RequiredDocumentItem.
        """
        paragraphs_text = paragraphs_text or []
        detected_clauses = detected_clauses or []
        
        # Collect all placeholder tokens and subtokens
        tokens = set()
        for p in placeholders:
            raw = ""
            if hasattr(p, "inferred_key"):
                raw = str(p.inferred_key).lower()
            elif hasattr(p, "canonical_key"):
                raw = str(p.canonical_key).lower()
            elif isinstance(p, str):
                raw = p.lower()
            elif isinstance(p, dict):
                raw = str(p.get("inferred_key") or p.get("canonical_key") or "").lower()
            
            if raw:
                tokens.add(raw)
                for part in raw.replace(".", " ").replace("_", " ").split():
                    tokens.add(part)

        full_text = " ".join(paragraphs_text).lower()

        def matches_any(keywords):
            for k in keywords:
                if k in tokens or any(k in tok for tok in tokens) or k in full_text:
                    return True
            return False

        required_docs: List[Dict[str, Any]] = []
        added_categories = set()

        def add_req(category: str, title: str, description: str, is_mandatory: bool = True):
            if category not in added_categories:
                added_categories.add(category)
                required_docs.append({
                    "document_category": category,
                    "title": title,
                    "description": description,
                    "is_mandatory": is_mandatory,
                    "accepted_mimes": ["application/pdf", "image/jpeg", "image/png"],
                })

        # 1. Government Photo ID & Address Proof
        if matches_any(["name", "full_name", "candidate_name", "address", "current_address", "residential_address", "national_id", "dob", "date_of_birth", "identity proof", "government id", "passport", "aadhaar"]):
            add_req(
                "passport",
                "Government Photo ID & Address Proof",
                "Clear color scan of valid Passport, Aadhaar, or National ID card",
                is_mandatory=True,
            )

        # 2. Tax / PAN / SSN Identification
        if matches_any(["pan", "pan_number", "tax", "tax_id", "ssn", "national_id", "pan card", "tax identification", "w-4", "form 16", "withholding"]):
            add_req(
                "tax_form",
                "Tax / Social Security Proof",
                "Official PAN card, Tax Registration, or Social Security documentation",
                is_mandatory=True,
            )

        # 3. Educational Degree Certificate
        if matches_any(["degree", "qualification", "education", "university", "college", "degree certificate", "highest qualification", "graduation", "transcript"]):
            add_req(
                "degree_certificate",
                "Highest Educational Degree Certificate",
                "Graduation or post-graduation degree certificate / transcript",
                is_mandatory=True,
            )

        # 4. Relieving / Experience Certificate
        if matches_any(["relieving", "experience", "prior_employer", "service_certificate", "relieving letter", "service certificate", "prior employment", "experience certificate"]):
            add_req(
                "relieving_letter",
                "Prior Employment Relieving Letter",
                "Official relieving letter and last 3 months pay slips from previous employer",
                is_mandatory=True,
            )

        # 5. Bank Account & Direct Deposit
        if matches_any(["bank", "bank_account", "ifsc", "routing_number", "account_number", "cancelled cheque", "direct deposit", "salary transfer"]):
            add_req(
                "bank_proof",
                "Bank Account Proof / Cancelled Cheque",
                "Cancelled bank cheque or bank account statement verifying account number and IFSC",
                is_mandatory=True,
            )

        # 6. Non-Disclosure Agreement (NDA)
        clause_types = {getattr(c, "clause_type", str(c)) for c in detected_clauses}
        if "confidentiality" in clause_types or any(w in full_text for w in ["non-disclosure", "confidentiality agreement", "proprietary information"]):
            add_req(
                "signed_nda",
                "Signed Confidentiality & NDA Agreement",
                "Signed copy of the Employee Proprietary Information & Inventions Agreement",
                is_mandatory=True,
            )

        # Default fallback: if nothing detected, ensure minimal ID & Tax proof
        if not required_docs:
            add_req(
                "passport",
                "Government Photo ID",
                "Clear scan of Passport, Aadhaar, or Driver's License",
                is_mandatory=True,
            )
            add_req(
                "tax_form",
                "Tax / Social Security Proof",
                "Official PAN card or Tax Registration",
                is_mandatory=True,
            )

        return required_docs
