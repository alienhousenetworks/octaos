"""Universal AI Plugin & Gateway router for external models (Claude, Grok, ChatGPT, DeepSeek, Kimi, In-House)."""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api import deps
from app.core.config import settings
from app.models.base import tenant_context
from jose import jwt
from app.models.base import User, tenant_context
from app.models.mcp import SystemMCPCredential
from app.services.mcp.registry.capability_registry import UNIVERSAL_TOOLS_SPEC, DOMAIN_WRAPPERS_SPEC
from app.services.mcp.server import mcp_server
from app.services.mcp.transport_http import extract_credential_from_request
from app.services.media.storage import (
    validate_and_quarantine_media,
    _write_bytes,
)
from app.services.collaboration import (
    AICollaborationEngine,
    AIProviderRegistry,
    CollaborationTaskSubmitRequest,
    ExecutionBridge,
    ExecutionBridgeRequest,
    LiveTerminalManager,
    TerminalLogEntry,
    ProcessStatusResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()
root_router = APIRouter()


class ProcessToggleRequest(BaseModel):
    active: bool = Field(description="True to start/resume the external collaboration listener, False to stop/pause it.")


def resolve_tenant_id_from_request(request: Request, db: Session) -> str:
    """
    Resolves tenant_id whether called from:
    1. Frontend dashboard (User JWT Bearer token)
    2. External AI model or custom script (octa_mcp_... key)
    3. Query parameter ?api_key=...
    """
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token_str = auth_header[7:].strip()
        if not token_str.startswith("octa_mcp_"):
            try:
                payload = jwt.decode(token_str, settings.SECRET_KEY, algorithms=["HS256"])
                t_id = payload.get("tenant_id")
                if t_id:
                    return str(t_id)
                user_id = payload.get("sub")
                if user_id:
                    user = db.query(User).filter(User.id == user_id).first()
                    if user and user.tenant_id:
                        return str(user.tenant_id)
            except Exception:
                pass

    # Fallback to MCP key authentication
    cred = extract_credential_from_request(request, db)
    return cred.tenant_id


# -------------------------------------------------------------
# 1. ChatGPT Plugin Manifest (/.well-known/ai-plugin.json)
# -------------------------------------------------------------

@root_router.get("/.well-known/ai-plugin.json", include_in_schema=False)
@router.get("/manifest.json")
def get_ai_plugin_manifest(request: Request) -> Dict[str, Any]:
    """
    Standard AI Plugin Manifest for OpenAI ChatGPT and Custom GPTs.
    """
    base_url = str(request.base_url).rstrip("/")
    return {
        "schema_version": "v1",
        "name_for_human": "OctaOS Autonomous AI Workforce",
        "name_for_model": "octaos_workforce",
        "description_for_human": "Plug-and-play AI Employees for marketing, sales, support, and omnichannel publishing.",
        "description_for_model": (
            "Universal plugin allowing you to command OctaOS AI Employees (Marketing AI, Sales AI, Support AI, HR AI, CEO). "
            "Supports publishing social media videos and images (Instagram, Facebook, LinkedIn, X), "
            "capturing sales leads, managing tickets, and ingesting enterprise media/documents."
        ),
        "auth": {
            "type": "user_http",
            "authorization_type": "bearer",
        },
        "api": {
            "type": "openapi",
            "url": f"{base_url}/api/v1/plugin/openapi.json",
            "is_user_authenticated": False,
        },
        "logo_url": f"{base_url}/media/octaos-plugin-icon.png",
        "contact_email": "support@octaos.ai",
        "legal_info_url": "https://octaos.ai/legal",
    }


# -------------------------------------------------------------
# 2. Dynamic OpenAPI 3.1 Specification for ChatGPT & Frontier Models
# -------------------------------------------------------------

@router.get("/openapi.json")
def get_plugin_openapi_spec(
    request: Request,
    db: Session = Depends(deps.get_db),
) -> Dict[str, Any]:
    """
    Dynamically generates an OpenAPI 3.1 JSON specification for all authorized
    OctaOS AI tools, allowing ChatGPT Custom GPTs or any OpenAPI agent to bind instantly.
    """
    base_url = str(request.base_url).rstrip("/")

    # Attempt to resolve scoped tools if credential is provided in request headers
    tools_to_expose = UNIVERSAL_TOOLS_SPEC + DOMAIN_WRAPPERS_SPEC
    try:
        cred = extract_credential_from_request(request, db)
        tools_to_expose = mcp_server.registry.get_authorized_tools(db, cred)
    except Exception:
        # Fallback to public catalog if called without credentials during initial spec inspection
        pass

    paths: Dict[str, Any] = {}
    for tool in tools_to_expose:
        tool_name = tool.get("name")
        description = tool.get("description", "")
        input_schema = tool.get("inputSchema", {"type": "object", "properties": {}})

        paths[f"/api/v1/plugin/actions/{tool_name}"] = {
            "post": {
                "summary": tool_name.replace("octaos_", "").replace("_", " ").title(),
                "description": description,
                "operationId": tool_name,
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": input_schema,
                        }
                    },
                },
                "responses": {
                    "200": {
                        "description": "Successful execution outcome",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                }
                            }
                        },
                    },
                    "400": {"description": "Validation or execution error"},
                    "401": {"description": "Missing or invalid API key"},
                    "403": {"description": "Permission denied by governance kernel"},
                },
                "security": [{"BearerAuth": []}, {"ApiKeyAuth": []}],
            }
        }

    return {
        "openapi": "3.1.0",
        "info": {
            "title": "OctaOS Universal AI Employee Gateway",
            "description": "Exposes OctaOS's autonomous workforce and tools to any frontier model or custom software.",
            "version": "2.0.0",
        },
        "servers": [{"url": base_url}],
        "paths": paths,
        "components": {
            "securitySchemes": {
                "BearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "octa_mcp_...",
                    "description": "Provide your OctaOS MCP Key (starts with octa_mcp_)",
                },
                "ApiKeyAuth": {
                    "type": "apiKey",
                    "in": "header",
                    "name": "X-OctaOS-Key",
                    "description": "OctaOS API Key",
                },
            }
        },
    }


# -------------------------------------------------------------
# 3. Direct Action Execution (for ChatGPT Custom GPTs)
# -------------------------------------------------------------

@router.post("/actions/{tool_name}")
async def execute_plugin_action(
    tool_name: str,
    request: Request,
    db: Session = Depends(deps.get_db),
) -> JSONResponse:
    """
    Direct endpoint invoked by ChatGPT Custom GPTs or OpenAPI REST callers.
    """
    credential = extract_credential_from_request(request, db)

    if not LiveTerminalManager.is_process_active(db, credential.tenant_id):
        LiveTerminalManager.log_event(
            tenant_id=credential.tenant_id,
            category="system",
            level="warn",
            source=credential.name or "external_connector",
            target="action_dispatcher",
            message=f"REJECTED: Action '{tool_name}' blocked because external collaboration process is STOPPED.",
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OctaOS External AI Collaboration Process is currently STOPPED. Enable the process in System MCP Hub to resume incoming requests.",
        )

    try:
        body = await request.json()
    except Exception:
        body = {}

    LiveTerminalManager.log_event(
        tenant_id=credential.tenant_id,
        category="inbound",
        level="info",
        source=credential.name or "external_ai",
        target=tool_name,
        message=f"Direct action execution requested: '{tool_name}'",
    )

    tool_result = await mcp_server.registry.call_tool(
        credential=credential,
        tool_name=tool_name,
        arguments=body,
    )

    # Unwrap content for clean JSON response to client
    content_text = ""
    for c in tool_result.content:
        content_text += getattr(c, "text", str(c))

    try:
        parsed_data = json.loads(content_text)
    except Exception:
        parsed_data = {"result": content_text}

    status_code = 400 if tool_result.isError else 200

    LiveTerminalManager.log_event(
        tenant_id=credential.tenant_id,
        category="inbound",
        level="success" if not tool_result.isError else "error",
        source=tool_name,
        target=credential.name or "external_ai",
        message=f"Action '{tool_name}' finished with status {status_code}",
    )

    return JSONResponse(status_code=status_code, content=parsed_data)


# -------------------------------------------------------------
# 4. Universal Polymorphic Gateway (JSON + Multipart Video/Media)
# -------------------------------------------------------------

class GatewayExecuteRequest(BaseModel):
    tool: Optional[str] = None
    name: Optional[str] = None # OpenAI tool format alias
    arguments: Optional[Dict[str, Any]] = None
    parameters: Optional[Dict[str, Any]] = None


@router.post("/gateway/execute")
async def universal_gateway_execute(
    request: Request,
    db: Session = Depends(deps.get_db),
) -> JSONResponse:
    """
    Universal execution bridge supporting:
    1. Standard JSON (Grok, DeepSeek, Kimi, Anthropic API, Custom Agents)
    2. Multipart Form-Data with direct binary Video/Image/Document attachments
    """
    credential = extract_credential_from_request(request, db)

    if not LiveTerminalManager.is_process_active(db, credential.tenant_id):
        LiveTerminalManager.log_event(
            tenant_id=credential.tenant_id,
            category="system",
            level="warn",
            source=credential.name or "external_connector",
            target="gateway_execute",
            message="REJECTED: Universal gateway execution blocked because external collaboration process is STOPPED.",
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OctaOS External AI Collaboration Process is currently STOPPED. Enable the process in System MCP Hub to resume incoming requests.",
        )

    content_type = request.headers.get("content-type", "")

    # A. Multipart File Upload Mode
    if "multipart/form-data" in content_type:
        form = await request.form()
        tool_name = form.get("tool") or form.get("name") or "octaos_social_publish_post"

        raw_args = form.get("arguments") or form.get("parameters")
        arguments: Dict[str, Any] = {}
        if isinstance(raw_args, str):
            try:
                arguments = json.loads(raw_args)
            except Exception:
                arguments = {}
        elif not raw_args:
            # Gather other form fields as arguments
            for k, v in form.items():
                if k not in ("tool", "name", "file", "media_file"):
                    arguments[k] = v

        upload_file: Optional[UploadFile] = form.get("file") or form.get("media_file")
        if upload_file:
            file_bytes = await upload_file.read()
            declared_mime = upload_file.content_type
            valid, detected_mime, err = validate_and_quarantine_media(
                file_bytes,
                declared_mime=declared_mime,
                filename=upload_file.filename,
            )
            if not valid:
                raise HTTPException(status_code=400, detail=f"File quarantine rejected: {err}")

            is_video = "video" in detected_mime or (upload_file.filename and upload_file.filename.endswith((".mp4", ".mov")))
            prefix = "vid" if is_video else "asset"
            media_url = _write_bytes(file_bytes, detected_mime, prefix=prefix)
            arguments["media_url"] = media_url
            if is_video:
                arguments["media_type"] = "video"

        LiveTerminalManager.log_event(
            tenant_id=credential.tenant_id,
            category="inbound",
            level="info",
            source=credential.name or "external_model",
            target=str(tool_name),
            message=f"Gateway execution: '{tool_name}' (multipart attachment)",
        )

        tool_result = await mcp_server.registry.call_tool(
            credential=credential,
            tool_name=str(tool_name),
            arguments=arguments,
        )

    # B. Pure JSON Payload Mode
    else:
        try:
            body = await request.json()
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid JSON payload.")

        tool_name = body.get("tool") or body.get("name")
        arguments = body.get("arguments") or body.get("parameters") or {}

        # Handle OpenAI format where arguments is a JSON-encoded string
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except Exception:
                pass

        if not tool_name:
            raise HTTPException(status_code=400, detail="Missing 'tool' or 'name' parameter.")

        LiveTerminalManager.log_event(
            tenant_id=credential.tenant_id,
            category="inbound",
            level="info",
            source=credential.name or "external_model",
            target=str(tool_name),
            message=f"Gateway execution: '{tool_name}' (JSON payload)",
        )

        tool_result = await mcp_server.registry.call_tool(
            credential=credential,
            tool_name=str(tool_name),
            arguments=arguments,
        )

    content_text = "".join(getattr(c, "text", str(c)) for c in tool_result.content)
    try:
        parsed_data = json.loads(content_text)
    except Exception:
        parsed_data = {"result": content_text}

    status_code = 400 if tool_result.isError else 200

    LiveTerminalManager.log_event(
        tenant_id=credential.tenant_id,
        category="inbound",
        level="success" if not tool_result.isError else "error",
        source=str(tool_name),
        target=credential.name or "external_model",
        message=f"Gateway execution '{tool_name}' finished ({'FAILED' if tool_result.isError else 'SUCCESS'})",
    )

    return JSONResponse(status_code=status_code, content=parsed_data)


# -------------------------------------------------------------
# 5. Direct AI Employee Workforce Delegation REST Endpoint
# -------------------------------------------------------------

class WorkforceDelegateRequest(BaseModel):
    employee: str = Field(description="Target AI Employee: marketing, sales, support, hr, or ceo")
    task_type: str = Field(default="execute_task", description="Task category")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Task parameters")
    instructions: str = Field(default="", description="Natural language instructions")


@router.post("/workforce/delegate")
async def delegate_to_ai_employee(
    req: WorkforceDelegateRequest,
    request: Request,
    db: Session = Depends(deps.get_db),
) -> JSONResponse:
    """
    Direct REST endpoint for external software to delegate work to an OctaOS AI Employee.
    """
    credential = extract_credential_from_request(request, db)

    if not LiveTerminalManager.is_process_active(db, credential.tenant_id):
        LiveTerminalManager.log_event(
            tenant_id=credential.tenant_id,
            category="system",
            level="warn",
            source=credential.name or "external_connector",
            target=f"{req.employee}_ai",
            message=f"REJECTED: Delegation to {req.employee.upper()} AI blocked because collaboration process is STOPPED.",
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OctaOS External AI Collaboration Process is currently STOPPED. Enable the process in System MCP Hub to resume incoming requests.",
        )

    LiveTerminalManager.log_event(
        tenant_id=credential.tenant_id,
        category="inbound",
        level="info",
        source=credential.name or "external_model",
        target=f"{req.employee}_ai",
        message=f"Workforce delegation: '{req.task_type}' assigned to {req.employee.upper()} AI",
        details=req.parameters,
    )

    tool_result = await mcp_server.registry.call_tool(
        credential=credential,
        tool_name="octaos_delegate_ai_employee",
        arguments=req.model_dump(),
    )

    content_text = "".join(getattr(c, "text", str(c)) for c in tool_result.content)
    try:
        parsed = json.loads(content_text)
    except Exception:
        parsed = {"result": content_text}

    LiveTerminalManager.log_event(
        tenant_id=credential.tenant_id,
        category="inbound",
        level="success" if not tool_result.isError else "error",
        source=f"{req.employee}_ai",
        target=credential.name or "external_model",
        message=f"Workforce task '{req.task_type}' executed by {req.employee.upper()} AI ({'FAILED' if tool_result.isError else 'SUCCESS'})",
    )

    return JSONResponse(status_code=400 if tool_result.isError else 200, content=parsed)


# -------------------------------------------------------------
# 6. Bidirectional Universal AI Collaboration Engine Endpoints
# -------------------------------------------------------------

def _collaboration_tenant_id(request: Request, db: Session) -> str:
    """Workspace screens send a user JWT. External plugins send an MCP API key.

    A user JWT must not be treated as an MCP key. That 401 was logging people
    out of the integrations page, because the app treats any 401 as a dead session.
    """
    auth_header = request.headers.get("Authorization") or ""
    token = auth_header[7:].strip() if auth_header.startswith("Bearer ") else ""
    if token.count(".") == 2:
        user = deps.get_current_user(db=db, token=token)
        return user.tenant_id
    credential = extract_credential_from_request(request, db)
    return credential.tenant_id


@router.get("/collaboration/providers")
def list_collaboration_providers(
    request: Request,
    db: Session = Depends(deps.get_db),
) -> JSONResponse:
    """
    Returns the real connectivity status, capabilities, and permitted scopes
    for all external AI models connected to this tenant.
    """
    tenant_id = _collaboration_tenant_id(request, db)
    providers = AIProviderRegistry.get_connected_providers(db, tenant_id=tenant_id)
    return JSONResponse(status_code=200, content=[p.model_dump() for p in providers])


@router.post("/collaboration/tasks")
async def submit_collaboration_task(
    req: CollaborationTaskSubmitRequest,
    request: Request,
    db: Session = Depends(deps.get_db),
) -> JSONResponse:
    """
    Submit an inbound or multi-step collaboration task to an OctaOS AI Employee.
    Supports both synchronous direct execution and asynchronous job queuing.
    """
    credential = extract_credential_from_request(request, db)

    if not LiveTerminalManager.is_process_active(db, credential.tenant_id):
        LiveTerminalManager.log_event(
            tenant_id=credential.tenant_id,
            category="system",
            level="warn",
            source=f"external:{credential.name or 'client'}",
            target=req.target_employee or "octaos_workforce",
            message="REJECTED: Task submission blocked because external collaboration process is STOPPED.",
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OctaOS External AI Collaboration Process is currently STOPPED. Enable the process in System MCP Hub to resume incoming requests.",
        )

    engine = AICollaborationEngine(db, tenant_id=credential.tenant_id)
    source_agent = f"external:{credential.name or 'client'}"

    try:
        task_response = await engine.submit_inbound_task(
            request=req,
            source_identifier=source_agent,
            mcp_credential=credential,
        )
        return JSONResponse(status_code=200, content=task_response.model_dump())
    except Exception as e:
        logger.error("Failed to submit collaboration task (%s)", type(e).__name__)
        return JSONResponse(status_code=400, content={"error": "Collaboration task submission failed. Check task constraints and retry."})


@router.get("/collaboration/tasks/{task_id}")
def get_collaboration_task_status(
    task_id: str,
    request: Request,
    db: Session = Depends(deps.get_db),
) -> JSONResponse:
    """
    Poll status, results, verified evidence, and lineage for a collaboration task.
    Guarantees tenant isolation.
    """
    credential = extract_credential_from_request(request, db)
    engine = AICollaborationEngine(db, tenant_id=credential.tenant_id)

    status_resp = engine.get_task_status(task_id)
    if not status_resp:
        raise HTTPException(status_code=404, detail="Collaboration task not found or cross-tenant access denied.")

    return JSONResponse(status_code=200, content=status_resp.model_dump())


@router.post("/collaboration/tasks/{task_id}/cancel")
def cancel_collaboration_task(
    task_id: str,
    request: Request,
    db: Session = Depends(deps.get_db),
) -> JSONResponse:
    """
    Cancel a pending or running collaboration task.
    """
    credential = extract_credential_from_request(request, db)
    engine = AICollaborationEngine(db, tenant_id=credential.tenant_id)

    cancelled = engine.cancel_task(task_id)
    if not cancelled:
        raise HTTPException(status_code=400, detail="Task not found, already completed, or cannot be cancelled.")

    return JSONResponse(status_code=200, content={"status": "cancelled", "task_id": task_id})


@router.post("/collaboration/execute_bridge")
async def execute_bridge_action(
    req: ExecutionBridgeRequest,
    request: Request,
    db: Session = Depends(deps.get_db),
) -> JSONResponse:
    """
    Result-to-Execution Bridge: Validates proposed external AI actions against
    security policy, executes via governed OctaOS tools, and returns verified execution evidence.
    """
    credential = extract_credential_from_request(request, db)

    if not LiveTerminalManager.is_process_active(db, credential.tenant_id):
        LiveTerminalManager.log_event(
            tenant_id=credential.tenant_id,
            category="system",
            level="warn",
            source=credential.name or "external_ai",
            target=req.proposed_tool,
            message=f"REJECTED: Execution bridge action '{req.proposed_tool}' blocked because external collaboration process is STOPPED.",
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OctaOS External AI Collaboration Process is currently STOPPED. Enable the process in System MCP Hub to resume incoming requests.",
        )

    LiveTerminalManager.log_event(
        tenant_id=credential.tenant_id,
        category="bridge",
        level="info",
        source=credential.name or "external_ai",
        target=req.proposed_tool,
        message=f"Execution bridge evaluation requested: '{req.proposed_tool}'",
    )

    try:
        bridge_res = await ExecutionBridge.process_proposed_action(
            db=db,
            tenant_id=credential.tenant_id,
            request=req,
            mcp_credential=credential,
        )

        LiveTerminalManager.log_event(
            tenant_id=credential.tenant_id,
            category="bridge",
            level="success" if bridge_res.status != "failed" else "error",
            source=req.proposed_tool,
            target=credential.name or "external_ai",
            message=f"Execution bridge action '{req.proposed_tool}' finished with status: {bridge_res.status}",
            details={"status": bridge_res.status, "evidence_count": len(bridge_res.evidence)},
        )

        return JSONResponse(
            status_code=200 if bridge_res.status != "failed" else 400,
            content=bridge_res.model_dump(),
        )
    except Exception as e:
        logger.error("Execution bridge error: %s", e)
        return JSONResponse(status_code=400, content={"error": str(e)})


# -------------------------------------------------------------
# 7. Live Terminal & Process Monitor Endpoints
# -------------------------------------------------------------

@router.get("/collaboration/terminal/logs")
def get_collaboration_terminal_logs(
    request: Request,
    limit: int = 100,
    category: Optional[str] = None,
    db: Session = Depends(deps.get_db),
) -> JSONResponse:
    """
    Returns real-time streaming terminal logs and current process status (RUNNING / STOPPED)
    for external AI connectors and custom software.
    """
    tenant_id = resolve_tenant_id_from_request(request, db)
    process_status = LiveTerminalManager.get_process_status(db, tenant_id)
    logs = LiveTerminalManager.get_logs(tenant_id, limit=limit, category=category)

    return JSONResponse(
        status_code=200,
        content={
            "process": process_status.model_dump(),
            "logs": [entry.model_dump() for entry in logs],
        },
    )


@router.post("/collaboration/process/toggle")
def toggle_collaboration_process(
    req: ProcessToggleRequest,
    request: Request,
    db: Session = Depends(deps.get_db),
) -> JSONResponse:
    """
    Turns the external AI collaboration & custom software listener process ON or OFF.
    When OFF, external inbound traffic is rejected and outbound tasks run internally.
    """
    tenant_id = resolve_tenant_id_from_request(request, db)
    status_resp = LiveTerminalManager.set_process_active(db, tenant_id, req.active)
    return JSONResponse(status_code=200, content=status_resp.model_dump())


@router.post("/collaboration/terminal/clear")
def clear_collaboration_terminal(
    request: Request,
    db: Session = Depends(deps.get_db),
) -> JSONResponse:
    """
    Clears the active live terminal log ring-buffer for this tenant.
    """
    tenant_id = resolve_tenant_id_from_request(request, db)
    LiveTerminalManager.clear_logs(tenant_id)
    return JSONResponse(status_code=200, content={"status": "cleared", "tenant_id": tenant_id})


@router.post("/collaboration/terminal/ping")
def ping_collaboration_terminal(
    request: Request,
    db: Session = Depends(deps.get_db),
) -> JSONResponse:
    """
    Sends a diagnostic ping event into the live terminal to test active streaming and latency.
    """
    tenant_id = resolve_tenant_id_from_request(request, db)
    entry = LiveTerminalManager.log_event(
        tenant_id=tenant_id,
        category="system",
        level="info",
        source="operator_console",
        target="collaboration_gateway",
        message="Diagnostic ping received from operator console. All listeners active.",
    )
    return JSONResponse(status_code=200, content={"status": "pong", "entry": entry.model_dump()})

