"""
Deterministic SQL metrics harvester for OctaOS Executive Briefings.
Gathers verified cross-vertical aggregates directly from SQLAlchemy models with strict tenant isolation.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.verticals import Lead, ContentPost, Ticket, Candidate, Transaction
from app.models.deal_room import DealRoom
from app.models.agents import ActivityLog
from app.schemas.orchestrator_briefing import MetricsPayload, MetricValue


class MetricsService:
    """Harvests deterministic tenant metrics from SQL without invoking an LLM."""

    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

    def harvest(self, period_days: int = 7) -> MetricsPayload:
        now = datetime.now(timezone.utc)
        current_start = now - timedelta(days=period_days)
        prior_start = current_start - timedelta(days=period_days)

        # 1. LEADS AGGREGATION
        leads_query = self.db.query(Lead).filter(Lead.tenant_id == self.tenant_id)
        all_leads = leads_query.all()
        total_leads = len(all_leads)
        
        leads_current_period = [l for l in all_leads if self._to_utc(l.created_at) and self._to_utc(l.created_at) >= current_start]
        leads_prior_period = [l for l in all_leads if self._to_utc(l.created_at) and prior_start <= self._to_utc(l.created_at) < current_start]
        
        lead_statuses: Dict[str, int] = {}
        unassigned_leads = 0
        uncontacted_leads = 0
        converted_leads = 0
        qualified_leads = 0

        for lead in all_leads:
            status = (lead.status or "captured").lower()
            lead_statuses[status] = lead_statuses.get(status, 0) + 1
            assigned = (lead.assigned_to or "").strip().lower()
            if not assigned or assigned in ["unassigned", "none"]:
                unassigned_leads += 1
            if status == "captured":
                uncontacted_leads += 1
            if status in ["qualified", "meeting_booked"]:
                qualified_leads += 1
            if status in ["converted", "won"]:
                converted_leads += 1

        conv_rate = (converted_leads / total_leads * 100.0) if total_leads > 0 else 0.0
        leads_delta = self._calc_pct_delta(len(leads_current_period), len(leads_prior_period))

        # 2. DEAL ROOM AGGREGATION
        deals = self.db.query(DealRoom).filter(DealRoom.tenant_id == self.tenant_id).all()
        total_deals = len(deals)
        pipeline_val = sum(float(d.annual_revenue_usd or 0.0) for d in deals if (d.stage or "").lower() not in ["lost"])
        won_val = sum(float(d.annual_revenue_usd or 0.0) for d in deals if (d.stage or "").lower() == "won")

        deals_current = [d for d in deals if self._to_utc(d.created_at) and self._to_utc(d.created_at) >= current_start]
        deals_prior = [d for d in deals if self._to_utc(d.created_at) and prior_start <= self._to_utc(d.created_at) < current_start]
        revenue_current = sum(float(d.annual_revenue_usd or 0.0) for d in deals_current if (d.stage or "").lower() == "won")
        revenue_prior = sum(float(d.annual_revenue_usd or 0.0) for d in deals_prior if (d.stage or "").lower() == "won")
        revenue_delta = self._calc_pct_delta(int(revenue_current), int(revenue_prior))

        pipeline_current = sum(float(d.annual_revenue_usd or 0.0) for d in deals_current if (d.stage or "").lower() not in ["lost"])
        pipeline_prior = sum(float(d.annual_revenue_usd or 0.0) for d in deals_prior if (d.stage or "").lower() not in ["lost"])
        pipeline_delta = self._calc_pct_delta(int(pipeline_current), int(pipeline_prior))

        deal_stages: Dict[str, Dict[str, Any]] = {}
        for d in deals:
            st = (d.stage or "discovered").lower()
            if st not in deal_stages:
                deal_stages[st] = {"count": 0, "value": 0.0}
            deal_stages[st]["count"] += 1
            deal_stages[st]["value"] += float(d.annual_revenue_usd or 0.0)

        # 3. SUPPORT TICKETS AGGREGATION
        tickets = self.db.query(Ticket).filter(Ticket.tenant_id == self.tenant_id).all()
        total_tickets = len(tickets)
        open_tickets = 0
        resolved_tickets = 0
        pending_human_tickets = 0
        stalled_tickets = 0
        ai_resolved_tickets = 0
        latencies: List[float] = []

        for t in tickets:
            st = (t.status or "open").lower()
            if st in ["open", "human_handling"]:
                open_tickets += 1
            elif st == "pending_human":
                pending_human_tickets += 1
            elif st in ["resolved", "closed"]:
                resolved_tickets += 1
                if (t.mode or "").lower() == "ai":
                    ai_resolved_tickets += 1
                if t.created_at and t.resolved_at:
                    c_dt = self._to_utc(t.created_at)
                    r_dt = self._to_utc(t.resolved_at)
                    if c_dt and r_dt and r_dt >= c_dt:
                        latencies.append((r_dt - c_dt).total_seconds() / 60.0)

            # Tickets created >48h ago still open
            ticket_created = self._to_utc(t.created_at)
            if ticket_created and ticket_created < (now - timedelta(hours=48)) and st not in ["resolved", "closed"]:
                stalled_tickets += 1

        tickets_current = [t for t in tickets if self._to_utc(t.created_at) and self._to_utc(t.created_at) >= current_start]
        tickets_prior = [t for t in tickets if self._to_utc(t.created_at) and prior_start <= self._to_utc(t.created_at) < current_start]
        tickets_delta = self._calc_pct_delta(len(tickets_current), len(tickets_prior))

        ticket_dist = {
            "open": open_tickets,
            "pending_human": pending_human_tickets,
            "resolved": resolved_tickets,
        }
        sla_compliance = ((total_tickets - stalled_tickets) / total_tickets * 100.0) if total_tickets > 0 else 100.0
        sla_breach_rate = (stalled_tickets / total_tickets * 100.0) if total_tickets > 0 else 0.0
        autonomous_deflection_rate = round((ai_resolved_tickets / resolved_tickets * 100.0), 1) if resolved_tickets > 0 else 0.0
        avg_resolution_latency_min = round(sum(latencies) / len(latencies), 1) if latencies else 0.0

        # 4. CONTENT & MARKETING POSTS
        posts = self.db.query(ContentPost).filter(ContentPost.tenant_id == self.tenant_id).all()
        total_posts = len(posts)
        total_impressions = sum(float(p.impressions or 0.0) for p in posts)
        total_reach = sum(float(p.reach or 0.0) for p in posts)
        avg_eng = (sum(float(p.engagement_rate or 0.0) for p in posts) / total_posts) if total_posts > 0 else 0.0
        avg_ctr = (sum(float(p.ctr or 0.0) for p in posts) / total_posts) if total_posts > 0 else 0.0

        posts_current = [p for p in posts if self._to_utc(p.created_at) and self._to_utc(p.created_at) >= current_start]
        posts_prior = [p for p in posts if self._to_utc(p.created_at) and prior_start <= self._to_utc(p.created_at) < current_start]
        posts_delta = self._calc_pct_delta(len(posts_current), len(posts_prior))

        posts_with_citation = sum(1 for p in posts if p.external_url or (p.impressions or 0) > 0 or (p.engagement or 0) > 0)
        brand_citation_rate = round((posts_with_citation / total_posts * 100.0), 1) if total_posts > 0 else 0.0

        channel_map: Dict[str, Dict[str, Any]] = {}
        for p in posts:
            plat = (p.platform or "general").lower()
            if plat not in channel_map:
                channel_map[plat] = {"platform": plat, "impressions": 0.0, "engagements": 0.0, "posts": 0}
            channel_map[plat]["impressions"] += float(p.impressions or 0.0)
            channel_map[plat]["engagements"] += float(p.engagement or 0.0)
            channel_map[plat]["posts"] += 1

        channel_perf: List[Dict[str, Any]] = []
        for k, v in channel_map.items():
            rate = (v["engagements"] / v["impressions"] * 100.0) if v["impressions"] > 0 else 0.0
            channel_perf.append({
                "platform": k,
                "impressions": int(v["impressions"]),
                "engagement_rate": round(rate, 2),
                "posts": v["posts"]
            })

        # 5. HR CANDIDATES & FINANCE ANOMALIES
        candidates = self.db.query(Candidate).filter(Candidate.tenant_id == self.tenant_id).all()
        candidates_current = [c for c in candidates if self._to_utc(c.created_at) and self._to_utc(c.created_at) >= current_start]
        candidates_prior = [c for c in candidates if self._to_utc(c.created_at) and prior_start <= self._to_utc(c.created_at) < current_start]
        candidates_delta = self._calc_pct_delta(len(candidates_current), len(candidates_prior))

        screened_candidates = sum(1 for c in candidates if (c.status or "").lower() in ["screened", "interviewed", "offered", "hired"])
        screening_pass_rate = round((screened_candidates / len(candidates) * 100.0), 1) if candidates else 0.0
        interviews_scheduled = sum(1 for c in candidates if (c.status or "").lower() in ["interviewed", "offered", "hired"])
        hired_count = sum(1 for c in candidates if (c.status or "").lower() == "hired")
        hiring_value_created = round(hired_count * 3500.0, 2)

        screen_hours_list = []
        for c in candidates:
            if (c.status or "").lower() != "sourced" and c.created_at:
                c_dt = self._to_utc(c.created_at)
                if c_dt:
                    hours = max(0.5, (now - c_dt).total_seconds() / 3600.0)
                    screen_hours_list.append(min(hours, 72.0))
        time_to_screen_hours = round(sum(screen_hours_list) / len(screen_hours_list), 1) if screen_hours_list else 0.0

        transactions = self.db.query(Transaction).filter(Transaction.tenant_id == self.tenant_id).all()
        tx_anomalies = sum(1 for tx in transactions if tx.is_anomaly)
        tx_volume = sum(float(tx.amount or 0.0) for tx in transactions)

        # 6. AGENT ACTIVITY LOGS
        logs = self.db.query(ActivityLog).filter(ActivityLog.tenant_id == self.tenant_id).all()
        agent_acts: Dict[str, int] = {}
        for log in logs:
            name = log.agent_name or "System"
            agent_acts[name] = agent_acts.get(name, 0) + 1

        # Check empty state
        is_empty = (total_leads == 0 and total_deals == 0 and total_tickets == 0 and total_posts == 0 and len(candidates) == 0)

        # Build typed MetricValues
        items: Dict[str, MetricValue] = {
            "leads.total": MetricValue(
                metric_id="leads.total",
                name="Total Active Leads",
                value=float(total_leads),
                formatted=str(total_leads),
                unit="count",
                change_pct_wow=leads_delta,
                direction="up" if (leads_delta or 0) >= 0 else "down",
                category="sales",
            ),
            "leads.conversion_rate": MetricValue(
                metric_id="leads.conversion_rate",
                name="Lead Conversion Rate",
                value=round(conv_rate, 2),
                formatted=f"{round(conv_rate, 1)}%",
                unit="%",
                direction="up" if conv_rate >= 10.0 else "down",
                category="sales",
            ),
            "leads.unassigned_count": MetricValue(
                metric_id="leads.unassigned_count",
                name="Unassigned Leads",
                value=float(unassigned_leads),
                formatted=str(unassigned_leads),
                unit="count",
                direction="down" if unassigned_leads > 0 else "neutral",
                category="sales",
            ),
            "leads.uncontacted_count": MetricValue(
                metric_id="leads.uncontacted_count",
                name="Uncontacted Stalled Leads",
                value=float(uncontacted_leads),
                formatted=str(uncontacted_leads),
                unit="count",
                direction="down" if uncontacted_leads > 10 else "neutral",
                category="sales",
            ),
            "deals.pipeline_value": MetricValue(
                metric_id="deals.pipeline_value",
                name="Total Deal Pipeline",
                value=round(pipeline_val, 2),
                formatted=f"${int(pipeline_val):,}",
                unit="USD",
                change_pct_wow=pipeline_delta,
                direction="up" if pipeline_val > 0 else "neutral",
                category="finance",
            ),
            "deals.won_value": MetricValue(
                metric_id="deals.won_value",
                name="Closed Won Revenue",
                value=round(won_val, 2),
                formatted=f"${int(won_val):,}",
                unit="USD",
                change_pct_wow=revenue_delta,
                direction="up" if won_val > 0 else "neutral",
                category="finance",
            ),
            "tickets.open_count": MetricValue(
                metric_id="tickets.open_count",
                name="Open Support Tickets",
                value=float(open_tickets + pending_human_tickets),
                formatted=str(open_tickets + pending_human_tickets),
                unit="count",
                direction="neutral",
                category="support",
            ),
            "tickets.sla_compliance": MetricValue(
                metric_id="tickets.sla_compliance",
                name="Support SLA Compliance",
                value=round(sla_compliance, 1),
                formatted=f"{round(sla_compliance, 1)}%",
                unit="%",
                direction="up" if sla_compliance >= 90.0 else "down",
                category="support",
            ),
            "tickets.sla_breach_rate": MetricValue(
                metric_id="tickets.sla_breach_rate",
                name="SLA Breach Rate",
                value=round(sla_breach_rate, 1),
                formatted=f"{round(sla_breach_rate, 1)}%",
                unit="%",
                direction="down" if sla_breach_rate > 10.0 else "neutral",
                category="support",
            ),
            "marketing.total_posts": MetricValue(
                metric_id="marketing.total_posts",
                name="Published Social Posts",
                value=float(total_posts),
                formatted=str(total_posts),
                unit="count",
                change_pct_wow=posts_delta,
                direction="neutral",
                category="marketing",
            ),
            "marketing.total_impressions": MetricValue(
                metric_id="marketing.total_impressions",
                name="Social Reach & Impressions",
                value=round(total_impressions, 0),
                formatted=f"{int(total_impressions):,}",
                unit="impressions",
                direction="up" if total_impressions > 0 else "neutral",
                category="marketing",
            ),
            "marketing.avg_engagement_rate": MetricValue(
                metric_id="marketing.avg_engagement_rate",
                name="Avg Engagement Rate",
                value=round(avg_eng, 2),
                formatted=f"{round(avg_eng, 2)}%",
                unit="%",
                direction="up" if avg_eng >= 3.0 else "neutral",
                category="marketing",
            ),
            "hr.candidates_total": MetricValue(
                metric_id="hr.candidates_total",
                name="Total Candidates Sourced",
                value=float(len(candidates)),
                formatted=str(len(candidates)),
                unit="count",
                change_pct_wow=candidates_delta,
                direction="neutral",
                category="hr",
            ),
            "finance.transaction_anomalies": MetricValue(
                metric_id="finance.transaction_anomalies",
                name="Financial Anomalies",
                value=float(tx_anomalies),
                formatted=str(tx_anomalies),
                unit="count",
                direction="down" if tx_anomalies > 0 else "neutral",
                category="finance",
            ),
            "operations.agent_actions": MetricValue(
                metric_id="operations.agent_actions",
                name="Total AI Agent Actions",
                value=float(len(logs)),
                formatted=str(len(logs)),
                unit="count",
                direction="up",
                category="operations",
            ),
        }

        # Raw funnel fallback
        funnel_dict = {
            "captured": total_leads,
            "contacted": total_leads - uncontacted_leads,
            "qualified": qualified_leads,
            "converted": converted_leads,
        }

        raw_support_dict = {
            "deflection_rate": autonomous_deflection_rate,
            "avg_latency_min": avg_resolution_latency_min,
            "tickets_delta": tickets_delta,
        }

        raw_hr_dict = {
            "screening_pass_rate": screening_pass_rate,
            "interviews_scheduled": interviews_scheduled,
            "time_to_screen_hours": time_to_screen_hours,
            "hiring_value_created": hiring_value_created,
            "candidates_delta": candidates_delta,
        }

        raw_deltas_dict = {
            "leads": leads_delta,
            "posts": posts_delta,
            "tickets": tickets_delta,
            "revenue": revenue_delta,
            "pipeline": pipeline_delta,
            "candidates": candidates_delta,
        }

        return MetricsPayload(
            tenant_id=self.tenant_id,
            harvested_at=now.isoformat(),
            data_freshness="live",
            empty_state=is_empty,
            items=items,
            raw_funnel=funnel_dict,
            raw_deal_stages=deal_stages,
            raw_ticket_distribution=ticket_dist,
            raw_channel_performance=channel_perf,
            raw_agent_activity=agent_acts,
            raw_support_metrics=raw_support_dict,
            raw_hr_metrics=raw_hr_dict,
            raw_deltas=raw_deltas_dict,
        )

    def _calc_pct_delta(self, current: int, previous: int) -> Optional[float]:
        if previous == 0:
            return 100.0 if current > 0 else 0.0
        return round(((current - previous) / previous) * 100.0, 1)

    def _to_utc(self, dt: Optional[datetime]) -> Optional[datetime]:
        if not dt:
            return None
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)


