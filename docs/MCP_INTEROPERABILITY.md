# OctaOS MCP interoperability

OctaOS exposes an MCP server for clients and can also connect to tenant-configured
remote MCP servers. This document describes the supported path and the security
boundary; a green credential test is not the same as a successful external tool call.

## OctaOS server endpoint

Use the canonical Streamable HTTP endpoint:

- `POST https://<your-octaos-host>/mcp`
- Authentication: `Authorization: Bearer <tenant MCP credential>`
- Request content type: `application/json`
- Accept: `application/json, text/event-stream`

The versioned compatibility endpoint remains at
`/api/v1/mcp/stream`. The legacy SSE endpoints remain under
`/api/v1/mcp/sse` and `/api/v1/mcp/messages`.

The server supports JSON-RPC initialization, ping, tool discovery, tool calls,
and the currently implemented resources surface. It negotiates supported protocol
versions and returns generic internal errors to clients while retaining diagnostic
details in server logs.

## Register and use an external MCP server

1. Create a tenant-scoped credential in **MCP → Credentials**. Store the returned
   raw key securely; it is displayed only once.
2. Register the external server using the authenticated management API:
   `POST /api/v1/mcp/servers`.
3. Use `streamable_http` for modern remote MCP servers, or `sse` for legacy
   remote servers. Endpoint headers and environment/config values are encrypted
   at rest by OctaOS.
4. Call `POST /api/v1/mcp/servers/{server_id}/test` to perform initialization
   and discover advertised tools.
5. Discover tools using `GET /api/v1/mcp/servers/{server_id}/tools`.
6. Invoke a tool using `POST /api/v1/mcp/servers/{server_id}/tools/call`, or
   use the governed `octaos_mcp_list_tools` and `octaos_mcp_call_tool` tools
   through an OctaOS MCP client credential.

For tools not explicitly marked `annotations.readOnlyHint=true`, the caller must
set `confirm_side_effects=true` after reviewing the tool's advertised schema.
The remote tool is re-discovered before invocation so a removed or renamed tool
is not invoked from stale metadata. OctaOS policy grants are still enforced.

## Transport and trust boundaries

- Remote Streamable HTTP and legacy SSE endpoints are supported by the generic
  client. Provider names are not hardcoded into an allow-list.
- The `stdio` transport launches a process on the OctaOS host. Do not expose
  arbitrary tenant-controlled stdio commands in a shared production deployment.
  Use an isolated, allow-listed runner/container for stdio connectors; until that
  runner is deployed, prefer a remote HTTPS MCP endpoint.
- Only connect to remote endpoints trusted by the tenant. Production deployments
  must enforce egress policy and DNS-rebinding/SSRF controls at the network layer;
  URL syntax validation alone is not a sufficient SSRF defense.
- Remote tool annotations are hints supplied by the remote server, not proof of
  safety. Apply least-privilege OctaOS grants and human approval for sensitive
  business actions.
- A successful initialize/list-tools test proves protocol reachability and
  discovery, not that every tool is executable or that external credentials
  authorize all requested actions.
- Tool calls can fail due to provider permissions, expired credentials, rate
  limits, unavailable services, or remote schema changes. Preserve those states
  rather than reporting false success.

## Verification

Run the MCP-specific tests from the repository root:

```bash
pytest -q tests/mcp
```

For deployment verification, run the same tests against the deployed HTTPS
endpoint with a non-production tenant credential. Confirm initialize, ping,
tools/list, one read-only tool call, one denied write without confirmation, and
one approved test write. Check the audit trail and revoke the test credential
afterward.
