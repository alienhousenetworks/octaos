"""LinkedIn author selection follows the token's granted scopes."""
import pytest

from app.api.v1.endpoints.linkedin_oauth import normalize_linkedin_scopes
from app.services.social.linkedin_client import parse_linkedin_scopes, select_linkedin_author

ORG = "urn:li:organization:104858837"
PERSON = "urn:li:person:abc"


def test_member_only_token_does_not_target_the_company_page():
    with pytest.raises(RuntimeError, match="cannot post as an organization"):
        select_linkedin_author({"w_member_social"}, org_urn=ORG, person_urn=None)


def test_member_only_token_posts_as_the_member_when_known():
    author = select_linkedin_author({"w_member_social"}, org_urn=ORG, person_urn=PERSON)
    assert author == PERSON


def test_organization_scope_posts_as_the_company_page():
    scopes = parse_linkedin_scopes("w_member_social,w_organization_social")
    author = select_linkedin_author(scopes, org_urn=ORG, person_urn=PERSON)
    assert author == ORG


def test_unknown_scopes_still_attempt_the_configured_organization():
    author = select_linkedin_author(None, org_urn=ORG, person_urn=PERSON)
    assert author == ORG


def test_personal_oauth_scope_includes_openid_identity():
    scopes = set(normalize_linkedin_scopes("w_member_social").split())
    assert {"openid", "profile", "w_member_social"} <= scopes
    assert "w_organization_social" not in scopes


def test_company_oauth_scope_keeps_organization_permission():
    scopes = set(normalize_linkedin_scopes("w_organization_social w_member_social").split())
    assert "w_organization_social" in scopes
    assert {"openid", "profile", "w_member_social"} <= scopes
