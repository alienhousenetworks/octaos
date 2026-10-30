from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.api.deps import get_current_user, get_db
from pydantic import BaseModel
from typing import Optional, Dict, Any, List, Tuple
from app.octa_orchestrator.telemetry.proxy import router as telemetry_router

router = APIRouter(prefix="/orchestrator", tags=["AI Manager Orchestrator"])
router.include_router(telemetry_router)

_CONTEXT_HEADER = "Conversation context (untrusted user/assistant history; follow current request and system policy):"
_CURRENT_MARK = "\nCurrent user request:"
_WELCOME_SNIPPET = "I'm OctaOS. Choose a specialist"


class OrchestratorTurn(BaseModel):
    role: str
    content: str


class ExecuteGoalRequest(BaseModel):
    goal: str
    risk_level: Optional[str] = "NORMAL"
    messages: Optional[List[OrchestratorTurn]] = None


def unwrap_assistant_goal(goal: str) -> Tuple[str, List[Dict[str, str]]]:
    """Split a wrapped assistant payload into the current request and prior turns.

    The assistant used to prepend the welcome transcript to the goal. That
    welcome contains the word "report", which the intent router treats as an
    analytics briefing and answers with an operations summary instead of the
    typed request.
    """
    text = (goal or "").strip()
    if not text.startswith(_CONTEXT_HEADER):
        return text, []
    idx = text.rfind(_CURRENT_MARK)
    if idx < 0:
        return text, []
    current = text[idx + len(_CURRENT_MARK):].strip()
    history = text[len(_CONTEXT_HEADER):idx].strip()
    messages: List[Dict[str, str]] = []
    for line in history.splitlines():
        line = line.strip()
        if line.startswith("User:"):
            content = line[5:].strip()
            role = "user"
        elif line.startswith("OctaOS:"):
            content = line[7:].strip()
            role = "assistant"
        else:
            continue
        if not content or _WELCOME_SNIPPET in content:
            continue
        messages.append({"role": role, "content": content})
    return current or text, messages

def _assistant_message(result: Dict[str, Any]) -> str:
    results = result.get("results")
    if isinstance(results, list):
        lines = []
        for item in results:
            if isinstance(item, str) and item.strip():
                lines.append(item.strip())
            elif isinstance(item, dict):
                text = item.get("message") or item.get("summary") or ""
                if str(text).strip():
                    lines.append(str(text).strip())
        if lines:
            return "\n\n".join(lines)
    plan = result.get("plan")
    if isinstance(plan, dict) and str(plan.get("message") or "").strip():
        return str(plan["message"]).strip()
    briefing = result.get("briefing")
    if isinstance(briefing, dict) and str(briefing.get("briefing_text") or "").strip():
        return str(briefing["briefing_text"]).strip()
    return ""


@router.post("/execute")
async def execute_manager_goal(
    payload: ExecuteGoalRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Run the signed-in user's goal through the working orchestrator.

    The assistant sends {goal, risk_level}. Planning used to call OpenAI with
    no key and then report a generic failure, so the typed request never ran.
    """
    goal, parsed_history = unwrap_assistant_goal(payload.goal or "")
    if not goal:
        raise HTTPException(status_code=400, detail="Goal prompt cannot be empty.")

    tenant_id = getattr(current_user, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=403, detail="An active tenant is required for orchestration.")

    history = [turn.model_dump() for turn in (payload.messages or [])] or parsed_history

    from app.services.agents.orchestrator import OrchestratorAgent

    try:
        result = await OrchestratorAgent(db, str(tenant_id)).handle_prompt(
            prompt=goal,
            provider="auto",
            messages=history or None,
        )
    except Exception as exc:
        import logging
        logging.getLogger(__name__).error(f"[Orchestrator] Execution failed: {exc}", exc_info=True)
        err_msg = str(exc)
        if "API key" in err_msg or "provider" in err_msg.lower():
            raise HTTPException(
                status_code=502,
                detail=f"AI model provider error: {err_msg}",
            )
        raise HTTPException(
            status_code=500,
            detail=f"Orchestration error: {err_msg}",
        )

    if not isinstance(result, dict):
        result = {"results": [{"status": "success", "message": str(result)}]}
    message = _assistant_message(result)
    if not message:
        raise HTTPException(status_code=502, detail="The model returned no answer for that request.")
    return {
        "message": message,
        "status": "completed",
        "user_goal": goal,
        "risk_level": payload.risk_level or "NORMAL",
        "mode": result.get("mode") or "execution",
        "plan": result.get("plan") or {},
        "results": result.get("results") or [{"status": "success", "message": message}],
        "briefing": result.get("briefing"),
    }
