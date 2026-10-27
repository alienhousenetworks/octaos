"""Regression tests for the industry-neutral active product surface."""

from pathlib import Path

from app.api.v1.api import api_router


def test_dedicated_real_estate_and_property_field_sales_routers_are_not_registered():
    paths = {route.path for route in api_router.routes}
    assert not any("/real-estate" in path or "/sales-real-estate" in path for path in paths)
    assert not any("/field-sales" in path for path in paths)


def test_property_campaign_endpoints_are_not_registered():
    paths = {route.path for route in api_router.routes}
    assert not any("/verticals/real-estate" in path for path in paths)


def test_primary_navigation_does_not_promote_property_specific_features():
    navigation = (
        Path(__file__).resolve().parents[1]
        / "frontend"
        / "src"
        / "lib"
        / "navigation.ts"
    ).read_text(encoding="utf-8")
    assert "sales_field_sales" not in navigation
    assert "sales_industries" not in navigation
    assert "real estate dispatch" not in navigation
