import pytest
from datetime import datetime, timezone, timedelta
from app.services.sales_os.discovery.web_discovery import (
    calculate_freshness_window_days,
    classify_archetype,
    extract_page_date_with_confidence,
    _archetype_queries,
)


def test_calculate_freshness_window_days():
    assert calculate_freshness_window_days("7_days") == 7
    assert calculate_freshness_window_days("14_days") == 14
    assert calculate_freshness_window_days("30_days") == 30
    assert calculate_freshness_window_days("90_days") == 90
    assert calculate_freshness_window_days("180_days") == 180
    assert calculate_freshness_window_days("365_days") == 365
    assert calculate_freshness_window_days("all") == 9999
    assert calculate_freshness_window_days(None) == 30


def test_classify_archetype():
    assert classify_archetype("Automated CNC machinery manufacturer in Pune", "Manufacturing") == "INDUSTRIAL_MANUFACTURING"
    assert classify_archetype("Dental clinic chain with multiple practice locations", "Healthcare") == "HEALTHCARE_CLINICAL"
    assert classify_archetype("Shopify D2C brand selling organic apparel", "Retail") == "ECOMMERCE_D2C"
    assert classify_archetype("Licensed commercial roofing contractor", "Construction") == "LOCAL_SERVICES"
    assert classify_archetype("Full service digital marketing and advertising agency", "Agency") == "PROFESSIONAL_SERVICES"
    assert classify_archetype("AI code review pipeline SaaS tool", "B2B SaaS") == "ENTERPRISE_B2B_SAAS"


def test_extract_page_date_structured_meta():
    html = '''
    <html>
      <head>
        <meta property="article:published_time" content="2026-10-01T10:00:00Z" />
      </head>
      <body><h1>New Product Release</h1></body>
    </html>
    '''
    text = "New Product Release"
    now = datetime(2026, 10, 7, 12, 0, tzinfo=timezone.utc)
    dt, conf, src, snippet = extract_page_date_with_confidence(html, text, now=now)

    assert dt is not None
    assert conf >= 0.85
    assert "article:published_time" in src
    assert dt.year == 2026
    assert dt.month == 10
    assert dt.day == 1

    # Check freshness age
    age_days = (now - dt).total_seconds() / 86400.0
    assert 5.0 <= age_days <= 7.0


def test_extract_page_date_relative_text():
    html = "<html><body>We expanded our operations 4 days ago. Contact us at sales@domain.com</body></html>"
    text = "We expanded our operations 4 days ago. Contact us at sales@domain.com"
    now = datetime(2026, 10, 7, 12, 0, tzinfo=timezone.utc)
    dt, conf, src, snippet = extract_page_date_with_confidence(html, text, now=now)

    assert dt is not None
    assert conf >= 0.60
    assert "relative" in src
    assert "4 days ago" in snippet
    age_days = (now - dt).total_seconds() / 86400.0
    assert 3.5 <= age_days <= 4.5


def test_anti_false_fresh_ignores_footer_copyright():
    # An old page with a current copyright notice should NOT be treated as a fresh article
    html = '''
    <html>
      <body>
        <p>Historic catalog from 2023.</p>
        <footer>Copyright © 2026 ACME Corp. All rights reserved.</footer>
      </body>
    </html>
    '''
    text = "Historic catalog from 2023. Copyright © 2026 ACME Corp. All rights reserved."
    now = datetime(2026, 10, 7, 12, 0, tzinfo=timezone.utc)
    dt, conf, src, snippet = extract_page_date_with_confidence(html, text, now=now)

    # Should not parse the copyright date as the event date
    if dt is not None:
        assert "copyright" not in src


def test_stale_lead_rejected_by_cutoff():
    # If content was published 270 days ago (9 months ago)
    html = '''
    <html>
      <head>
        <meta name="pubdate" content="2026-01-10T12:00:00Z" />
      </head>
      <body>Old news from January</body>
    </html>
    '''
    now = datetime(2026, 10, 7, 12, 0, tzinfo=timezone.utc)
    dt, conf, src, snippet = extract_page_date_with_confidence(html, "Old news from January", now=now)

    assert dt is not None
    age_days = (now - dt).total_seconds() / 86400.0
    assert age_days > 260

    # User configured 30 days max window
    max_days = calculate_freshness_window_days("30_days")
    is_fresh = age_days <= max_days
    assert is_fresh is False, "A 9-month-old lead must be rejected by the 30-day freshness gate!"


def test_archetype_queries():
    mfg_queries = _archetype_queries("INDUSTRIAL_MANUFACTURING", "metal fabrication", [])
    assert len(mfg_queries) > 0
    assert any("tender" in q.lower() or "procurement" in q.lower() or "gem" in q.lower() or "iso" in q.lower() for q in mfg_queries)

    saas_queries = _archetype_queries("ENTERPRISE_B2B_SAAS", "developer tooling", [])
    assert any("hiring" in q.lower() or "greenhouse" in q.lower() or "funding" in q.lower() for q in saas_queries)
