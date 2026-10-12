"""
Grounded Narrative Synthesis and Anti-Hallucination Validator for OctaOS Executive Briefings.
Enforces that every numeric figure in generated narratives is anchored in the verified MetricsPayload.
"""
from __future__ import annotations

import re
import json
import logging
from typing import Dict, Any, List, Optional, Tuple

from app.schemas.orchestrator_briefing import MetricsPayload, Finding, ActionItem

logger = logging.getLogger(__name__)


class GroundingValidator:
    """Validates that numbers mentioned in generated text exist in the verified MetricsPayload."""

    @classmethod
    def extract_numbers(cls, text: str) -> List[float]:
        """Extracts candidate numeric scalars from text (percentages, currencies, counts)."""
        # Matches numbers like 24.5%, $425,000, 142, etc.
        raw_matches = re.findall(r"(?:[\$\£\€])?(\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?)(?:%)?", text)
        numbers = []
        for m in raw_matches:
            cleaned = m.replace(",", "")
            try:
                val = float(cleaned)
                # Ignore small structural numbers like 7, 30, 90 (phases) or 1..10 (agent IDs)
                if val not in [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 30.0, 90.0]:
                    numbers.append(val)
            except ValueError:
                continue
        return numbers

    @classmethod
    def validate(cls, text: str, metrics: MetricsPayload, tolerance_pct: float = 5.0) -> Tuple[bool, List[str]]:
        """
        Checks whether extracted numbers correlate with known metrics in the payload.
        Returns (is_valid, list_of_ungrounded_numbers).
        """
        extracted = cls.extract_numbers(text)
        if not extracted:
            return True, []

        valid_values = []
        for item in metrics.items.values():
            valid_values.append(item.value)
            if item.change_pct_wow is not None:
                valid_values.append(abs(item.change_pct_wow))

        for v in metrics.raw_funnel.values():
            valid_values.append(float(v))

        for stage_data in metrics.raw_deal_stages.values():
            valid_values.append(float(stage_data.get("count", 0)))
            valid_values.append(float(stage_data.get("value", 0.0)))

        for t_count in metrics.raw_ticket_distribution.values():
            valid_values.append(float(t_count))

        unanchored = []
        for num in extracted:
            # Check if num is close to any valid value
            matched = False
            for target in valid_values:
                if target == 0 and num == 0:
                    matched = True
                    break
                if target != 0 and abs(num - target) / (abs(target) + 1e-5) * 100.0 <= tolerance_pct:
                    matched = True
                    break
            if not matched:
                unanchored.append(str(num))

        return len(unanchored) == 0, unanchored


class NarrativeService:
    """Synthesizes C-level narratives and improvement plans grounded strictly in SQL metrics."""

    @classmethod
    def generate_deterministic_briefing(cls, metrics: MetricsPayload, findings: List[Finding]) -> str:
        """Factual data summary strictly grounded in SQL metrics without speculative narrative."""
        if metrics.empty_state:
            return (
                "Workspace Status: Clean state with no active leads, deals, or support tickets registered. "
                "Operational metrics will populate as activities are recorded."
            )

        leads_tot = metrics.items.get("leads.total")
        conv = metrics.items.get("leads.conversion_rate")
        pipeline = metrics.items.get("deals.pipeline_value")
        sla = metrics.items.get("tickets.sla_compliance")

        lead_txt = f"{int(leads_tot.value)} total leads" if leads_tot else "0 leads"
        conv_txt = f"{conv.formatted} conversion rate" if conv else "0.0% conversion"
        pipe_txt = f"{pipeline.formatted} pipeline" if pipeline else "$0 pipeline"
        sla_txt = f"{sla.formatted} SLA compliance" if sla else "100.0% SLA"

        crit_count = sum(1 for f in findings if f.severity == "CRITICAL")
        warn_count = sum(1 for f in findings if f.severity == "WARNING")

        alert_str = ""
        if crit_count > 0:
            alert_str = f" Flagged {crit_count} critical operational bottlenecks."
        elif warn_count > 0:
            alert_str = f" Flagged {warn_count} operational warnings."
        else:
            alert_str = " No operational bottlenecks detected."

        return (
            f"Operational Metrics Summary: Active operations reflect {lead_txt} with a {conv_txt}. "
            f"Deal pipeline stands at {pipe_txt}, and Customer Support maintains {sla_txt}.{alert_str}"
        )

    @classmethod
    def generate_deterministic_improvement_plan(
        cls, metrics: MetricsPayload, findings: List[Finding]
    ) -> List[ActionItem]:
        """Produces rule-grounded ActionItems mapped directly to verified findings. Returns empty list if no findings exist."""
        if metrics.empty_state or not findings:
            return []

        actions: List[ActionItem] = []
        action_idx = 1

        for finding in findings:
            if finding.id == "W-LEADS-UNASSIGNED":
                unassigned = int(metrics.items.get("leads.unassigned_count", 0).value if metrics.items.get("leads.unassigned_count") else 0)
                if unassigned > 0:
                    actions.append(
                        ActionItem(
                            id=f"ACT-7D-0{action_idx}",
                            phase="7d",
                            title=f"Assign {unassigned} Unassigned Leads",
                            description=f"Assign {unassigned} captured leads to sales team or automated outreach sequence.",
                            department="Sales",
                            action_type="sales_outreach",
                            parameters={"count": unassigned, "channel": "smtp"},
                            estimated_roi="",
                            requires_approval=True,
                        )
                    )
                    action_idx += 1
            elif finding.id == "W-LEADS-STALLED":
                stalled = int(metrics.items.get("leads.uncontacted_count", 0).value if metrics.items.get("leads.uncontacted_count") else 0)
                if stalled > 0:
                    actions.append(
                        ActionItem(
                            id=f"ACT-7D-0{action_idx}",
                            phase="7d",
                            title=f"Dispatch Follow-up Sequence to {stalled} Stalled Leads",
                            description=f"Trigger follow-up outreach for {stalled} leads in captured state.",
                            department="Sales",
                            action_type="sales_outreach",
                            parameters={"channel": "smtp", "count": stalled},
                            estimated_roi="",
                            requires_approval=True,
                        )
                    )
                    action_idx += 1
            elif finding.id == "W-SUPPORT-SLA":
                actions.append(
                    ActionItem(
                        id=f"ACT-30D-0{action_idx}",
                        phase="30d",
                        title="Review Stalled Support Tickets Exceeding SLA",
                        description="Prioritize resolution of support tickets that have exceeded the 48-hour resolution window.",
                        department="Support",
                        action_type="resolve_stalled_tickets",
                        parameters={"mode": "sla_remediation"},
                        estimated_roi="",
                        requires_approval=True,
                    )
                )
                action_idx += 1
            elif finding.id == "W-CONV-LOW":
                actions.append(
                    ActionItem(
                        id=f"ACT-90D-0{action_idx}",
                        phase="90d",
                        title="Audit Lead Qualification & Conversion Stages",
                        description="Review pipeline stages to identify conversion drop-off points.",
                        department="Sales",
                        action_type="optimize_pipeline",
                        parameters={},
                        estimated_roi="",
                        requires_approval=True,
                    )
                )
                action_idx += 1

        return actions
