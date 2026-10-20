"""
OctaOS Document Field Mapper & Template Populator.
Maps unstructured extracted document text into validated schema fields using LLM Gateway
and populates approved DOCX templates using the native TemplateEngine.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.orm import Session

from app.services.llm_gateway import LLMGateway
from app.services.hr.template_engine import detect_tokens

logger = logging.getLogger(__name__)


class DocumentFieldMapper:
    """
    Extracts structured key-value fields from extracted document text conforming to
    a user-supplied or template schema.
    """

    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id
        self.llm_gateway = LLMGateway(db, tenant_id)

    async def map_fields(
        self,
        text: str,
        target_schema: Dict[str, Any],
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Extracts structured fields matching target_schema from document text.
        Calculates confidence and flags missing required fields.
        """
        system_prompt = f"""You are the OctaOS Document Intelligence Extraction Engine.
Extract the requested fields from the provided document text into a clean JSON object conforming strictly to this schema:
{json.dumps(target_schema, indent=2)}

Rules:
1. Return ONLY a single valid JSON object.
2. If a field cannot be found in the document, set its value to null.
3. Normalize dates to YYYY-MM-DD format.
4. Normalize currency numbers to pure float/integer without symbols.
"""
        prompt = f"DOCUMENT TEXT:\n\"\"\"\n{text[:12000]}\n\"\"\"\n\nExtract all schema fields as JSON."

        try:
            raw_response = await self.llm_gateway.complete(
                prompt=prompt,
                system_prompt=system_prompt,
                provider=provider,
                model=model,
                temperature=0.0,
            )

            clean_json = raw_response.strip()
            match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw_response)
            if match:
                clean_json = match.group(1).strip()

            extracted_fields = json.loads(clean_json)
        except Exception as e:
            logger.error(f"Field extraction failed: {e}")
            extracted_fields = {k: None for k in target_schema.keys()}

        # Evaluate extraction confidence & missing fields
        total_keys = len(target_schema)
        filled_keys = sum(1 for k in target_schema.keys() if extracted_fields.get(k) is not None)
        confidence = round(filled_keys / max(total_keys, 1), 2)

        missing_fields = [k for k in target_schema.keys() if extracted_fields.get(k) is None]

        return {
            "fields": extracted_fields,
            "confidence": confidence,
            "missing_fields": missing_fields,
            "requires_review": confidence < 0.75 or len(missing_fields) > 0,
        }

    @staticmethod
    def validate_extracted_fields(
        fields: Dict[str, Any],
        required_fields: List[str],
        min_confidence: float = 0.75,
        current_confidence: float = 1.0,
    ) -> Dict[str, Any]:
        """Validates extracted fields against business constraints."""
        from datetime import datetime, timezone
        missing = [f for f in required_fields if not fields.get(f)]
        passed = len(missing) == 0 and current_confidence >= min_confidence

        flagged = []
        if current_confidence < min_confidence:
            flagged.append({
                "field": "_overall",
                "value": current_confidence,
                "reason": f"Confidence score ({current_confidence}) below minimum threshold ({min_confidence})",
                "severity": "warning",
            })
        for m in missing:
            flagged.append({
                "field": m,
                "value": None,
                "reason": f"Required field '{m}' is missing or empty",
                "severity": "error",
            })

        return {
            "is_valid": passed,
            "passed": passed,
            "requires_human_review": not passed,
            "requires_human_approval": not passed,
            "confidence_score": current_confidence,
            "confidence": current_confidence,
            "min_confidence_required": min_confidence,
            "missing_required_fields": missing,
            "missing_required": missing,
            "flagged_fields": flagged,
            "validated_at": datetime.now(timezone.utc).isoformat(),
        }
