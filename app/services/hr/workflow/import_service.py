"""
Enterprise HR Workflow & Template Import Service.
Handles cross-folder and cross-department cloning with internal node ID remapping,
template cloning/inheritance, provenance tracking, and draft-only lifecycle isolation.
"""
import uuid
import copy
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session

from app.models.hr import (
    HRWorkflowDefinition,
    HRWorkflowImportRecord,
    TenantDocumentTemplate,
    TemplateVersion,
    TemplateVariableSchema,
)


class WorkflowImportService:
    @staticmethod
    def get_all_folders(db: Session, tenant_id: str) -> List[str]:
        """Returns all distinct folders across workflows and document templates."""
        wf_folders = [
            f[0] for f in db.query(HRWorkflowDefinition.folder_path)
            .filter_by(tenant_id=tenant_id).distinct().all() if f[0]
        ]
        tpl_folders = [
            f[0] for f in db.query(TenantDocumentTemplate.folder_path)
            .filter_by(tenant_id=tenant_id).distinct().all() if f[0]
        ]
        # Standard default corporate departments
        standard_folders = ["/", "/Engineering", "/Sales", "/Operations", "/Executive", "/Product"]
        merged = sorted(list(set(wf_folders + tpl_folders + standard_folders)))
        return merged

    @classmethod
    def clone_workflow(
        cls,
        db: Session,
        tenant_id: str,
        user_id: Optional[str],
        source_definition_id: str,
        target_folder_path: str = "/",
        target_name: Optional[str] = None,
        target_department_id: Optional[str] = None,
        clone_templates: bool = True,
    ) -> HRWorkflowDefinition:
        """
        Clones an existing workflow into a target folder or department.
        Remaps internal node IDs and connections.
        Optionally clones referenced document templates into the target folder.
        Saves as draft (is_active=False).
        """
        source_wf = db.query(HRWorkflowDefinition).filter_by(
            id=source_definition_id,
            tenant_id=tenant_id,
        ).first()

        if not source_wf:
            raise ValueError("Source workflow definition not found.")

        target_folder = target_folder_path.strip()
        if not target_folder.startswith("/"):
            target_folder = f"/{target_folder}"

        source_graph = copy.deepcopy(source_wf.graph_schema or {"nodes": [], "edges": []})
        nodes = source_graph.get("nodes", [])
        edges = source_graph.get("edges", [])

        # 1. Remap internal node IDs
        node_id_map: Dict[str, str] = {}
        for node in nodes:
            old_id = node.get("id")
            if old_id:
                new_id = f"node_{uuid.uuid4().hex[:8]}"
                node_id_map[old_id] = new_id
                node["id"] = new_id

        # 2. Remap edge sources, targets, and IDs
        for edge in edges:
            edge["id"] = f"edge_{uuid.uuid4().hex[:8]}"
            if edge.get("source") in node_id_map:
                edge["source"] = node_id_map[edge["source"]]
            if edge.get("target") in node_id_map:
                edge["target"] = node_id_map[edge["target"]]

        # 3. Handle template references if clone_templates is True
        cloned_template_map: Dict[str, str] = {}
        if clone_templates:
            for node in nodes:
                config = node.get("config", {})
                tpl_id = config.get("template_id")
                if tpl_id and tpl_id not in cloned_template_map:
                    # Look up original template
                    orig_tpl = db.query(TenantDocumentTemplate).filter_by(
                        id=tpl_id,
                        tenant_id=tenant_id,
                    ).first()

                    if orig_tpl:
                        # Check if a template with this name already exists in target folder
                        existing_target_tpl = db.query(TenantDocumentTemplate).filter_by(
                            tenant_id=tenant_id,
                            document_type=orig_tpl.document_type,
                            name=orig_tpl.name,
                            folder_path=target_folder,
                        ).first()

                        if existing_target_tpl:
                            cloned_template_map[tpl_id] = existing_target_tpl.id
                            config["template_id"] = existing_target_tpl.id
                        else:
                            # Clone TenantDocumentTemplate
                            new_tpl = TenantDocumentTemplate(
                                tenant_id=tenant_id,
                                document_type=orig_tpl.document_type,
                                category=orig_tpl.category or "onboarding",
                                name=orig_tpl.name,
                                description=f"Imported from {orig_tpl.folder_path}",
                                folder_path=target_folder,
                                tags=orig_tpl.tags or [],
                                is_active=True,
                            )
                            db.add(new_tpl)
                            db.flush()

                            # Clone latest TemplateVersion
                            latest_ver = db.query(TemplateVersion).filter_by(
                                template_id=orig_tpl.id,
                                tenant_id=tenant_id,
                            ).order_by(TemplateVersion.version.desc()).first()

                            if latest_ver:
                                new_ver = TemplateVersion(
                                    template_id=new_tpl.id,
                                    tenant_id=tenant_id,
                                    version=1,
                                    format=latest_ver.format,
                                    status="draft",
                                    storage_key=latest_ver.storage_key,
                                    content_sha256=latest_ver.content_sha256,
                                    raw_content=latest_ver.raw_content,
                                    docx_structure=latest_ver.docx_structure or {},
                                    detected_clauses=latest_ver.detected_clauses or [],
                                    proposed_mappings=latest_ver.proposed_mappings or [],
                                )
                                db.add(new_ver)
                                db.flush()

                                # Clone variable schemas
                                schemas = db.query(TemplateVariableSchema).filter_by(
                                    template_version_id=latest_ver.id
                                ).all()
                                for s in schemas:
                                    new_s = TemplateVariableSchema(
                                        template_version_id=new_ver.id,
                                        variable_name=s.variable_name,
                                        data_type=s.data_type,
                                        is_required=s.is_required,
                                        source_field=s.source_field,
                                        sensitivity=s.sensitivity,
                                        editable_by_recruiter=s.editable_by_recruiter,
                                    )
                                    db.add(new_s)

                            cloned_template_map[tpl_id] = new_tpl.id
                            config["template_id"] = new_tpl.id
                elif tpl_id and tpl_id in cloned_template_map:
                    config["template_id"] = cloned_template_map[tpl_id]

        # 4. Construct cloned HRWorkflowDefinition
        final_name = target_name.strip() if target_name else f"{source_wf.name} (Copy)"
        new_wf = HRWorkflowDefinition(
            tenant_id=tenant_id,
            name=final_name,
            description=f"Imported from {source_wf.folder_path} - {source_wf.name}",
            folder_path=target_folder,
            department_id=target_department_id or source_wf.department_id,
            tags=source_wf.tags or [],
            is_active=False,  # Draft-only; must be reviewed and published
            version=1,
            graph_schema=source_graph,
        )
        db.add(new_wf)
        db.flush()

        # 5. Record import audit log
        import_record = HRWorkflowImportRecord(
            tenant_id=tenant_id,
            source_definition_id=source_wf.id,
            target_definition_id=new_wf.id,
            source_folder_path=source_wf.folder_path or "/",
            target_folder_path=target_folder,
            remapped_node_ids=node_id_map,
            cloned_template_ids=cloned_template_map,
            imported_by_user_id=user_id,
        )
        db.add(import_record)
        db.commit()
        db.refresh(new_wf)

        return new_wf
