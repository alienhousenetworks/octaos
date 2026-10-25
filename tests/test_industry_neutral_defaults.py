"""Regression tests for industry-neutral Sales and Marketing defaults."""

from app.services.sales_os.verticals.registry import list_packs, shared_terminology, terminology_for
from app.services.marketing.verticals.registry import (
    list_marketing_packs,
    default_terminology,
    terminology_for as marketing_terminology_for,
    get_content_pillars,
    get_compliance_rules,
    get_visual_tokens,
    get_calendar_events,
)


def test_general_sales_does_not_expose_industry_packs():
    assert list_packs() == []
    assert terminology_for("real_estate") == shared_terminology()
    assert terminology_for("banking") == shared_terminology()


def test_general_marketing_does_not_expose_industry_packs():
    assert list_marketing_packs() == []
    assert marketing_terminology_for("real_estate") == default_terminology()
    assert marketing_terminology_for("banking") == default_terminology()
    assert get_content_pillars("real_estate") == []
    assert get_compliance_rules("real_estate") == {
        "prohibited_guarantees": [],
        "taboo_words": [],
        "required_disclosures": [],
    }
    assert get_visual_tokens("real_estate") == {}
    assert get_calendar_events("real_estate") == []
