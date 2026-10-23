"""Generic MCP client for tenant-configured remote and local MCP servers.

The client deliberately does not contain a provider allow-list. Any MCP server
that speaks streamable HTTP, legacy SSE, or stdio can be registered and called
through the same JSON-RPC surface.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import shlex
from string import Template
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

import httpx

from app.services.mcp.protocol import LATEST_PROTOCOL_VERSION

logger = logging.getLogger(__name__)

SUPPORTED_EXTERNAL_MCP_TRANSPORTS = {
    "streamable_http",
    "http",
    "sse",
    "stdio",
}


class ExternalMCPError(RuntimeError):
    """Raised when an external MCP server cannot complete a protocol request."""


def normalize_external_transport(transport: str) -> str:
    normalized = (transport or "streamable_http").strip().lower().replace("-", "_")
    aliases = {
        "streamablehttp": "streamable_http",
        "streamable_http": "streamable_http",
        "http": "streamable_http",
        "https": "streamable_http",
        "server_sent_events": "sse",
        "server_sent_event": "sse",
        "sse": "sse",
        "stdio": "stdio",
        "local": "stdio",
    }
    normalized = aliases.get(normalized, normalized)
    if normalized not in {"streamable_http", "sse", "stdio"}:
        raise ValueError(
            "Unsupported MCP transport. Use streamable_http, sse, or stdio."
        )
    return normalized


def validate_external_mcp_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize and validate non-secret MCP connection configuration."""
    normalized = dict(config or {})
    transport = normalize_external_transport(normalized.get("transport", "streamable_http"))
    normalized["transport"] = transport

    if transport in {"streamable_http", "sse"}:
        endpoint = str(normalized.get("endpoint") or "").strip()
        parsed = urlparse(endpoint)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("MCP endpoint must be a valid http:// or https:// URL.")
        normalized["endpoint"] = endpoint
    else:
        command = str(normalized.get("command") or "").strip()
        if not command:
            raise ValueError("stdio MCP servers require a command.")
        normalized["command"] = command
        normalized["args"] = [str(value) for value in (normalized.get("args") or [])]

    normalized["headers"] = {
        str(key): str(value)
        for key, value in (normalized.get("headers") or {}).items()
        if str(key).strip()
    }
    normalized["env"] = {
        str(key): str(value)
        for key, value in (normalized.get("env") or {}).items()
        if str(key).strip()
    }
    normalized["timeout_seconds"] = max(
        1.0, min(float(normalized.get("timeout_seconds", 30.0)), 120.0)
    )
    return normalized


def _response_from_sse(body: str, expected_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """Extract a JSON-RPC response from an SSE response body."""
    responses: List[Dict[str, Any]] = []
    for line in body.splitlines():
        if not line.startswith("data:"):
            continue
        raw_data = line[5:].strip()
        if not raw_data or raw_data == "[DONE]":
            continue
        try:
            payload = json.loads(raw_data)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            responses.append(payload)

    if expected_id is not None:
        for response in responses:
            if response.get("id") == expected_id:
                return response
    return responses[-1] if responses else None


class ExternalMCPClient:
    """Small dependency-light client supporting the common MCP transports."""

    def __init__(self, config: Dict[str, Any]):
        self.config = validate_external_mcp_config(config)
        self.transport = self.config["transport"]
        self._next_id = 1
        self._session_id: Optional[str] = None
        self._initialize_result: Optional[Dict[str, Any]] = None

    def _next_request_id(self) -> int:
        request_id = self._next_id
        self._next_id += 1
        return request_id

    def _headers(self) -> Dict[str, str]:
        headers = {
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
        }
        headers.update(self.config.get("headers") or {})
        if self._session_id:
            headers.setdefault("Mcp-Session-Id", self._session_id)
        return headers

    async def initialize(self) -> Dict[str, Any]:
        if self._initialize_result is not None:
            return self._initialize_result
        result = await self._request(
            "initialize",
            {
                "protocolVersion": LATEST_PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "octaos-external-mcp", "version": "1.0.0"},
            },
        )
        # Notifications must be sent after initialize for compliant servers.
        try:
            await self._request("notifications/initialized", {}, notification=True)
        except ExternalMCPError:
            # A few older servers close the request without returning a body for
            # notifications. Initialization itself is still usable in that case.
            logger.debug("External MCP server did not return a notification response", exc_info=True)
        self._initialize_result = result
        return result

    async def list_tools(self) -> Dict[str, Any]:
        await self.initialize()
        return await self._request("tools/list", {})

    async def call_tool(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if not name or not name.strip():
            raise ValueError("MCP tool name is required.")
        await self.initialize()
        return await self._request(
            "tools/call",
            {"name": name, "arguments": arguments or {}},
        )

    async def _request(
        self,
        method: str,
        params: Dict[str, Any],
        *,
        notification: bool = False,
    ) -> Dict[str, Any]:
        request_id = None if notification else self._next_request_id()
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
        }
        if request_id is not None:
            payload["id"] = request_id

        if self.transport == "stdio":
            response = await self._stdio_request(
                payload,
                request_id,
                bootstrap=method != "initialize",
            )
        elif self.transport == "sse":
            response = await self._sse_request(payload, request_id)
        else:
            response = await self._http_request(payload, request_id)

        if notification:
            return {}
        if not response:
            raise ExternalMCPError(f"MCP server returned no response for '{method}'.")
        if response.get("error"):
            error = response["error"]
            raise ExternalMCPError(
                f"MCP server rejected '{method}': {error.get('message', error)}"
            )
        return response.get("result") or {}

    async def _http_request(
        self,
        payload: Dict[str, Any],
        request_id: Optional[int],
    ) -> Optional[Dict[str, Any]]:
        endpoint = self.config["endpoint"]
        timeout = self.config["timeout_seconds"]
        try:
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
                response = await client.post(endpoint, headers=self._headers(), json=payload)
        except httpx.HTTPError as exc:
            raise ExternalMCPError(f"MCP HTTP request failed: {exc}") from exc
        self._capture_session_id(response)
        return self._decode_response(response, request_id)

    async def _sse_request(
        self,
        payload: Dict[str, Any],
        request_id: Optional[int],
    ) -> Optional[Dict[str, Any]]:
        timeout = self.config["timeout_seconds"]
        endpoint = self.config["endpoint"]
        message_endpoint: Optional[str] = None
        try:
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
                async with client.stream("GET", endpoint, headers=self._headers()) as response:
                    self._capture_session_id(response)
                    if response.status_code >= 400:
                        raise ExternalMCPError(
                            f"MCP SSE endpoint returned HTTP {response.status_code}."
                        )
                    async for line in response.aiter_lines():
                        if line.startswith("data:"):
                            candidate = line[5:].strip()
                            if candidate and candidate != "[DONE]":
                                message_endpoint = candidate
                                break
        except httpx.HTTPError as exc:
            raise ExternalMCPError(f"MCP SSE request failed: {exc}") from exc
        if not message_endpoint:
            raise ExternalMCPError("MCP SSE server did not announce a message endpoint.")

        target = urljoin(endpoint, message_endpoint)
        try:
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
                response = await client.post(target, headers=self._headers(), json=payload)
        except httpx.HTTPError as exc:
            raise ExternalMCPError(f"MCP SSE message request failed: {exc}") from exc
        self._capture_session_id(response)
        return self._decode_response(response, request_id)

    async def _stdio_request(
        self,
        payload: Dict[str, Any],
        request_id: Optional[int],
        *,
        bootstrap: bool,
    ) -> Optional[Dict[str, Any]]:
        env = os.environ.copy()
        env.update(self.config.get("env") or {})
        argv = [Template(part).safe_substitute(env) for part in shlex.split(self.config["command"])]
        argv.extend(Template(str(part)).safe_substitute(env) for part in (self.config.get("args") or []))
        try:
            process = await asyncio.create_subprocess_exec(
                *argv,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )
        except OSError as exc:
            raise ExternalMCPError(f"Could not start MCP stdio server: {exc}") from exc
        timeout = self.config["timeout_seconds"]
        try:
            if bootstrap:
                await self._write_stdio(process, {
                    "jsonrpc": "2.0",
                    "id": self._next_request_id(),
                    "method": "initialize",
                    "params": {
                        "protocolVersion": LATEST_PROTOCOL_VERSION,
                        "capabilities": {},
                        "clientInfo": {"name": "octaos-external-mcp", "version": "1.0.0"},
                    },
                })
                await self._read_stdio_response(process, timeout)
                await self._write_stdio(process, {
                    "jsonrpc": "2.0",
                    "method": "notifications/initialized",
                    "params": {},
                })
            await self._write_stdio(process, payload)
            if request_id is None:
                return None
            return await self._read_stdio_response(process, timeout)
        finally:
            if process.returncode is None:
                process.terminate()
                try:
                    await asyncio.wait_for(process.wait(), timeout=1.0)
                except asyncio.TimeoutError:
                    process.kill()
                    await process.wait()

    @staticmethod
    async def _write_stdio(process: asyncio.subprocess.Process, payload: Dict[str, Any]) -> None:
        if process.stdin is None:
            raise ExternalMCPError("MCP stdio process has no writable stdin.")
        process.stdin.write((json.dumps(payload) + "\n").encode("utf-8"))
        await process.stdin.drain()

    @staticmethod
    async def _read_stdio_response(
        process: asyncio.subprocess.Process,
        timeout: float,
    ) -> Dict[str, Any]:
        if process.stdout is None:
            raise ExternalMCPError("MCP stdio process has no readable stdout.")
        while True:
            line = await asyncio.wait_for(process.stdout.readline(), timeout=timeout)
            if not line:
                raise ExternalMCPError("MCP stdio server closed before returning a response.")
            try:
                payload = json.loads(line.decode("utf-8"))
            except json.JSONDecodeError:
                # Some servers write diagnostics to stdout. Ignore non-JSON lines
                # and continue until a JSON-RPC response arrives.
                continue
            if isinstance(payload, dict) and ("result" in payload or "error" in payload):
                return payload

    def _capture_session_id(self, response: httpx.Response) -> None:
        session_id = response.headers.get("Mcp-Session-Id") or response.headers.get("mcp-session-id")
        if session_id:
            self._session_id = session_id

    @staticmethod
    def _decode_response(
        response: httpx.Response,
        request_id: Optional[int],
    ) -> Optional[Dict[str, Any]]:
        if response.status_code == 202 and not response.content:
            return None
        if response.status_code >= 400:
            raise ExternalMCPError(
                f"MCP server returned HTTP {response.status_code}: {response.text[:500]}"
            )
        content_type = response.headers.get("content-type", "").lower()
        if "text/event-stream" in content_type:
            return _response_from_sse(response.text, request_id)
        try:
            payload = response.json()
        except ValueError as exc:
            raise ExternalMCPError("MCP server returned a non-JSON response.") from exc
        if isinstance(payload, list):
            for item in payload:
                if isinstance(item, dict) and (request_id is None or item.get("id") == request_id):
                    return item
            return payload[-1] if payload else None
        return payload if isinstance(payload, dict) else None
