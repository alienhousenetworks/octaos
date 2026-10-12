import pytest
from app.services.agents.intent_router import IntentRouter


LABELED_PROMPTS = [
    # --- EXECUTION PROMPTS (15) ---
    ("Create 5 posts for LinkedIn about AI employees", "execution"),
    ("Source 10 senior React developers in San Francisco", "execution"),
    ("Send email outreach to all qualified leads with subject Partnership", "execution"),
    ("Schedule interview with candidate John Doe for tomorrow 3pm", "execution"),
    ("Generate a 7-day Instagram content campaign on meal prep", "execution"),
    ("Find 20 marketing agencies in London and email them", "execution"),
    ("Draft property descriptions for 123 Main Street", "execution"),
    ("Post daily specials to Facebook and Instagram", "execution"),
    ("Hire developers with 5+ years python experience salary $140k", "execution"),
    ("Send pitch proposal to prospective client Acme Corp", "execution"),
    ("Create posts for Twitter regarding product launch", "execution"),
    ("Source 5 CTOs at early stage startups in New York", "execution"),
    ("Schedule meeting on Google Calendar for Friday morning", "execution"),
    ("Generate campaign with image prompts and video prompts", "execution"),
    ("Write blog outline on AI automation for agencies", "execution"),

    # --- ANALYTICS PROMPTS (15) ---
    ("Generate a full executive report on our current operations", "analytics"),
    ("How are our campaigns and lead conversions performing?", "analytics"),
    ("What are our biggest operational weaknesses and bottlenecks?", "analytics"),
    ("Give me a CEO briefing with charts of revenue and conversion", "analytics"),
    ("Audit our customer support tickets and SLA breach rate", "analytics"),
    ("Show me our deal pipeline value and stage waterfall", "analytics"),
    ("What is our conversion rate and audience reach by channel?", "analytics"),
    ("Diagnose current operations and highlight stalled accounts", "analytics"),
    ("Visual analytics of lead funnel velocity with Plotly charts", "analytics"),
    ("How did our sales pipeline grow this month compared to last?", "analytics"),
    ("Review our operational KPIs and agent actions completed", "analytics"),
    ("What are our financial transaction anomalies?", "analytics"),
    ("Executive health check of our workspace metrics", "analytics"),
    ("Report on support queue backlog and response latency", "analytics"),
    ("Provide a breakdown of marketing impressions across platforms", "analytics"),

    # --- HYBRID PROMPTS (10) ---
    ("Why is conversion low, and fix it", "hybrid"),
    ("Audit our lead pipeline and schedule outreach to stalled leads", "hybrid"),
    ("Diagnose operational bottlenecks and create improvement posts", "hybrid"),
    ("Find weaknesses in our support queue and resolve them", "hybrid"),
    ("Audit our lead funnel and then source 10 new qualified leads", "hybrid"),
    ("Why is our SLA breaching and schedule staff interviews to fix it", "hybrid"),
    ("Review campaign engagement weaknesses and generate 3 new posts", "hybrid"),
    ("Diagnose why revenue stalled and launch outreach campaign", "hybrid"),
    ("Audit our conversion drop and fix it immediately", "hybrid"),
    ("Find weaknesses in sales cadence and send re-engagement emails", "hybrid"),
]


@pytest.mark.parametrize("prompt,expected_mode", LABELED_PROMPTS)
def test_intent_classification(prompt, expected_mode):
    mode, conf = IntentRouter.classify(prompt)
    assert mode == expected_mode, f"Failed for '{prompt}': got {mode}, expected {expected_mode} (conf: {conf})"
    assert conf >= 0.70
