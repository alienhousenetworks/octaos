"""
API Endpoints for Automation Document Intelligence.
Bridges visual workflow nodes directly to DocumentProcessingPipeline and DocumentFieldMapper.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api import deps
from app.core.rbac import Action, Resource, require_permission
from app.models.base import User
from app.services.automation.document_extraction_adapter import DocumentExtractionAdapter
from app.services.automation.document_field_mapper import DocumentFieldMapper

logger = logging.getLogger(__name__)

router = APIRouter()


class MapFieldsRequest(BaseModel):
    text: str = Field(..., description="Sanitized text from extracted document")
    schema_definition: Dict[str, Any] = Field(..., description="Target JSON Schema to extract into")
    provider: Optional[str] = None
    model: Optional[str] = None


class ValidateFieldsRequest(BaseModel):
    fields: Dict[str, Any]
    required_fields: List[str] = Field(default_factory=list)
    min_confidence: float = 0.75
    current_confidence: float = 1.0


@router.post("/extract")
async def extract_document(
    file: UploadFile = File(...),
    department: str = Form("General"),
    doc_type_override: Optional[str] = Form(None),
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    _: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Directly extracts an uploaded document using the master cascading extraction pipeline:
    Native (PDF/DOCX/XLSX/CSV) -> RapidOCR -> Multimodal Vision fallback -> Sanitization.
    """
    try:
        file_bytes = await file.read()
        adapter = DocumentExtractionAdapter(db, tenant_id)
        result = await adapter.extract_document(
            filename=file.filename or "uploaded_document",
            file_bytes=file_bytes,
            department=department,
            doc_type_override=doc_type_override,
        )
        return result
    except Exception as e:
        logger.error(f"Document extraction failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document extraction failed: {str(e)}"
        )


@router.post("/map-fields")
async def map_document_fields(
    request: MapFieldsRequest,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    _: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Extracts structured fields matching the target schema from document text using LLM Gateway.
    """
    mapper = DocumentFieldMapper(db, tenant_id)
    result = await mapper.map_fields(
        text=request.text,
        target_schema=request.schema_definition,
        provider=request.provider,
        model=request.model,
    )
    return result


@router.post("/validate")
def validate_extracted_fields(
    request: ValidateFieldsRequest,
    _: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Validates extracted fields against business constraints, flags missing items and review requirements.
    """
    return DocumentFieldMapper.validate_extracted_fields(
        fields=request.fields,
        required_fields=request.required_fields,
        min_confidence=request.min_confidence,
        current_confidence=request.current_confidence,
    )
