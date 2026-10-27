"""The interface toggle changes the current page. It does not leave for another section."""
from pathlib import Path


def _source(relative: str) -> str:
    return (Path(__file__).resolve().parents[1] / relative).read_text(encoding="utf-8")


def test_interface_toggle_stays_on_the_current_page():
    source = _source("frontend/src/components/shell/app-shell.tsx")
    toggle = source.split('data-testid="interface-mode-toggle"', 1)[1][:1200]
    assert "setMode('bot')" in toggle
    assert "setMode('classic')" in toggle
    assert "router.push" not in toggle
    assert "window.location" not in toggle
    assert "/app/assistant" not in toggle
    assert "/app/home" not in toggle
    assert "if (interfaceMode === 'bot')" in source
    shell = _source("frontend/src/components/shell/ai-workspace-shell.tsx")
    assert "setMode('classic')" in shell
    assert "window.location.assign('/app/home')" not in shell


def test_overview_and_cockpit_follow_the_same_toggle():
    dashboard = _source("frontend/src/components/views/dashboard-view.tsx")
    cockpit = _source("frontend/src/features/workforce/agent-detail-view.tsx")
    card = _source("frontend/src/features/workforce/components/agent-card.tsx")
    assert "mode === 'classic' ? 'analytics' : 'workforce'" in dashboard
    assert "mode === 'bot' ? 'console' : 'overview'" in cockpit
    assert "?tab=console" in card
    assert "${cockpitHref}?tab=" not in card
    assert "${agentPath}?tab=" in card
    shell = _source("frontend/src/components/shell/ai-workspace-shell.tsx")
    header = shell.split('data-testid="interface-mode-toggle"', 1)[1][:500]
    assert "setMode('classic')" in header
    assert "window.location" not in header
