# NexusOS - AI Cost Optimization Layer Migration Guide

This document outlines the steps required to transition to the **Universal AI Cost Optimization Layer** in NexusOS and illustrates how to register custom adapters.

---

## 1. Database Migrations

The gateway dynamically scans and updates the database schema at startup. However, for manual deployments, run the following SQL queries on your PostgreSQL/SQLite instance:

```sql
-- 1. Expand provider_usage with telemetry tracking
ALTER TABLE provider_usage ADD COLUMN latency FLOAT DEFAULT 0.0;
ALTER TABLE provider_usage ADD COLUMN cache_hit BOOLEAN DEFAULT FALSE;
ALTER TABLE provider_usage ADD COLUMN cached_tokens INTEGER DEFAULT 0;
ALTER TABLE provider_usage ADD COLUMN is_batch BOOLEAN DEFAULT FALSE;
ALTER TABLE provider_usage ADD COLUMN task_type VARCHAR DEFAULT 'general';
ALTER TABLE provider_usage ADD COLUMN status VARCHAR DEFAULT 'success';
ALTER TABLE provider_usage ADD COLUMN error_message VARCHAR;
ALTER TABLE provider_usage ADD COLUMN failover_from VARCHAR;

-- 2. Create the asynchronous batch jobs tracking table
CREATE TABLE ai_batch_jobs (
    id VARCHAR PRIMARY KEY,
    tenant_id VARCHAR NOT NULL,
    provider VARCHAR NOT NULL,
    model VARCHAR NOT NULL,
    status VARCHAR DEFAULT 'pending',
    total_tasks INTEGER DEFAULT 0,
    completed_tasks INTEGER DEFAULT 0,
    failed_tasks INTEGER DEFAULT 0,
    results JSON,
    provider_batch_id VARCHAR,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE
);
```

---

## 2. Integrating Custom Provider Adapters

The gateway uses a pluggable adapter registration system. To plug in a new custom model provider (e.g. `future-ai`), subclass `BaseProviderAdapter` and register it.

### Code Example: Implementing a Custom Adapter

Create `app/services/ai_gateway/custom_adapter.py`:

```python
from app.services.ai_gateway.adapters import BaseProviderAdapter
import httpx
from typing import Dict, Any

class FutureAIAdapter(BaseProviderAdapter):
    def supports_native_caching(self, model: str) -> bool:
        # Return True if the future provider supports native prompt caching
        return True

    async def execute_request(self, prompt: str, model: str, system_prompt: str = None, **kwargs) -> Dict[str, Any]:
        url = f"https://api.futureai.example.com/v1/chat"
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            **kwargs
        }
        if system_prompt:
            payload["system_instruction"] = system_prompt

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=payload,
                timeout=30.0
            )
            response.raise_for_status()
            data = response.json()
            
            # Normalize response and extract metrics
            return {
                "content": data["choices"][0]["text"],
                "input_tokens": data["usage"]["prompt_tokens"],
                "output_tokens": data["usage"]["completion_tokens"],
                "cached_tokens": data["usage"].get("cached_prompt_tokens", 0),
                "raw_response": data
            }
```

### Registering the Custom Adapter

Add this to your gateway initialization (inside `AIProviderGateway._initialize_adapters` or at startup):

```python
from app.services.ai_gateway import ai_gateway
from app.services.ai_gateway.custom_adapter import FutureAIAdapter

# Retrieve tenant's credentials from DB/settings
future_api_key = "your-api-key"

# Instantiate and register the adapter
future_adapter = FutureAIAdapter(api_key=future_api_key)
ai_gateway.registerProvider("future-ai", future_adapter)
```

Now, you can route tasks to `future-ai` models dynamically:
```python
response = await ai_gateway.executeRequest(
    db=db,
    tenant_id=tenant_id,
    prompt="Hello!",
    provider="future-ai",
    model="future-grandmaster"
)
```
