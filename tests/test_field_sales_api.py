"""The retired property-oriented field-sales API must stay off the public surface."""

from app.api.v1.api import api_router


def test_property_field_sales_api_is_not_registered():
    paths = {route.path for route in api_router.routes}
    assert not any("/field-sales" in path or "/real-estate" in path for path in paths)
    assert not any("/sales-real-estate" in path for path in paths)
