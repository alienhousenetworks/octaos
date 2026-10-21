"""CPQ (Configure-Price-Quote) and Deal Desk services."""
from app.services.sales_os.cpq.pricing_engine import CPQPricingEngine, QuoteCalculationResult, QuoteLineItem
from app.services.sales_os.cpq.proposal_generator import ProposalDocumentGenerator
from app.services.sales_os.cpq.stage_gatekeeper import StageTransitionGatekeeper

__all__ = [
    "CPQPricingEngine",
    "QuoteCalculationResult",
    "QuoteLineItem",
    "ProposalDocumentGenerator",
    "StageTransitionGatekeeper",
]
