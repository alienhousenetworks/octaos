import json
import random
import smtplib
import urllib.parse
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import base64
import httpx
from datetime import datetime, timedelta

from app.services.agents.base import BaseAgent
from app.models.verticals import Candidate
from app.models.teams import AgentMetric
from app.models.base import APICredential
from app.core.security import decrypt_api_key

class HRAgent(BaseAgent):
    def __init__(self, db, tenant_id):
        super().__init__(db, tenant_id, "HR AI")

    async def execute_task(self, task: dict) -> dict:
        action = task.get("action")
        params = task.get("parameters", {})
        
        if action == "source_candidates":
            return await self._source_candidates(params)
        elif action == "candidate_outreach":
            return await self._candidate_outreach(params)
        elif action == "schedule_interview":
            return await self._schedule_interview(params)
        return {"status": f"Unknown action: {action}"}

    async def _source_candidates(self, params: dict):
        role = params.get("role", "Software Engineer")
        requirements = params.get("requirements", "General qualifications")
        salary = params.get("salary", "$100,000/year")
        count = params.get("count", 5)
        platforms = params.get("platforms", ["linkedin"])
        
        self.log_activity("Candidate Sourcing", f"Sourcing {count} candidates for role: '{role}' from {', '.join(platforms)}")
        
        created_count = 0
        for platform in platforms:
            # Check for API credentials
            cred = self.db.query(APICredential).filter_by(
                tenant_id=self.tenant_id, provider=platform.lower()
            ).first()

            if cred and cred.encrypted_key:
                # Real API flow
                try:
                    candidates_data = await self._fetch_real_candidates(
                        platform, decrypt_api_key(cred.encrypted_key), role, requirements, count
                    )
                except Exception as e:
                    raise ValueError(f"Failed to fetch candidates from {platform}: {e}. Please check your {platform} API key or settings.")
            else:
                raise ValueError(f"No API credentials found for {platform}. Please configure your API credentials for {platform} under Platform Setup -> API Settings.")

            for data in candidates_data:
                # Check duplicate email
                exists = self.db.query(Candidate).filter_by(tenant_id=self.tenant_id, email=data["email"]).first()
                if not exists:
                    scorecard = {
                        "skills": data.get("skills", []),
                        "experience_summary": data.get("experience_summary", ""),
                        "match_score": data.get("match_score", 80),
                        "requirements_match": data.get("requirements_match", ""),
                        "salary_expectation": data.get("salary_expectation", salary),
                        "source_platform": platform,
                        "notes": f"Sourced via HR AI agent from {platform}."
                    }
                    candidate = Candidate(
                        tenant_id=self.tenant_id,
                        name=data["name"],
                        email=data["email"],
                        role=role,
                        scorecard=scorecard,
                        status="sourced"
                    )
                    self.db.add(candidate)
                    created_count += 1
        
        self.db.commit()
        
        # Update metrics
        metric = self.db.query(AgentMetric).filter_by(
            tenant_id=self.tenant_id, metric_name="candidates_sourced"
        ).first()
        if not metric:
            metric = AgentMetric(tenant_id=self.tenant_id, metric_name="candidates_sourced", value=0.0)
            self.db.add(metric)
        metric.value += created_count
        self.db.commit()

        self.log_activity("Sourcing Complete", f"Successfully sourced {created_count} candidate profiles in the database.", "success")
        return {"status": "success", "sourced_count": created_count}

    async def _fetch_real_candidates(self, platform: str, api_key: str, role: str, requirements: str, count: int):
        async with httpx.AsyncClient() as client:
            platform = platform.lower()
            if platform == "greenhouse":
                res = await client.get(
                    "https://harvest.greenhouse.io/v1/candidates",
                    auth=(api_key, ""),
                    params={"per_page": count},
                    timeout=30.0,
                )
                if res.status_code == 200:
                    return [
                        {
                            "name": c.get("first_name", "") + " " + c.get("last_name", ""),
                            "email": (c.get("email_addresses") or [{}])[0].get("value", f"candidate{c['id']}@example.com"),
                            "skills": [s.strip() for s in requirements.split(",")[:4]] or ["General"],
                            "experience_summary": f"Greenhouse candidate for {role}.",
                            "match_score": 80,
                            "requirements_match": "Sourced via Greenhouse API.",
                            "salary_expectation": "Market rate",
                        }
                        for c in res.json()[:count]
                    ]
            elif platform == "lever":
                res = await client.get(
                    "https://api.lever.co/v1/opportunities",
                    auth=(api_key, ""),
                    params={"limit": count},
                    timeout=30.0,
                )
                if res.status_code == 200:
                    data = res.json().get("data", [])
                    return [
                        {
                            "name": o.get("name", "Lever Candidate"),
                            "email": (o.get("emails") or [f"lever_{i}@example.com"])[0],
                            "skills": [s.strip() for s in requirements.split(",")[:4]] or ["General"],
                            "experience_summary": f"Lever opportunity for {role}.",
                            "match_score": 82,
                            "requirements_match": "Sourced via Lever API.",
                            "salary_expectation": "Market rate",
                        }
                        for i, o in enumerate(data[:count])
                    ]

        raise ValueError(f"Real API endpoints for {platform} returned no results or are not configured.")

    async def _candidate_outreach(self, params: dict):
        channel = params.get("channel", "smtp")
        subject = params.get("subject", "Exciting job opportunity: {role}")
        body_template = params.get("body_template", "Hello {name},\n\nI saw your profile and thought you would be a great fit for our {role} opening...")
        candidate_id = params.get("candidate_id")

        query = self.db.query(Candidate).filter(
            Candidate.tenant_id == self.tenant_id
        )
        if candidate_id:
            query = query.filter(Candidate.id == candidate_id)
        else:
            query = query.filter(Candidate.status.in_(["sourced", "accepted"]))
        
        candidates = query.all()
        if not candidates:
            self.log_activity("Candidate Outreach", "No sourced candidates found needing outreach.", "success")
            return {"status": "success", "sent_count": 0}

        self.log_activity("Recruiter Outreach", f"Initiating outreach to {len(candidates)} candidates via {channel}.")

        # Check SMTP settings if using SMTP
        smtp_credentials = None
        if channel == "smtp":
            cred = self.db.query(APICredential).filter_by(
                tenant_id=self.tenant_id, provider="smtp"
            ).first()
            if cred and cred.encrypted_key:
                smtp_credentials = self._parse_smtp_credentials(decrypt_api_key(cred.encrypted_key))
            
            if not smtp_credentials:
                raise ValueError("No SMTP server details configured. Please configure SMTP credentials under Platform Setup -> API Settings to send outreach emails.")

        sent_count = 0
        for cand in candidates:
            scorecard = cand.scorecard or {}
            
            prompt = f"""Write a personalized recruiter outreach email.
Candidate Name: {cand.name}
Role Opening: {cand.role}
Candidate Skills: {', '.join(scorecard.get('skills', []))}
Experience Summary: {scorecard.get('experience_summary', '')}
Salary Budget: {scorecard.get('salary_expectation', '')}
Base Template: {body_template}
Subject: {subject}
Output a JSON object with keys 'subject' and 'body'. No other text."""
            
            response = await self.llm.complete(prompt=prompt, provider="anthropic", model="claude-3-haiku-20240307")
            
            outbound_subject = subject.format(role=cand.role, name=cand.name)
            outbound_body = body_template.format(role=cand.role, name=cand.name)
            
            try:
                cleaned = response.strip().strip("```json").strip("```").strip()
                parsed = json.loads(cleaned)
                outbound_subject = parsed.get("subject", outbound_subject)
                outbound_body = parsed.get("body", outbound_body)
            except:
                pass # Fallback to template

            # Send or Simulate
            sent_successfully = False
            if channel == "smtp":
                try:
                    sent_successfully = self._send_actual_email(
                        smtp_credentials, cand.email, outbound_subject, outbound_body
                    )
                except Exception as e:
                    raise ValueError(f"SMTP email outreach failed for {cand.name} ({cand.email}): {str(e)}. Please check your SMTP settings.")
            elif channel == "gmail":
                cred = self.db.query(APICredential).filter_by(
                    tenant_id=self.tenant_id, provider="gmail"
                ).first()
                if cred and cred.encrypted_key:
                    try:
                        self._send_gmail_api_email(decrypt_api_key(cred.encrypted_key), cand.email, outbound_subject, outbound_body)
                        sent_successfully = True
                    except Exception as e:
                        raise ValueError(f"Gmail API outreach failed for {cand.name} ({cand.email}): {str(e)}. Please check your Gmail connection.")
                else:
                    raise ValueError("No Gmail API credentials found. Please connect Google Workspace under Platform Setup -> API Settings to send outreach emails.")
            else:
                sent_successfully = True

            if channel in ("smtp", "gmail") and not sent_successfully:
                raise ValueError(f"Failed to send email via {channel.upper()} for {cand.name}. Please verify your credentials and connection.")

            self.log_activity(
                f"Outreach Sent ({channel.upper()})",
                f"Recruiter message to candidate: {cand.name} ({cand.email}). Subject: '{outbound_subject}'"
            )

            cand.status = "screened"
            cand.scorecard = {
                **scorecard,
                "outreach_channel": channel,
                "outbound_subject": outbound_subject,
                "outbound_body": outbound_body,
                "sent_actual": sent_successfully
            }
            sent_count += 1
            
        self.db.commit()
        return {"status": "success", "sent_count": sent_count}

    async def _schedule_interview(self, params: dict):
        tool = params.get("tool", "google_calendar")
        candidate_id = params.get("candidate_id")

        query = self.db.query(Candidate).filter(
            Candidate.tenant_id == self.tenant_id
        )
        if candidate_id:
            query = query.filter(Candidate.id == candidate_id)
        else:
            query = query.filter(Candidate.status == "accepted")
            
        candidates = query.all()
        if not candidates:
            self.log_activity("Schedule Interviews", "No accepted candidates found. Cannot book interviews.", "success")
            return {"status": "success", "booked_interviews": 0}

        self.log_activity("Interview Scheduling", f"Scheduling interviews for {len(candidates)} candidates.")

        booked_count = 0
        for cand in candidates:
            scorecard = cand.scorecard or {}
            meeting_time = scorecard.get("suggested_time") or scorecard.get("meeting_time") or "Next business day at 11:00 AM local time"
            meet_url = ""
            
            # Check for Google Calendar API
            calendar_cred = self.db.query(APICredential).filter_by(
                tenant_id=self.tenant_id, provider="google_calendar"
            ).first()

            if not calendar_cred or not calendar_cred.encrypted_key.strip():
                raise ValueError("No Google Calendar credentials found. Please connect Google Workspace under Platform Setup -> API Settings to schedule calendar events.")

            try:
                # Call Google Calendar API
                meet_url_real, actual_time = self._create_calendar_event(decrypt_api_key(calendar_cred.encrypted_key), cand.email, meeting_time)
                meet_url = meet_url_real or f"https://meet.google.com/hr-{cand.id[:8]}"
                meeting_time = actual_time or meeting_time
            except Exception as ce:
                raise ValueError(f"Google Calendar API Error: {str(ce)}. Please verify your Google Workspace connection.")

            cand.status = "interviewed"
            cand.scorecard = {
                **cand.scorecard,
                "meeting_time": meeting_time,
                "meeting_link": meet_url,
                "calendar_booked": True
            }
            booked_count += 1
            
            self.log_activity(
                "Interview Scheduled",
                f"Booked interview with candidate {cand.name} ({cand.role}) for {meeting_time}. Meet: {meet_url}",
                "success"
            )
            
            # Update interview metrics
            metric_int = self.db.query(AgentMetric).filter_by(
                tenant_id=self.tenant_id, metric_name="interviews_scheduled"
            ).first()
            if not metric_int:
                metric_int = AgentMetric(tenant_id=self.tenant_id, metric_name="interviews_scheduled", value=0.0)
                self.db.add(metric_int)
            metric_int.value += 1.0
            
            # Also increment general meetings booked metric
            metric_meet = self.db.query(AgentMetric).filter_by(
                tenant_id=self.tenant_id, metric_name="meetings_booked"
            ).first()
            if not metric_meet:
                metric_meet = AgentMetric(tenant_id=self.tenant_id, metric_name="meetings_booked", value=0.0)
                self.db.add(metric_meet)
            metric_meet.value += 1.0
            
            self.db.commit()

        self.db.commit()
        return {"status": "success", "booked_interviews": booked_count}

    def _parse_smtp_credentials(self, key_str: str) -> dict:
        try:
            parsed = urllib.parse.urlparse(key_str.strip())
            if parsed.scheme == "smtp":
                return {
                    "username": parsed.username or "",
                    "password": parsed.password or "",
                    "host": parsed.hostname or "localhost",
                    "port": parsed.port or 587
                }
        except:
            pass
        return None

    def _send_actual_email(self, smtp_cred: dict, to_email: str, subject: str, body: str) -> bool:
        msg = MIMEMultipart()
        msg['From'] = smtp_cred["username"]
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP(smtp_cred["host"], smtp_cred["port"])
        server.starttls()
        server.login(smtp_cred["username"], smtp_cred["password"])
        server.send_message(msg)
        server.quit()
        return True

    def _send_gmail_api_email(self, cred_json: str, to_email: str, subject: str, body: str):
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        
        creds_data = json.loads(cred_json)
        creds = Credentials(**creds_data)
        
        service = build('gmail', 'v1', credentials=creds)
        message = MIMEText(body)
        message['to'] = to_email
        message['subject'] = subject
        raw_msg = base64.urlsafe_b64encode(message.as_bytes()).decode()
        
        service.users().messages().send(userId='me', body={'raw': raw_msg}).execute()

    def _create_calendar_event(self, cred_json: str, attendee_email: str, suggested_time: str):
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        
        creds_data = json.loads(cred_json)
        creds = Credentials(**creds_data)
        service = build('calendar', 'v3', credentials=creds)
        
        start_time = datetime.utcnow() + timedelta(days=1)
        end_time = start_time + timedelta(hours=1)
        
        event = {
            'summary': 'Interview',
            'description': 'Interview scheduled by HR AI.',
            'start': {
                'dateTime': start_time.isoformat() + 'Z',
                'timeZone': 'UTC',
            },
            'end': {
                'dateTime': end_time.isoformat() + 'Z',
                'timeZone': 'UTC',
            },
            'attendees': [
                {'email': attendee_email},
            ],
            'conferenceData': {
                'createRequest': {
                    'requestId': f"hr-meet-{random.randint(1000,9999)}",
                    'conferenceSolutionKey': {'type': 'hangoutsMeet'}
                }
            }
        }
        
        event_result = service.events().insert(
            calendarId='primary', 
            body=event, 
            conferenceDataVersion=1
        ).execute()
        
        meet_link = event_result.get('hangoutLink')
        actual_time_str = event_result.get('start', {}).get('dateTime', suggested_time)
        return meet_link, actual_time_str

    async def daily_routine(self):
        self.log_activity("Daily Routine", "Checking active job sourcing campaigns.", status="success")
