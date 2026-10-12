"""
Pure function Plotly chart builders for OctaOS Executive Briefings.
Generates standard, schema-compliant Plotly JSON specifications for direct browser rendering.
"""
from __future__ import annotations

from typing import List
from app.schemas.orchestrator_briefing import MetricsPayload, PlotlyChartSpec


DARK_LAYOUT_TEMPLATE = {
    "paper_bgcolor": "rgba(0,0,0,0)",
    "plot_bgcolor": "rgba(0,0,0,0)",
    "font": {"color": "#94a3b8", "family": "Inter, sans-serif", "size": 11},
    "margin": {"l": 40, "r": 20, "t": 40, "b": 40},
    "legend": {"orientation": "h", "yanchor": "bottom", "y": -0.3, "xanchor": "center", "x": 0.5},
    "xaxis": {"gridcolor": "rgba(255,255,255,0.06)", "zerolinecolor": "rgba(255,255,255,0.1)"},
    "yaxis": {"gridcolor": "rgba(255,255,255,0.06)", "zerolinecolor": "rgba(255,255,255,0.1)"},
}


def build_funnel_chart(metrics: MetricsPayload) -> PlotlyChartSpec:
    """Builds lead acquisition and conversion funnel chart."""
    rf = metrics.raw_funnel or {}
    stages = ["Captured", "Contacted", "Qualified", "Converted"]
    vals = [
        rf.get("captured", 0),
        rf.get("contacted", 0),
        rf.get("qualified", 0),
        rf.get("converted", 0),
    ]

    colors = ["#8b5cf6", "#6366f1", "#3b82f6", "#10b981"]

    layout = {
        **DARK_LAYOUT_TEMPLATE,
        "title": {"text": "Lead Acquisition & Conversion Velocity", "font": {"color": "#ffffff", "size": 13}},
    }

    spec = {
        "data": [
            {
                "type": "funnel",
                "y": stages,
                "x": vals,
                "textinfo": "value+percent initial",
                "marker": {"color": colors},
                "connector": {"line": {"color": "rgba(255,255,255,0.15)", "width": 1}},
            }
        ],
        "layout": layout,
        "config": {"responsive": True, "displayModeBar": False},
    }

    return PlotlyChartSpec(
        chart_id="funnel_chart",
        title="Lead Conversion Funnel",
        description="Factual breakdown of lead stage progression from initial capture through conversion.",
        category="funnel",
        spec=spec,
    )


def build_pipeline_waterfall(metrics: MetricsPayload) -> PlotlyChartSpec:
    """Builds deal stage pipeline value bar chart."""
    stages_dict = metrics.raw_deal_stages or {}
    stages = list(stages_dict.keys()) or ["discovered", "qualified", "proposal", "won"]
    values = [stages_dict.get(s, {}).get("value", 0.0) for s in stages]
    counts = [stages_dict.get(s, {}).get("count", 0) for s in stages]

    labels = [f"{s.capitalize()} ({c})" for s, c in zip(stages, counts)]

    layout = {
        **DARK_LAYOUT_TEMPLATE,
        "title": {"text": "Pipeline Value by Stage ($ USD)", "font": {"color": "#ffffff", "size": 13}},
        "yaxis": {"title": "Pipeline ($)", "gridcolor": "rgba(255,255,255,0.06)"},
    }

    spec = {
        "data": [
            {
                "type": "bar",
                "x": labels,
                "y": values,
                "marker": {
                    "color": "#3b82f6",
                    "line": {"color": "#60a5fa", "width": 1},
                },
                "text": [f"${int(v):,}" for v in values],
                "textposition": "auto",
            }
        ],
        "layout": layout,
        "config": {"responsive": True, "displayModeBar": False},
    }

    return PlotlyChartSpec(
        chart_id="pipeline_waterfall",
        title="Deal Pipeline by Stage",
        description="Active capital distribution across sales pipeline deal stages.",
        category="financial",
        spec=spec,
    )


def build_channel_performance_chart(metrics: MetricsPayload) -> PlotlyChartSpec:
    """Builds multi-channel social impressions and engagement chart."""
    channels = metrics.raw_channel_performance or []
    if not channels:
        platforms = ["LinkedIn", "Meta", "Twitter"]
        impressions = [0, 0, 0]
        rates = [0.0, 0.0, 0.0]
    else:
        platforms = [c.get("platform", "").capitalize() for c in channels]
        impressions = [c.get("impressions", 0) for c in channels]
        rates = [c.get("engagement_rate", 0.0) for c in channels]

    layout = {
        **DARK_LAYOUT_TEMPLATE,
        "title": {"text": "Audience Reach & Engagement by Channel", "font": {"color": "#ffffff", "size": 13}},
        "yaxis": {"title": "Reach / Impressions", "gridcolor": "rgba(255,255,255,0.06)"},
        "yaxis2": {
            "title": "Engagement Rate (%)",
            "overlaying": "y",
            "side": "right",
            "showgrid": False,
            "font": {"color": "#34d399"},
        },
    }

    spec = {
        "data": [
            {
                "type": "bar",
                "name": "Impressions",
                "x": platforms,
                "y": impressions,
                "marker": {"color": "#8b5cf6"},
            },
            {
                "type": "scatter",
                "mode": "lines+markers",
                "name": "Eng. Rate (%)",
                "x": platforms,
                "y": rates,
                "yaxis": "y2",
                "line": {"color": "#10b981", "width": 2},
                "marker": {"size": 8, "color": "#10b981"},
            },
        ],
        "layout": layout,
        "config": {"responsive": True, "displayModeBar": False},
    }

    return PlotlyChartSpec(
        chart_id="channel_performance",
        title="Channel Growth & Engagement",
        description="Comparative visibility and audience engagement rate across marketing channels.",
        category="overview",
        spec=spec,
    )


def build_support_sla_chart(metrics: MetricsPayload) -> PlotlyChartSpec:
    """Builds support ticket health and resolution distribution donut chart."""
    tickets = metrics.raw_ticket_distribution or {}
    labels = ["Resolved", "Open Active", "Pending Human"]
    values = [
        tickets.get("resolved", 0),
        tickets.get("open", 0),
        tickets.get("pending_human", 0),
    ]

    colors = ["#10b981", "#3b82f6", "#f59e0b"]

    layout = {
        **DARK_LAYOUT_TEMPLATE,
        "title": {"text": "Support Queue Status & SLA Ratio", "font": {"color": "#ffffff", "size": 13}},
    }

    spec = {
        "data": [
            {
                "type": "pie",
                "hole": 0.55,
                "labels": labels,
                "values": values,
                "marker": {"colors": colors},
                "textinfo": "label+percent",
            }
        ],
        "layout": layout,
        "config": {"responsive": True, "displayModeBar": False},
    }

    return PlotlyChartSpec(
        chart_id="support_sla_chart",
        title="Support Ticket Health",
        description="Ticket resolution ratios and human escalation queue volume.",
        category="operations",
        spec=spec,
    )


def build_agent_throughput_chart(metrics: MetricsPayload) -> PlotlyChartSpec:
    """Builds operational throughput bar chart by specialized agent."""
    acts = metrics.raw_agent_activity or {}
    agents = list(acts.keys()) or ["Sales AI Agent", "Marketing AI Agent", "Support AI Agent"]
    counts = [acts.get(a, 0) for a in agents]

    layout = {
        **DARK_LAYOUT_TEMPLATE,
        "title": {"text": "Agent Autonomous Actions Completed", "font": {"color": "#ffffff", "size": 13}},
        "yaxis": {"title": "Completed Tasks", "gridcolor": "rgba(255,255,255,0.06)"},
    }

    spec = {
        "data": [
            {
                "type": "bar",
                "x": agents,
                "y": counts,
                "marker": {"color": ["#8b5cf6", "#ec4899", "#3b82f6", "#10b981", "#f59e0b"][:len(agents)]},
            }
        ],
        "layout": layout,
        "config": {"responsive": True, "displayModeBar": False},
    }

    return PlotlyChartSpec(
        chart_id="agent_throughput",
        title="AI Workforce Throughput",
        description="Execution volume across specialized AI agents in the workspace.",
        category="operations",
        spec=spec,
    )


def build_all_charts(metrics: MetricsPayload) -> List[PlotlyChartSpec]:
    """Generates the full suite of visual analytics charts for executive briefings."""
    return [
        build_funnel_chart(metrics),
        build_pipeline_waterfall(metrics),
        build_channel_performance_chart(metrics),
        build_support_sla_chart(metrics),
        build_agent_throughput_chart(metrics),
    ]
