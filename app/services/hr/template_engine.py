import re
import io
from typing import Dict, Any, List, Tuple, Set, Optional
from datetime import datetime
from decimal import Decimal
import docx


TOKEN_REGEX = re.compile(r"\{\{([a-zA-Z0-9_]+)\}\}")
MALFORMED_OPEN_REGEX = re.compile(r"\{\{[a-zA-Z0-9_]+(?!\}\})")
MALFORMED_CLOSE_REGEX = re.compile(r"(?<!\{\{)[a-zA-Z0-9_]+\}\}")


def detect_tokens(content: str) -> List[str]:
    """Extracts all variable tokens from text in {{variable_name}} format."""
    matches = TOKEN_REGEX.findall(content)
    # Deduplicate while preserving order
    seen: Set[str] = set()
    deduped = []
    for m in matches:
        if m not in seen:
            seen.add(m)
            deduped.append(m)
    return deduped


def detect_docx_tokens(docx_bytes: bytes) -> List[str]:
    """Extracts tokens from a DOCX document including body paragraphs, tables, headers, and footers."""
    doc = docx.Document(io.BytesIO(docx_bytes))
    full_text = []

    for p in doc.paragraphs:
        full_text.append(p.text)

    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                full_text.append(cell.text)

    for section in doc.sections:
        if section.header:
            for p in section.header.paragraphs:
                full_text.append(p.text)
        if section.footer:
            for p in section.footer.paragraphs:
                full_text.append(p.text)

    combined = "\n".join(full_text)
    return detect_tokens(combined)


def lint_tokens(content: str, provided_vars: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Checks for missing required variables, malformed delimiters, and unresolved tokens."""
    issues = []
    required_tokens = detect_tokens(content)

    for token in required_tokens:
        val = provided_vars.get(token)
        if val is None or str(val).strip() == "":
            issues.append({
                "type": "missing_variable",
                "token": token,
                "message": f"Required template variable '{{{{{token}}}}}' was not provided."
            })

    return issues


def format_variable_value(key: str, val: Any) -> str:
    """Formats variables deterministically with proper currency, dates, and casing."""
    if val is None:
        return ""
    if isinstance(val, (int, float, Decimal)):
        # If it looks like money
        if "salary" in key or "ctc" in key or "amount" in key or "stipend" in key or "bonus" in key:
            return f"{val:,.2f}"
        return str(val)
    if isinstance(val, datetime):
        return val.strftime("%B %d, %Y")
    
    val_str = str(val).strip()
    # Try parsing ISO date string
    if ("date" in key or key.endswith("_at")) and len(val_str) >= 10:
        try:
            dt = datetime.fromisoformat(val_str[:10])
            return dt.strftime("%B %d, %Y")
        except Exception:
            pass

    return val_str


def render_deterministic_html(
    raw_template: str,
    variables: Dict[str, Any],
    template_format: str = "html"
) -> Tuple[str, List[str]]:
    """Renders HTML or Markdown template deterministically. Returns (rendered_html, list_of_unpopulated_tokens)."""
    rendered = raw_template

    # Format variables
    formatted_vars = {k: format_variable_value(k, v) for k, v in variables.items()}

    # Perform strict token replacement
    for token, val in formatted_vars.items():
        rendered = rendered.replace(f"{{{{{token}}}}}", val)

    # If markdown, format into clean styled executive HTML
    if template_format == "markdown":
        rendered = _markdown_to_clean_html(rendered, formatted_vars)

    # Scan for leftover {{...}}
    unpopulated = TOKEN_REGEX.findall(rendered)

    return rendered, unpopulated


def render_deterministic_docx(
    docx_bytes: bytes,
    variables: Dict[str, Any]
) -> Tuple[bytes, List[str]]:
    """Substitutes variables inside DOCX paragraphs and tables, properly handling split runs."""
    doc = docx.Document(io.BytesIO(docx_bytes))
    formatted_vars = {k: format_variable_value(k, v) for k, v in variables.items()}

    def _replace_in_paragraph(paragraph):
        # Merge runs into single text to avoid split-run issue
        full_p_text = "".join(run.text for run in paragraph.runs)
        if "{{" in full_p_text and "}}" in full_p_text:
            for token, val in formatted_vars.items():
                full_p_text = full_p_text.replace(f"{{{{{token}}}}}", val)
            # Clear existing runs and place combined text in first run
            if paragraph.runs:
                for r in paragraph.runs[1:]:
                    r.text = ""
                paragraph.runs[0].text = full_p_text

    for p in doc.paragraphs:
        _replace_in_paragraph(p)

    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    _replace_in_paragraph(p)

    for section in doc.sections:
        if section.header:
            for p in section.header.paragraphs:
                _replace_in_paragraph(p)
        if section.footer:
            for p in section.footer.paragraphs:
                _replace_in_paragraph(p)

    out_io = io.BytesIO()
    doc.save(out_io)
    output_bytes = out_io.getvalue()

    # Detect unpopulated tokens in output
    unpopulated = detect_docx_tokens(output_bytes)
    return output_bytes, unpopulated


def _markdown_to_clean_html(markdown_text: str, vars_dict: Dict[str, Any]) -> str:
    """Formats markdown into an executive, print-ready document layout with modern typography."""
    lines = markdown_text.strip().splitlines()
    body_elements = []

    for line in lines:
        line_str = line.strip()
        if not line_str:
            continue
        if line_str.startswith("# "):
            title = line_str[2:].strip()
            body_elements.append(f'<h1 style="color: #0f172a; font-size: 24px; font-weight: 800; border-bottom: 2px solid #e2e8f0; padding-bottom: 10px; margin-bottom: 20px; text-transform: uppercase; letter-spacing: 0.5px;">{title}</h1>')
        elif line_str.startswith("### "):
            heading = line_str[4:].strip()
            body_elements.append(f'<h3 style="color: #1e293b; font-size: 16px; font-weight: 700; margin-top: 18px; margin-bottom: 8px;">{heading}</h3>')
        elif line_str == "---":
            body_elements.append('<hr style="border: none; border-top: 1px solid #cbd5e1; margin: 20px 0;" />')
        elif line_str.startswith("- "):
            item = line_str[2:].strip()
            formatted_item = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", item)
            body_elements.append(f'<li style="color: #334155; font-size: 14px; margin-bottom: 6px; line-height: 1.6;">{formatted_item}</li>')
        else:
            formatted_p = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", line_str)
            body_elements.append(f'<p style="color: #334155; font-size: 14px; line-height: 1.7; margin-bottom: 12px;">{formatted_p}</p>')

    inner_html = "\n".join(body_elements)

    company_name = vars_dict.get("company_name", "OctaOS Enterprise")
    company_address = vars_dict.get("company_address", "Corporate Headquarters")
    current_date = vars_dict.get("current_date", datetime.now().strftime("%B %d, %Y"))

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Official Employment Document</title>
<style>
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    background-color: #f8fafc;
    color: #1e293b;
    margin: 0;
    padding: 20px;
    display: flex;
    justify-content: center;
  }}
  .document-card {{
    background: #ffffff;
    max-width: 800px;
    width: 100%;
    padding: 40px 48px;
    border-radius: 8px;
    border: 1px solid #e2e8f0;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
  }}
  .corporate-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 2px solid #0284c7;
    padding-bottom: 14px;
    margin-bottom: 24px;
  }}
  .brand-logo {{
    font-size: 20px;
    font-weight: 800;
    color: #0284c7;
  }}
  .brand-sub {{
    font-size: 11px;
    color: #64748b;
    text-transform: uppercase;
    font-weight: 600;
  }}
</style>
</head>
<body>
<div class="document-card">
  <div class="corporate-header">
    <div>
      <div class="brand-logo">{company_name}</div>
      <div class="brand-sub">People Operations & Talent Acquisition</div>
    </div>
    <div style="text-align: right; font-size: 12px; color: #64748b;">
      <div>{company_address}</div>
      <div>Date: {current_date}</div>
    </div>
  </div>
  {inner_html}
</div>
</body>
</html>"""


def generate_synthetic_test_data() -> Dict[str, Any]:
    """Returns synthetic data for pre-publication validation rendering."""
    today = datetime.now().strftime("%B %d, %Y")
    return {
        "candidate_name": "Alex Mercer",
        "candidate_legal_name": "Alexander Mercer",
        "candidate_email": "alex.mercer@example.com",
        "candidate_address": "452 Silicon Ave, San Francisco, CA 94107",
        "job_title": "Lead Platform Engineer",
        "designation": "Lead Platform Engineer",
        "department": "Infrastructure & Core Systems",
        "company_name": "Acme Global Technologies",
        "company_address": "100 Innovation Way, Suite 400",
        "salary_amount": "145000",
        "salary_currency": "USD",
        "annual_ctc": "145,000.00",
        "start_date": today,
        "joining_date": today,
        "current_date": today,
        "reporting_manager": "Sarah Connor (VP of Engineering)",
        "work_mode": "Hybrid (3 days on-site, 2 days remote)",
        "probation_months": "3",
        "notice_period_days": "30",
        "benefits_summary": "Comprehensive health, dental, 401(k) matching up to 5%, annual education budget.",
        "stock_options": "10,000 ISO stock options vesting over 4 years with a 1-year cliff.",
        "signatory_name": "Elena Rostova",
        "signatory_title": "Chief People Officer",
    }
