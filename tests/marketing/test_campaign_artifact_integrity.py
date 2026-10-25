from app.api.v1.endpoints.marketing import _campaign_artifact_hash


def test_campaign_artifact_hash_is_deterministic_for_same_content_and_sources():
    content = {"title": "Launch plan", "sections": [{"heading": "Goal", "body": "Increase demos"}]}
    sources = [{"type": "user_input", "label": "Campaign brief"}]
    assert _campaign_artifact_hash(content, sources) == _campaign_artifact_hash(content, sources)


def test_campaign_artifact_hash_changes_when_content_or_sources_change():
    content = {"title": "Launch plan"}
    sources = [{"type": "user_input", "label": "Campaign brief"}]
    original = _campaign_artifact_hash(content, sources)
    assert original != _campaign_artifact_hash({"title": "Updated launch plan"}, sources)
    assert original != _campaign_artifact_hash(content, [{"type": "external", "label": "New evidence"}])


def test_campaign_artifact_hash_is_sha256_hex():
    digest = _campaign_artifact_hash({"content": "safe"}, [])
    assert len(digest) == 64
    assert all(character in "0123456789abcdef" for character in digest)
