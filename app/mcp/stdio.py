"""Local stdio bridge for desktop MCP clients (Claude Desktop, Cursor, Zed, Windsurf)."""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from typing import Optional

# Suppress standard logging to stdout to keep JSON-RPC stream pure
logging.basicConfig(level=logging.ERROR, stream=sys.stderr)

from app.db.session import SessionLocal
from app.services.mcp.auth.credentials import authenticate_mcp_key
from app.services.mcp.server import mcp_server


async def run_stdio_server(api_key: str):
    """
    Main loop reading JSON-RPC lines from stdin and outputting responses to stdout.
    """
    db = SessionLocal()
    try:
        credential = authenticate_mcp_key(db, api_key)
        if not credential:
            sys.stderr.write("Error: Invalid or expired OctaOS MCP API Key.\n")
            sys.exit(1)

        sys.stderr.write(f"OctaOS MCP Stdio Server running for client: {credential.name} (Tenant: {credential.tenant_id})\n")

        loop = asyncio.get_event_loop()
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        await loop.connect_read_pipe(lambda: protocol, sys.stdin)

        while True:
            line_bytes = await reader.readline()
            if not line_bytes:
                break
            line = line_bytes.decode("utf-8").strip()
            if not line:
                continue

            try:
                msg = json.loads(line)
                response = await mcp_server.handle_message(credential, msg)
                if response is not None:
                    sys.stdout.write(json.dumps(response) + "\n")
                    sys.stdout.flush()
            except json.JSONDecodeError:
                err_resp = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}}
                sys.stdout.write(json.dumps(err_resp) + "\n")
                sys.stdout.flush()
            except Exception as e:
                sys.stderr.write(f"Unexpected error handling message: {e}\n")
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="OctaOS System MCP Local Stdio Bridge")
    parser.add_argument("--api-key", required=True, help="OctaOS MCP API key (starts with octa_mcp_)")
    args = parser.parse_args()

    asyncio.run(run_stdio_server(args.api_key))


if __name__ == "__main__":
    main()
