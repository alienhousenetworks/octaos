"""Automated Commercial Proposal & Contract Document Generator.

Produces professional, publication-ready commercial agreements:
1. Complete Executive Summary and Scope of Deliverables.
2. Structured Itemized Commercial Schedule.
3. Rigorous SLAs, SOC2 / DPDP / GDPR Security Commitments.
4. Cryptographic SHA-256 Integrity Verification Hash.
5. Binding Signature Execution Blocks for Client & Provider.
"""
from typing import Dict, Any, Optional
import hashlib
import json
import time
from sqlalchemy.orm import Session

from app.models.deal_room import DealRoom, DealActivity
from app.services.sales_os.cpq.pricing_engine import QuoteCalculationResult


class ProposalDocumentGenerator:
    """Generates and archives formal B2B proposals and contracts."""

    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

    def generate_proposal(
        self,
        deal_room: DealRoom,
        quote: QuoteCalculationResult,
        client_signatory_name: Optional[str] = None,
        client_signatory_title: Optional[str] = None,
        custom_notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generates structured proposal Markdown and archives it in the deal room."""
        today = time.strftime("%B %d, %Y")
        valid_until = time.strftime("%B %d, %Y", time.localtime(time.time() + 30 * 86400))
        company_name = deal_room.company_name or "Target Enterprise"
        domain = deal_room.domain or "client.com"
        signatory_name = client_signatory_name or "Authorized Economic Buyer"
        signatory_title = client_signatory_title or "Executive Decision Maker"

        # Generate cryptographic integrity hash of the pricing payload
        terms_payload = {
            "quote_number": quote.quote_number,
            "company_name": company_name,
            "tenant_id": self.tenant_id,
            "gross_total_usd": quote.gross_total_usd,
            "net_total_usd": quote.net_total_usd,
            "contract_term_months": quote.contract_term_months,
            "payment_terms": quote.payment_terms,
            "line_items": [li.model_dump() if hasattr(li, "model_dump") else li.dict() for li in quote.line_items],
        }
        terms_hash = hashlib.sha256(
            json.dumps(terms_payload, sort_keys=True).encode("utf-8")
        ).hexdigest()

        special_notes_section = (
            f"### 6. Special Commercial Notes\n{custom_notes}\n" if custom_notes else ""
        )

        # Build Line Items Table
        line_item_rows = []
        for it in quote.line_items:
            line_item_rows.append(
                f"| **{it.name}**<br>*{it.description or ''}* | `{it.sku}` | {it.quantity} | "
                f"${it.unit_price:,.2f} | {it.discount_pct:.1f}% | **${it.line_net:,.2f}** |"
            )
        table_content = "\n".join(line_item_rows)

        # Markdown Document
        doc_md = f"""# Master Commercial Services Agreement & Proposal
**Document ID:** {quote.quote_number}  
**Date of Issuance:** {today}  
**Commercial Validity:** Through {valid_until} (30 Days)  
**Integrity Hash (SHA-256):** `{terms_hash[:16]}...{terms_hash[-8:]}`  

---

### Parties to Agreement
* **Service Provider:** OctaOS Autonomous Enterprise Systems Inc. ("Provider")
* **Client Organization:** {company_name} ("Client"), Domain: `{domain}`

---

### 1. Executive Summary & Statement of Work
Provider shall grant Client access to the OctaOS Autonomous Enterprise Platform. This deployment furnishes multi-agent sales swarms, durable cadence execution engines, and buying committee intelligence designed to accelerate enterprise pipeline creation and operational velocity across {company_name}'s go-to-market teams.

### 2. Commercial Investment Schedule
All figures in United States Dollars (USD), exclusive of applicable sales or statutory taxes.

| Solution Component | SKU | Qty | List Unit Price | Discount | Total Net Investment |
| :--- | :--- | :---: | :---: | :---: | :---: |
{table_content}

---

### 3. Financial Summary & Payment Terms
* **Gross Catalog Value:** ${quote.gross_total_usd:,.2f} USD
* **Multi-Year & Commitment Invoicing Credits ({quote.commitment_discount_pct:.1f}%):** -${quote.commitment_discount_amount:,.2f} USD
* **Commercial Concession ({quote.additional_discount_pct:.1f}%):** -${quote.additional_discount_amount:,.2f} USD
* **Total Net Contract Consideration:** **${quote.net_total_usd:,.2f} USD**
* **Contract Commitment:** {quote.contract_term_months} Months
* **Billing & Payment Terms:** {quote.payment_terms}

### 4. Projected Business ROI & Efficiency Value
* **Projected Annual Labor Savings:** ${quote.roi_model.projected_annual_labor_savings_usd:,.2f} USD
* **Estimated Payback Velocity:** ~{quote.roi_model.payback_period_months} Months
* **Expected 1-Year Net Value Return:** {quote.roi_model.projected_roi_pct:.1f}% ROI
* **Administrative Hours Recaptured:** ~{quote.roi_model.estimated_hours_saved_per_month} hours/month

---

### 5. Enterprise Governance, Security & SLA Commitments
1. **Service Level Agreement (SLA):** 99.9% scheduled platform availability.
2. **Data Isolation & Residency:** Client data remains encrypted in transit (TLS 1.3) and at rest (AES-256) within isolated tenant boundaries. No customer data is utilized to train third-party public foundation models without explicit opt-in.
3. **Compliance Standard:** Provider adheres to SOC 2 Type II controls, GDPR Article 28 data processing guidelines, and India DPDP Act statutory requirements.

{special_notes_section}
---

### 7. Authorized Acceptance & Signatures
IN WITNESS WHEREOF, the parties hereto have executed this Commercial Agreement as of the date signed below.

| Authorized Provider Signatory | Authorized Client Signatory |
| :--- | :--- |
| **OctaOS Autonomous Systems** | **{company_name}** |
| Signature: *[Digitally Signed - OctaOS Commercial Ops]* | Signature: ____________________________________ |
| Name: Marcus Vance | Name: {signatory_name} |
| Title: VP, Commercial Deal Desk | Title: {signatory_title} |
| Date: {today} | Date: ____________________________________ |
"""

        # Update Deal Room Metadata
        room_meta = dict(deal_room.account_brief or {})
        room_meta["latest_quote"] = quote.model_dump() if hasattr(quote, "model_dump") else quote.dict()
        room_meta["latest_proposal"] = {
            "quote_number": quote.quote_number,
            "terms_hash": terms_hash,
            "net_total_usd": quote.net_total_usd,
            "generated_at": today,
            "valid_until": valid_until,
            "markdown": doc_md,
            "signatory_name": signatory_name,
            "signatory_title": signatory_title,
            "policy_status": quote.policy_status,
        }
        deal_room.account_brief = room_meta

        # If stage is earlier than proposal, advance stage
        if deal_room.stage in ("discovered", "qualified", "researching", "outreach_ready", "in_cadence", "replied", "meeting_booked"):
            deal_room.stage = "proposal"

        # Log Deal Activity
        activity = DealActivity(
            deal_room_id=deal_room.id,
            tenant_id=self.tenant_id,
            activity_type="proposal_generated",
            channel="cpq",
            direction="outbound",
            subject=f"Commercial Proposal {quote.quote_number} generated (${quote.net_total_usd:,.2f})",
            content=f"Generated formal commercial proposal {quote.quote_number} for {company_name}. Terms hash: {terms_hash[:12]}",
            metadata_json={
                "quote_number": quote.quote_number,
                "net_total_usd": quote.net_total_usd,
                "terms_hash": terms_hash,
                "policy_status": quote.policy_status,
            },
        )
        self.db.add(activity)
        self.db.commit()

        return {
            "quote_number": quote.quote_number,
            "deal_room_id": deal_room.id,
            "company_name": company_name,
            "net_total_usd": quote.net_total_usd,
            "terms_hash": terms_hash,
            "policy_status": quote.policy_status,
            "proposal_markdown": doc_md,
            "generated_at": today,
            "valid_until": valid_until,
        }
