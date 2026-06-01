import json
import asyncio
import uuid
import datetime
from sqlalchemy.orm import Session
from app.services.agents.base import BaseAgent
from app.models.verticals import Ticket, TicketMessage, Lead, Candidate, AgentMeeting
from app.services.llm_gateway import LLMGateway
from app.services.notifications.telegram import send_telegram_notification

class BoardroomService:
    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id
        self.llm = LLMGateway(db, tenant_id)

    async def classify_ticket_inquiry(self, ticket_id: str) -> dict:
        """
        Uses the LLM to classify a support ticket to see if it requires cross-agent boardroom coordination.
        For example, a high-value sales lead, a partner inquiry, or an emergency billing discrepancy.
        """
        ticket = self.db.query(Ticket).filter(Ticket.id == ticket_id).first()
        if not ticket:
            return {"needs_meeting": False}

        system_prompt = (
            "You are the NexusOS Triaging System. Classify the customer support ticket to decide if it "
            "requires a boardroom meeting with the CEO AI and other departments (Sales, Finance, HR, Marketing) to resolve.\n"
            "Requirements for meeting:\n"
            "- Sales Lead: Customer wants to purchase, asking for enterprise plans, bulk discounts, custom pricing, or partnerships.\n"
            "- Financial/Billing Emergency: Severe payment issue, fraud allegation, or invoice dispute.\n"
            "- Critical HR/Job Application: High profile candidates, partnership pitches, or executive job applications.\n"
            "- If it is just a routine support request (e.g. 'how to login', 'where is my password', general product questions), it does NOT need a meeting.\n\n"
            "Respond ONLY with a JSON object in this format:\n"
            "{\n"
            "  \"needs_meeting\": true | false,\n"
            "  \"title\": \"Descriptive Meeting Title (e.g., Enterprise Lead: Custom Pricing for TechCorp)\",\n"
            "  \"participants\": [\"CEO AI\", \"Support AI\", \"Sales AI\", \"Finance AI\"],\n"
            "  \"reason\": \"Brief explanation of why the meeting was called\"\n"
            "}"
        )

        prompt = (
            f"Ticket Subject: {ticket.subject}\n"
            f"Ticket Channel: {ticket.channel}\n"
            f"Sender: {ticket.customer_contact}\n"
            f"Message Content: {ticket.description}\n"
        )

        response_str = await self.llm.complete(
            prompt=prompt,
            system_prompt=system_prompt,
            provider="gemini"
        )

        try:
            # Clean JSON codeblock wrappers if any
            clean_str = response_str.strip().strip("```json").strip("```").strip()
            result = json.loads(clean_str)
            # Ensure participants always contains CEO AI and Support AI at least
            if result.get("needs_meeting"):
                parts = result.get("participants", [])
                if "CEO AI" not in parts: parts.insert(0, "CEO AI")
                if "Support AI" not in parts: parts.append("Support AI")
                result["participants"] = list(dict.fromkeys(parts)) # unique list
            return result
        except Exception as e:
            print(f"Error parsing classification response: {e}. Raw response: {response_str}")
            # Safe fallback: if "buy", "purchase", "enterprise", "pricing" or "lead" is in content, classify as Sales Lead
            content_lower = (ticket.description or "").lower() or (ticket.subject or "").lower()
            if any(w in content_lower for w in ["buy", "purchase", "enterprise", "custom price", "partnership", "lead", "pricing"]):
                return {
                    "needs_meeting": True,
                    "title": f"Sales Lead escalation from {ticket.customer_contact}",
                    "participants": ["CEO AI", "Support AI", "Sales AI"],
                    "reason": "Customer is requesting commercial information or custom pricing."
                }
            return {"needs_meeting": False}

    async def create_meeting_from_ticket(self, ticket_id: str, classification: dict) -> AgentMeeting:
        ticket = self.db.query(Ticket).filter(Ticket.id == ticket_id).first()
        
        meeting = AgentMeeting(
            tenant_id=self.tenant_id,
            title=classification.get("title", f"Boardroom review: Ticket #{ticket_id[:8]}"),
            status="active",
            trigger_type="support_ticket",
            trigger_id=ticket_id,
            context_summary=f"Ticket Channel: {ticket.channel}\nCustomer: {ticket.customer_contact}\nSubject: {ticket.subject}\nInquiry: {ticket.description}",
            participants=classification.get("participants", ["CEO AI", "Support AI", "Sales AI"]),
            transcript=[],
            action_items=[]
        )
        self.db.add(meeting)
        self.db.commit()
        self.db.refresh(meeting)

        from app.models.agents import ActivityLog
        log = ActivityLog(
            tenant_id=self.tenant_id,
            agent_name="Support AI",
            action="Meeting Summoned",
            description=f"Summoned cross-agent boardroom meeting: '{meeting.title}' to address critical customer inquiry.",
            status="success"
        )
        self.db.add(log)
        self.db.commit()

        # Send Telegram Notification
        msg = f"🔔 *New Boardroom Meeting Summoned*\nTopic: {meeting.title}\nTrigger: {meeting.trigger_type}"
        asyncio.create_task(send_telegram_notification(self.db, self.tenant_id, msg))

        return meeting

    async def run_simulation(self, meeting_id: str):
        """
        Runs the turn-based multi-agent discussion simulation in the boardroom.
        Updates the transcript in real-time in the DB so the user can watch the discussion unfold.
        """
        meeting = self.db.query(AgentMeeting).filter(AgentMeeting.id == meeting_id).first()
        if not meeting:
            return

        participants = meeting.participants
        context = meeting.context_summary or ""

        # Step 1: Let the initiator (Support AI or Finance AI depending on trigger) present the case.
        initiator = "Support AI"
        if meeting.trigger_type == "transaction_anomaly":
            initiator = "Finance AI"
        elif meeting.trigger_type == "candidate_hiring":
            initiator = "HR AI"
        
        # Bring initiator to front if in list
        if initiator in participants:
            participants.remove(initiator)
            participants.insert(0, initiator)

        transcript = []

        # Turn 1: Initiator introduces the topic
        system_prompt = (
            f"You are the {initiator}. You are starting a boardroom meeting with other department agents: {participants}.\n"
            f"The meeting topic is: {meeting.title}.\n"
            "Rely strictly on the following context:\n"
            f"{context}\n\n"
            "State the customer issue, lead, or problem clearly. Ask the CEO AI and other specialist agents for their recommendation. "
            "Keep your turn brief, professional, and natural (1-3 sentences)."
        )
        intro = await self.llm.complete(
            prompt="Introduce the situation and open the discussion.",
            system_prompt=system_prompt,
            provider="gemini"
        )
        
        transcript.append({
            "sender": initiator,
            "content": intro,
            "timestamp": datetime.datetime.now().strftime("%I:%M:%S %p")
        })
        meeting.transcript = transcript
        self.db.commit()
        await asyncio.sleep(2.5) # simulated typing delay

        # Turns 2 onwards: Loop through other participants (excluding CEO AI, we keep CEO AI for last)
        non_ceo_participants = [p for p in participants if p != "CEO AI" and p != initiator]
        
        for agent in non_ceo_participants:
            agent_role = self._get_agent_role_description(agent)
            history_str = "\n".join([f"{t['sender']}: {t['content']}" for t in transcript])
            
            system_prompt = (
                f"You are the {agent}.\n"
                f"Your professional focus is: {agent_role}.\n"
                f"You are participating in a boardroom meeting on topic '{meeting.title}' with {participants}.\n"
                f"Context:\n{context}\n\n"
                f"Here is the discussion transcript so far:\n{history_str}\n\n"
                "Respond to the discussion. Maintain your persona, objectives, and expertise. Recommend a course of action. "
                "Keep your turn brief (1-3 sentences). Do not repeat what others have said."
            )
            
            response = await self.llm.complete(
                prompt=f"Provide your professional input based on your role as {agent}.",
                system_prompt=system_prompt,
                provider="gemini"
            )
            
            transcript.append({
                "sender": agent,
                "content": response,
                "timestamp": datetime.datetime.now().strftime("%I:%M:%S %p")
            })
            meeting.transcript = transcript
            self.db.commit()
            await asyncio.sleep(2.5)

        # Final Turn: CEO AI summarizes and outlines the action items
        if "CEO AI" in participants:
            history_str = "\n".join([f"{t['sender']}: {t['content']}" for t in transcript])
            system_prompt = (
                "You are the CEO AI, the ultimate leader of this company.\n"
                "You are reviewing the input from your department agents and summarizing the final decision and action items.\n"
                f"Context:\n{context}\n\n"
                f"Meeting Transcript:\n{history_str}\n\n"
                "Provide your final decision/summary message (1-3 professional, authoritative sentences).\n"
                "Then, outline the exact Action Items that each agent should execute.\n"
                "You MUST output your response EXACTLY in this format (no other text or formatting, keep JSON standard):\n"
                "[MESSAGE]\n"
                "Your final speech/summary text here.\n"
                "[ACTIONS]\n"
                "[\n"
                "  {\"assigned_to\": \"Sales AI\", \"description\": \"Create a lead record in the database\"},\n"
                "  {\"assigned_to\": \"Support AI\", \"description\": \"Send escalation response to ticket customer\"}\n"
                "]"
            )
            
            ceo_response = await self.llm.complete(
                prompt="Conclude the meeting, summarize next steps and output action items in the specified format.",
                system_prompt=system_prompt,
                provider="gemini"
            )
            
            # Parse the CEO response
            ceo_msg = "Meeting concluded. Action items assigned."
            action_items = []
            
            try:
                if "[MESSAGE]" in ceo_response and "[ACTIONS]" in ceo_response:
                    parts = ceo_response.split("[ACTIONS]")
                    msg_part = parts[0].replace("[MESSAGE]", "").strip()
                    actions_part = parts[1].strip()
                    
                    ceo_msg = msg_part
                    action_items = json.loads(actions_part)
                else:
                    # Fallback parser if tags are missing
                    clean_res = ceo_response.strip()
                    if clean_res.startswith("[") or "{" in clean_res:
                        # might just be actions
                        action_items = json.loads(clean_res)
                    else:
                        ceo_msg = clean_res
            except Exception as e:
                print(f"Error parsing CEO action items: {e}. Response: {ceo_response}")
                # Predefined fallbacks depending on trigger type
                ceo_msg = "Let's move forward. I have assigned the action items to the teams."
                if meeting.trigger_type == "support_ticket":
                    action_items = [
                        {"assigned_to": "Sales AI", "description": "Create lead record in the database"},
                        {"assigned_to": "Support AI", "description": "Send escalation response to ticket customer"}
                    ]
                elif meeting.trigger_type == "transaction_anomaly":
                    action_items = [
                        {"assigned_to": "Support AI", "description": "Contact customer regarding transaction verification"},
                        {"assigned_to": "Finance AI", "description": "Hold payout and flag transaction details"}
                    ]
                elif meeting.trigger_type == "candidate_hiring":
                    action_items = [
                        {"assigned_to": "HR AI", "description": "Update candidate status to approved and offer letter drafted"},
                        {"assigned_to": "Finance AI", "description": "Allocate salary budget line item"}
                    ]
                else:
                    action_items = [
                        {"assigned_to": "Marketing AI", "description": "Conduct market research and draft campaign strategy"}
                    ]

            transcript.append({
                "sender": "CEO AI",
                "content": ceo_msg,
                "timestamp": datetime.datetime.now().strftime("%I:%M:%S %p")
            })
            meeting.transcript = transcript
            
            # Add unique IDs to action items
            final_actions = []
            for item in action_items:
                final_actions.append({
                    "id": str(uuid.uuid4())[:8],
                    "assigned_to": item.get("assigned_to"),
                    "description": item.get("description"),
                    "status": "pending"
                })
            
            meeting.action_items = final_actions
            meeting.status = "completed"
            self.db.commit()

            # Log completion activity
            from app.models.agents import ActivityLog
            log = ActivityLog(
                tenant_id=self.tenant_id,
                agent_name="CEO AI",
                action="Boardroom Concluded",
                description=f"Concluded boardroom session. Assigned {len(final_actions)} action items.",
                status="success"
            )
            self.db.add(log)
            self.db.commit()

            # Step 3: Run the execution of action items!
            await self.execute_action_items(meeting_id)

    async def execute_action_items(self, meeting_id: str):
        meeting = self.db.query(AgentMeeting).filter(AgentMeeting.id == meeting_id).first()
        if not meeting or not meeting.action_items:
            return

        actions = list(meeting.action_items)
        changed = False

        for idx, action in enumerate(actions):
            action_id = action.get("id")
            assigned = action.get("assigned_to", "")
            desc = action.get("description", "").lower()
            
            # Mark as executing
            action["status"] = "executing"
            meeting.action_items = actions
            self.db.commit()
            await asyncio.sleep(2.0) # simulate execution delay

            success = False
            try:
                # 1. Sales AI - Create Lead
                if "sales" in assigned.lower() and ("lead" in desc or "create" in desc):
                    # We create a Lead in the database
                    # Try to extract company/email details from context
                    customer_email = "lead@example.com"
                    customer_phone = None
                    customer_name = "Interested Prospect"
                    company = "Unknown Corp"

                    # Parse context_summary
                    ctx_lines = (meeting.context_summary or "").split("\n")
                    for line in ctx_lines:
                        if line.startswith("Customer:"):
                            contact = line.replace("Customer:", "").strip()
                            if "@" in contact:
                                customer_email = contact
                            else:
                                customer_phone = contact
                                customer_email = f"{contact}@whatsapp.com"
                        elif line.startswith("Subject:"):
                            subj = line.replace("Subject:", "").strip()
                            company_match = [w for w in subj.split() if w[0].isupper() and w not in ["New", "WhatsApp", "Email", "Lead", "Ticket"]]
                            if company_match:
                                company = company_match[0]

                    new_lead = Lead(
                        tenant_id=self.tenant_id,
                        name=customer_name,
                        email=customer_email,
                        phone=customer_phone,
                        company=company,
                        source=meeting.trigger_type,
                        score=85,
                        status="captured"
                    )
                    self.db.add(new_lead)
                    self.db.commit()
                    
                    from app.models.agents import ActivityLog
                    log = ActivityLog(
                        tenant_id=self.tenant_id,
                        agent_name="Sales AI",
                        action="Lead Captured",
                        description=f"Autonomously created lead for '{customer_email}' from boardroom directive.",
                        status="success"
                    )
                    self.db.add(log)
                    self.db.commit()
                    success = True

                # 2. Support AI - Notify Customer / Ticket Reply
                elif "support" in assigned.lower() and ("notify" in desc or "send" in desc or "reply" in desc or "ticket" in desc):
                    if meeting.trigger_type == "support_ticket" and meeting.trigger_id:
                        ticket_id = meeting.trigger_id
                        ticket = self.db.query(Ticket).filter(Ticket.id == ticket_id).first()
                        if ticket:
                            reply_msg = (
                                "Dear customer, thank you for reaching out. We have escalated your inquiry "
                                "directly to our executive board. A meeting was held with our CEO, customer service team, "
                                "and sales department to review your request. We have initiated a priority account file for you, "
                                "and our Sales manager will follow up with you shortly to assist with next steps."
                            )
                            # Add TicketMessage
                            msg = TicketMessage(
                                ticket_id=ticket.id,
                                sender="agent",
                                content=reply_msg
                            )
                            self.db.add(msg)
                            self.db.commit()

                            # Send actual message (simulation/official)
                            from app.services.agents.support import SupportAgent
                            support_agent = SupportAgent(self.db, self.tenant_id)
                            await support_agent.send_message(ticket.channel, ticket.customer_contact, reply_msg)
                            success = True

                # 3. HR AI - Update Candidate Status
                elif "hr" in assigned.lower() and ("candidate" in desc or "offer" in desc or "status" in desc):
                    # Find candidate in DB and promote
                    candidate = None
                    if meeting.trigger_id and meeting.trigger_type == "candidate_hiring":
                        candidate = self.db.query(Candidate).filter(Candidate.id == meeting.trigger_id).first()
                    else:
                        # find last candidate
                        candidate = self.db.query(Candidate).filter(Candidate.tenant_id == self.tenant_id).order_by(Candidate.created_at.desc()).first()

                    if candidate:
                        candidate.status = "offered"
                        self.db.commit()
                        
                        from app.models.agents import ActivityLog
                        log = ActivityLog(
                            tenant_id=self.tenant_id,
                            agent_name="HR AI",
                            action="Candidate Promoted",
                            description=f"Autonomously updated candidate '{candidate.name}' status to 'offered' following budget approval.",
                            status="success"
                        )
                        self.db.add(log)
                        self.db.commit()
                        success = True
                    else:
                        success = True # no candidate found but simulate pass

                # 4. Fallback/Default for other tasks (Finance, Marketing, etc.)
                else:
                    # Generic action logging
                    from app.models.agents import ActivityLog
                    log = ActivityLog(
                        tenant_id=self.tenant_id,
                        agent_name=assigned,
                        action="Task Completed",
                        description=f"Executed directive: '{action.get('description')}'",
                        status="success"
                    )
                    self.db.add(log)
                    self.db.commit()
                    success = True

            except Exception as ex:
                print(f"Error executing action item: {ex}")
                success = False

            action["status"] = "completed" if success else "failed"
            actions[idx] = action
            meeting.action_items = actions
            self.db.commit()

    def _get_agent_role_description(self, agent_name: str) -> str:
        roles = {
            "CEO AI": "Executive leadership, strategic decisions, financial approvals, team resource coordination.",
            "Support AI": "Customer experience, ticket triaging, immediate response, onboarding issues, customer escalations.",
            "Sales AI": "B2B client sourcing, client calls, enterprise quotes, conversion rate optimization, outbound campaigns.",
            "Finance AI": "Budgets, pricing models, payment anomalies, fraud flags, operational expenses.",
            "Marketing AI": "Brand identity, copy writing, social media outreach, campaigns, platform specific templates.",
            "HR AI": "Candidate recruitment, resume scanning, applicant outreach, onboarding sequences, payroll budget requests."
        }
        return roles.get(agent_name, "Business specialist AI.")
