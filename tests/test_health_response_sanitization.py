from app.api.v2 import api as health_api


def test_health_endpoint_does_not_expose_dependency_exception_details(monkeypatch):
    class BrokenSessionFactory:
        def __call__(self):
            raise RuntimeError("postgres://admin:super-secret@internal-db:5432/octaos")

    class BrokenRedis:
        def __init__(self, **kwargs):
            raise RuntimeError("redis://:redis-secret@internal-cache:6379/0")

    monkeypatch.setattr(health_api, "SessionLocal", BrokenSessionFactory())
    monkeypatch.setattr(health_api.redis, "Redis", BrokenRedis)

    result = health_api.check_health()
    public_payload = repr(result)

    assert result["status"] == "degraded"
    assert result["checks"]["database"] == "unavailable"
    assert result["checks"]["redis"] == "unavailable"
    assert "super-secret" not in public_payload
    assert "redis-secret" not in public_payload
    assert "internal-db" not in public_payload
    assert "internal-cache" not in public_payload
    assert "enterprise_hardened" not in result
