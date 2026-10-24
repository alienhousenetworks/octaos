"""Tenant-scoped persistence for companies, evidence, signals, and outcomes."""
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.sales_intelligence import (
    AccountContact,
    ContactVerification,
    SalesCompany,
    SalesOpportunity,
    SalesSignal,
    SignalEvidence,
    SourceCost,
    SourceOutcome,
    SourceRecord,
    SourceRun,
)
from app.models.verticals import Lead
from app.services.sales_os.discovery.identity import canonical_domain, domain_from_email
from app.services.sales_os.signals.normalize import NormalizedSignal


def _now() -> datetime:
    return datetime.now(timezone.utc)


class SalesIntelligenceStore:
    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

    def _companies(self):
        return self.db.query(SalesCompany).filter(SalesCompany.tenant_id == self.tenant_id)

    def get_company(self, company_id: str) -> SalesCompany | None:
        return self._companies().filter(SalesCompany.id == company_id).first()

    def get_company_by_domain(self, domain: str | None) -> SalesCompany | None:
        if not domain:
            return None
        return self._companies().filter(SalesCompany.canonical_domain == domain).first()

    def list_companies(self, limit: int = 100) -> list[SalesCompany]:
        return self._companies().order_by(SalesCompany.updated_at.desc()).limit(limit).all()

    def list_companies_with_opportunity(
        self, limit: int = 100
    ) -> list[tuple[SalesCompany, SalesOpportunity | None]]:
        companies = self.list_companies(limit=limit)
        if not companies:
            return []
        company_ids = [c.id for c in companies]
        opps = (
            self.db.query(SalesOpportunity)
            .filter(
                SalesOpportunity.tenant_id == self.tenant_id,
                SalesOpportunity.company_id.in_(company_ids),
            )
            .order_by(SalesOpportunity.created_at.desc(), SalesOpportunity.id.desc())
            .all()
        )
        latest_by_company: dict[str, SalesOpportunity] = {}
        for opp in opps:
            if opp.company_id not in latest_by_company:
                latest_by_company[opp.company_id] = opp
        return [(c, latest_by_company.get(c.id)) for c in companies]

    def upsert_company(self, fields: dict, source_key: str) -> SalesCompany:
        domain = canonical_domain(fields.get("canonical_domain") or fields.get("website"))
        company = self.get_company_by_domain(domain) if domain else None
        if company is None and fields.get("id"):
            company = self.get_company(fields["id"])
        if company is None and not domain and fields.get("display_name"):
            company = self._companies().filter(SalesCompany.display_name == fields["display_name"]).first()
        created = company is None
        if company is None:
            company = SalesCompany(
                tenant_id=self.tenant_id,
                canonical_domain=domain,
                field_provenance={},
                conflicts=[],
                aliases=[],
            )
            self.db.add(company)
            self.db.flush()
        provenance = dict(company.field_provenance or {})
        conflicts = list(company.conflicts or [])
        for column in (
            "legal_name", "display_name", "industry", "employee_count", "employee_band",
            "hq_country", "hq_city", "website",
        ):
            incoming = fields.get(column)
            if incoming is None or incoming == "":
                continue
            current = getattr(company, column)
            if current in (None, ""):
                setattr(company, column, incoming)
                provenance[column] = {"source": source_key, "inferred": False}
            elif current != incoming:
                conflicts.append({"field": column, "kept": current, "rejected": incoming, "source": source_key})
        if domain and not company.canonical_domain:
            company.canonical_domain = domain
            provenance["canonical_domain"] = {"source": source_key, "inferred": False}
        alias = fields.get("display_name")
        aliases = list(company.aliases or [])
        if alias and alias not in aliases and alias != company.display_name:
            aliases.append(alias)
        company.aliases = aliases
        company.field_provenance = provenance
        company.conflicts = conflicts
        if not created:
            company.version = (company.version or 1) + 1
        self.db.flush()
        return company

    def record_signal(self, company_id: str, signal: NormalizedSignal, license_class: str | None = None) -> tuple[SignalEvidence, SalesSignal, bool]:
        evidence = (
            self.db.query(SignalEvidence)
            .filter(
                SignalEvidence.tenant_id == self.tenant_id,
                SignalEvidence.payload_hash == signal.payload_hash,
                SignalEvidence.source_key == signal.source_key,
            )
            .first()
        )
        created = evidence is None
        if evidence is None:
            evidence = SignalEvidence(
                tenant_id=self.tenant_id,
                company_id=company_id,
                source_key=signal.source_key,
                source_url=signal.source_url,
                observed_at=signal.observed_at,
                retrieved_at=signal.retrieved_at,
                excerpt=signal.excerpt,
                claim=signal.summary,
                payload_hash=signal.payload_hash,
                confidence=signal.source_confidence,
                license_class=license_class,
            )
            self.db.add(evidence)
            self.db.flush()
        existing_signal = (
            self.db.query(SalesSignal)
            .filter(
                SalesSignal.tenant_id == self.tenant_id,
                SalesSignal.company_id == company_id,
                SalesSignal.signal_type == signal.signal_type,
                SalesSignal.payload_hash == signal.payload_hash,
            )
            .first()
        )
        if existing_signal:
            return evidence, existing_signal, False
        row = SalesSignal(
            tenant_id=self.tenant_id,
            company_id=company_id,
            evidence_id=evidence.id,
            signal_type=signal.signal_type,
            family=signal.family,
            base_strength=signal.base_strength,
            source_confidence=signal.source_confidence,
            half_life_days=signal.half_life_days,
            observed_at=signal.observed_at,
            retrieved_at=signal.retrieved_at,
            source_key=signal.source_key,
            independent_key=signal.independent_key,
            summary=signal.summary,
            is_inferred=1 if signal.is_inferred else 0,
            inference_method=signal.inference_method,
            inference_model=signal.inference_model,
            payload_hash=signal.payload_hash,
        )
        self.db.add(row)
        self.db.flush()
        return evidence, row, created

    def list_signals(self, company_id: str) -> list[SalesSignal]:
        return (
            self.db.query(SalesSignal)
            .filter(SalesSignal.tenant_id == self.tenant_id, SalesSignal.company_id == company_id)
            .order_by(SalesSignal.retrieved_at.desc())
            .all()
        )

    def list_evidence(self, company_id: str) -> list[SignalEvidence]:
        return (
            self.db.query(SignalEvidence)
            .filter(SignalEvidence.tenant_id == self.tenant_id, SignalEvidence.company_id == company_id)
            .order_by(SignalEvidence.retrieved_at.desc())
            .all()
        )

    def upsert_contact(self, company_id: str, fields: dict, source_key: str) -> AccountContact | None:
        email = (fields.get("email") or "").strip().lower() or None
        if not email and not fields.get("provider_id") and not fields.get("full_name"):
            return None
        contact = None
        if email:
            contact = (
                self.db.query(AccountContact)
                .filter(AccountContact.tenant_id == self.tenant_id, AccountContact.email == email)
                .first()
            )
        if contact is None:
            contact = AccountContact(tenant_id=self.tenant_id, company_id=company_id, provider_ids={}, channels=[])
            self.db.add(contact)
        for column in ("full_name", "role_title", "seniority", "department", "phone", "linkedin_url"):
            incoming = fields.get(column)
            if incoming and not getattr(contact, column):
                setattr(contact, column, incoming)
        if email and not contact.email:
            contact.email = email
        if fields.get("provider_id"):
            ids = dict(contact.provider_ids or {})
            ids[source_key] = fields["provider_id"]
            contact.provider_ids = ids
        if fields.get("confidence") is not None and contact.confidence is None:
            contact.confidence = fields["confidence"]
        contact.is_inferred = 1 if fields.get("is_inferred") else 0
        contact.inference_method = fields.get("inference_method")
        contact.inference_model = fields.get("inference_model")
        self.db.flush()
        return contact

    def get_contact(self, contact_id: str) -> AccountContact | None:
        return (
            self.db.query(AccountContact)
            .filter(AccountContact.tenant_id == self.tenant_id, AccountContact.id == contact_id)
            .first()
        )

    def save_verification(self, contact_id: str, tier: dict) -> ContactVerification:
        row = ContactVerification(
            tenant_id=self.tenant_id,
            contact_id=contact_id,
            tier=tier["tier"],
            status=tier["status"],
            verifier=tier["verifier"],
            score=tier.get("score"),
            failure_reason=tier.get("failure_reason"),
            details=tier.get("details") or {},
            checked_at=_now(),
        )
        self.db.add(row)
        self.db.flush()
        return row

    def save_opportunity(self, company_id: str, scored: dict, tier6: str, evidence_ids: list[str]) -> SalesOpportunity:
        row = SalesOpportunity(
            tenant_id=self.tenant_id,
            company_id=company_id,
            stage="qualified" if tier6 == "READY" else "discovered",
            score=scored.get("score"),
            component_scores=scored.get("components") or {},
            explanation=scored,
            rationale=scored.get("explanation"),
            score_version=scored.get("score_version"),
            config_hash=scored.get("config_hash"),
            tier6_state=tier6,
            evidence_ids=evidence_ids,
        )
        self.db.add(row)
        self.db.flush()
        return row

    def latest_opportunity(self, company_id: str) -> SalesOpportunity | None:
        return (
            self.db.query(SalesOpportunity)
            .filter(SalesOpportunity.tenant_id == self.tenant_id, SalesOpportunity.company_id == company_id)
            .order_by(SalesOpportunity.created_at.desc())
            .first()
        )

    def start_run(self, query: str, trigger: str = "manual") -> SourceRun:
        run = SourceRun(
            tenant_id=self.tenant_id,
            trigger=trigger,
            status="running",
            query=query,
            counts={},
            checkpoint={},
            started_at=_now(),
        )
        self.db.add(run)
        self.db.flush()
        return run

    def finish_run(self, run: SourceRun, status: str, counts: dict, error_summary: str | None = None) -> None:
        run.status = status
        run.counts = counts
        run.error_summary = error_summary
        run.finished_at = _now()
        run.checkpoint = {"completed": True}
        self.db.flush()

    def add_source_record(self, run_id: str | None, provider_key: str, operation: str, status: str, request_id: str, reason: str | None = None, estimated_cost: float | None = None, actual_cost: float | None = None, latency_ms: int | None = None, response_hash: str | None = None) -> SourceRecord:
        row = SourceRecord(
            tenant_id=self.tenant_id,
            source_run_id=run_id,
            provider_key=provider_key,
            operation=operation,
            status=status,
            request_id=request_id,
            reason=reason,
            estimated_cost=estimated_cost,
            actual_cost=actual_cost,
            latency_ms=latency_ms,
            response_hash=response_hash,
        )
        self.db.add(row)
        self.db.flush()
        if estimated_cost is not None or actual_cost is not None:
            self.db.add(SourceCost(
                tenant_id=self.tenant_id,
                provider_key=provider_key,
                source_record_id=row.id,
                operation=operation,
                estimated_amount=estimated_cost,
                actual_amount=actual_cost,
            ))
            self.db.flush()
        return row

    def list_costs(self) -> list[SourceCost]:
        return self.db.query(SourceCost).filter(SourceCost.tenant_id == self.tenant_id).all()

    def add_outcome(self, fields: dict) -> SourceOutcome:
        row = SourceOutcome(
            tenant_id=self.tenant_id,
            provider_key=fields["provider_key"],
            company_id=fields.get("company_id"),
            contact_id=fields.get("contact_id"),
            opportunity_id=fields.get("opportunity_id"),
            lead_id=fields.get("lead_id"),
            outcome_type=fields["outcome_type"],
            amount=fields.get("amount"),
            touch_role=fields.get("touch_role") or "unknown",
            occurred_at=fields.get("occurred_at") or _now(),
        )
        self.db.add(row)
        self.db.flush()
        return row

    def list_outcomes(self) -> list[SourceOutcome]:
        return self.db.query(SourceOutcome).filter(SourceOutcome.tenant_id == self.tenant_id).all()

    def backfill_leads(self) -> dict[str, int]:
        created = linked = skipped = 0
        leads = self.db.query(Lead).filter(Lead.tenant_id == self.tenant_id).all()
        for lead in leads:
            domain = domain_from_email(lead.email)
            if not domain:
                skipped += 1
                continue
            existing = self.get_company_by_domain(domain)
            company = self.upsert_company(
                {
                    "canonical_domain": domain,
                    "display_name": lead.company or None,
                    "website": domain,
                },
                source_key=lead.source or "legacy_lead",
            )
            if existing is None:
                created += 1
            contact = None
            if lead.email:
                contact = self.upsert_contact(
                    company.id,
                    {
                        "full_name": lead.name or None,
                        "email": lead.email,
                        "phone": lead.phone or None,
                    },
                    source_key=lead.source or "legacy_lead",
                )
            lead.sales_company_id = company.id
            if contact:
                lead.sales_contact_id = contact.id
            linked += 1
        self.db.flush()
        return {"created_companies": created, "linked_leads": linked, "skipped_leads": skipped}

    def company_dict(self, company: SalesCompany) -> dict[str, Any]:
        return {
            "id": company.id,
            "canonical_domain": company.canonical_domain,
            "legal_name": company.legal_name,
            "display_name": company.display_name,
            "aliases": company.aliases or [],
            "industry": company.industry,
            "employee_count": company.employee_count,
            "hq_country": company.hq_country,
            "hq_city": company.hq_city,
            "website": company.website,
            "icp_score": company.icp_score,
            "intent_score": company.intent_score,
            "confidence": company.confidence,
            "deal_room_id": company.deal_room_id,
            "conflicts": company.conflicts or [],
            "field_provenance": company.field_provenance or {},
            "version": company.version,
        }
