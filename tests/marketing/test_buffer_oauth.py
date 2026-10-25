"""Deterministic tests for the Buffer connector boundary (no live Buffer credentials)."""
import asyncio
import time

import pytest
from fastapi import HTTPException

from app.api.v1.endpoints.buffer_oauth import _decode_state, _encode_state, _normalize_buffer_platform
from app.services.integrations.buffer_service import BufferAPIError, BufferService


def test_oauth_state_round_trips_and_is_bound_to_short_lifetime():
    payload = {
        "tenant_id": "tenant-a",
        "user_id": "user-a",
        "verifier": "pkce-verifier",
        "issued_at": int(time.time()),
        "nonce": "random-nonce",
    }
    assert _decode_state(_encode_state(payload)) == payload


def test_oauth_state_rejects_tampering():
    token = _encode_state({"tenant_id": "tenant-a", "issued_at": int(time.time())})
    with pytest.raises(HTTPException):
        _decode_state(token[:-2] + "xx")


def test_oauth_state_rejects_expired_timestamp():
    token = _encode_state({"tenant_id": "tenant-a", "issued_at": int(time.time()) - 601})
    with pytest.raises(HTTPException):
        _decode_state(token)


def test_buffer_post_includes_image_asset_and_requires_https():
    service = BufferService(db=None, tenant_id="tenant-a")
    seen = {}

    async def fake_graphql(query, variables=None):
        seen["query"] = query
        seen["variables"] = variables
        return {"createPost": {"post": {"id": "post-123", "channelId": "channel-1", "dueAt": None}}}

    service.graphql = fake_graphql
    result = asyncio.run(service.create_post(
        channel_id="channel-1",
        text="Evidence-backed post",
        image_url="https://cdn.example.com/approved-image.jpg",
    ))
    assert result["id"] == "post-123"
    assert seen["variables"]["input"]["assets"] == [
        {"image": {"url": "https://cdn.example.com/approved-image.jpg"}}
    ]


def test_buffer_rejects_private_or_non_https_media_urls():
    for media_url in [
        "http://127.0.0.1/private.mp4",
        "https://127.0.0.1/private.mp4",
        "https://user:pass@cdn.example.com/private.mp4",
    ]:
        service = BufferService(db=None, tenant_id="tenant-a")
        with pytest.raises(BufferAPIError):
            asyncio.run(service.create_post(
                channel_id="channel-1",
                text="Do not post a local or credentialed file",
                video_url=media_url,
            ))


def test_buffer_rejects_image_and_video_on_same_post():
    service = BufferService(db=None, tenant_id="tenant-a")
    with pytest.raises(BufferAPIError):
        asyncio.run(service.create_post(
            channel_id="channel-1",
            text="Invalid media combination",
            image_url="https://cdn.example.com/image.jpg",
            video_url="https://cdn.example.com/video.mp4",
        ))


def test_buffer_status_reconciliation_reads_pages_without_writing():
    service = BufferService(db=None, tenant_id="tenant-a")
    calls = []

    async def fake_graphql(query, variables=None):
        calls.append(variables)
        if len(calls) == 1:
            return {
                "posts": {
                    "edges": [{"node": {"id": "buffer-post-1", "status": "sent"}}],
                    "pageInfo": {"hasNextPage": True, "endCursor": "cursor-1"},
                }
            }
        return {
            "posts": {
                "edges": [{"node": {"id": "buffer-post-2", "status": "scheduled"}}],
                "pageInfo": {"hasNextPage": False, "endCursor": None},
            }
        }

    service.graphql = fake_graphql
    posts = asyncio.run(service.list_posts(
        organization_id="org-1",
        channel_ids=["channel-1"],
    ))
    assert [post["id"] for post in posts] == ["buffer-post-1", "buffer-post-2"]
    assert len(calls) == 2
    assert calls[1]["after"] == "cursor-1"
    assert calls[0]["input"]["filter"]["channelIds"] == ["channel-1"]


def test_buffer_custom_schedule_preserves_future_utc_time():
    from datetime import datetime, timedelta, timezone

    service = BufferService(db=None, tenant_id="tenant-a")
    seen = {}
    scheduled_at = datetime.now(timezone.utc) + timedelta(hours=2)

    async def fake_graphql(query, variables=None):
        seen["variables"] = variables
        return {"createPost": {"post": {"id": "scheduled-1", "channelId": "channel-1", "dueAt": variables["input"]["dueAt"]}}}

    service.graphql = fake_graphql
    result = asyncio.run(service.create_post(
        channel_id="channel-1",
        text="Scheduled at the intended time",
        scheduled_at=scheduled_at,
    ))
    assert result["id"] == "scheduled-1"
    assert seen["variables"]["input"]["mode"] == "customScheduled"
    assert seen["variables"]["input"]["dueAt"].endswith("Z")


def test_buffer_api_platform_registry_covers_supported_publishing_services():
    supported = {
        "instagram", "threads", "linkedin", "x", "facebook", "tiktok",
        "googlebusiness", "mastodon", "youtube", "pinterest", "bluesky",
    }
    assert {_normalize_buffer_platform(platform) for platform in supported} == supported
    assert _normalize_buffer_platform("twitter") == "x"
    assert _normalize_buffer_platform("google_business") == "googlebusiness"


def test_buffer_api_rejects_channels_not_supported_for_programmatic_publishing():
    for platform in ("substack", "startPage", "whatsapp", "reddit", "instagram_personal"):
        with pytest.raises(HTTPException) as error:
            _normalize_buffer_platform(platform)
        assert error.value.status_code == 422
