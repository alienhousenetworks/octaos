"""Review Studio: Deterministic DOCX Renderer, Paginated Preview, and Approval Invalidation."""
import io
import re
import hashlib
from datetime import datetime, timezone
from typing import Dict, Any, List, Tuple, Optional
import docx
from sqlalchemy.orm import Session

from app.models.hr import (
    DocumentDraft,
    TemplateVersion,
    DocumentReviewComment,
)
from app.schemas.hr_workflow import (
    DraftPreviewPage,
    DraftPreviewResponse,
    FieldConflictItem,
)


class ReviewStudioRenderer:
    """Manages high-fidelity DOCX rendering, browser preview pagination, and edit tracking."""

    @classmethod
    def render_docx_draft(
        cls,
        template_bytes: bytes,
        field_values: Dict[str, Any],
        paragraph_overrides: Optional[Dict[int, str]] = None,
    ) -> Tuple[bytes, str]:
        """Populates a DOCX template with field values and paragraph overrides, returning bytes and SHA-256."""
        doc = docx.Document(io.BytesIO(template_bytes))
        paragraph_overrides = paragraph_overrides or {}

        # 1. Substitute variables in paragraphs
        for p_idx, p in enumerate(doc.paragraphs):
            if p_idx in paragraph_overrides:
                p.text = paragraph_overrides[p_idx]
            else:
                original_text = p.text or ""
                new_text = original_text
                for key, val in field_values.items():
                    if val is None:
                        continue
                    clean_key = key.split(".")[-1]
                    # match {{key}}, [Key], etc.
                    patterns = [
                        f"{{{{{key}}}}}", f"{{{{{clean_key}}}}}",
                        f"<<{key}>>", f"<<{clean_key}>>",
                        f"[{key}]", f"[{clean_key}]",
                    ]
                    for pat in patterns:
                        if pat in new_text:
                            new_text = new_text.replace(pat, str(val))
                if new_text != original_text:
                    p.text = new_text

        # 2. Substitute in tables
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    cell_text = cell.text or ""
                    new_cell_text = cell_text
                    for key, val in field_values.items():
                        if val is None:
                            continue
                        clean_key = key.split(".")[-1]
                        patterns = [
                            f"{{{{{key}}}}}", f"{{{{{clean_key}}}}}",
                            f"<<{key}>>", f"<<{clean_key}>>",
                            f"[{key}]", f"[{clean_key}]",
                        ]
                        for pat in patterns:
                            if pat in new_cell_text:
                                new_cell_text = new_cell_text.replace(pat, str(val))
                    if new_cell_text != cell_text:
                        cell.text = new_cell_text

        # Save to buffer
        out_buf = io.BytesIO()
        doc.save(out_buf)
        rendered_bytes = out_buf.getvalue()
        sha256_hash = hashlib.sha256(rendered_bytes).hexdigest()
        return rendered_bytes, sha256_hash

    @classmethod
    def generate_paginated_preview(
        cls,
        docx_bytes: bytes,
        paragraphs_per_page: int = 6,
    ) -> List[DraftPreviewPage]:
        """Segments DOCX paragraphs and tables into high-fidelity paginated HTML preview pages."""
        try:
            doc = docx.Document(io.BytesIO(docx_bytes))
            paragraphs = doc.paragraphs
        except Exception:
            return [
                DraftPreviewPage(
                    page_number=1,
                    html_content="<div class='p-8 text-neutral-800'><p>Document preview unavailable</p></div>",
                    editable_paragraph_indices=[],
                )
            ]

        pages: List[DraftPreviewPage] = []
        curr_page_html = []
        curr_indices = []
        page_num = 1

        for idx, p in enumerate(paragraphs):
            text = p.text or ""
            if not text.strip():
                continue

            # Detect heading vs body
            if p.style and "Heading" in p.style.name:
                curr_page_html.append(f"<h3 class='text-lg font-bold text-neutral-900 mt-4 mb-2' data-p-idx='{idx}'>{text}</h3>")
            else:
                curr_page_html.append(f"<p class='text-sm text-neutral-700 leading-relaxed mb-3' data-p-idx='{idx}'>{text}</p>")
            curr_indices.append(idx)

            if len(curr_indices) >= paragraphs_per_page:
                pages.append(
                    DraftPreviewPage(
                        page_number=page_num,
                        html_content=f"<div class='a4-page p-12 bg-white shadow-sm border border-neutral-200 min-h-[842px] max-w-[595px] mx-auto'>{''.join(curr_page_html)}</div>",
                        editable_paragraph_indices=list(curr_indices),
                    )
                )
                curr_page_html = []
                curr_indices = []
                page_num += 1

        if curr_page_html or not pages:
            pages.append(
                DraftPreviewPage(
                    page_number=page_num,
                    html_content=f"<div class='a4-page p-12 bg-white shadow-sm border border-neutral-200 min-h-[842px] max-w-[595px] mx-auto'>{''.join(curr_page_html)}</div>",
                    editable_paragraph_indices=list(curr_indices),
                )
            )

        return pages

    @classmethod
    def apply_draft_edit(
        cls,
        db: Session,
        draft_id: str,
        user_id: str,
        field_overrides: Optional[Dict[str, Any]] = None,
        paragraph_updates: Optional[Dict[int, str]] = None,
        edit_summary: str = "Edited document draft",
    ) -> DocumentDraft:
        """Applies edits to a draft and strictly invalidates prior approvals."""
        draft = db.query(DocumentDraft).filter_by(id=draft_id).first()
        if not draft:
            raise ValueError(f"Draft {draft_id} not found")

        # 1. Check approval invalidation rule
        prior_status = draft.current_approval_status
        if prior_status in ("approved", "pending_approval"):
            draft.current_approval_status = "draft"
            draft.approved_by_user_id = None
            draft.approved_at = None
            draft.bound_approval_sha256 = None

        # 2. Update field overrides
        if field_overrides:
            merged_fields = dict(draft.field_overrides or {})
            merged_fields.update(field_overrides)
            draft.field_overrides = merged_fields

        # 3. Record revision history
        revisions = list(draft.editor_revisions or [])
        revisions.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": user_id,
            "summary": edit_summary,
            "prior_approval_invalidated": prior_status in ("approved", "pending_approval"),
        })
        draft.editor_revisions = revisions

        db.commit()
        db.refresh(draft)
        return draft
