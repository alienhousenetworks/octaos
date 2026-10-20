"""
OctaOS Document Extraction Adapter.
Thin, authorized integration layer bridging visual workflow nodes directly to the existing
master DocumentProcessingPipeline (native extraction, RapidOCR rasterization, Multimodal Vision,
and sanitization).
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional
from sqlalchemy.orm import Session

from app.services.document_processing.pipeline import DocumentProcessingPipeline

logger = logging.getLogger(__name__)


class DocumentExtractionAdapter:
    """
    Adapter bridging automation workflow nodes to OctaOS's core document intelligence pipeline.
    Ensures zero duplicate parsing code while exposing standard workflow contracts.
    """

    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id
        self.pipeline = DocumentProcessingPipeline(db, tenant_id)

    async def extract_document(
        self,
        filename: str,
        file_bytes: bytes,
        department: str = "General",
        doc_type_override: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Executes the master cascading pipeline:
        1. Native parsing (PDF, DOCX, XLSX, CSV, etc.)
        2. Per-page quality check & targeted RapidOCR rasterization
        3. Multimodal Vision fallback for low-quality/scanned layouts
        4. Prompt injection sanitization
        5. Section and table extraction
        """
        logger.info(f"Extracting document '{filename}' ({len(file_bytes)} bytes) for tenant {self.tenant_id}")
        result = await self.pipeline.process_document(
            filename=filename,
            file_bytes=file_bytes,
            department=department,
            doc_type_override=doc_type_override,
        )

        return {
            "status": "succeeded",
            "filename": result.get("filename", filename),
            "file_type": result.get("file_type", "unknown"),
            "category": result.get("category", "General"),
            "department": result.get("department", department),
            "text": result.get("text", ""),
            "tables": result.get("tables", []),
            "pages": result.get("pages", []),
            "quality_score": result.get("quality_score", 0.0),
            "extraction_method": result.get("extraction_method", "unknown"),
            "total_pages": len(result.get("pages", [])),
            "total_tables": len(result.get("tables", [])),
            "total_chunks": result.get("total_chunks", 0),
        }

    async def extract_from_path(
        self,
        filepath: str,
        department: str = "General",
        doc_type_override: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Loads file bytes from disk / vault and triggers cascading extraction."""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Document file not found at: {filepath}")

        filename = os.path.basename(filepath)
        with open(filepath, "rb") as f:
            file_bytes = f.read()

        return await self.extract_document(
            filename=filename,
            file_bytes=file_bytes,
            department=department,
            doc_type_override=doc_type_override,
        )
