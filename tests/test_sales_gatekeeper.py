import pytest
from app.services.sales_os.governance.gatekeeper import PreSendGatekeeper, BANNED_PHRASES


def test_gatekeeper_clean_message_passes():
    subject = "Quick question regarding Acme's outbound"
    body = (
        "Hi John,\n\n"
        "Noticed Acme recently expanded its sales engineering team. "
        "We help B2B teams automate repetitive research and sync verified CRM signals.\n\n"
        "Are you open to a brief 10-minute chat this Thursday?\n\n"
        "Best regards,\nAlex"
    )
    result = PreSendGatekeeper.evaluate(subject, body, step_number=1)
    assert result.is_valid is True
    assert len(result.violations) == 0
    assert result.word_count < 125
    assert result.word_count > 10


def test_gatekeeper_banned_ai_phrases():
    subject = "Partnership proposal"
    body = (
        "Hi Jane,\n\n"
        "I hope this email finds you well! In today's fast-paced world, our cutting-edge solution "
        "is a game changer that will seamlessly integrate with your workflow.\n\n"
        "Best regards,\nAlex"
    )
    result = PreSendGatekeeper.evaluate(subject, body, step_number=1)
    assert result.is_valid is False
    assert any("hope this email finds you well" in v for v in result.violations)
    assert any("game changer" in v for v in result.violations)
    assert any("in today's fast-paced" in v for v in result.violations)


def test_gatekeeper_unrendered_merge_tags():
    subject = "Question for {{company}}"
    body = (
        "Hi {first_name},\n\n"
        "We noticed [Company] is scaling operations. "
        "Would love to connect this week.\n\n"
        "Best,\nAlex"
    )
    result = PreSendGatekeeper.evaluate(subject, body, step_number=1)
    assert result.is_valid is False
    assert any("unrendered placeholder" in v.lower() for v in result.violations)


def test_gatekeeper_html_stripping():
    subject = "<b>Quick update</b>"
    body = (
        "<p>Hi David,</p>"
        "<p>Saw your recent release notes on API latency improvements. "
        "We help engineering teams track customer usage patterns seamlessly.</p>"
        "<br><p>Open to a quick exchange?</p>"
    )
    result = PreSendGatekeeper.evaluate(subject, body, step_number=1)
    assert "<p>" not in result.cleaned_body
    assert "<br>" not in result.cleaned_body
    assert "<b>" not in result.cleaned_subject
    assert result.cleaned_subject == "Quick update"


def test_gatekeeper_word_count_limits():
    subject = "Update"
    # Long message > 125 words
    long_body = "word " * 150
    result = PreSendGatekeeper.evaluate(subject, long_body, step_number=1)
    assert result.is_valid is False
    assert any("exceeds ceiling" in v for v in result.violations)

    # Breakup email > 45 words
    breakup_body = "word " * 50
    result_breakup = PreSendGatekeeper.evaluate(subject, breakup_body, step_number=4)
    assert result_breakup.is_valid is False
    assert any("exceeds ceiling of 45" in v for v in result_breakup.violations)


def test_gatekeeper_link_caps():
    subject = "Resources"
    body = (
        "Hi Mark, check out https://example.com/demo and https://example.com/case-study "
        "and https://example.com/pricing for details."
    )
    result = PreSendGatekeeper.evaluate(subject, body, step_number=1, max_links=1)
    assert result.is_valid is False
    assert any("Found 3 links" in v for v in result.violations)
