"""Template Parser for DOCX and HTML documents in OctaOS Template Hub."""
import re
import io
from typing import List, Dict, Any, Tuple
import docx
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from app.schemas.hr_workflow import DetectedPlaceholder


PLACEHOLDER_REGEXES = [
    re.compile(r"\{\{([a-zA-Z0-9_\.\s\-]+)\}\}"),       # {{ candidate_name }}
    re.compile(r"<<([a-zA-Z0-9_\.\s\-]+)>>"),           # << candidate_name >>
    re.compile(r"\[([A-Z][a-zA-Z0-9_\.\s\-]{2,40})\]"),  # [Candidate Name]
    re.compile(r"<([A-Z][a-zA-Z0-9_\.\s\-]{2,40})>"),   # <Candidate Name>
]


def _clean_token(raw: str) -> str:
    cleaned = raw.strip()
    # convert spaces and hyphens to snake_case
    cleaned = re.sub(r"[\s\-]+", "_", cleaned).lower()
    return cleaned


class DocumentTemplateParser:
    """Parses DOCX and HTML files extracting paragraphs, tables, content controls, and placeholders."""

    @staticmethod
    def parse_docx(file_bytes: bytes) -> Tuple[List[DetectedPlaceholder], Dict[str, Any]]:
        """Extracts placeholders and structural metadata from a DOCX binary."""
        doc = docx.Document(io.BytesIO(file_bytes))
        placeholders: List[DetectedPlaceholder] = []
        seen_expressions = set()

        # 1. Inspect Paragraphs
        paragraph_count = len(doc.paragraphs)
        for p_idx, p in enumerate(doc.paragraphs):
            text = p.text or ""
            for regex in PLACEHOLDER_REGEXES:
                for match in regex.finditer(text):
                    expr = match.group(0)
                    inner = match.group(1).strip()
                    key = _clean_token(inner)
                    if expr not in seen_expressions:
                        seen_expressions.add(expr)
                        placeholders.append(
                            DetectedPlaceholder(
                                expression=expr,
                                inferred_key=key,
                                context_type="paragraph",
                                location_index=p_idx,
                                sample_text=text[:120],
                            )
                        )

        # 2. Inspect Tables
        table_count = len(doc.tables)
        for t_idx, table in enumerate(doc.tables):
            for r_idx, row in enumerate(table.rows):
                for c_idx, cell in enumerate(row.cells):
                    cell_text = cell.text or ""
                    for regex in PLACEHOLDER_REGEXES:
                        for match in regex.finditer(cell_text):
                            expr = match.group(0)
                            inner = match.group(1).strip()
                            key = _clean_token(inner)
                            if expr not in seen_expressions:
                                seen_expressions.add(expr)
                                placeholders.append(
                                    DetectedPlaceholder(
                                        expression=expr,
                                        inferred_key=key,
                                        context_type=f"table[{t_idx}].r{r_idx}c{c_idx}",
                                        location_index=t_idx,
                                        sample_text=cell_text[:120],
                                    )
                                )

        # 3. Inspect Headers & Footers
        for s_idx, section in enumerate(doc.sections):
            for header in [section.header, section.first_page_header]:
                if header:
                    for hp in header.paragraphs:
                        text = hp.text or ""
                        for regex in PLACEHOLDER_REGEXES:
                            for match in regex.finditer(text):
                                expr = match.group(0)
                                inner = match.group(1).strip()
                                key = _clean_token(inner)
                                if expr not in seen_expressions:
                                    seen_expressions.add(expr)
                                    placeholders.append(
                                        DetectedPlaceholder(
                                            expression=expr,
                                            inferred_key=key,
                                            context_type=f"header_s{s_idx}",
                                            location_index=s_idx,
                                            sample_text=text[:120],
                                        )
                                    )

        # 4. Inspect Content Controls (w:sdt)
        try:
            for sdt in doc.element.xpath(".//w:sdt"):
                alias_elem = sdt.find(qn("w:sdtPr")/qn("w:alias"))
                tag_elem = sdt.find(qn("w:sdtPr")/qn("w:tag"))
                ctrl_name = ""
                if alias_elem is not None:
                    ctrl_name = alias_elem.get(qn("w:val"))
                elif tag_elem is not None:
                    ctrl_name = tag_elem.get(qn("w:val"))
                if ctrl_name:
                    expr = f"[[{ctrl_name}]]"
                    key = _clean_token(ctrl_name)
                    if expr not in seen_expressions:
                        seen_expressions.add(expr)
                        placeholders.append(
                            DetectedPlaceholder(
                                expression=expr,
                                inferred_key=key,
                                context_type="content_control",
                                location_index=0,
                                sample_text=f"Content Control: {ctrl_name}",
                            )
                        )
        except Exception:
            pass

        structure_meta = {
            "paragraph_count": paragraph_count,
            "table_count": table_count,
            "section_count": len(doc.sections),
            "sample_first_paragraph": doc.paragraphs[0].text[:160] if doc.paragraphs else "",
        }
        return placeholders, structure_meta

    @staticmethod
    def parse_html(html_content: str) -> Tuple[List[DetectedPlaceholder], Dict[str, Any]]:
        """Extracts placeholders and structural metadata from an HTML string."""
        placeholders: List[DetectedPlaceholder] = []
        seen_expressions = set()

        for regex in PLACEHOLDER_REGEXES:
            for idx, match in enumerate(regex.finditer(html_content)):
                expr = match.group(0)
                inner = match.group(1).strip()
                key = _clean_token(inner)
                if expr not in seen_expressions:
                    seen_expressions.add(expr)
                    start = max(0, match.start() - 30)
                    end = min(len(html_content), match.end() + 30)
                    placeholders.append(
                        DetectedPlaceholder(
                            expression=expr,
                            inferred_key=key,
                            context_type="html_body",
                            location_index=idx,
                            sample_text=html_content[start:end].strip(),
                        )
                    )

        structure_meta = {
            "paragraph_count": html_content.count("<p>") or 1,
            "table_count": html_content.count("<table"),
            "section_count": 1,
            "sample_first_paragraph": html_content[:160],
        }
        return placeholders, structure_meta
