"""Safe HTTP egress client with DNS pinning and redirect guards."""
from __future__ import annotations

import httpx
from typing import Any, Dict, Optional, Tuple
from app.services.knowledge_connectors.security.url_validation import validate_and_resolve_destination
from app.services.knowledge_connectors.errors import SSRFProtectionError, ConnectorSecurityError


class SafeHTTPClient:
    """Enterprise HTTP egress client with DNS resolution validation and strict limits."""

    def __init__(
        self,
        timeout_seconds: float = 10.0,
        allow_redirects: bool = False,
        max_redirects: int = 2,
        allow_http_for_testing: bool = False,
    ):
        self.timeout_seconds = timeout_seconds
        self.allow_redirects = allow_redirects
        self.max_redirects = max_redirects
        self.allow_http_for_testing = allow_http_for_testing

    async def execute_request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Any] = None,
    ) -> httpx.Response:
        """
        Executes an HTTP request with validated egress destination and redirect re-checking.
        """
        current_url = url
        redirect_count = 0
        req_headers = headers.copy() if headers else {}

        while True:
            # 1. Validate destination and resolve public IP
            normalized_url, resolved_ips, port = validate_and_resolve_destination(
                current_url,
                allow_http_for_testing=self.allow_http_for_testing,
            )

            # 2. Build non-redirecting async client with verified timeouts
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout_seconds, connect=5.0),
                follow_redirects=False,
                verify=True,
            ) as client:
                response = await client.request(
                    method=method,
                    url=normalized_url,
                    headers=req_headers,
                    params=params if redirect_count == 0 else None,
                    json=json_data if redirect_count == 0 else None,
                )

            # 3. Check for redirects
            if response.is_redirect:
                if not self.allow_redirects:
                    raise ConnectorSecurityError(
                        f"HTTP redirect to '{response.headers.get('Location')}' is prohibited by egress policy.",
                        code="REDIRECT_DENIED",
                    )

                redirect_count += 1
                if redirect_count > self.max_redirects:
                    raise ConnectorSecurityError(
                        f"Exceeded maximum allowed redirects ({self.max_redirects}).",
                        code="MAX_REDIRECTS_EXCEEDED",
                    )

                redirect_target = response.headers.get("Location")
                if not redirect_target:
                    raise ConnectorSecurityError("Missing Location header in redirect response.")

                # Re-validate new target from scratch on next iteration
                current_url = str(response.url.join(redirect_target))
                continue

            return response
