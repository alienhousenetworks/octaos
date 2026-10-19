import os
import json
try:
    import yaml
except ImportError:
    yaml = None
from typing import Dict, List, Any, Optional

class SkillMetadata:
    def __init__(self, name: str, description: str, category: str, triggers: List[str]):
        self.name = name
        self.description = description
        self.category = category
        self.triggers = triggers

class ProgressiveSkillSynthesizer:
    """
    Progressive Token Disclosure & Autonomous Skill Synthesizer.
    
    Prevents token bloat by exposing skills in 3 progressive levels:
    - Level 1 (~20 tokens): Skill name & concise summary
    - Level 2 (~200 tokens): Input parameters & schema definitions
    - Level 3 (Full body): Procedural step-by-step tool execution body
    """
    
    def __init__(self, base_skills_dir: Optional[str] = None):
        self.base_skills_dir = base_skills_dir or os.path.expanduser("~/.octaos/skills")
        os.makedirs(self.base_skills_dir, exist_ok=True)
        self.builtin_skills_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "skills"))

    def distill_execution_trace(self, skill_name: str, description: str, 
                                category: str, triggers: List[str],
                                execution_steps: List[Dict[str, Any]]) -> str:
        """
        Distills a successful multi-step agent execution trace into a standardized SKILL.md document.
        """
        skill_dir = os.path.join(self.base_skills_dir, skill_name.lower().replace(" ", "_"))
        os.makedirs(skill_dir, exist_ok=True)
        
        skill_path = os.path.join(skill_dir, "SKILL.md")
        
        frontmatter = {
            "name": skill_name,
            "description": description,
            "category": category,
            "triggers": triggers,
            "version": "1.0.0"
        }
        
        frontmatter_str = yaml.dump(frontmatter) if yaml else json.dumps(frontmatter, indent=2)
        content = f"---\n{frontmatter_str}---\n\n"
        content += f"# Skill: {skill_name}\n\n"
        content += f"## Overview\n{description}\n\n"
        content += "## Procedural Execution Steps\n"
        
        for idx, step in enumerate(execution_steps, 1):
            content += f"### Step {idx}: {step.get('action', 'Execute Action')}\n"
            content += f"- **Tool**: `{step.get('tool', 'system')}`\n"
            content += f"- **Parameters**: `{json.dumps(step.get('params', {}))}`\n"
            if step.get('notes'):
                content += f"- **Notes**: {step.get('notes')}\n"
            content += "\n"
            
        with open(skill_path, "w", encoding="utf-8") as f:
            f.write(content)
            
        return skill_path

    def _find_skill_file(self, skill_name: str) -> Optional[str]:
        """Locate SKILL.md in user custom directory or built-in app/skills catalog."""
        normalized = skill_name.lower().replace(" ", "_").replace("-", "_")
        candidates = [
            os.path.join(self.builtin_skills_dir, normalized, "SKILL.md"),
            os.path.join(self.builtin_skills_dir, skill_name, "SKILL.md"),
            os.path.join(self.base_skills_dir, normalized, "SKILL.md"),
            os.path.join(self.base_skills_dir, skill_name, "SKILL.md"),
        ]
        for p in candidates:
            try:
                if os.path.exists(p):
                    return p
            except Exception:
                continue
        return None

    def list_all_skills(self) -> List[str]:
        """List distinct skill folder names from both user and built-in roots."""
        names = set()
        for root in (self.builtin_skills_dir, self.base_skills_dir):
            try:
                if os.path.exists(root):
                    for entry in os.listdir(root):
                        if os.path.isdir(os.path.join(root, entry)) and os.path.exists(os.path.join(root, entry, "SKILL.md")):
                            names.add(entry)
            except Exception:
                continue
        return sorted(list(names))


    def get_skill_disclosure(self, skill_name: str, level: int = 1) -> str:
        """
        Returns skill content according to progressive token disclosure level (1, 2, or 3).
        """
        skill_path = self._find_skill_file(skill_name)
        if not skill_path:
            return f"Skill '{skill_name}' not found."
            
        with open(skill_path, "r", encoding="utf-8") as f:
            full_text = f.read()
            
        parts = full_text.split("---")
        metadata = {}
        if len(parts) >= 3:
            try:
                metadata = yaml.safe_load(parts[1]) if yaml else json.loads(parts[1])
            except Exception:
                metadata = {}
            
        if level == 1:
            # Level 1 (~20 tokens): Name + description
            desc = metadata.get('purpose') or metadata.get('description', '')
            return f"Skill `{metadata.get('name', skill_name)}`: {desc}"
        elif level == 2:
            # Level 2 (~200 tokens): Triggers & schema overview
            desc = metadata.get('purpose') or metadata.get('description', '')
            triggers = metadata.get('triggers', [])
            return (
                f"Skill: {metadata.get('name', skill_name)} (v{metadata.get('version', '1.0.0')})\n"
                f"Purpose: {desc}\n"
                f"Input Modes: {', '.join(metadata.get('input_modes', []))}\n"
                f"Output Modes: {', '.join(metadata.get('output_modes', []))}\n"
                f"Triggers: {', '.join(triggers[:5])}"
            )
        else:
            # Level 3: Full execution body
            return full_text

    def resolve_registered_skill(self, request: str, granted_permissions=None, level: int = 1) -> dict:
        """Resolve a request to a versioned Sales OS, discovery, or visual creative director skill.

        The returned disclosure does not grant tool permission. Execution stays
        with the registered agent after a separate authorization check.
        """
        lowered = (request or "").lower()
        visual_triggers = [
            "image", "photo", "video", "illustration", "poster", "artwork", "ad",
            "thumbnail", "shot list", "storyboard", "retouch", "cinematic", "visual"
        ]
        if any(vt in lowered for vt in visual_triggers):
            disclosure = self.get_skill_disclosure("universal_visual_creative_director", level=level)
            return {
                "matched": True,
                "skill_id": "creative.universal_visual_director",
                "skill_name": "Universal Visual Creative Director",
                "disclosure": disclosure,
                "version": "1.0.0",
                "authorized": True,
            }

        try:
            from app.services.sales_os.search_v4.skills import resolve_request
            return resolve_request(request, granted_permissions or [], level=level)
        except Exception:
            return {"matched": False, "request": request}

skill_synthesizer = ProgressiveSkillSynthesizer()
