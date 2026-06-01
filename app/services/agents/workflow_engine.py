from sqlalchemy.orm import Session
from app.models.workflows import Workflow, WorkflowTask
from app.models.agents import ActivityLog
from app.models.verticals import Lead, ContentPost
from app.services.ai_gateway import ai_gateway
from app.services.email.sender import send_email
from app.services.credentials import get_decrypted_credential
from app.core.config import settings
from datetime import datetime, timezone, timedelta
import httpx
import os


class WorkflowEngine:
    def __init__(self, db: Session):
        self.db = db

    async def execute_task(self, task: WorkflowTask):
        try:
            task.status = "in_progress"
            self.db.commit()

            workflow = task.workflow
            tenant_id = workflow.tenant_id

            result_data = {}
            if task.task_type == "email_sequence":
                result_data = await self._execute_email_sequence(task, tenant_id)
            elif task.task_type == "linkedin_dm":
                result_data = await self._execute_linkedin_dm(task, tenant_id)
            elif task.task_type == "yelp_auto_reply":
                result_data = await self._execute_yelp_auto_reply(task, tenant_id)
            elif task.task_type == "zillow_scrape":
                result_data = await self._execute_zillow_scrape(task, tenant_id)
            elif task.task_type == "pinterest_schedule":
                result_data = await self._execute_pinterest_schedule(task, tenant_id)
            elif task.task_type == "video_to_clips":
                result_data = await self._execute_video_to_clips(task, tenant_id)
            else:
                result_data = {"message": f"Unknown task type: {task.task_type}"}

            task.result = result_data
            task.status = "completed"

            log = ActivityLog(
                tenant_id=tenant_id,
                agent_name="Workflow Engine",
                action=f"Executed {task.name}",
                description=f"Successfully ran task of type {task.task_type}.",
                status="success",
            )
            self.db.add(log)
            self.db.commit()

        except Exception as e:
            task.status = "failed"
            task.result = {"error": str(e)}

            workflow = task.workflow
            if workflow:
                log = ActivityLog(
                    tenant_id=workflow.tenant_id,
                    agent_name="Workflow Engine",
                    action=f"Failed {task.name}",
                    description=f"Error running task {task.task_type}: {str(e)}",
                    status="failed",
                )
                self.db.add(log)
            self.db.commit()

    async def _execute_email_sequence(self, task: WorkflowTask, tenant_id: str):
        step = task.payload.get("step", 1) if task.payload else 1
        leads = (
            self.db.query(Lead)
            .filter(Lead.tenant_id == tenant_id, Lead.status.in_(["captured", "scored", "enriched"]))
            .limit(5)
            .all()
        )

        content = await ai_gateway.executeRequest(
            db=self.db,
            tenant_id=tenant_id,
            prompt=f"Write cold email step {step} for SaaS product.",
            model=None,
            provider="gemini",
            system_prompt="You are a sales SDR.",
            task_type="email_generation",
        )

        sent = 0
        for lead in leads:
            if send_email(self.db, tenant_id, lead.email, f"SaaS Outreach — Step {step}", content):
                sent += 1
                lead.status = "contacted"

        if step < 3:
            next_task = WorkflowTask(
                workflow_id=task.workflow_id,
                name=f"Cold Email Sequence Step {step + 1}",
                task_type="email_sequence",
                scheduled_at=datetime.now(timezone.utc) + timedelta(days=2),
                payload={"step": step + 1},
            )
            self.db.add(next_task)

        self.db.commit()
        return {"step": step, "emails_sent": sent, "preview": content[:200]}

    async def _execute_linkedin_dm(self, task: WorkflowTask, tenant_id: str):
        limit = task.payload.get("limit", 5) if task.payload else 5
        leads = (
            self.db.query(Lead)
            .filter(Lead.tenant_id == tenant_id)
            .limit(limit)
            .all()
        )

        token, settings = get_decrypted_credential(self.db, tenant_id, "linkedin")
        messages_created = 0
        posts_created = 0

        for lead in leads:
            message = await ai_gateway.executeRequest(
                db=self.db,
                tenant_id=tenant_id,
                prompt=f"Write a concise LinkedIn connection note for {lead.name} at {lead.company}.",
                model=None,
                provider="gemini",
                system_prompt="You are a B2B sales professional.",
                task_type="sales",
            )
            lead.data = {**(lead.data or {}), "linkedin_outreach": message}
            messages_created += 1

            # LinkedIn Messaging API requires partner access; publish as feed post when token available
            if token and lead.data.get("publish_as_post"):
                from app.services.social.linkedin_client import LinkedInClient

                client = LinkedInClient(token, settings)
                await client.publish_post(message)
                posts_created += 1

        self.db.commit()
        return {
            "outreach_drafted": messages_created,
            "linkedin_posts": posts_created,
            "message": (
                "Personalized LinkedIn outreach drafted and saved on leads. "
                "Direct DMs require LinkedIn partner API; use saved messages or enable publish_as_post."
            ),
        }

    async def _execute_yelp_auto_reply(self, task: WorkflowTask, tenant_id: str):
        business_id = (task.payload or {}).get("business_id")
        api_key = settings.YELP_API_KEY or os.environ.get("YELP_API_KEY")
        if not api_key or not business_id:
            return {
                "replied_to": 0,
                "message": "Configure YELP_API_KEY and business_id in task payload.",
            }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"https://api.yelp.com/v3/businesses/{business_id}/reviews",
                headers={"Authorization": f"Bearer {api_key}"},
            )
            resp.raise_for_status()
            reviews = resp.json().get("reviews", [])[:3]

        replies = []
        for review in reviews:
            reply = await ai_gateway.executeRequest(
                db=self.db,
                tenant_id=tenant_id,
                prompt=f"Write a professional reply to this Yelp review (rating {review.get('rating')}): {review.get('text')}",
                model=None,
                provider="gemini",
                system_prompt="You are a restaurant owner.",
                task_type="support",
            )
            replies.append({"review_id": review.get("id"), "draft_reply": reply})

        return {"replied_to": len(replies), "drafts": replies}

    async def _execute_zillow_scrape(self, task: WorkflowTask, tenant_id: str):
        location = (task.payload or {}).get("location", "Austin, TX")
        token, _ = get_decrypted_credential(self.db, tenant_id, "google_places")
        leads_found = 0

        if token:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(
                    "https://maps.googleapis.com/maps/api/place/textsearch/json",
                    params={"query": f"real estate {location}", "key": token},
                )
                if resp.status_code == 200:
                    for place in resp.json().get("results", [])[:15]:
                        lead = Lead(
                            tenant_id=tenant_id,
                            name="Listing Agent",
                            email=f"info@{place.get('name', 'agency').lower().replace(' ', '')}.com",
                            company=place.get("name", "Real Estate"),
                            source=f"Google Places: {location}",
                            status="captured",
                        )
                        self.db.add(lead)
                        leads_found += 1
                    self.db.commit()

        return {"leads_found": leads_found, "location": location, "source": "google_places"}

    async def _execute_pinterest_schedule(self, task: WorkflowTask, tenant_id: str):
        pins = (task.payload or {}).get("pins", 3)
        token, _ = get_decrypted_credential(self.db, tenant_id, "pinterest")
        token = token or settings.PINTEREST_ACCESS_TOKEN or os.environ.get("PINTEREST_ACCESS_TOKEN")

        if not token:
            return {"pins_scheduled": 0, "message": "Pinterest access token not configured."}

        board_id = (task.payload or {}).get("board_id")
        if not board_id:
            return {"pins_scheduled": 0, "message": "board_id required in task payload."}

        created = 0
        async with httpx.AsyncClient(timeout=60.0) as client:
            for i in range(pins):
                title = await ai_gateway.executeRequest(
                    db=self.db,
                    tenant_id=tenant_id,
                    prompt=f"Write Pinterest pin title #{i + 1} for marketing content.",
                    model=None,
                    provider="gemini",
                    task_type="marketing",
                )
                image_url = (task.payload or {}).get("image_url", "https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=800")
                resp = await client.post(
                    "https://api.pinterest.com/v5/pins",
                    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                    json={
                        "board_id": board_id,
                        "title": title[:100],
                        "media_source": {"source_type": "image_url", "url": image_url},
                    },
                )
                if resp.status_code < 400:
                    created += 1

        return {"pins_scheduled": created, "board_id": board_id}

    async def _execute_video_to_clips(self, task: WorkflowTask, tenant_id: str):
        transcript = (task.payload or {}).get("transcript", "")
        if not transcript:
            return {"clips": 0, "message": "transcript required in payload."}

        clips_json = await ai_gateway.executeRequest(
            db=self.db,
            tenant_id=tenant_id,
            prompt=(
                f"From this video transcript, extract 3 short social media clip captions (under 220 chars each). "
                f"Return JSON array of strings.\n\n{transcript[:8000]}"
            ),
            model=None,
            provider="gemini",
            task_type="marketing",
        )

        import json

        try:
            cleaned = clips_json.strip().strip("```json").strip("```").strip()
            clips = json.loads(cleaned)
        except Exception:
            clips = [clips_json[:220]]

        for i, caption in enumerate(clips[:3]):
            post = ContentPost(
                tenant_id=tenant_id,
                platform="instagram",
                content=str(caption),
                day=i + 1,
                approval_status="pending",
            )
            self.db.add(post)
        self.db.commit()
        return {"clips": len(clips[:3]), "platform": "instagram"}
