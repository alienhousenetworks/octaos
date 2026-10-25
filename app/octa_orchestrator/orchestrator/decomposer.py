import json
import httpx
from pydantic import BaseModel, model_validator
from typing import List, Optional

class SubTask(BaseModel):
    task_id: str
    description: str
    assigned_agent: str  # e.g., "data_collector", "market_analyst", "code_executor"
    dependencies: List[str]
    roi_priority: int  # 1 (Critical) to 5 (Low)

class ExecutionPlanDAG(BaseModel):
    goal: str
    tasks: List[SubTask]
    estimated_total_roi: str

    @model_validator(mode="after")
    def validate_dependency_graph(self):
        ids = [task.task_id for task in self.tasks]
        if not ids or len(ids) != len(set(ids)):
            raise ValueError("Execution plan must contain tasks with unique IDs")
        known = set(ids)
        indegree = {task.task_id: 0 for task in self.tasks}
        children = {task.task_id: [] for task in self.tasks}
        for task in self.tasks:
            if not task.description.strip() or not task.assigned_agent.strip():
                raise ValueError(f"Task {task.task_id} is missing a description or assigned agent")
            if len(task.dependencies) != len(set(task.dependencies)):
                raise ValueError(f"Task {task.task_id} contains duplicate dependencies")
            missing = set(task.dependencies) - known
            if missing:
                raise ValueError(f"Task {task.task_id} has unknown dependencies: {sorted(missing)}")
            if task.task_id in task.dependencies:
                raise ValueError(f"Task {task.task_id} cannot depend on itself")
            indegree[task.task_id] = len(task.dependencies)
            for parent in task.dependencies:
                children[parent].append(task.task_id)
        ready = [task_id for task_id, degree in indegree.items() if degree == 0]
        visited = 0
        while ready:
            node = ready.pop()
            visited += 1
            for child in children[node]:
                indegree[child] -= 1
                if indegree[child] == 0:
                    ready.append(child)
        if visited != len(ids):
            raise ValueError("Execution plan contains a dependency cycle")
        return self

DECOMPOSER_PROMPT = """
You are the AI Executive Manager. Break down the user's high-level request into a Directed Acyclic Graph (DAG) of actionable sub-tasks.
Each task must be assigned to an appropriate specialized worker sub-agent.
Prioritize sub-tasks by business ROI and list explicit dependencies.

Return ONLY valid JSON matching this schema:
{{
  "goal": "Original user goal",
  "tasks": [
    {{
      "task_id": "task_1",
      "description": "Extract market trend metrics",
      "assigned_agent": "market_analyst",
      "dependencies": [],
      "roi_priority": 1
    }}
  ],
  "estimated_total_roi": "Not assessed until measured evidence is available"
}}
"""

class DAGDecomposer:
    """Decomposes vague user requests into structured, executable DAG graphs."""
    
    def __init__(self, slm_url: str = None, api_key: str = None):
        self.slm_url = slm_url or "https://api.openai.com/v1/chat/completions"
        self.api_key = api_key

    async def decompose_goal(self, user_goal: str, model_name: str = "gpt-4o") -> ExecutionPlanDAG:
        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": DECOMPOSER_PROMPT},
                {"role": "user", "content": f"User Goal: {user_goal}"}
            ],
            "response_format": {"type": "json_object"}
        }
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}

        try:
            async with httpx.AsyncClient() as client:
                res = await client.post(self.slm_url, json=payload, headers=headers, timeout=40.0)
                if res.status_code != 200:
                    raise RuntimeError(f"Planner provider returned HTTP {res.status_code}")
                data = res.json()["choices"][0]["message"]["content"]
                parsed = json.loads(data)
                return ExecutionPlanDAG(**parsed)
        except Exception as exc:
            # Never replace a failed plan with a generic task labelled as successful.
            raise RuntimeError("Orchestration planning failed; no execution plan was accepted.") from exc
