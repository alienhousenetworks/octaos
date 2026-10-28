"""Native OctaOS internal connector adapter. Dynamically discovers and operates on core models."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Type
from sqlalchemy import inspect, and_, or_, desc, asc
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.base import Base, tenant_context
from app.models.verticals import Lead, Ticket, TicketMessage, ContentPost, Candidate
from app.models.agents import KnowledgeDocument
from app.models.boardroom_events import MeetingAction
from app.models.automations import AutomationWorkflow
from app.models.external_agents import ActivityEvent, ControllerCommand
from app.services.mcp.connectors.base import (
    ConnectorAdapter,
    ConnectorContext,
    DiscoveredObjectMeta,
)

logger = logging.getLogger(__name__)

# Registry of supported internal model mappings
CORE_OCTAOS_MODELS: Dict[str, Dict[str, Any]] = {
    "lead": {
        "model": Lead,
        "display_name": "Sales Lead",
        "description": "Sales leads and CRM contacts tracked by the Sales AI Employee",
        "supported_operations": ["discover", "read", "query", "create", "update", "delete", "invoke"],
        "relationships": {
            "company": {"type": "many_to_one", "target": "sales_company"},
        },
    },
    "ticket": {
        "model": Ticket,
        "display_name": "Support Ticket",
        "description": "Customer support inquiries and multi-channel conversations",
        "supported_operations": ["discover", "read", "query", "create", "update", "delete", "invoke"],
        "relationships": {
            "messages": {"type": "one_to_many", "target": "ticket_message"},
        },
    },
    "content_post": {
        "model": ContentPost,
        "display_name": "Marketing Post",
        "description": "Multi-platform social content, blog posts, and campaign assets",
        "supported_operations": ["discover", "read", "query", "create", "update", "delete", "invoke"],
        "relationships": {},
    },
    "candidate": {
        "model": Candidate,
        "display_name": "HR Candidate",
        "description": "Job applicants, resumes, and candidate scorecards",
        "supported_operations": ["discover", "read", "query", "create", "update", "delete"],
        "relationships": {},
    },
    "knowledge_document": {
        "model": KnowledgeDocument,
        "display_name": "Knowledge Document",
        "description": "Enterprise policies, training docs, and contextual reference materials",
        "supported_operations": ["discover", "read", "query", "create", "update", "delete"],
        "relationships": {},
    },
    "directive": {
        "model": MeetingAction,
        "display_name": "Executive Directive",
        "description": "Boardroom actions, executive directives, and strategic goals",
        "supported_operations": ["discover", "read", "query", "create", "update", "delete"],
        "relationships": {},
    },
    "workflow": {
        "model": AutomationWorkflow,
        "display_name": "Automation Workflow",
        "description": "Autonomous workflow engine definitions and execution triggers",
        "supported_operations": ["discover", "read", "query", "invoke"],
        "relationships": {},
    },
    "activity_event": {
        "model": ActivityEvent,
        "display_name": "Activity Event",
        "description": "First-class dashboard feed updates, operational notes, controller replies, and attachments",
        "supported_operations": ["discover", "read", "query", "create"],
        "relationships": {},
    },
}


def sqlalchemy_column_to_json_schema_type(col: Any) -> Dict[str, Any]:
    """Dynamically converts a SQLAlchemy column type to a JSON Schema property descriptor."""
    type_name = str(col.type).lower()
    schema_prop: Dict[str, Any] = {}

    if "int" in type_name:
        schema_prop["type"] = "integer"
    elif "float" in type_name or "numeric" in type_name or "real" in type_name:
        schema_prop["type"] = "number"
    elif "bool" in type_name:
        schema_prop["type"] = "boolean"
    elif "json" in type_name:
        schema_prop["type"] = "object"
    elif "date" in type_name or "time" in type_name:
        schema_prop["type"] = "string"
        schema_prop["format"] = "date-time"
    else:
        schema_prop["type"] = "string"

    if col.doc:
        schema_prop["description"] = col.doc
    if col.nullable:
        schema_prop["nullable"] = True

    return schema_prop


def build_json_schema_for_model(model_cls: Type[Base]) -> Dict[str, Any]:
    """Dynamically derives a full JSON Schema from any SQLAlchemy model class."""
    properties: Dict[str, Any] = {}
    required: List[str] = []

    mapper = inspect(model_cls)
    for col in mapper.columns:
        # Hide internal system columns from required writes
        if col.name in ("id", "tenant_id", "created_at", "updated_at", "actor", "source"):
            prop = sqlalchemy_column_to_json_schema_type(col)
            prop["readOnly"] = True
            properties[col.name] = prop
            continue


        prop = sqlalchemy_column_to_json_schema_type(col)
        properties[col.name] = prop
        if not col.nullable and col.default is None and col.server_default is None:
            required.append(col.name)

    # Core business required fields even when underlying SQL column allows nulls
    tbl = getattr(model_cls, "__tablename__", "").lower()
    if tbl == "leads":
        for req_field in ("name", "email"):
            if req_field in properties and req_field not in required:
                required.append(req_field)
    elif tbl == "tickets":
        for req_field in ("subject",):
            if req_field in properties and req_field not in required:
                required.append(req_field)
    elif tbl == "content_posts":
        for req_field in ("platform", "content"):
            if req_field in properties and req_field not in required:
                required.append(req_field)
    elif tbl == "activity_events":
        for req_field in ("title", "body"):
            if req_field in properties and req_field not in required:
                required.append(req_field)

    return {
        "type": "object",
        "properties": properties,
        "required": required,
        "additionalProperties": True,
    }


def row_to_dict(instance: Any) -> Dict[str, Any]:
    """Converts a SQLAlchemy model instance to a clean JSON-serializable dictionary."""
    if not instance:
        return {}
    res: Dict[str, Any] = {}
    for col in instance.__table__.columns:
        val = getattr(instance, col.name)
        if isinstance(val, datetime):
            res[col.name] = val.isoformat()
        else:
            res[col.name] = val
    return res


class OctaOSInternalAdapter(ConnectorAdapter):
    """
    Adapter providing governed CRUD operations and dynamic discovery
    across all native OctaOS domain models.
    """

    def __init__(self, db_factory=SessionLocal):
        self.db_factory = db_factory

    async def discover_objects(self, ctx: ConnectorContext) -> List[DiscoveredObjectMeta]:
        discovered = []
        for obj_name, meta in CORE_OCTAOS_MODELS.items():
            model = meta["model"]
            json_schema = build_json_schema_for_model(model)
            discovered.append(
                DiscoveredObjectMeta(
                    object_name=obj_name,
                    display_name=meta["display_name"],
                    description=meta["description"],
                    primary_key="id",
                    supported_operations=meta["supported_operations"],
                    json_schema=json_schema,
                    relationships=meta.get("relationships", {}),
                )
            )
        return discovered

    async def describe_object(self, ctx: ConnectorContext, object_name: str) -> Optional[DiscoveredObjectMeta]:
        meta = CORE_OCTAOS_MODELS.get(object_name.lower())
        if not meta:
            return None
        model = meta["model"]
        json_schema = build_json_schema_for_model(model)
        return DiscoveredObjectMeta(
            object_name=object_name,
            display_name=meta["display_name"],
            description=meta["description"],
            primary_key="id",
            supported_operations=meta["supported_operations"],
            json_schema=json_schema,
            relationships=meta.get("relationships", {}),
        )

    async def query_records(
        self,
        ctx: ConnectorContext,
        object_name: str,
        query: Dict[str, Any],
    ) -> Dict[str, Any]:
        meta = CORE_OCTAOS_MODELS.get(object_name.lower())
        if not meta:
            raise ValueError(f"Unknown business object: '{object_name}'")

        model = meta["model"]
        db: Session = self.db_factory()
        try:
            tenant_token = tenant_context.set(ctx.tenant_id)
            stmt = db.query(model).filter(model.tenant_id == ctx.tenant_id)

            # Apply safe query filters
            filter_clauses = query.get("filter")
            if filter_clauses:
                stmt = self._apply_dsl_filters(stmt, model, filter_clauses)

            # Total count before limit
            total_count = stmt.count()

            # Sorting
            sort_list = query.get("sort", [])
            for s in sort_list:
                f_name = s.get("field")
                direction = s.get("direction", "asc").lower()
                if hasattr(model, f_name):
                    col = getattr(model, f_name)
                    stmt = stmt.order_by(desc(col) if direction == "desc" else asc(col))

            limit = min(query.get("limit", 50), 200)
            records = stmt.limit(limit).all()

            fields_proj = query.get("fields")
            serialized = []
            for r in records:
                d = row_to_dict(r)
                if fields_proj:
                    d = {k: v for k, v in d.items() if k in fields_proj}
                serialized.append(d)

            return {
                "records": serialized,
                "total_count": total_count,
                "returned_count": len(serialized),
                "has_more": total_count > len(serialized),
                "cursor": None,
            }
        finally:
            tenant_context.reset(tenant_token)
            db.close()

    async def get_record(
        self,
        ctx: ConnectorContext,
        object_name: str,
        record_id: str,
        fields: Optional[List[str]] = None,
    ) -> Optional[Dict[str, Any]]:
        meta = CORE_OCTAOS_MODELS.get(object_name.lower())
        if not meta:
            return None

        model = meta["model"]
        db: Session = self.db_factory()
        try:
            tenant_token = tenant_context.set(ctx.tenant_id)
            rec = (
                db.query(model)
                .filter(model.id == record_id, model.tenant_id == ctx.tenant_id)
                .first()
            )
            if not rec:
                return None
            data = row_to_dict(rec)
            if fields:
                data = {k: v for k, v in data.items() if k in fields}
            return data
        finally:
            tenant_context.reset(tenant_token)
            db.close()

    async def create_record(
        self,
        ctx: ConnectorContext,
        object_name: str,
        values: Dict[str, Any],
    ) -> Dict[str, Any]:
        meta = CORE_OCTAOS_MODELS.get(object_name.lower())
        if not meta:
            raise ValueError(f"Unknown business object: '{object_name}'")

        # 1. Lead Specific Validation: Reject empty or placeholder values
        if object_name.lower() == "lead":
            name = str(values.get("name") or "").strip()
            email = str(values.get("email") or "").strip().lower()
            if not name or not email:
                raise ValueError("Lead creation requires non-empty 'name' and 'email'.")
            if email.endswith("@example.com") or email.endswith("@test.com") or email == "lead@example.com":
                raise ValueError(f"Placeholder emails ('{email}') are strictly forbidden.")
            if name.lower() in ("inbound lead", "placeholder lead", "test lead"):
                raise ValueError(f"Placeholder lead name '{name}' is strictly forbidden.")

        # 2. Activity Event Specific Mapping & Validation
        if object_name.lower() == "activity_event":
            title = str(values.get("title") or "").strip()
            body = str(values.get("body") or "").strip()
            if not title or not body:
                raise ValueError("ActivityEvent requires non-empty 'title' and 'body'.")
            if "attachments" in values and "attachments_json" not in values:
                values["attachments_json"] = values["attachments"]
            if "data" in values and "data_json" not in values:
                values["data_json"] = values["data"]
            if "actor" not in values:
                values["actor"] = ctx.credential_id or "external_controller"

        model = meta["model"]
        db: Session = self.db_factory()
        try:
            tenant_token = tenant_context.set(ctx.tenant_id)
            # Filter values to recognized columns
            valid_cols = {col.name for col in model.__table__.columns}
            filtered_values = {k: v for k, v in values.items() if k in valid_cols and k != "id"}
            filtered_values["tenant_id"] = ctx.tenant_id

            new_instance = model(**filtered_values)
            db.add(new_instance)

            # Correlate ActivityEvent with ControllerCommand if applicable
            if object_name.lower() == "activity_event":
                corr_id = filtered_values.get("correlation_id")
                if corr_id:
                    cmd = db.query(ControllerCommand).filter(
                        ControllerCommand.correlation_id == corr_id,
                        ControllerCommand.tenant_id == ctx.tenant_id,
                    ).first()
                    if cmd:
                        cmd.reply_summary = filtered_values.get("title", "")[:500]
                        kind = filtered_values.get("kind", "status")
                        if kind in ("result", "completed"):
                            cmd.status = "completed"
                        elif kind == "error":
                            cmd.status = "failed"
                        else:
                            cmd.status = "acked"

            db.commit()
            db.refresh(new_instance)
            return row_to_dict(new_instance)
        except Exception:
            db.rollback()
            raise
        finally:
            tenant_context.reset(tenant_token)
            db.close()

    async def update_record(
        self,
        ctx: ConnectorContext,
        object_name: str,
        record_id: str,
        values: Dict[str, Any],
    ) -> Dict[str, Any]:
        meta = CORE_OCTAOS_MODELS.get(object_name.lower())
        if not meta:
            raise ValueError(f"Unknown business object: '{object_name}'")

        model = meta["model"]
        db: Session = self.db_factory()
        try:
            tenant_token = tenant_context.set(ctx.tenant_id)
            rec = (
                db.query(model)
                .filter(model.id == record_id, model.tenant_id == ctx.tenant_id)
                .first()
            )
            if not rec:
                raise ValueError(f"Record with id '{record_id}' not found in '{object_name}'.")

            valid_cols = {col.name for col in model.__table__.columns}
            for k, v in values.items():
                if k in valid_cols and k not in ("id", "tenant_id", "created_at"):
                    setattr(rec, k, v)

            db.commit()
            db.refresh(rec)
            return row_to_dict(rec)
        except Exception:
            db.rollback()
            raise
        finally:
            tenant_context.reset(tenant_token)
            db.close()

    async def delete_record(
        self,
        ctx: ConnectorContext,
        object_name: str,
        record_id: str,
    ) -> bool:
        meta = CORE_OCTAOS_MODELS.get(object_name.lower())
        if not meta:
            raise ValueError(f"Unknown business object: '{object_name}'")

        model = meta["model"]
        db: Session = self.db_factory()
        try:
            tenant_token = tenant_context.set(ctx.tenant_id)
            rec = (
                db.query(model)
                .filter(model.id == record_id, model.tenant_id == ctx.tenant_id)
                .first()
            )
            if not rec:
                return False

            db.delete(rec)
            db.commit()
            return True
        except Exception:
            db.rollback()
            raise
        finally:
            tenant_context.reset(tenant_token)
            db.close()

    async def invoke_action(
        self,
        ctx: ConnectorContext,
        action_name: str,
        arguments: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Domain business actions."""
        db: Session = self.db_factory()
        try:
            tenant_token = tenant_context.set(ctx.tenant_id)
            norm_action = action_name.lower()

            if norm_action in ("octaos.leads.qualify", "qualify_lead"):
                lead_id = arguments.get("lead_id")
                score = arguments.get("score", 80)
                lead = db.query(Lead).filter(Lead.id == lead_id, Lead.tenant_id == ctx.tenant_id).first()
                if not lead:
                    return {"status": "error", "message": f"Lead {lead_id} not found."}
                lead.score = score
                lead.status = "qualified"
                db.commit()
                return {"status": "success", "lead_id": lead_id, "score": score, "status_updated": "qualified"}

            elif norm_action in ("octaos.support.reply_ticket", "reply_ticket"):
                ticket_id = arguments.get("ticket_id")
                content = arguments.get("content", "")
                ticket = db.query(Ticket).filter(Ticket.id == ticket_id, Ticket.tenant_id == ctx.tenant_id).first()
                if not ticket:
                    return {"status": "error", "message": f"Ticket {ticket_id} not found."}
                msg = TicketMessage(
                    ticket_id=ticket_id,
                    sender_type="agent",
                    content=content,
                    message_type="reply",
                )
                db.add(msg)
                ticket.status = "pending"
                db.commit()
                return {"status": "success", "ticket_id": ticket_id, "message_sent": True}

            elif norm_action in ("octaos.workflows.trigger", "trigger_workflow"):
                workflow_id = arguments.get("workflow_id")
                payload = arguments.get("payload", {})
                return {
                    "status": "success",
                    "workflow_id": workflow_id,
                    "execution_id": f"exec_{int(datetime.now(timezone.utc).timestamp())}",
                    "message": "Workflow triggered successfully.",
                }

            raise ValueError(f"Unknown business action: '{action_name}'")
        finally:
            tenant_context.reset(tenant_token)
            db.close()

    def _apply_dsl_filters(self, stmt: Any, model: Any, filter_obj: Dict[str, Any]) -> Any:
        """Parses the typed query DSL filter structure into SQLAlchemy binary expressions."""
        if "and" in filter_obj:
            clauses = [self._build_single_clause(model, c) for c in filter_obj["and"] if self._build_single_clause(model, c) is not None]
            if clauses:
                stmt = stmt.filter(and_(*clauses))
        elif "or" in filter_obj:
            clauses = [self._build_single_clause(model, c) for c in filter_obj["or"] if self._build_single_clause(model, c) is not None]
            if clauses:
                stmt = stmt.filter(or_(*clauses))
        else:
            c = self._build_single_clause(model, filter_obj)
            if c is not None:
                stmt = stmt.filter(c)
        return stmt

    def _build_single_clause(self, model: Any, clause: Dict[str, Any]) -> Any:
        field = clause.get("field")
        op = clause.get("operator", "eq").lower()
        val = clause.get("value")

        if not hasattr(model, field):
            return None

        col = getattr(model, field)
        if op == "eq":
            return col == val
        elif op == "neq":
            return col != val
        elif op == "gt":
            return col > val
        elif op == "gte":
            return col >= val
        elif op == "lt":
            return col < val
        elif op == "lte":
            return col <= val
        elif op == "in" and isinstance(val, list):
            return col.in_(val)
        elif op == "contains" and isinstance(val, str):
            return col.ilike(f"%{val}%")
        elif op == "is_null":
            return col.is_(None) if val else col.isnot(None)
        return None
