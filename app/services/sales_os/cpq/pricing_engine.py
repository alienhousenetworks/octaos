"""Deterministic CPQ Pricing Engine and Dynamic Floor Gatekeeper.

Enforces financial integrity:
1. Multi-tier catalog line items with quantity & unit price scaling.
2. Volume tier discount curves and multi-year commitment incentives.
3. Strict Gross Margin & Floor Price Gatekeeping (blocks deals under $5,000 USD net or exceeding 35% discount).
4. Code-level approval routing matching the Enterprise Autonomy Ladder (L0/L1/L2).
5. Explainable ROI & Payback modeling.
"""
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
import uuid


class QuoteLineItem(BaseModel):
    sku: str
    name: str
    description: Optional[str] = None
    unit_price: float = Field(..., ge=0.0)
    quantity: int = Field(default=1, ge=1)
    discount_pct: float = Field(default=0.0, ge=0.0, le=100.0)
    line_gross: float = 0.0
    line_discount_amount: float = 0.0
    line_net: float = 0.0


class ROIProjection(BaseModel):
    projected_annual_labor_savings_usd: float
    payback_period_months: float
    projected_roi_pct: float
    estimated_hours_saved_per_month: int


class QuoteCalculationResult(BaseModel):
    quote_number: str
    contract_term_months: int
    payment_terms: str
    line_items: List[QuoteLineItem]
    gross_total_usd: float
    commitment_discount_pct: float
    commitment_discount_amount: float
    additional_discount_pct: float
    additional_discount_amount: float
    total_discount_pct: float
    total_discount_amount: float
    net_total_usd: float
    floor_price_usd: float
    floor_violation: bool
    policy_status: str  # auto_approved | requires_manager_approval | requires_vp_approval | blocked
    approval_tier: str   # L2 | L1 | L0 | BLOCKED
    policy_reason: str
    roi_model: ROIProjection


STANDARD_CATALOG = [
    {
        "sku": "OCTA-PLATFORM",
        "name": "OctaOS Core Autonomous Platform",
        "description": "Enterprise multi-agent control plane, canonical data model & audit logging.",
        "price": 18000.0,
    },
    {
        "sku": "OCTA-SALES-SWARM",
        "name": "Dedicated Sales Swarm Capacity",
        "description": "Autonomous prospecting, cadence execution, meeting booking & inbox copilot.",
        "price": 12000.0,
    },
    {
        "sku": "OCTA-ENTERPRISE-SLA",
        "name": "Enterprise Governance & Security SLA",
        "description": "SOC2/GDPR boundary controls, 99.9% uptime SLA, and dedicated engineering support.",
        "price": 6000.0,
    },
    {
        "sku": "OCTA-INTEGRATIONS",
        "name": "CRM & ERP Custom Integration Module",
        "description": "Real-time bidirectional sync for Salesforce, HubSpot, and internal warehouse.",
        "price": 5000.0,
    },
]


class CPQPricingEngine:
    """Calculates deterministic pricing, discount approvals, and margin floor compliance."""

    MINIMUM_DEAL_FLOOR_USD = 5000.0
    MAXIMUM_DISCOUNT_CEILING_PCT = 35.0

    @classmethod
    def get_commitment_discount_pct(cls, contract_term_months: int) -> float:
        """Multi-year commitment discounts."""
        if contract_term_months >= 36:
            return 10.0
        if contract_term_months >= 24:
            return 5.0
        return 0.0

    @classmethod
    def get_volume_discount_pct(cls, total_quantity: int) -> float:
        """Volume tiered discounts."""
        if total_quantity >= 21:
            return 10.0
        if total_quantity >= 6:
            return 5.0
        return 0.0

    @classmethod
    def calculate_quote(
        cls,
        line_items_input: List[Dict[str, Any]],
        requested_discount_pct: float = 0.0,
        contract_term_months: int = 12,
        payment_terms: str = "Net 30",
        quote_number: Optional[str] = None,
    ) -> QuoteCalculationResult:
        """Calculates commercial quote totals, discounts, ROI, and approval gates."""
        q_num = quote_number or f"Q-{uuid.uuid4().hex[:6].upper()}"
        
        # 1. Process Line Items
        processed_items: List[QuoteLineItem] = []
        gross_total = 0.0
        total_quantity = 0

        for raw in line_items_input:
            unit_price = float(raw.get("unit_price") or raw.get("price") or 0.0)
            qty = int(raw.get("quantity") or 1)
            item_disc = float(raw.get("discount_pct") or 0.0)

            line_gross = round(unit_price * qty, 2)
            line_disc_amt = round(line_gross * (item_disc / 100.0), 2)
            line_net = round(line_gross - line_disc_amt, 2)

            total_quantity += qty
            gross_total += line_gross

            processed_items.append(
                QuoteLineItem(
                    sku=raw.get("sku") or "CUSTOM-SKU",
                    name=raw.get("name") or "Product Item",
                    description=raw.get("description"),
                    unit_price=unit_price,
                    quantity=qty,
                    discount_pct=item_disc,
                    line_gross=line_gross,
                    line_discount_amount=line_disc_amt,
                    line_net=line_net,
                )
            )

        if not processed_items:
            # Default to standard base platform
            base = STANDARD_CATALOG[0]
            gross_total = base["price"]
            processed_items.append(
                QuoteLineItem(
                    sku=base["sku"],
                    name=base["name"],
                    description=base["description"],
                    unit_price=base["price"],
                    quantity=1,
                    discount_pct=0.0,
                    line_gross=base["price"],
                    line_discount_amount=0.0,
                    line_net=base["price"],
                )
            )
            total_quantity = 1

        # 2. Multi-Year & Volume Commitments
        commitment_discount_pct = cls.get_commitment_discount_pct(contract_term_months)
        volume_discount_pct = cls.get_volume_discount_pct(total_quantity)

        # Baseline combined structural discount
        structural_discount_pct = min(commitment_discount_pct + volume_discount_pct, 15.0)
        structural_discount_amt = round(gross_total * (structural_discount_pct / 100.0), 2)

        # 3. Discretionary Additional Discount requested by Rep
        additional_discount_pct = max(0.0, requested_discount_pct)
        
        # Effective combined discount percentage
        total_discount_pct = round(structural_discount_pct + additional_discount_pct, 2)
        total_discount_amt = round(gross_total * (total_discount_pct / 100.0), 2)
        net_total = max(0.0, round(gross_total - total_discount_amt, 2))

        # 4. Floor Price & Margin Check
        floor_violation = False
        if net_total < cls.MINIMUM_DEAL_FLOOR_USD:
            floor_violation = True
        if total_discount_pct > cls.MAXIMUM_DISCOUNT_CEILING_PCT:
            floor_violation = True

        # 5. Autonomy Level & Approval Routing
        if floor_violation:
            policy_status = "blocked"
            approval_tier = "BLOCKED"
            if total_discount_pct > cls.MAXIMUM_DISCOUNT_CEILING_PCT:
                policy_reason = f"Combined discount ({total_discount_pct:.1f}%) exceeds hard policy ceiling of {cls.MAXIMUM_DISCOUNT_CEILING_PCT}%."
            else:
                policy_reason = f"Net contract value (${net_total:,.2f}) violates minimum deal floor of ${cls.MINIMUM_DEAL_FLOOR_USD:,.2f} USD."
        elif total_discount_pct > 20.0:
            policy_status = "requires_vp_approval"
            approval_tier = "L0"
            policy_reason = f"Substantial discount of {total_discount_pct:.1f}% requires VP of Sales / Commercial Director escalation."
        elif total_discount_pct > 10.0:
            policy_status = "requires_manager_approval"
            approval_tier = "L1"
            policy_reason = f"Discount of {total_discount_pct:.1f}% requires Sales Manager approval."
        else:
            policy_status = "auto_approved"
            approval_tier = "L2"
            policy_reason = "Commercial terms meet standard pricing policy and are auto-approved."

        # 6. ROI & Payback Model
        annual_labor_saved = round(gross_total * 3.4, 2)
        monthly_saving = annual_labor_saved / 12.0
        payback_months = round(net_total / monthly_saving, 1) if monthly_saving > 0 else 0.0
        projected_roi = (
            round(((annual_labor_saved - net_total) / net_total) * 100.0, 1) if net_total > 0 else 0.0
        )

        roi = ROIProjection(
            projected_annual_labor_savings_usd=annual_labor_saved,
            payback_period_months=payback_months,
            projected_roi_pct=projected_roi,
            estimated_hours_saved_per_month=160,
        )

        return QuoteCalculationResult(
            quote_number=q_num,
            contract_term_months=contract_term_months,
            payment_terms=payment_terms,
            line_items=processed_items,
            gross_total_usd=gross_total,
            commitment_discount_pct=structural_discount_pct,
            commitment_discount_amount=structural_discount_amt,
            additional_discount_pct=additional_discount_pct,
            additional_discount_amount=round(gross_total * (additional_discount_pct / 100.0), 2),
            total_discount_pct=total_discount_pct,
            total_discount_amount=total_discount_amt,
            net_total_usd=net_total,
            floor_price_usd=cls.MINIMUM_DEAL_FLOOR_USD,
            floor_violation=floor_violation,
            policy_status=policy_status,
            approval_tier=approval_tier,
            policy_reason=policy_reason,
            roi_model=roi,
        )
