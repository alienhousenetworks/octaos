"""Evidence-Backed AI Extraction & Multi-Source Reconciliation Service."""
import re
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.models.hr import (
    HRWorkflowInstance,
    CandidateEvidence,
    CandidateFieldValue,
)
from app.schemas.hr_workflow import (
    FieldConflictItem,
    ReconciliationSummary,
)


def _fuzzy_match(s1: Optional[str], s2: Optional[str]) -> bool:
    """Checks if two strings are identical ignoring punctuation, extra whitespace, and case."""
    if not s1 or not s2:
        return False
    norm1 = re.sub(r"[^a-zA-Z0-9]", "", str(s1)).lower()
    norm2 = re.sub(r"[^a-zA-Z0-9]", "", str(s2)).lower()
    return norm1 == norm2


class EvidenceReconciliationService:
    """Extracts, validates provenance, and reconciles candidate data with zero hallucination."""

    @classmethod
    def simulate_document_ocr_extraction(
        cls,
        document_category: str,
        filename: str,
        content_bytes: bytes,
    ) -> Dict[str, Dict[str, Any]]:
        """Simulates deterministic OCR evidence extraction with page, snippet, and confidence provenance."""
        extracted: Dict[str, Dict[str, Any]] = {}
        
        # In a real environment with OCR/Vision API, this parses the image/PDF.
        # Here we provide deterministic extraction heuristics based on category & content markers:
        text_content = ""
        try:
            text_content = content_bytes.decode("utf-8", errors="ignore")
        except Exception:
            text_content = ""

        if document_category in ("passport", "national_id"):
            # Check for name markers
            name_match = re.search(r"(?:name|given names?|holder)[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)", text_content, re.IGNORECASE)
            if name_match:
                extracted["candidate.full_name"] = {
                    "value": name_match.group(1).strip(),
                    "confidence": 0.94,
                    "page": 1,
                    "snippet": name_match.group(0),
                }

            dob_match = re.search(r"(?:dob|date of birth|birth date)[:\s]+(\d{4}[-/]\d{2}[-/]\d{2}|\d{2}[-/]\d{2}[-/]\d{4})", text_content, re.IGNORECASE)
            if dob_match:
                extracted["candidate.date_of_birth"] = {
                    "value": dob_match.group(1).strip(),
                    "confidence": 0.96,
                    "page": 1,
                    "snippet": dob_match.group(0),
                }

        elif document_category == "tax_form":
            pan_match = re.search(r"([A-Z]{5}[0-9]{4}[A-Z])", text_content)
            if pan_match:
                extracted["candidate.pan_number"] = {
                    "value": pan_match.group(1).strip(),
                    "confidence": 0.98,
                    "page": 1,
                    "snippet": pan_match.group(0),
                }

        return extracted

    @classmethod
    def reconcile_instance_data(
        cls,
        db: Session,
        instance_id: str,
    ) -> ReconciliationSummary:
        """Reconciles candidate provided values with OCR evidence and HR inputs."""
        instance = db.query(HRWorkflowInstance).filter_by(id=instance_id).first()
        if not instance:
            raise ValueError(f"Workflow instance {instance_id} not found")

        # 1. Fetch all candidate evidence items
        evidence_items = db.query(CandidateEvidence).filter_by(instance_id=instance_id).all()
        doc_extracted_map: Dict[str, Dict[str, Any]] = {}
        for ev in evidence_items:
            for key, val_dict in (ev.extracted_data or {}).items():
                # If multiple docs extract the same key, pick higher confidence
                curr_conf = doc_extracted_map.get(key, {}).get("confidence", 0.0)
                if val_dict.get("confidence", 0.0) > curr_conf:
                    val_copy = dict(val_dict)
                    val_copy["evidence_id"] = ev.id
                    doc_extracted_map[key] = val_copy

        # 2. Fetch existing field values
        field_records = db.query(CandidateFieldValue).filter_by(instance_id=instance_id).all()
        field_dict = {f.canonical_key: f for f in field_records}

        conflicts: List[FieldConflictItem] = []
        reconciled_count = 0
        missing_count = 0

        # Check all candidate-facing and context fields
        all_keys = set(field_dict.keys()).union(doc_extracted_map.keys())

        for key in all_keys:
            rec = field_dict.get(key)
            if not rec:
                rec = CandidateFieldValue(
                    tenant_id=instance.tenant_id,
                    instance_id=instance.id,
                    canonical_key=key,
                )
                db.add(rec)
                field_dict[key] = rec

            cand_val = rec.candidate_provided_value
            doc_ext = doc_extracted_map.get(key)
            hr_val = rec.hr_approved_value

            rec.document_extracted_value = doc_ext.get("value") if doc_ext else None
            rec.source_provenance = {
                "evidence_id": doc_ext.get("evidence_id"),
                "page": doc_ext.get("page"),
                "confidence": doc_ext.get("confidence"),
            } if doc_ext else None

            # Hierarchical resolution
            if hr_val is not None:
                rec.resolved_value = hr_val
                rec.has_conflict = False
                rec.status = "hr_overridden"
                reconciled_count += 1
            elif doc_ext and cand_val:
                doc_val = doc_ext.get("value")
                # Compare candidate entry vs OCR extraction
                if not _fuzzy_match(str(cand_val), str(doc_val)):
                    rec.has_conflict = True
                    rec.status = "conflict"
                    rec.conflict_details = {
                        "candidate_value": cand_val,
                        "extracted_value": doc_val,
                        "reason": f"Discrepancy between candidate entered '{cand_val}' and document proof '{doc_val}'",
                    }
                    conflicts.append(
                        FieldConflictItem(
                            canonical_key=key,
                            candidate_value=cand_val,
                            extracted_value=doc_val,
                            source_snippet=doc_ext.get("snippet"),
                            confidence=doc_ext.get("confidence", 0.0),
                            reason=rec.conflict_details["reason"],
                        )
                    )
                else:
                    rec.resolved_value = doc_val  # Prefer official document value
                    rec.has_conflict = False
                    rec.status = "reconciled"
                    reconciled_count += 1
            elif cand_val is not None:
                rec.resolved_value = cand_val
                rec.has_conflict = False
                rec.status = "reconciled"
                reconciled_count += 1
            elif doc_ext:
                rec.resolved_value = doc_ext.get("value")
                rec.has_conflict = False
                rec.status = "reconciled"
                reconciled_count += 1
            else:
                # Value is completely missing
                rec.resolved_value = None
                rec.has_conflict = False
                rec.status = "pending"
                missing_count += 1

        db.commit()

        return ReconciliationSummary(
            total_fields=len(field_dict),
            reconciled_count=reconciled_count,
            conflict_count=len(conflicts),
            missing_required_count=missing_count,
            conflicts=conflicts,
            is_blocked=len(conflicts) > 0,
        )
