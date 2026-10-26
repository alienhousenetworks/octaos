import pytest

from app.core.config import Settings


def test_production_configuration_rejects_default_secret():
    settings = Settings(
        ENVIRONMENT="production",
        DEV=False,
        SECRET_KEY="dev-only-insecure-secret-key-change-me",
        SQLALCHEMY_DATABASE_URI="postgresql://octaos:StrongDbPassword987@db.example.com/octaos",
        CORS_ORIGINS="https://app.example.com",
    )

    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        settings.validate_production_configuration()


def test_production_configuration_rejects_default_database_password():
    settings = Settings(
        ENVIRONMENT="production",
        DEV=False,
        SECRET_KEY="a-unique-production-secret-key-with-more-than-32-chars",
        SQLALCHEMY_DATABASE_URI="postgresql://octaos:password@db.example.com/octaos",
        CORS_ORIGINS="https://app.example.com",
    )

    with pytest.raises(RuntimeError, match="database URL"):
        settings.validate_production_configuration()


def test_production_configuration_rejects_wildcard_cors_and_dev_mode():
    settings = Settings(
        ENVIRONMENT="production",
        DEV=True,
        SECRET_KEY="a-unique-production-secret-key-with-more-than-32-chars",
        SQLALCHEMY_DATABASE_URI="postgresql://octaos:StrongDbPassword987@db.example.com/octaos",
        CORS_ORIGINS="*",
    )

    with pytest.raises(RuntimeError) as exc:
        settings.validate_production_configuration()

    assert "DEV must be false" in str(exc.value)
    assert "CORS_ORIGINS" in str(exc.value)


def test_valid_production_configuration_passes():
    settings = Settings(
        ENVIRONMENT="production",
        DEV=False,
        SECRET_KEY="a-unique-production-secret-key-with-more-than-32-chars",
        SQLALCHEMY_DATABASE_URI="postgresql://octaos:StrongDbPassword987@db.example.com/octaos",
        CORS_ORIGINS="https://app.example.com",
    )

    settings.validate_production_configuration()


def test_development_configuration_does_not_require_production_secrets():
    settings = Settings(ENVIRONMENT="development", DEV=True)
    settings.validate_production_configuration()
