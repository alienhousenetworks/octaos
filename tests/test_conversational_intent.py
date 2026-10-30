from app.services.agents.intent_router import IntentRouter


def test_conversational_greetings_classified_correctly():
    """Verify that pure greetings, acknowledgments, and identity queries are classified as conversational."""
    for prompt in ["hi", "hello", "hey", "good morning", "who are you", "what can you do", "help", "thanks", "ok"]:
        mode, conf = IntentRouter.classify(prompt)
        assert mode == "conversational", f"Expected 'conversational' for '{prompt}', got '{mode}'"
        assert conf >= 0.90


def test_conversational_not_poisoned_by_prior_execution_history():
    """Verify that when a user says 'hi' after an execution task, it stays conversational rather than rerunning execution."""
    prior_execution_history = [
        {"role": "user", "content": "create one post for Diwali on alienhouse brand with caption Instagram post"},
        {"role": "assistant", "content": "Here is the Diwali post draft with image asset."},
    ]
    mode, conf = IntentRouter.classify("hi", messages=prior_execution_history)
    assert mode == "conversational", f"Expected 'conversational' for 'hi' after task, got '{mode}'"


def test_actionable_task_still_classified_as_execution():
    """Verify that explicit tasks containing greetings or actions still classify as execution."""
    mode, conf = IntentRouter.classify("create one post for Diwali on alienhouse brand with caption Instagram post")
    assert mode == "execution"
    assert conf >= 0.70
