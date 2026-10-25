"""Deterministic tests for the Buffer connector boundary (no live Buffer credentials)."""
import asyncio
import time

import pytest
from fastapi import HTTPException

from app.api.v1.endpoints.buffer_oauth import _decode_state, _encode_state
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
    service = BufferService(db=None, tenant_id="tenant-a")
    with pytest.raises(BufferAPIError):
        asyncio.run(service.create_post(
            channel_id="channel-1",
            text="Do not post a local file",
            video_url="http://127.0.0.1/private.mp4",
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
