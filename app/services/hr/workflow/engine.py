from typing import Dict, Any, List, Set, Tuple, Optional
import uuid
import re
from app.schemas.hr_workflow import (
    WorkflowGraphSchema,
    WorkflowGraphContract,
    WorkflowNode,
    WorkflowEdge,
    WorkflowTestRunResponse,
    NodeTypeMetadata,
    TemplateVersionRef,
    AIPipelineGenerateResponse,
)


class WorkflowEvaluationError(Exception):
    pass


def _safe_eval_condition(condition_str: str, context: Dict[str, Any]) -> bool:
    """Safely evaluates a conditional edge predicate without using eval/exec."""
    cleaned = condition_str.strip()
    if not cleaned:
        return True

    # Support simple comparison expressions like:
    # "context.employment_type == 'permanent'"
    # "context.employment_type == 'contractor'"
    # "context.department == 'Engineering'"
    # "context.annual_ctc >= 2500000"
    
    # Handle equality '=='
    if "==" in cleaned:
        left, right = cleaned.split("==", 1)
        left = left.strip()
        right = right.strip().strip("'\"")
        
        # resolve left key from context
        val = None
        if left.startswith("context."):
            val = context.get(left.replace("context.", ""))
        else:
            val = context.get(left)
        return str(val).lower() == str(right).lower()

    # Handle inequality '!='
    if "!=" in cleaned:
        left, right = cleaned.split("!=", 1)
        left = left.strip()
        right = right.strip().strip("'\"")
        val = context.get(left.replace("context.", "").strip())
        return str(val).lower() != str(right).lower()

    # Handle numeric comparisons '>=' or '>'
    if ">=" in cleaned:
        left, right = cleaned.split(">=", 1)
        val = float(context.get(left.replace("context.", "").strip(), 0) or 0)
        target = float(right.strip())
        return val >= target

    if ">" in cleaned:
        left, right = cleaned.split(">", 1)
        val = float(context.get(left.replace("context.", "").strip(), 0) or 0)
        target = float(right.strip())
        return val > target

    # Handle boolean flags e.g. "context.needs_relocation"
    if cleaned.startswith("context."):
        key = cleaned.replace("context.", "")
        return bool(context.get(key))

    return True


from app.schemas.hr_workflow import (
    WorkflowGraphSchema,
    WorkflowNode,
    WorkflowEdge,
    WorkflowTestRunResponse,
    NodeTypeMetadata,
)


NODE_REGISTRY: Dict[str, Dict[str, Any]] = {
    "start": {
        "node_type": "start",
        "label": "Start / Trigger",
        "category": "Triggers",
        "description": "Start manually, when a candidate is created, or from an authorized event",
        "icon": "Play",
        "default_config": {"trigger_type": "manual", "auto_start_on_candidate_creation": True},
        "input_schema": {},
        "output_schema": {"candidate_id": "string", "application_id": "string"},
    },
    "generate_document": {
        "node_type": "generate_document",
        "label": "Generate Document",
        "category": "Documents & Templates",
        "description": "Choose a template, field mappings, AI fill instructions, and output format",
        "icon": "FileText",
        "default_config": {
            "template_id": None,
            "template_name": "Standard Offer Letter",
            "ai_fill_instructions": "Populate the selected template using verified candidate evidence and authorized company records. Preserve original document structure and legal clauses. Do not invent missing values.",
            "data_sources": ["candidate_form", "uploaded_evidence", "hr_records", "company_settings"],
            "field_mappings": {},
            "missing_data_policy": "route_to_hr",
            "output_format": "both",  # docx, pdf, both
        },
        "input_schema": {"candidate_fields": "dict", "evidence": "list"},
        "output_schema": {"document_draft_id": "string", "content_sha256": "string"},
    },
    "upload_template": {
        "node_type": "upload_template",
        "label": "Upload Template",
        "category": "Documents & Templates",
        "description": "Upload or select a reusable DOCX/HTML template and propose mappings",
        "icon": "Upload",
        "default_config": {"template_category": "onboarding", "allowed_formats": ["docx", "html"]},
        "input_schema": {},
        "output_schema": {"template_version_id": "string"},
    },
    "candidate_upload": {
        "node_type": "candidate_upload",
        "label": "Candidate Document Upload",
        "category": "Candidate Interaction",
        "description": "Request evidence or documents (passport, national ID, certificates)",
        "icon": "UploadCloud",
        "default_config": {
            "required_documents": [
                {"category": "national_id", "title": "Government Photo ID", "is_mandatory": True},
                {"category": "tax_form", "title": "Tax Information / PAN Card", "is_mandatory": True},
            ],
            "allowed_formats": ["application/pdf", "image/jpeg", "image/png"],
            "max_file_size_mb": 15,
            "deadline_days": 5,
        },
        "input_schema": {"candidate_portal_token": "string"},
        "output_schema": {"uploaded_evidence_ids": "list"},
    },
    "ai_form_generator": {
        "node_type": "ai_form_generator",
        "label": "AI Form Generator",
        "category": "Candidate Interaction",
        "description": "Collect fields detected from connected templates and workflow rules",
        "icon": "Sparkles",
        "default_config": {
            "deduplicate_fields": True,
            "intake_fields": ["candidate.full_name", "candidate.email", "candidate.phone", "candidate.current_address"],
            "sensitive_check_required": True,
        },
        "input_schema": {"required_fields": "list"},
        "output_schema": {"collected_field_values": "dict"},
    },
    "candidate_email": {
        "node_type": "candidate_email",
        "label": "Candidate Email",
        "category": "Candidate Interaction",
        "description": "Send a secure form link, upload request, or welcome instructions",
        "icon": "Mail",
        "default_config": {
            "recipient_type": "candidate",
            "subject": "Complete your onboarding documentation with OctaCorp",
            "email_template": "Hello {{ candidate.name }},\n\nPlease review and complete your onboarding documentation by visiting your secure portal:\n{{ candidate_portal_url }}\n\nBest regards,\nHR Team",
            "include_portal_link": True,
            "send_delay_minutes": 0,
        },
        "input_schema": {"candidate_portal_url": "string"},
        "output_schema": {"email_dispatched": "boolean", "delivery_id": "string"},
    },
    "extract_validate": {
        "node_type": "extract_validate",
        "label": "Extract & Validate",
        "category": "Extraction & Logic",
        "description": "OCR evidence extraction, validation rules, missing fields, and conflict handling",
        "icon": "CheckSquare",
        "default_config": {
            "ocr_engine": "rapidocr",
            "confidence_threshold": 0.85,
            "flag_conflicts_to_hr": True,
            "auto_resolve_high_confidence": False,
        },
        "input_schema": {"evidence_items": "list"},
        "output_schema": {"reconciliation_summary": "dict", "conflicts": "list"},
    },
    "condition_branch": {
        "node_type": "condition_branch",
        "label": "Condition / Branch",
        "category": "Extraction & Logic",
        "description": "Route based on approved candidate attributes, role, or completed tasks",
        "icon": "GitBranch",
        "default_config": {
            "branch_attribute": "employment_type",
            "default_branch": "permanent",
        },
        "input_schema": {"context": "dict"},
        "output_schema": {"active_branch": "string"},
    },
    "hr_review": {
        "node_type": "hr_review",
        "label": "HR Review",
        "category": "Review & Governance",
        "description": "Inspect, edit, and request changes to drafts and reconciled candidate fields",
        "icon": "Eye",
        "default_config": {
            "reviewer_role": "hr_specialist",
            "editable_fields": ["compensation.annual_ctc", "role.start_date", "role.department"],
            "allow_paragraph_overrides": True,
            "invalidate_prior_approvals_on_edit": True,
        },
        "input_schema": {"draft_id": "string"},
        "output_schema": {"review_status": "string", "comments_count": "integer"},
    },
    "approval": {
        "node_type": "approval",
        "label": "Approval Gate",
        "category": "Review & Governance",
        "description": "Require authorized sign-off bound cryptographically to content SHA-256",
        "icon": "ShieldCheck",
        "default_config": {
            "required_role": "hr_director",
            "approval_policy": "strict_sha_binding",
            "escalation_hours": 48,
            "rejection_action": "route_back_to_review",
        },
        "input_schema": {"draft_id": "string", "content_sha256": "string"},
        "output_schema": {"approval_id": "string", "bound_sha256": "string"},
    },
    "wait_schedule": {
        "node_type": "wait_schedule",
        "label": "Wait / Schedule",
        "category": "Automation & Scheduling",
        "description": "Pause until a target date, interval, or candidate time zone release",
        "icon": "Clock",
        "default_config": {
            "wait_type": "interval",  # interval, specific_date, candidate_start_date
            "wait_hours": 24,
            "timezone": "UTC",
        },
        "input_schema": {},
        "output_schema": {"resumed_at": "string"},
    },
    "notification": {
        "node_type": "notification",
        "label": "Notification",
        "category": "Automation & Scheduling",
        "description": "Notify candidate, HR recruiter, hiring manager, or approver",
        "icon": "Bell",
        "default_config": {
            "channels": ["in_app", "email"],
            "target_recipient": "hiring_manager",
            "notification_template": "Candidate {{ candidate.name }} onboarding stage updated.",
        },
        "input_schema": {},
        "output_schema": {"notification_sent": "boolean"},
    },
    "signature": {
        "node_type": "signature",
        "label": "Signature Integration",
        "category": "Review & Governance",
        "description": "Initiate and track electronic signature process",
        "icon": "PenTool",
        "default_config": {
            "provider": "internal_octaos",
            "signer_order": ["candidate", "company_signatory"],
            "reminder_interval_days": 2,
        },
        "input_schema": {"approved_draft_id": "string"},
        "output_schema": {"signature_request_id": "string", "status": "string"},
    },
    "export_archive": {
        "node_type": "export_archive",
        "label": "Export / Archive",
        "category": "Automation & Scheduling",
        "description": "Generate final artifacts and apply legal retention policies",
        "icon": "Archive",
        "default_config": {
            "formats": ["pdf", "docx"],
            "retention_years": 7,
            "export_destination": "tenant_vault",
        },
        "input_schema": {"artifacts": "list"},
        "output_schema": {"archived_storage_keys": "list"},
    },
    "end": {
        "node_type": "end",
        "label": "End Workflow",
        "category": "Automation & Scheduling",
        "description": "Complete, cancel, or terminate the pipeline execution",
        "icon": "CheckCircle2",
        "default_config": {"completion_state": "hired", "notify_participants": True},
        "input_schema": {},
        "output_schema": {"final_status": "string"},
    },
}


class DynamicWorkflowEngine:
    """Validates, traverses, and simulates dynamic onboarding workflow DAGs."""

    @classmethod
    def get_node_registry(cls) -> List[NodeTypeMetadata]:
        """Returns metadata for all registered node types in the system."""
        return [
            NodeTypeMetadata(
                node_type=item["node_type"],
                label=item["label"],
                category=item["category"],
                description=item["description"],
                icon=item["icon"],
                default_config=item["default_config"],
                input_schema=item["input_schema"],
                output_schema=item["output_schema"],
            )
            for item in NODE_REGISTRY.values()
        ]

    @classmethod
    def validate_graph(cls, graph: Any) -> Tuple[bool, List[str]]:
        """Checks graph connectivity, valid node types, handles, reachability, configuration, and detects cycles."""
        errors: List[str] = []
        nodes = graph.nodes if hasattr(graph, "nodes") else (graph.get("nodes", []) if isinstance(graph, dict) else [])
        edges = graph.edges if hasattr(graph, "edges") else (graph.get("edges", []) if isinstance(graph, dict) else [])

        if not nodes:
            errors.append("Workflow must contain at least one node.")
            return False, errors

        node_ids: Set[str] = set()
        node_map: Dict[str, Any] = {}
        has_start = False

        for n in nodes:
            n_id = n.id if hasattr(n, "id") else n.get("id")
            n_type = n.type if hasattr(n, "type") else n.get("type")
            n_config = n.config if hasattr(n, "config") else n.get("config", {})

            if n_id in node_ids:
                errors.append(f"Duplicate node ID '{n_id}' found in workflow graph.")
            node_ids.add(n_id)
            node_map[n_id] = n

            # Check supported node types
            if n_type not in NODE_REGISTRY and n_type not in ("candidate_intake", "document_generation"):
                errors.append(f"Node '{n_id}' has unsupported type '{n_type}'.")

            if n_type in ("start", "candidate_intake"):
                has_start = True

            # Configuration validation
            if n_type in ("generate_document", "document_generation"):
                tpl = n_config.get("template_name") or n_config.get("template_id") or n_config.get("required_fields")
                if not tpl:
                    errors.append(f"Document generation node '{n_id}' is missing a template reference.")
            elif n_type == "approval":
                if "required_role" in n_config and not n_config.get("required_role"):
                    errors.append(f"Approval node '{n_id}' requires a 'required_role' sign-off specification.")

        if not has_start:
            errors.append("Workflow must contain at least one 'start' trigger node.")

        for edge in edges:
            e_source = edge.source if hasattr(edge, "source") else edge.get("source")
            e_target = edge.target if hasattr(edge, "target") else edge.get("target")

            if e_source not in node_ids:
                errors.append(f"Edge source '{e_source}' does not exist in graph nodes.")
            else:
                source_node = node_map.get(e_source)
                s_type = source_node.type if hasattr(source_node, "type") else source_node.get("type")
                if s_type == "end":
                    errors.append(f"Terminal node '{e_source}' cannot have outgoing connections.")

            if e_target not in node_ids:
                errors.append(f"Edge target '{e_target}' does not exist in graph nodes.")
            else:
                target_node = node_map.get(e_target)
                t_type = target_node.type if hasattr(target_node, "type") else target_node.get("type")
                if t_type in ("start", "candidate_intake"):
                    errors.append(f"Start node '{e_target}' cannot have incoming connections.")

        # Reachability from start nodes
        adj: Dict[str, List[str]] = {nid: [] for nid in node_ids}
        for edge in edges:
            e_source = edge.source if hasattr(edge, "source") else edge.get("source")
            e_target = edge.target if hasattr(edge, "target") else edge.get("target")
            if e_source in adj and e_target in node_ids:
                adj[e_source].append(e_target)

        start_nodes = [
            (n.id if hasattr(n, "id") else n.get("id"))
            for n in nodes
            if (n.type if hasattr(n, "type") else n.get("type")) in ("start", "candidate_intake")
        ]

        if start_nodes:
            reachable: Set[str] = set()
            q = list(start_nodes)
            while q:
                curr = q.pop(0)
                if curr in reachable:
                    continue
                reachable.add(curr)
                for neighbor in adj.get(curr, []):
                    if neighbor not in reachable:
                        q.append(neighbor)

            unreachable = node_ids - reachable
            if unreachable and len(nodes) > 1:
                errors.append(f"Nodes {sorted(list(unreachable))} are unreachable from start.")

        # Detect cycles using DFS
        visited: Dict[str, int] = {}  # 0 = unvisited, 1 = visiting, 2 = visited

        def has_cycle(u: str) -> bool:
            visited[u] = 1
            for v in adj.get(u, []):
                if visited.get(v, 0) == 1:
                    return True
                if visited.get(v, 0) == 0:
                    if has_cycle(v):
                        return True
            visited[u] = 2
            return False

        for nid in node_ids:
            if visited.get(nid, 0) == 0:
                if has_cycle(nid):
                    errors.append("Workflow contains an illegal loop or cycle.")
                    break

        return len(errors) == 0, errors

    @classmethod
    def generate_workflow_graph_from_prompt(
        cls,
        prompt: str,
        job_role: Optional[str] = None,
        tenant_id: Optional[str] = None,
        db: Optional[Any] = None,
    ) -> AIPipelineGenerateResponse:
        """Synthesizes a proposed DAG workflow graph from a natural language prompt.
        Uses deterministic domain-aware planner producing a validated WorkflowGraphContract.
        """
        role_hint = (job_role or "").strip().lower()
        prompt_lower = (prompt or "").strip().lower()

        # Determine workflow title
        workflow_name = "Custom Onboarding Pipeline"
        if "python" in role_hint or "python" in prompt_lower:
            workflow_name = "Python Backend Developer Pipeline"
        elif "developer" in role_hint or "engineer" in role_hint or "engineer" in prompt_lower:
            workflow_name = f"{(job_role or 'Engineering').title()} Technical Onboarding"
        elif "executive" in prompt_lower or "director" in prompt_lower or "c-level" in prompt_lower:
            workflow_name = "Executive & Leadership Onboarding Flow"
        elif "contractor" in prompt_lower or "freelance" in prompt_lower:
            workflow_name = "Contractor & Vendor Compliance Pipeline"

        # Check for tenant templates
        template_refs: List[TemplateVersionRef] = []
        if db and tenant_id:
            try:
                from app.models.hr import TenantDocumentTemplate, TemplateVersion
                templates = db.query(TenantDocumentTemplate).filter_by(tenant_id=tenant_id).all()
                for t in templates:
                    ver = (
                        db.query(TemplateVersion)
                        .filter_by(template_id=t.id)
                        .order_by(TemplateVersion.version.desc())
                        .first()
                    )
                    if ver:
                        template_refs.append(
                            TemplateVersionRef(
                                template_id=t.id,
                                version_id=ver.id,
                                template_name=t.name,
                                content_sha256=ver.content_sha256,
                            )
                        )
            except Exception:
                pass

        generator_used = "rule_based_fallback"
        nodes: List[WorkflowNode] = []
        edges: List[WorkflowEdge] = []
        warnings: List[str] = []

        is_tech = any(k in prompt_lower or k in role_hint for k in ["python", "backend", "developer", "engineer", "software", "tech"])
        is_exec = any(k in prompt_lower or k in role_hint for k in ["executive", "director", "vp", "chief", "head", "c-level"])
        is_contractor = any(k in prompt_lower or k in role_hint for k in ["contractor", "freelance", "vendor", "consultant", "msa"])
        has_nda = "nda" in prompt_lower or "non-disclosure" in prompt_lower or is_exec

        col = 0
        def next_pos(c: int, r: int = 0) -> Dict[str, float]:
            return {"x": float(60 + c * 270), "y": float(160 + r * 140)}

        # 1. Start Node
        node_start = WorkflowNode(
            id="node_start",
            name="Start Pipeline",
            type="start",
            config={"trigger_type": "candidate_created", "auto_start": True},
            position=next_pos(col),
        )
        nodes.append(node_start)
        last_node_id = node_start.id
        col += 1

        # 2. Candidate Document Upload Node
        needs_upload = is_tech or is_exec or is_contractor or any(k in prompt_lower for k in ["upload", "evidence", "document", "degree", "payslip", "id", "passport"])
        if needs_upload:
            req_docs = []
            if is_tech:
                req_docs = [
                    {"category": "degree_certificate", "title": "B.Tech / MCA Degree Certificate", "is_mandatory": True, "accepted_mimes": ["application/pdf"]},
                    {"category": "relieving_letter", "title": "Previous Employer Relieving Letter", "is_mandatory": True, "accepted_mimes": ["application/pdf"]},
                    {"category": "national_id", "title": "PAN Card / Government Photo ID", "is_mandatory": True, "accepted_mimes": ["application/pdf", "image/jpeg"]},
                ]
            elif is_exec:
                req_docs = [
                    {"category": "national_id", "title": "Passport / Director Identification", "is_mandatory": True, "accepted_mimes": ["application/pdf"]},
                    {"category": "tax_form", "title": "Prior Form 16 / Executive Tax Filings", "is_mandatory": True, "accepted_mimes": ["application/pdf"]},
                ]
            else:
                req_docs = [
                    {"category": "national_id", "title": "Government Photo ID", "is_mandatory": True, "accepted_mimes": ["application/pdf", "image/jpeg"]},
                    {"category": "tax_form", "title": "Tax Identification / PAN", "is_mandatory": True, "accepted_mimes": ["application/pdf"]},
                ]

            node_upload = WorkflowNode(
                id="node_candidate_upload",
                name="Candidate Evidence Upload",
                type="candidate_upload",
                config={
                    "required_documents": req_docs,
                    "allowed_formats": ["application/pdf", "image/jpeg", "image/png"],
                    "max_file_size_mb": 15,
                    "deadline_days": 5,
                },
                position=next_pos(col),
            )
            nodes.append(node_upload)
            edges.append(WorkflowEdge(id=f"e_{last_node_id}_{node_upload.id}", source=last_node_id, target=node_upload.id))
            last_node_id = node_upload.id
            col += 1

        # 3. Extract & Validate OCR Node
        needs_ocr = (needs_upload and any(k in prompt_lower for k in ["extract", "ocr", "validate", "verify", "check", "evidence", "pan"])) or is_tech
        if needs_ocr:
            node_ocr = WorkflowNode(
                id="node_extract_validate",
                name="OCR Evidence Extraction",
                type="extract_validate",
                config={
                    "extraction_rules": [
                        {"target_field": "candidate.pan_number", "validation_pattern": "[A-Z]{5}[0-9]{4}[A-Z]{1}", "min_confidence": 0.85, "missing_data_action": "flag_for_review"},
                        {"target_field": "candidate.degree", "validation_pattern": "", "min_confidence": 0.80, "missing_data_action": "flag_for_review"},
                    ],
                    "auto_flag_conflicts": True,
                },
                position=next_pos(col),
            )
            nodes.append(node_ocr)
            edges.append(WorkflowEdge(id=f"e_{last_node_id}_{node_ocr.id}", source=last_node_id, target=node_ocr.id))
            last_node_id = node_ocr.id
            col += 1

        # 4. AI Form Generator (Synthesizes intake fields)
        intake_fields = [
            {"id": "f_name", "canonical_key": "candidate.full_name", "label": "Full Legal Name", "data_type": "text", "is_required": True},
            {"id": "f_email", "canonical_key": "candidate.email", "label": "Primary Email Address", "data_type": "email", "is_required": True},
            {"id": "f_pan", "canonical_key": "candidate.pan_number", "label": "PAN / Tax ID", "data_type": "text", "is_required": True},
            {"id": "f_addr", "canonical_key": "candidate.current_address", "label": "Permanent Address", "data_type": "text", "is_required": True},
        ]
        if is_tech:
            intake_fields.append({"id": "f_github", "canonical_key": "candidate.github_url", "label": "GitHub / Portfolio URL", "data_type": "text", "is_required": False})
            intake_fields.append({"id": "f_notice", "canonical_key": "candidate.notice_period_days", "label": "Notice Period (Days)", "data_type": "number", "is_required": True})

        node_form = WorkflowNode(
            id="node_ai_form",
            name="AI Candidate Intake Form",
            type="ai_form_generator",
            config={
                "intake_fields": [f["canonical_key"] for f in intake_fields],
                "field_definitions": intake_fields,
                "deduplicate_across_templates": True,
            },
            position=next_pos(col),
        )
        nodes.append(node_form)
        edges.append(WorkflowEdge(id=f"e_{last_node_id}_{node_form.id}", source=last_node_id, target=node_form.id))
        last_node_id = node_form.id
        col += 1

        # 5. HR Review Node
        node_review = WorkflowNode(
            id="node_hr_review",
            name="Technical & HR Review",
            type="hr_review",
            config={
                "reviewer_role": "hr_specialist" if not is_tech else "technical_recruiter",
                "sla_hours": 24,
                "required_checklist": ["verified_identity", "background_check_initiated", "scorecard_confirmed"],
            },
            position=next_pos(col),
        )
        nodes.append(node_review)
        edges.append(WorkflowEdge(id=f"e_{last_node_id}_{node_review.id}", source=last_node_id, target=node_review.id))
        last_node_id = node_review.id
        col += 1

        # 6. Approval Node
        app_role = "hr_director"
        if is_tech:
            app_role = "vp_department"
        elif is_exec:
            app_role = "ceo"

        node_app = WorkflowNode(
            id="node_approval",
            name="Offer & Salary Sign-off",
            type="approval",
            config={
                "required_role": app_role,
                "approval_type": "single_signoff",
                "enforce_sha_lock": True,
            },
            position=next_pos(col),
        )
        nodes.append(node_app)
        edges.append(WorkflowEdge(id=f"e_{last_node_id}_{node_app.id}", source=last_node_id, target=node_app.id))
        last_node_id = node_app.id
        col += 1

        # 7. Document Generation Node
        doc_tpl_name = "Standard Offer Letter"
        if is_contractor:
            doc_tpl_name = "Independent Contractor MSA"
        elif is_exec:
            doc_tpl_name = "Executive Employment Agreement"
        elif has_nda:
            doc_tpl_name = "Mutual Non-Disclosure Agreement (NDA)"

        node_doc = WorkflowNode(
            id="node_generate_doc",
            name=f"Generate {doc_tpl_name}",
            type="generate_document",
            config={
                "template_name": doc_tpl_name,
                "ai_fill_instructions": f"Draft the {doc_tpl_name} using verified candidate facts and approved salary terms. Preserve legal clauses.",
                "output_format": "both",
                "field_mappings": {
                    "candidate_name": "candidate.full_name",
                    "annual_ctc": "compensation.annual_ctc",
                    "joining_date": "offer.joining_date",
                },
            },
            position=next_pos(col),
        )
        nodes.append(node_doc)
        edges.append(WorkflowEdge(id=f"e_{last_node_id}_{node_doc.id}", source=last_node_id, target=node_doc.id))
        last_node_id = node_doc.id
        col += 1

        # 8. Candidate Email Node
        node_email = WorkflowNode(
            id="node_candidate_email",
            name="Dispatch Offer Email",
            type="candidate_email",
            config={
                "subject": f"Offer of Employment — {job_role or 'OctaOS Team'}",
                "email_template": "Dear {{candidate.full_name}},\n\nWe are excited to extend this formal offer. Please review and sign your offer packet via your secure portal link below.",
                "include_portal_link": True,
            },
            position=next_pos(col),
        )
        nodes.append(node_email)
        edges.append(WorkflowEdge(id=f"e_{last_node_id}_{node_email.id}", source=last_node_id, target=node_email.id))
        last_node_id = node_email.id
        col += 1

        # 9. Terminal End Node
        node_end = WorkflowNode(
            id="node_end",
            name="Complete Onboarding",
            type="end",
            config={"completion_state": "hired", "sync_to_payroll": True},
            position=next_pos(col),
        )
        nodes.append(node_end)
        edges.append(WorkflowEdge(id=f"e_{last_node_id}_{node_end.id}", source=last_node_id, target=node_end.id))

        contract = WorkflowGraphContract(
            name=workflow_name,
            description=f"Generated proposal for prompt: '{prompt}' (Role: {job_role or 'General'})",
            nodes=nodes,
            edges=edges,
            template_references=template_refs,
            provenance={"generator": generator_used, "prompt": prompt, "job_role": job_role},
        )

        is_valid, validation_errors = cls.validate_graph(contract)

        return AIPipelineGenerateResponse(
            graph=contract,
            is_valid=is_valid,
            warnings=warnings,
            validation_errors=validation_errors,
            generator_used=generator_used,
        )

    @classmethod
    def evaluate_traversal(
        cls,
        graph: WorkflowGraphSchema,
        context: Dict[str, Any],
    ) -> WorkflowTestRunResponse:
        """Evaluates active execution path through the graph based on candidate context."""
        is_valid, validation_errors = cls.validate_graph(graph)
        if not is_valid:
            return WorkflowTestRunResponse(
                is_valid=False,
                traversed_path=[],
                evaluated_documents=[],
                required_candidate_fields=[],
                validation_errors=validation_errors,
            )

        # Build adjacency map
        target_nodes = {edge.target for edge in graph.edges}
        entry_nodes = [n for n in graph.nodes if n.id not in target_nodes]
        if not entry_nodes:
            entry_nodes = [graph.nodes[0]]

        traversed_node_ids: List[str] = []
        visited: Set[str] = set()
        queue: List[str] = [entry_nodes[0].id]

        node_map: Dict[str, WorkflowNode] = {n.id: n for n in graph.nodes}
        edges_from: Dict[str, List[WorkflowEdge]] = {}
        for edge in graph.edges:
            edges_from.setdefault(edge.source, []).append(edge)

        while queue:
            curr_id = queue.pop(0)
            if curr_id in visited:
                continue
            visited.add(curr_id)
            traversed_node_ids.append(curr_id)

            # Check outgoing edges
            out_edges = edges_from.get(curr_id, [])
            for edge in out_edges:
                condition_met = True
                if edge.condition:
                    condition_met = _safe_eval_condition(edge.condition, context)

                if condition_met and edge.target not in visited:
                    queue.append(edge.target)

        # Collect documents to generate and candidate fields required
        evaluated_documents: List[str] = []
        required_candidate_fields: Set[str] = set()

        for n_id in traversed_node_ids:
            node = node_map.get(n_id)
            if not node:
                continue
            ntype = node.type
            # Handle document generation (both new and legacy aliases)
            if ntype in ("generate_document", "document_generation"):
                doc_name = node.config.get("template_name") or node.config.get("document_type") or node.name
                evaluated_documents.append(doc_name)
                for f in node.config.get("required_fields", []):
                    required_candidate_fields.add(f)
            # Handle candidate intake and AI form generation
            elif ntype in ("ai_form_generator", "candidate_intake"):
                for f in node.config.get("intake_fields", []):
                    required_candidate_fields.add(f)
            # Handle candidate uploads
            elif ntype == "candidate_upload":
                for doc in node.config.get("required_documents", []):
                    cat = doc.get("category") if isinstance(doc, dict) else str(doc)
                    if cat:
                        required_candidate_fields.add(f"evidence.{cat}")

        return WorkflowTestRunResponse(
            is_valid=True,
            traversed_path=traversed_node_ids,
            evaluated_documents=evaluated_documents,
            required_candidate_fields=sorted(list(required_candidate_fields)),
            validation_errors=[],
        )
