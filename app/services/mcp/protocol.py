"""Model Context Protocol (MCP) JSON-RPC 2.0 definitions and protocol constants."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field

# MCP Protocol Version supported
LATEST_PROTOCOL_VERSION = "2024-11-05"
SUPPORTED_PROTOCOL_VERSIONS = [
    "2024-11-05",
    "2024-10-07",
]

# Standard JSON-RPC Error Codes
class RPCErrorCode:
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603

    # MCP Custom Application Error Codes
    UNAUTHORIZED = -32001
    PERMISSION_DENIED = -32002
    RATE_LIMITED = -32003
    RESOURCE_NOT_FOUND = -32004
    SCHEMA_VALIDATION_FAILED = -32005
    APPROVAL_REQUIRED = -32006


class JSONRPCRequest(BaseModel):
    jsonrpc: str = "2.0"
    id: Optional[Union[str, int]] = None
    method: str
    params: Optional[Dict[str, Any]] = None


class JSONRPCResponse(BaseModel):
    jsonrpc: str = "2.0"
    id: Optional[Union[str, int]] = None
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None


class TextContent(BaseModel):
    type: str = "text"
    text: str


class ToolResult(BaseModel):
    content: List[TextContent]
    isError: bool = False
    metadata: Optional[Dict[str, Any]] = None


def make_rpc_error(
    req_id: Optional[Union[str, int]],
    code: int,
    message: str,
    data: Optional[Any] = None,
) -> Dict[str, Any]:
    err: Dict[str, Any] = {"code": code, "message": message}
    if data is not None:
        err["data"] = data
    return {"jsonrpc": "2.0", "id": req_id, "error": err}


def make_rpc_success(req_id: Optional[Union[str, int]], result: Any) -> Dict[str, Any]:
    return {"jsonrpc": "2.0", "id": req_id, "result": result}
