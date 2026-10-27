"""Regression checks for interface mode navigation semantics."""
from pathlib import Path


def test_interface_toggle_uses_client_router_without_full_page_reload():
    source = (
        Path(__file__).resolve().parents[1]
        / "frontend" / "src" / "components" / "shell" / "app-shell.tsx"
    ).read_text(encoding="utf-8")
    assert "router.push('/app/assistant')" in source
    assert "router.push('/app/home')" in source
    assert "window.location.assign('/app/assistant')" not in source
    assert "window.location.assign('/app/home')" not in source


def test_explicit_workspace_routes_override_stale_saved_mode():
    source = (
        Path(__file__).resolve().parents[1]
        / "frontend" / "src" / "components" / "shell" / "app-shell.tsx"
    ).read_text(encoding="utf-8")
    assert "const routeMode = pathname === '/app/home' ? 'classic' : pathname === '/app/assistant' || pathname === '/app' ? 'bot' : null;" in source
    assert "const nextMode = routeMode || (savedMode === 'classic' ? 'classic' : 'bot');" in source