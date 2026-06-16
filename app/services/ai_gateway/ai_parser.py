import json
import re
import logging
from typing import Type, TypeVar, List, Dict, Any, Optional
from pydantic import BaseModel, Field, ValidationError

logger = logging.getLogger(__name__)
T = TypeVar('T', bound=BaseModel)

# --- Standard Pydantic Schemas ---

class OrchestratorTask(BaseModel):
    department: str
    action: str
    parameters: Dict[str, Any] = Field(default_factory=dict)

class OrchestratorPlan(BaseModel):
    tasks: List[OrchestratorTask]

class CandidateProfile(BaseModel):
    name: str
    email: str
    skills: List[str]
    experience_summary: str
    match_score: int
    requirements_match: str
    salary_expectation: str

class CandidateList(BaseModel):
    candidates: List[CandidateProfile]

class LeadProfile(BaseModel):
    name: str
    email: str
    phone: str
    company: str
    need_of_what: Optional[str] = None
    how_much: Optional[str] = None
    why: Optional[str] = None
    target_context: Optional[str] = None

class LeadList(BaseModel):
    leads: List[LeadProfile]

class ActionItem(BaseModel):
    assigned_to: str
    description: str

class ActionItemList(BaseModel):
    action_items: List[ActionItem]

# --- Parser & Retry Manager ---

class AIResponseParser:
    @staticmethod
    def clean_json_string(raw_response: str) -> str:
        if not raw_response:
            return ""
            
        clean = raw_response.strip()
        
        # Strip markdown block quotes
        if clean.startswith("```"):
            clean = re.sub(r"^```(json)?", "", clean, flags=re.IGNORECASE).strip()
            clean = re.sub(r"```$", "", clean).strip()
            
        # Extract content between outer brackets if not already standard JSON format
        if not (clean.startswith("{") and clean.endswith("}")) and not (clean.startswith("[") and clean.endswith("]")):
            # Check for JSON object
            match_obj = re.search(r"(\{.*\})", clean, re.DOTALL)
            if match_obj:
                clean = match_obj.group(1)
            else:
                # Check for JSON array
                match_arr = re.search(r"(\[.*\])", clean, re.DOTALL)
                if match_arr:
                    clean = match_arr.group(1)
                    
        return clean

    @classmethod
    def parse_as_model(cls, raw_response: str, model_class: Type[T]) -> T:
        cleaned = cls.clean_json_string(raw_response)
        try:
            return model_class.model_validate_json(cleaned)
        except (ValidationError, ValueError) as e:
            # Secondary fallback: standard json.loads followed by pydantic validate
            try:
                data = json.loads(cleaned)
                # Handle single object vs list wrapper mismatch if model expects List
                if isinstance(data, list) and hasattr(model_class, "__fields__") and len(model_class.__fields__) == 1:
                    field_name = list(model_class.__fields__.keys())[0]
                    data = {field_name: data}
                return model_class.model_validate(data)
            except Exception as inner_e:
                raise ValueError(f"Failed to validate response against schema {model_class.__name__}: {inner_e}") from e

class AIRetryManager:
    @staticmethod
    async def call_with_retry(
        gateway_call_fn,
        model_class: Type[T],
        max_retries: int = 3,
        **gateway_kwargs
    ) -> T:
        last_error = None
        current_kwargs = gateway_kwargs.copy()
        
        for attempt in range(max_retries):
            try:
                # Add instructions for strict JSON compliance to the system prompt
                sys_prompt = current_kwargs.get("system_prompt") or ""
                extra_instructions = (
                    f"\n\nCRITICAL: You must return valid JSON that conforms exactly to the schema '{model_class.__name__}'. "
                    "Do not include any explanation or extra text. Output ONLY raw JSON."
                )
                if extra_instructions not in sys_prompt:
                    current_kwargs["system_prompt"] = sys_prompt + extra_instructions

                raw_response = await gateway_call_fn(**current_kwargs)
                parsed = AIResponseParser.parse_as_model(raw_response, model_class)
                return parsed
            except Exception as e:
                last_error = e
                logger.warning(f"Attempt {attempt + 1} failed to parse/validate for model {model_class.__name__}: {e}. Retrying...")
                
                # Append correction prompt
                prompt = current_kwargs.get("prompt") or ""
                correction_note = (
                    f"\n\n[Correction Note] Your previous output was invalid: {str(e)}. "
                    "Please correct it and strictly format your response as valid JSON matching the schema requirements."
                )
                current_kwargs["prompt"] = prompt + correction_note
                
        raise ValueError(
            f"AI failed to produce valid structured output for {model_class.__name__} after {max_retries} attempts. Last error: {last_error}"
        )
