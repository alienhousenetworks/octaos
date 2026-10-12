"""
Rule-based vulnerability and bottleneck detectors for OctaOS Executive Briefings.
Inspects deterministic MetricsPayload and emits strongly-grounded Finding instances.
"""
from __future__ import annotations

from typing import List
from app.schemas.orchestrator_briefing import MetricsPayload, Finding


def detect_all_findings(metrics: MetricsPayload) -> List[Finding]:
    """Runs all rule-based detectors against the verified metrics payload."""
    findings: List[Finding] = []

    # 1. Empty workspace: return empty findings list
    if metrics.empty_state:
        return findings

    # 2. Lead stagnation & conversion drop detector
    leads_total = metrics.items.get("leads.total")
    conv_rate = metrics.items.get("leads.conversion_rate")
    unassigned = metrics.items.get("leads.unassigned_count")
    uncontacted = metrics.items.get("leads.uncontacted_count")

    if unassigned and unassigned.value >= 10:
        findings.append(
            Finding(
                id="W-LEADS-UNASSIGNED",
                title=f"Unassigned Inbound Leads ({int(unassigned.value)} accounts)",
                severity="CRITICAL" if unassigned.value >= 25 else "WARNING",
                category="revenue_leak",
                metric_citations=["leads.unassigned_count", "leads.total"],
                evidence=f"{int(unassigned.value)} active leads currently lack an assigned agent or sales representative.",
                root_cause=f"{int(unassigned.value)} captured leads have not been assigned to a representative or AI sales workflow.",
                impact="Unassigned accounts risk extended contact latency and lower outreach velocity.",
            )
        )

    if uncontacted and uncontacted.value >= 15:
        findings.append(
            Finding(
                id="W-LEADS-STALLED",
                title=f"Stalled Uncontacted Inbound Leads ({int(uncontacted.value)} accounts)",
                severity="CRITICAL" if uncontacted.value >= 30 else "WARNING",
                category="bottleneck",
                metric_citations=["leads.uncontacted_count", "leads.conversion_rate"],
                evidence=f"{int(uncontacted.value)} leads remain in captured state without outreach dispatched.",
                root_cause=f"{int(uncontacted.value)} leads have not received an initial contact sequence or cadence enrollment.",
                impact="Lead decay risk increases with delayed initial outreach window.",
            )
        )

    if conv_rate and leads_total and leads_total.value >= 20 and conv_rate.value < 5.0:
        findings.append(
            Finding(
                id="W-CONV-LOW",
                title=f"Depressed Lead-to-Conversion Rate ({conv_rate.formatted})",
                severity="WARNING",
                category="conversion_drop",
                metric_citations=["leads.conversion_rate", "leads.total"],
                evidence=f"Overall lead-to-conversion rate is {conv_rate.formatted} across {int(leads_total.value)} total leads.",
                root_cause="Low qualification-to-close progression rate observed in current lead pipeline.",
                impact="Reduced throughput and lower revenue yield per captured lead.",
            )
        )

    # 3. Support queue SLA breach detector (requires statistically meaningful volume >= 5 tickets)
    sla_breach = metrics.items.get("tickets.sla_breach_rate")
    open_tickets = metrics.items.get("tickets.open_count")
    total_tickets = sum(metrics.raw_ticket_distribution.values()) if metrics.raw_ticket_distribution else 0

    if sla_breach and sla_breach.value >= 20.0 and total_tickets >= 5 and open_tickets and open_tickets.value > 0:
        findings.append(
            Finding(
                id="W-SUPPORT-SLA",
                title=f"Elevated Support SLA Breach Rate ({sla_breach.formatted})",
                severity="CRITICAL" if sla_breach.value >= 35.0 else "WARNING",
                category="sla_breach",
                metric_citations=["tickets.sla_breach_rate", "tickets.open_count"],
                evidence=f"{sla_breach.formatted} of {total_tickets} support tickets have exceeded the 48-hour SLA resolution window.",
                root_cause=f"{int(sla_breach.value)}% of support tickets remained open beyond target resolution SLA threshold.",
                impact="Extended resolution turnaround times for active support tickets.",
            )
        )
    elif open_tickets and open_tickets.value >= 20:
        findings.append(
            Finding(
                id="W-SUPPORT-VOLUME",
                title=f"High Support Queue Backlog ({int(open_tickets.value)} tickets)",
                severity="WARNING",
                category="bottleneck",
                metric_citations=["tickets.open_count"],
                evidence=f"{int(open_tickets.value)} support tickets currently pending resolution.",
                root_cause=f"Active support queue backlog has accumulated to {int(open_tickets.value)} open tickets.",
                impact="Potential queue delay if inbound volume exceeds current resolution rate.",
            )
        )

    # 4. Financial anomalies detector
    anomalies = metrics.items.get("finance.transaction_anomalies")
    if anomalies and anomalies.value > 0:
        findings.append(
            Finding(
                id="W-FIN-ANOMALY",
                title=f"Flagged Financial Transaction Anomalies ({int(anomalies.value)} detected)",
                severity="CRITICAL",
                category="revenue_leak",
                metric_citations=["finance.transaction_anomalies"],
                evidence=f"{int(anomalies.value)} transactions flagged as anomalous by ledger validation.",
                root_cause=f"{int(anomalies.value)} transactions were flagged with ledger or payment anomalies.",
                impact="Potential billing discrepancies requiring review.",
            )
        )

    return findings
