import pytest
from datetime import datetime, timezone, timedelta
from app.models.schedules import ScheduledTrigger

def test_daily_schedule_calculation():
    trigger = ScheduledTrigger(
        tenant_id="test-tenant",
        target_type="lead_generation",
        frequency="daily",
        time_of_day="15:00"
    )
    
    # Given a time before 15:00 UTC
    ref_morning = datetime(2026, 10, 7, 10, 0, 0, tzinfo=timezone.utc)
    next_run = trigger.calculate_next_run(from_time=ref_morning)
    assert next_run == datetime(2026, 10, 7, 15, 0, 0, tzinfo=timezone.utc)

    # Given a time after 15:00 UTC
    ref_evening = datetime(2026, 10, 7, 16, 0, 0, tzinfo=timezone.utc)
    next_run_tomorrow = trigger.calculate_next_run(from_time=ref_evening)
    assert next_run_tomorrow == datetime(2026, 10, 8, 15, 0, 0, tzinfo=timezone.utc)


def test_weekly_schedule_calculation():
    # Day 0 = Monday
    trigger = ScheduledTrigger(
        tenant_id="test-tenant",
        target_type="campaign_planner",
        frequency="weekly",
        day_of_week=0,
        time_of_day="09:00"
    )

    # Wednesday (2026-10-07 is Wednesday, day 2)
    ref_wednesday = datetime(2026, 10, 7, 12, 0, 0, tzinfo=timezone.utc)
    next_run = trigger.calculate_next_run(from_time=ref_wednesday)
    # Next Monday is 2026-10-12
    assert next_run.weekday() == 0
    assert next_run.hour == 9
    assert next_run.minute == 0
    assert next_run > ref_wednesday


def test_hourly_schedule_calculation():
    trigger = ScheduledTrigger(
        tenant_id="test-tenant",
        target_type="lead_generation",
        frequency="hourly",
        interval_hours=2
    )

    ref_time = datetime(2026, 10, 7, 10, 15, 0, tzinfo=timezone.utc)
    next_run = trigger.calculate_next_run(from_time=ref_time)
    assert next_run > ref_time
    assert next_run.minute == 0


def test_schedule_endpoints_with_test_client():
    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.main import app
    from app.models.base import Base, User
    from app.models.schedules import ScheduledTrigger
    from app.models.verticals import BusinessProfile
    from app.api import deps

    from sqlalchemy.pool import StaticPool

    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    Base.metadata.create_all(bind=test_engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    dummy_user = User(
        id="test-user-1",
        email="test@example.com",
        tenant_id="tenant-123",
        is_active=True,
        is_system_admin=True,
    )

    def override_get_current_user():
        return dummy_user

    def override_get_current_active_user():
        return dummy_user

    def override_get_current_tenant_id():
        return "tenant-123"

    app.dependency_overrides[deps.get_db] = override_get_db
    app.dependency_overrides[deps.get_current_user] = override_get_current_user
    app.dependency_overrides[deps.get_current_active_user] = override_get_current_active_user
    app.dependency_overrides[deps.get_current_tenant_id] = override_get_current_tenant_id

    try:
        client = TestClient(app)

        # 1. GET schedule (defaults)
        res = client.get("/api/v1/schedules/lead_generation")
        assert res.status_code == 200
        data = res.json()
        assert data["target_type"] == "lead_generation"
        assert "instructions" in data

        # 2. POST save schedule
        save_res = client.post(
            "/api/v1/schedules/lead_generation",
            json={
                "frequency": "daily",
                "time_of_day": "15:00",
                "instructions": "Target CTOs with fresh signals",
                "is_active": True,
            }
        )
        assert save_res.status_code == 200
        saved_data = save_res.json()
        assert saved_data["instructions"] == "Target CTOs with fresh signals"
        assert saved_data["message"] == "Schedule trigger saved successfully."

        # 3. GET schedule again (persisted)
        get_res = client.get("/api/v1/schedules/lead_generation")
        assert get_res.status_code == 200
        assert get_res.json()["instructions"] == "Target CTOs with fresh signals"
    finally:
        app.dependency_overrides.clear()

