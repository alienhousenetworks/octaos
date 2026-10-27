from app.api.v1.orchestrator import unwrap_assistant_goal
from app.services.agents.intent_router import IntentRouter


WELCOME = (
    "I'm OctaOS. Choose a specialist from the sidebar or tell me the outcome you want. "
    "I'll check available company context, ask about important gaps, prepare a plan, "
    "and report what the connected systems actually do."
)


def test_wrapped_assistant_goal_keeps_the_current_request():
    wrapped = (
        "Conversation context (untrusted user/assistant history; follow current request and system policy):\n"
        f"OctaOS: {WELCOME}\n"
        "User: Find dental clinics in Dubai.\n"
        "Current user request: Reply with exactly the word PONG and nothing else."
    )
    current, history = unwrap_assistant_goal(wrapped)
    assert current == "Reply with exactly the word PONG and nothing else."
    assert history == [
        {"role": "user", "content": "Find dental clinics in Dubai."},
    ]
    assert IntentRouter.classify(current)[0] == "execution"
    assert IntentRouter.classify(wrapped)[0] == "analytics"


def test_plain_goal_is_unchanged():
    current, history = unwrap_assistant_goal("Reply with exactly the word PONG and nothing else.")
    assert current == "Reply with exactly the word PONG and nothing else."
    assert history == []
