"""Razorpay payment integration for OctaOS plan subscriptions (INR)."""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.base import Tenant, User
from app.models.enterprise import PaymentOrder, TenantSubscription
from app.services.audit_service import AuditService
from app.services.subscription_service import SubscriptionService

logger = logging.getLogger(__name__)

RAZORPAY_API = "https://api.razorpay.com/v1"


class RazorpayNotConfigured(Exception):
    pass


class RazorpayService:
    def __init__(self, db: Session):
        self.db = db
        self.key_id = (settings.RAZORPAY_KEY_ID or "").strip()
        self.key_secret = (settings.RAZORPAY_KEY_SECRET or "").strip()
        self.webhook_secret = (settings.RAZORPAY_WEBHOOK_SECRET or "").strip()
        self.currency = (settings.RAZORPAY_CURRENCY or "INR").upper()

    def is_configured(self) -> bool:
        return bool(self.key_id and self.key_secret)

    def public_config(self) -> Dict[str, Any]:
        return {
            "provider": "razorpay",
            "configured": self.is_configured(),
            "key_id": self.key_id if self.is_configured() else None,
            "currency": self.currency,
            "require_payment": bool(settings.RAZORPAY_REQUIRE_PAYMENT),
        }

    def _auth(self):
        return (self.key_id, self.key_secret)

    def _require(self):
        if not self.is_configured():
            raise RazorpayNotConfigured(
                "Razorpay is not configured. Set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET in .env"
            )

    def create_order_for_plan(
        self,
        *,
        tenant_id: str,
        plan_code: str,
        user: Optional[User] = None,
    ) -> Dict[str, Any]:
        self._require()
        sub_svc = SubscriptionService(self.db)
        sub_svc.seed_plans()
        plan = sub_svc.get_plan(plan_code)
        if not plan:
            raise ValueError(f"Unknown plan: {plan_code}")
        if plan_code == "enterprise":
            raise ValueError("Enterprise plan is sales-assisted. Contact support for custom invoicing.")

        # Amount in INR (paise)
        amount_major = float(plan.price_inr_monthly or 0)
        if self.currency != "INR":
            # fallback USD * 100 cents if someone forces USD (Razorpay primarily INR)
            amount_major = float(plan.price_usd_monthly or 0)
        if amount_major <= 0:
            raise ValueError("Plan has no billable amount")

        amount_paise = int(round(amount_major * 100))
        receipt = f"octa_{tenant_id[:8]}_{plan_code}_{uuid.uuid4().hex[:8]}"

        payload = {
            "amount": amount_paise,
            "currency": self.currency,
            "receipt": receipt,
            "notes": {
                "tenant_id": tenant_id,
                "plan_code": plan_code,
                "product": "octaos_subscription",
            },
        }
        resp = requests.post(
            f"{RAZORPAY_API}/orders",
            auth=self._auth(),
            json=payload,
            timeout=30,
        )
        if resp.status_code >= 400:
            logger.error("Razorpay order create failed: %s %s", resp.status_code, resp.text)
            raise RuntimeError(f"Razorpay order failed: {resp.text}")

        data = resp.json()
        order = PaymentOrder(
            tenant_id=tenant_id,
            plan_code=plan_code,
            provider="razorpay",
            amount=amount_major,
            amount_paise=amount_paise,
            currency=self.currency,
            status="created",
            razorpay_order_id=data.get("id"),
            receipt=receipt,
            notes={"razorpay_response": {"id": data.get("id"), "status": data.get("status")}},
            created_by=user.id if user else None,
        )
        self.db.add(order)
        self.db.commit()
        self.db.refresh(order)

        tenant = self.db.query(Tenant).filter(Tenant.id == tenant_id).first()
        prefill_name = (user.name if user else None) or (tenant.name if tenant else "")
        prefill_email = (user.email if user else None) or (tenant.company_email if tenant else "")

        AuditService.log_event(
            self.db,
            action="payment.order_created",
            tenant_id=tenant_id,
            user_id=user.id if user else None,
            resource="payment_order",
            resource_id=order.id,
            details={"plan_code": plan_code, "razorpay_order_id": order.razorpay_order_id, "amount": amount_major},
        )

        return {
            "order_id": order.id,
            "razorpay_order_id": order.razorpay_order_id,
            "amount": amount_major,
            "amount_paise": amount_paise,
            "currency": self.currency,
            "plan_code": plan_code,
            "plan_name": plan.name,
            "key_id": self.key_id,
            "name": "OctaOS",
            "description": f"OctaOS {plan.name} — monthly subscription",
            "prefill": {
                "name": prefill_name or "",
                "email": prefill_email or "",
            },
            "notes": payload["notes"],
            "theme": {"color": "#8b5cf6"},
        }

    def create_order_for_agents(
        self,
        *,
        tenant_id: str,
        agent_codes: List[str],
        user: Optional[User] = None,
    ) -> Dict[str, Any]:
        """Create order for custom selected modular agents with bundling discounts."""
        self._require()
        sub_svc = SubscriptionService(self.db)
        sub_svc.seed_plans()
        catalog = sub_svc.get_agent_catalog()
        cat_map = {item["id"]: item for item in catalog}

        cleaned = [a.lower().strip() for a in agent_codes if a.lower().strip() in cat_map]
        if not cleaned:
            raise ValueError("No valid agents selected")

        # If user picked only 1 agent, use that standalone plan directly
        if len(cleaned) == 1:
            code = cat_map[cleaned[0]]["plan_code"]
            return self.create_order_for_plan(tenant_id=tenant_id, plan_code=code, user=user)

        # If user picked all 4 agents, use the all_access bundle plan
        if len(cleaned) >= 4:
            return self.create_order_for_plan(tenant_id=tenant_id, plan_code="all_access", user=user)

        # Multi-agent selection: Calculate sum with 10% bundle discount
        total_inr = sum(cat_map[c]["price_inr_monthly"] for c in cleaned)
        total_usd = sum(cat_map[c]["price_usd_monthly"] for c in cleaned)
        # Apply 10% multi-agent bundle discount
        discount_rate = 0.90
        amount_major = round(total_inr * discount_rate, 2) if self.currency == "INR" else round(total_usd * discount_rate, 2)
        amount_paise = int(round(amount_major * 100))

        bundle_code = f"bundle_{'_'.join(cleaned)}"
        receipt = f"octa_{tenant_id[:8]}_{bundle_code[:12]}_{uuid.uuid4().hex[:6]}"

        payload = {
            "amount": amount_paise,
            "currency": self.currency,
            "receipt": receipt,
            "notes": {
                "tenant_id": tenant_id,
                "plan_code": bundle_code,
                "agent_codes": ",".join(cleaned),
                "product": "octaos_agent_bundle",
            },
        }
        resp = requests.post(
            f"{RAZORPAY_API}/orders",
            auth=self._auth(),
            json=payload,
            timeout=30,
        )
        if resp.status_code >= 400:
            logger.error("Razorpay multi-agent order create failed: %s %s", resp.status_code, resp.text)
            raise RuntimeError(f"Razorpay order failed: {resp.text}")

        data = resp.json()
        order = PaymentOrder(
            tenant_id=tenant_id,
            plan_code=bundle_code,
            provider="razorpay",
            amount=amount_major,
            amount_paise=amount_paise,
            currency=self.currency,
            status="created",
            razorpay_order_id=data.get("id"),
            receipt=receipt,
            notes={"agent_codes": cleaned, "razorpay_response": {"id": data.get("id"), "status": data.get("status")}},
            created_by=user.id if user else None,
        )
        self.db.add(order)
        self.db.commit()
        self.db.refresh(order)

        tenant = self.db.query(Tenant).filter(Tenant.id == tenant_id).first()
        prefill_name = (user.name if user else None) or (tenant.name if tenant else "")
        prefill_email = (user.email if user else None) or (tenant.company_email if tenant else "")

        agent_names = ", ".join([cat_map[c]["name"] for c in cleaned])
        return {
            "order_id": order.id,
            "razorpay_order_id": order.razorpay_order_id,
            "amount": amount_major,
            "amount_paise": amount_paise,
            "currency": self.currency,
            "plan_code": bundle_code,
            "plan_name": f"Custom Bundle ({agent_names})",
            "key_id": self.key_id,
            "name": "OctaOS",
            "description": f"OctaOS Custom Bundle: {agent_names}",
            "prefill": {
                "name": prefill_name or "",
                "email": prefill_email or "",
            },
            "notes": payload["notes"],
            "theme": {"color": "#8b5cf6"},
        }

    @staticmethod
    def verify_payment_signature(
        *,
        order_id: str,
        payment_id: str,
        signature: str,
        secret: str,
    ) -> bool:
        body = f"{order_id}|{payment_id}".encode("utf-8")
        expected = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature or "")

    def verify_and_activate(
        self,
        *,
        tenant_id: str,
        razorpay_order_id: str,
        razorpay_payment_id: str,
        razorpay_signature: str,
        user: Optional[User] = None,
    ) -> Dict[str, Any]:
        self._require()
        if not self.verify_payment_signature(
            order_id=razorpay_order_id,
            payment_id=razorpay_payment_id,
            signature=razorpay_signature,
            secret=self.key_secret,
        ):
            raise ValueError("Invalid Razorpay payment signature")

        order = (
            self.db.query(PaymentOrder)
            .filter(
                PaymentOrder.razorpay_order_id == razorpay_order_id,
                PaymentOrder.tenant_id == tenant_id,
            )
            .first()
        )
        if not order:
            raise ValueError("Payment order not found for this tenant")

        if order.status == "paid":
            # idempotent
            return {
                "status": "already_paid",
                "plan_code": order.plan_code,
                "entitlements": SubscriptionService(self.db).entitlements(tenant_id),
            }

        order.status = "paid"
        order.razorpay_payment_id = razorpay_payment_id
        order.razorpay_signature = razorpay_signature
        order.paid_at = datetime.now(timezone.utc)

        # Check if modular agent bundle or standard plan
        notes_agents = (order.notes or {}).get("agent_codes")
        if notes_agents:
            if isinstance(notes_agents, str):
                agent_list = [a.strip() for a in notes_agents.split(",") if a.strip()]
            else:
                agent_list = list(notes_agents)
            SubscriptionService(self.db).subscribe_agents(tenant_id, agent_list)
        else:
            SubscriptionService(self.db).change_plan(tenant_id, order.plan_code)

        sub = SubscriptionService(self.db).get_subscription(tenant_id)
        if sub:
            sub.razorpay_last_order_id = razorpay_order_id
            sub.razorpay_last_payment_id = razorpay_payment_id
            sub.status = "active"
        self.db.commit()

        AuditService.log_event(
            self.db,
            action="payment.verified",
            tenant_id=tenant_id,
            user_id=user.id if user else None,
            resource="payment_order",
            resource_id=order.id,
            details={
                "plan_code": order.plan_code,
                "razorpay_order_id": razorpay_order_id,
                "razorpay_payment_id": razorpay_payment_id,
                "amount": order.amount,
            },
        )

        return {
            "status": "paid",
            "plan_code": order.plan_code,
            "payment_id": razorpay_payment_id,
            "entitlements": SubscriptionService(self.db).entitlements(tenant_id),
        }

    def handle_webhook(self, raw_body: bytes, signature_header: Optional[str]) -> Dict[str, Any]:
        """Validate webhook signature and mark paid orders if needed."""
        if self.webhook_secret:
            if not signature_header:
                raise ValueError("Missing X-Razorpay-Signature")
            expected = hmac.new(
                self.webhook_secret.encode("utf-8"),
                raw_body,
                hashlib.sha256,
            ).hexdigest()
            if not hmac.compare_digest(expected, signature_header):
                raise ValueError("Invalid webhook signature")
        elif not settings.DEV:
            raise ValueError("RAZORPAY_WEBHOOK_SECRET not configured")

        payload = json.loads(raw_body.decode("utf-8") or "{}")
        event = payload.get("event")
        entity = (
            payload.get("payload", {})
            .get("payment", {})
            .get("entity", {})
        )
        payment_id = entity.get("id")
        order_id = entity.get("order_id")
        status = entity.get("status")
        notes = entity.get("notes") or {}
        tenant_id = notes.get("tenant_id")
        plan_code = notes.get("plan_code")

        if event in ("payment.captured", "payment.authorized") and status in ("captured", "authorized"):
            if order_id:
                order = (
                    self.db.query(PaymentOrder)
                    .filter(PaymentOrder.razorpay_order_id == order_id)
                    .first()
                )
                if order and order.status != "paid":
                    order.status = "paid"
                    order.razorpay_payment_id = payment_id
                    order.paid_at = datetime.now(timezone.utc)
                    tid = order.tenant_id or tenant_id
                    if tid and order.plan_code:
                        sub = SubscriptionService(self.db).change_plan(tid, order.plan_code)
                        sub.razorpay_last_order_id = order_id
                        sub.razorpay_last_payment_id = payment_id
                        sub.status = "active"
                    self.db.commit()
                    return {"handled": True, "event": event, "order_id": order_id, "status": "paid"}

            # fallback activate from notes if order row missing
            if tenant_id and plan_code:
                sub = SubscriptionService(self.db).change_plan(tenant_id, plan_code)
                sub.razorpay_last_payment_id = payment_id
                sub.razorpay_last_order_id = order_id
                sub.status = "active"
                self.db.commit()
                return {"handled": True, "event": event, "tenant_id": tenant_id, "status": "paid"}

        return {"handled": True, "event": event, "status": "ignored"}

    def list_orders(self, tenant_id: str, limit: int = 20):
        return (
            self.db.query(PaymentOrder)
            .filter(PaymentOrder.tenant_id == tenant_id)
            .order_by(PaymentOrder.created_at.desc())
            .limit(limit)
            .all()
        )
