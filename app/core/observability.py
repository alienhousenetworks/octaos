import time
import logging
from typing import Dict, Any, List, Tuple
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import threading

logger = logging.getLogger(__name__)

class MetricsRegistry:
    def __init__(self):
        self._lock = threading.Lock()
        # http_requests_total: {(method, path, status): count}
        self.http_requests_total: Dict[Tuple[str, str, int], int] = {}
        # http_request_duration_seconds_sum: {(method, path): sum_seconds}
        self.http_request_duration_sum: Dict[Tuple[str, str], float] = {}
        # http_request_duration_seconds_count: {(method, path): count}
        self.http_request_duration_count: Dict[Tuple[str, str], int] = {}

        # AI Gateway calls: {(provider, model, status): count}
        self.ai_gateway_calls_total: Dict[Tuple[str, str, str], int] = {}
        # AI Gateway latency sum: {(provider, model): sum_seconds}
        self.ai_gateway_latency_sum: Dict[Tuple[str, str], float] = {}
        # AI Gateway latency count: {(provider, model): count}
        self.ai_gateway_latency_count: Dict[Tuple[str, str], int] = {}

        # Cache hits: {(provider, model): count}
        self.cache_hits_total: Dict[Tuple[str, str], int] = {}

    def record_request(self, method: str, path: str, status: int, duration: float):
        with self._lock:
            # Standardize path to avoid high cardinality (e.g. group IDs)
            normalized_path = self._normalize_path(path)
            
            key = (method, normalized_path, status)
            self.http_requests_total[key] = self.http_requests_total.get(key, 0) + 1

            dur_key = (method, normalized_path)
            self.http_request_duration_sum[dur_key] = self.http_request_duration_sum.get(dur_key, 0.0) + duration
            self.http_request_duration_count[dur_key] = self.http_request_duration_count.get(dur_key, 0) + 1

    def record_ai_call(self, provider: str, model: str, status: str, duration: float, cache_hit: bool = False):
        with self._lock:
            key = (provider, model, status)
            self.ai_gateway_calls_total[key] = self.ai_gateway_calls_total.get(key, 0) + 1

            dur_key = (provider, model)
            self.ai_gateway_latency_sum[dur_key] = self.ai_gateway_latency_sum.get(dur_key, 0.0) + duration
            self.ai_gateway_latency_count[dur_key] = self.ai_gateway_latency_count.get(dur_key, 0) + 1

            if cache_hit:
                self.cache_hits_total[dur_key] = self.cache_hits_total.get(dur_key, 0) + 1

    def _normalize_path(self, path: str) -> str:
        """Replace dynamic IDs in path with placeholders to prevent label bloat."""
        parts = path.split("/")
        for i, part in enumerate(parts):
            # Check if part looks like a uuid or integer ID
            if len(part) > 20 or part.isdigit() or (part.startswith("usr_") or part.startswith("tnt_")):
                parts[i] = "{id}"
        return "/".join(parts)

    def generate_prometheus_format(self) -> str:
        lines = []
        with self._lock:
            # 1. HTTP request counts
            lines.append("# HELP http_requests_total Total number of HTTP requests.")
            lines.append("# TYPE http_requests_total counter")
            for (method, path, status), count in self.http_requests_total.items():
                lines.append(f'http_requests_total{{method="{method}",path="{path}",status="{status}"}} {count}')

            # 2. HTTP request duration
            lines.append("# HELP http_request_duration_seconds_sum Total duration of HTTP requests in seconds.")
            lines.append("# TYPE http_request_duration_seconds_sum counter")
            for (method, path), val in self.http_request_duration_sum.items():
                lines.append(f'http_request_duration_seconds_sum{{method="{method}",path="{path}"}} {val:.6f}')

            lines.append("# HELP http_request_duration_seconds_count Count of HTTP requests tracked for duration.")
            lines.append("# TYPE http_request_duration_seconds_count counter")
            for (method, path), val in self.http_request_duration_count.items():
                lines.append(f'http_request_duration_seconds_count{{method="{method}",path="{path}"}} {val}')

            # 3. AI Gateway calls
            lines.append("# HELP ai_gateway_calls_total Total number of AI provider requests.")
            lines.append("# TYPE ai_gateway_calls_total counter")
            for (provider, model, status), count in self.ai_gateway_calls_total.items():
                lines.append(f'ai_gateway_calls_total{{provider="{provider}",model="{model}",status="{status}"}} {count}')

            # 4. AI Gateway latency
            lines.append("# HELP ai_gateway_latency_seconds_sum Total AI request latency in seconds.")
            lines.append("# TYPE ai_gateway_latency_seconds_sum counter")
            for (provider, model), val in self.ai_gateway_latency_sum.items():
                lines.append(f'ai_gateway_latency_seconds_sum{{provider="{provider}",model="{model}"}} {val:.6f}')

            lines.append("# HELP ai_gateway_latency_seconds_count Total AI requests counted for latency.")
            lines.append("# TYPE ai_gateway_latency_seconds_count counter")
            for (provider, model), val in self.ai_gateway_latency_count.items():
                lines.append(f'ai_gateway_latency_seconds_count{{provider="{provider}",model="{model}"}} {val}')

            # 5. Cache hits
            lines.append("# HELP ai_gateway_cache_hits_total Total number of prompt cache hits.")
            lines.append("# TYPE ai_gateway_cache_hits_total counter")
            for (provider, model), count in self.cache_hits_total.items():
                lines.append(f'ai_gateway_cache_hits_total{{provider="{provider}",model="{model}"}} {count}')

        return "\n".join(lines) + "\n"

# Global registry instance
metrics_registry = MetricsRegistry()

class PrometheusMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.time()
        
        # Capture trace/request ID if present
        trace_id = request.headers.get("X-Trace-ID") or request.headers.get("X-Request-ID")
        
        response = await call_next(request)
        
        duration = time.time() - start_time
        
        # Inject trace ID into response header for downstream verification
        if trace_id:
            response.headers["X-Trace-ID"] = trace_id
            
        # Do not track /metrics requests to avoid pollution
        if request.url.path != "/metrics" and request.url.path != "/api/v1/metrics":
            metrics_registry.record_request(
                method=request.method,
                path=request.url.path,
                status=response.status_code,
                duration=duration
            )
            
        return response
