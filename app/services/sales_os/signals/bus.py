"""Intent Signal Bus & Convergence Engine for Enterprise Sales OS.

Provides:
1. Signal Ingestion: Ingests ATS hiring surges, funding rounds, leadership changes, and technographic events.
2. Immutable Provenance: Anchors every signal to a SignalEvidence row with SHA256 payload hash.
3. Deterministic Exponential Decay: Applies half_life_days decay to calculate current effective signal strength.
4. Multi-Source Convergence: Detects independent signal families and applies convergence bonuses without duplicate stacking.
5. Canonical Score Reconciliation: Continuously updates SalesCompany.intent_score.
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.sales_intelligence import SalesCompany, SalesSignal, SignalEvidence
from app.services.sales_os.signals.convergence import convergence_bonus
from app.services.sales_os.signals.decay import age_in_days, effective_strength

logger = logging.getLogger(__name__)


def compute_payload_hash(payload: Dict[str, Any]) -> str:
    """Calculates deterministic SHA256 hash of payload."""
    serialized = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


class IntentSignalBus:
    """Enterprise intent signal coordination and convergence engine."""

    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

    def ingest_signal(
        self,
        company_id: str,
        signal_type: str,
        family: str,
        summary: str,
        base_strength: float = 75.0,
        source_confidence: float = 0.90,
        half_life_days: int = 30,
        source_key: str = "ats_greenhouse",
        source_url: Optional[str] = None,
        publisher: Optional[str] = None,
        observed_at: Optional[datetime] = None,
        payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Ingests a verified intent signal into the bus with immutable evidence.
        Recalculates company intent score with convergence stacking.
        """
        now = datetime.now(timezone.utc)
        observed = observed_at or now
        raw_payload = payload or {
            "signal_type": signal_type,
            "summary": summary,
            "source_key": source_key,
            "timestamp": observed.isoformat(),
        }
        payload_hash = compute_payload_hash(raw_payload)

        # 1. Create or retrieve SignalEvidence
        evidence = (
            self.db.query(SignalEvidence)
            .filter(
                SignalEvidence.tenant_id == self.tenant_id,
                SignalEvidence.source_key == source_key,
                SignalEvidence.payload_hash == payload_hash,
            )
            .first()
        )

        if not evidence:
            evidence = SignalEvidence(
                tenant_id=self.tenant_id,
                company_id=company_id,
                source_key=source_key,
                source_url=source_url,
                publisher=publisher or source_key,
                observed_at=observed,
                retrieved_at=now,
                excerpt=summary[:500] if summary else None,
                claim=summary,
                payload_hash=payload_hash,
                confidence=source_confidence,
            )
            self.db.add(evidence)
            self.db.commit()
            self.db.refresh(evidence)

        # 2. Upsert SalesSignal
        signal = (
            self.db.query(SalesSignal)
            .filter(
                SalesSignal.tenant_id == self.tenant_id,
                SalesSignal.company_id == company_id,
                SalesSignal.signal_type == signal_type,
                SalesSignal.payload_hash == payload_hash,
            )
            .first()
        )

        if not signal:
            signal = SalesSignal(
                tenant_id=self.tenant_id,
                company_id=company_id,
                evidence_id=evidence.id,
                signal_type=signal_type,
                family=family,
                base_strength=base_strength,
                source_confidence=source_confidence,
                half_life_days=half_life_days,
                observed_at=observed,
                retrieved_at=now,
                source_key=source_key,
                independent_key=payload_hash,
                summary=summary,
                payload_hash=payload_hash,
            )
            self.db.add(signal)
            self.db.commit()
            self.db.refresh(signal)

        # 3. Recalculate company intent score with convergence
        recalculated = self.recalculate_account_intent(company_id)

        return {
            "signal_id": signal.id,
            "company_id": company_id,
            "signal_type": signal.signal_type,
            "family": signal.family,
            "summary": signal.summary,
            "evidence_id": evidence.id,
            "effective_intent_score": recalculated.get("intent_score"),
            "convergence": recalculated.get("convergence"),
        }

    def recalculate_account_intent(self, company_id: str) -> Dict[str, Any]:
        """
        Calculates decayed strength for all account signals and adds convergence bonus.
        Updates SalesCompany.intent_score.
        """
        now = datetime.now(timezone.utc)
        signals = (
            self.db.query(SalesSignal)
            .filter(
                SalesSignal.tenant_id == self.tenant_id,
                SalesSignal.company_id == company_id,
            )
            .all()
        )

        if not signals:
            return {"intent_score": 0.0, "convergence": {"bonus": 0.0}}

        total_decayed_strength = 0.0
        signal_dicts: List[Dict[str, Any]] = []

        for s in signals:
            age = age_in_days(s.observed_at, now=now) or 0.0
            eff = effective_strength(
                s.base_strength or 50.0,
                s.source_confidence or 0.8,
                age,
                s.half_life_days or 30,
            )
            strength_val = eff if eff is not None else (s.base_strength or 50.0) * 0.5
            total_decayed_strength += strength_val

            signal_dicts.append({
                "id": s.id,
                "family": s.family,
                "signal_type": s.signal_type,
                "independent_key": s.independent_key or s.payload_hash,
                "decayed_strength": round(strength_val, 2),
                "age_days": round(age, 1),
            })

        # Calculate multi-source convergence bonus
        conv = convergence_bonus(signal_dicts)
        bonus = conv.get("bonus", 0.0)

        # Composite score capped between 0 and 100
        raw_score = (total_decayed_strength / max(1, len(signals))) + bonus
        composite_score = round(min(100.0, max(0.0, raw_score)), 1)

        # Update SalesCompany
        company = (
            self.db.query(SalesCompany)
            .filter(
                SalesCompany.id == company_id,
                SalesCompany.tenant_id == self.tenant_id,
            )
            .first()
        )
        if company:
            company.intent_score = composite_score
            self.db.commit()

        return {
            "company_id": company_id,
            "intent_score": composite_score,
            "decayed_signals_count": len(signals),
            "convergence": conv,
        }

    def get_account_signals(self, company_id: str) -> Dict[str, Any]:
        """Fetches detailed active signals and convergence calculation for an account."""
        now = datetime.now(timezone.utc)
        signals = (
            self.db.query(SalesSignal)
            .filter(
                SalesSignal.tenant_id == self.tenant_id,
                SalesSignal.company_id == company_id,
            )
            .order_by(desc(SalesSignal.observed_at))
            .all()
        )

        signal_list: List[Dict[str, Any]] = []
        for s in signals:
            age = age_in_days(s.observed_at, now=now) or 0.0
            eff = effective_strength(
                s.base_strength or 50.0,
                s.source_confidence or 0.8,
                age,
                s.half_life_days or 30,
            )
            signal_list.append({
                "id": s.id,
                "signal_type": s.signal_type,
                "family": s.family,
                "summary": s.summary,
                "source_key": s.source_key,
                "base_strength": s.base_strength,
                "source_confidence": s.source_confidence,
                "half_life_days": s.half_life_days,
                "age_days": round(age, 1),
                "effective_strength": round(eff, 2) if eff is not None else None,
                "observed_at": s.observed_at.isoformat() if s.observed_at else None,
            })

        conv = convergence_bonus([
            {
                "family": s["family"],
                "independent_key": s["id"],
            }
            for s in signal_list
        ])

        return {
            "company_id": company_id,
            "signals": signal_list,
            "convergence": conv,
        }

    def get_tenant_signal_feed(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Returns chronological feed of verified intent signals across all tenant accounts."""
        now = datetime.now(timezone.utc)
        signals = (
            self.db.query(SalesSignal, SalesCompany)
            .join(SalesCompany, SalesSignal.company_id == SalesCompany.id)
            .filter(SalesSignal.tenant_id == self.tenant_id)
            .order_by(desc(SalesSignal.observed_at))
            .limit(limit)
            .all()
        )

        feed: List[Dict[str, Any]] = []
        for s, c in signals:
            age = age_in_days(s.observed_at, now=now) or 0.0
            eff = effective_strength(
                s.base_strength or 50.0,
                s.source_confidence or 0.8,
                age,
                s.half_life_days or 30,
            )
            feed.append({
                "id": s.id,
                "company_id": c.id,
                "company_name": c.display_name or c.legal_name or c.canonical_domain or "Unknown Company",
                "canonical_domain": c.canonical_domain,
                "industry": c.industry,
                "intent_score": c.intent_score,
                "signal_type": s.signal_type,
                "family": s.family,
                "summary": s.summary,
                "source_key": s.source_key,
                "age_days": round(age, 1),
                "effective_strength": round(eff, 2) if eff is not None else None,
                "observed_at": s.observed_at.isoformat() if s.observed_at else None,
            })

        return feed
