# NexusOS AI Employee Workspace - Setup & Run Guide

Welcome to NexusOS! This platform transforms your business operations by providing autonomous AI employees for Marketing, Sales, Support, and Finance.

## Prerequisites
Ensure you have the following installed on your machine:
- **Python 3.10+**
- **Node.js 18+ & npm**
- **PostgreSQL** (Running locally on default port 5432)
- **Redis** (Running locally on default port 6379)

## 1. Backend Setup (FastAPI & Celery)

1. **Activate the Virtual Environment**
   Open a terminal in the root folder (`jules_session_166401146785413967`) and run:
   ```bash
   source venv/bin/activate
   ```

2. **Install Python Dependencies** (If not already installed)
   ```bash
   pip install -r requirements.txt
   ```

3. **Database Configuration**
   Ensure your local PostgreSQL has a database named `nexusos` and the credentials match your `.env` file (`DATABASE_URL=postgresql://postgres@localhost:5432/nexusos`).
   - *Note: The database tables have already been created.*

4. **Start the FastAPI Server**
   ```bash
   uvicorn app.main:app --port 8000 --reload
   ```
   The backend API will now be running at `http://localhost:8000`.

5. **Start the Celery Worker & Beat (Optional for Autonomous Mode)**
   Open a **new terminal tab**, activate the virtual environment, and run:
   ```bash
   celery -A app.worker.tasks worker --loglevel=info
   ```
   To trigger the daily autonomous routines (like auto-posting at 8 AM), open another tab and run:
   ```bash
   celery -A app.worker.tasks beat --loglevel=info
   ```

## 2. Frontend Setup (Next.js)

1. **Navigate to Frontend Directory**
   Open a new terminal tab and navigate to the frontend folder:
   ```bash
   cd frontend
   ```

2. **Install Dependencies**
   ```bash
   npm install
   ```

3. **Start the Development Server**
   ```bash
   npm run dev
   ```
   The frontend will be accessible at `http://localhost:3000`.

## 3. How to Use the System & Marketplace Automations

NexusOS features an interactive **Workflow Marketplace** and an autonomous **Orchestrator AI** to let non-technical users install and execute complex automations without writing code.

### Step-by-Step Marketplace Workflow

1. **Select and Install a Pack**
   - Click **Workflow Marketplace** in the sidebar.
   - Choose a pack tailored to your industry:
     - **Restaurant Growth Pack**: Automates Yelp reviews, daily Instagram specials, and local lead generation.
     - **SaaS Outreach System**: Handles cold email sequencing, LinkedIn DMs, and demo bookings.
     - **Real Estate Lead Engine**: Auto-generates property listings, scrapes Zillow, and automates client follow-ups.
     - **Creative Content Lab**: Converts video transcripts to social clips, drafts blog outlines, and schedules pins.
   - Click **Install Pack**. The app instantly registers this pack and displays it under **Installed Automations** on the Operating Dashboard.

2. **Configure API Keys**
   - Go to the **Instructions & APIs** tab (under **Platform Setup & API Connection Guide**).
   - Under the **API Provider Setup** sub-tab, identify which integrations your installed pack requires.
   - Click the **API Settings** button in the header (or click **Configure** on the respective provider card), paste your key, and save.
   - The status badge on the card will update in real-time to green **● Connected** once configured.
   - **Pro-Tip for Non-Tech Users**: You can paste your key directly into the **Orchestrator AI** chat (e.g. `"My Claude key is: sk-ant-..."`). The AI will automatically detect the key pattern and configure the provider for you!

3. **Instruct the Orchestrator AI**
   - Navigate to the **Orchestrator AI** tab.
   - Type a natural language command explaining your goal. For instance: *"Trigger the SaaS Outreach System for 5 New York tech CEOs."*
   - The Orchestrator will automatically parse your prompt, check active API connections, verify the installed pack, and delegate sub-tasks to specialized Marketing, Sales, or Support agents.

4. **Review & Approve Content**
   - Navigate to the **Operating Dashboard**.
   - Scroll down to the **Approvals Pipeline** queue. You will see generated drafts (such as draft social posts, outbound email sequences, or sourced leads) marked as `Pending Review`.
   - Click **Approve** to publish/send them, or click **Reject** to dismiss or request changes.

---
## 4. Detailed API Connection & Key Setup

To operate autonomous agents, you need to connect your external tools. The Orchestrator AI requires at least one primary LLM key to function, and other agents require their respective API keys. Below are detailed, step-by-step setup instructions for each service:

### 1. LLM Brains (Claude / OpenAI)
*Powers decision-making and content generation.*

**Claude (Anthropic)**:
1. Go to the [Anthropic Console](https://console.anthropic.com/) and sign in or create an account.
2. Navigate to the **API Keys** dashboard from the main menu.
3. Click on **Create Key**, give it a descriptive name (e.g., "NexusOS Orchestrator"), and generate the key.
4. Copy the key (it should start with `sk-ant-`).
5. In NexusOS, click **API Settings** and paste this key under the Anthropic/Claude section.

**OpenAI**:
1. Go to the [OpenAI Platform API Dashboard](https://platform.openai.com/api-keys).
2. Log in and navigate to the **API Keys** section on the left sidebar.
3. Click **Create new secret key**.
4. Copy the generated key (it usually starts with `sk-proj-` or `sk-`).
5. Paste this key into the NexusOS **API Settings** under OpenAI.

*Note: At least one primary LLM key is mandatory for the Orchestrator AI to operate.*

### 2. Social Media (Meta Graph & LinkedIn)
*Allows the Marketing Agent to publish posts autonomously.*

**Recommended: OAuth connect (industry standard)**

1. Set environment variables in `.env`:
   - `META_APP_ID` / `META_APP_SECRET` — from [Meta for Developers](https://developers.facebook.com/)
   - `LINKEDIN_CLIENT_ID` / `LINKEDIN_CLIENT_SECRET` — from [LinkedIn Developer Portal](https://developer.linkedin.com/)
   - `PUBLIC_BASE_URL` — **optional**. Meta, Instagram, and LinkedIn receive images/videos via **direct binary upload** from the server, so ngrok is **not required** for posting. Only set this if you need publicly reachable `/media/` URLs for other integrations.
2. Start the API, then open in a browser (replace `TENANT_ID`):
   - Meta: `http://localhost:8000/api/v1/meta/auth?tenant_id=TENANT_ID`
   - LinkedIn: `http://localhost:8000/api/v1/linkedin/auth?tenant_id=TENANT_ID`
3. OAuth stores encrypted tokens and auto-discovers your Facebook Page + Instagram Business account.

**Manual token (fallback)**

**Meta Graph API (Instagram & Facebook)**:
1. Log into [Meta for Developers](https://developers.facebook.com/).
2. Go to **My Apps** and click **Create App**. Select the appropriate app type (usually "Business").
3. Add the **Instagram Graph API** product to your app.
4. Navigate to the **Graph API Explorer** tool.
5. Generate a **Page Access Token** and ensure you grant the `instagram_content_publish` permission.
6. Extend the token to a long-lived token via the Access Token Tool.
7. Ensure your Instagram Business Profile is correctly linked to your Facebook Page.
8. Paste the long-lived token into the NexusOS API Settings.

**LinkedIn Share API**:
1. Log into the [LinkedIn Developer Portal](https://developer.linkedin.com/) and click **Create App**.
2. Fill in the required details and link a LinkedIn Company Page.
3. Under the **Products** tab, request access to "Share on LinkedIn" and "Sign In with LinkedIn".
4. Navigate to the **Auth** tab and use the OAuth 2.0 Token Generator to generate an **Access Token**.
5. Copy this Access Token into the NexusOS API Settings.

### 3. Chat Messaging (WhatsApp & Telegram)
*Connects support lines to the Support AI.*

**WhatsApp Cloud Business API**:
1. In your [Meta Developer Console](https://developers.facebook.com/), add the **WhatsApp** product.
2. Go to the **API Setup** section under WhatsApp.
3. Copy the **Phone Number ID** and the **Temporary or Permanent Access Token**.
4. In NexusOS, configure the WhatsApp settings with these credentials.
5. Set up the webhook URL in Meta to point to your backend support endpoint to receive messages.

**Telegram Bot API**:
1. Open the Telegram app and search for the `@BotFather`.
2. Start a chat and type `/newbot`.
3. Follow the prompts to choose a name and a unique username for your bot.
4. `@BotFather` will provide you with an HTTP API token (e.g., `12345:AA..`).
5. Copy this token and paste it into the Telegram section of the NexusOS API Settings.
6. Set your **chat_id** in Telegram API settings (message `@userinfobot` or your bot to learn your chat id).
7. **Sales alerts** (requires Celery worker + beat): instant message when a sales meeting is booked; reminders ~24h before the meeting, ~1h before the call, and a follow-up nudge 24h after outreach if no meeting was booked.

### 6. Sales inbound replies (real, not simulated)

When a lead has been contacted, **replies are handled by Sales AI** (not Support tickets):

| Channel | How replies arrive |
|---------|-------------------|
| **Email** | SendGrid/Mailgun inbound webhook → same URL as support: `POST /api/v1/support/email/webhook/{tenant_id}` |
| **WhatsApp** | Meta webhook → `POST /api/v1/support/whatsapp/webhook/{tenant_id}` |
| **Gmail outreach** | Celery polls inbox every 3 minutes (`poll_gmail_sales_inbox`) — requires **Gmail readonly** scope; re-connect Google OAuth after upgrade |

**Flow:** match sender to lead email/phone → classify reply with AI → Telegram alert → auto-reply (optional) → book meeting if interested → calendar + Telegram meeting alert.

**Setup:**
1. Re-authorize Google (`/api/v1/google/auth?tenant_id=...`) so Gmail readonly is granted.
2. Point your inbound email provider to the webhook URL (see `docs/EMAIL_WEBHOOKS.md`).
3. Ensure lead **email** or **phone** matches the sender exactly.
4. Run Celery worker + beat.


### 4. Email & Bookings (Google Workspace / Gmail / Calendar / SMTP)
*Allows outreach agents to send emails and schedule meetings.*

**Google Cloud OAuth (Recommended for Full Access)**:
1. Go to the [Google Cloud Console](https://cloud.google.com/) and create a new project.
2. Navigate to **APIs & Services > Library** and enable both the **Gmail API** and **Google Calendar API**.
3. Go to **OAuth consent screen** and configure it (External or Internal depending on your workspace).
4. Go to **Credentials**, click **Create Credentials > OAuth client ID**, and select "Web application" or "Desktop app".
5. Download the JSON file containing your client secret and configure it in NexusOS.

**SMTP Alternative (Easier Setup)**:
1. If you just need outbound emails, you can use standard SMTP.
2. For Gmail, enable 2-Step Verification on your account.
3. Go to your Google Account > Security > App Passwords, and generate a new password for "Mail".
4. In NexusOS, provide your SMTP details (e.g., `smtp://username:app-password@smtp.gmail.com:587`).

### 5. Sales Lead Generation (Apollo / Hunter / Google Places)
*Powers Sales AI search routines.*

**Apollo.io / Hunter.io**:
1. Log into your Apollo.io or Hunter.io account.
2. Navigate to **Settings > Integrations > API** (or similar menu item depending on the platform).
3. Generate a new API Key and copy it.
4. Paste the key into the corresponding section in NexusOS API Settings.

**Google Places API**:
1. In the [Google Cloud Console](https://cloud.google.com/), select your project.
2. Navigate to **APIs & Services > Library** and enable the **Places API**.
3. Go to **Credentials**, click **Create Credentials > API key**.
4. Copy the API key and paste it into the NexusOS API Settings.

---

## 5. Agent Behavioral Parameters & Delays

To maintain a human-like operational style, NexusOS enforces natural delays on autonomous actions:

- **WhatsApp Support Auto-Replies**: Employs a **4-5 minute response delay** so communication doesn't look instantly robotic.
- **Email Ticket Auto-Replies**: Employs a **20-minute delay** before sending replies.
- **Human Interception Override**: If a team member manually type a reply and sends it in the Support Ticket UI before the delay expires, the AI automatically cancels its pending reply draft and steps back.
- **Knowledge Base Integration**: Prior to executing any tasks, agents scan files uploaded to the **Knowledge Base** (accessible via the header). Uploading documents like FAQs, Brand Guidelines, Pricing sheets, or Job Specs ensures the agent follows company guidelines to the letter.

---

## 6. Ready-to-Run Launch Prompts

Go to the **Orchestrator AI** tab and copy-paste these commands to quickly test the installed packs:

*   **Restaurant Growth Pack**:
    ```text
    Trigger the daily special post for Restaurant Pack. Create a draft of today's specials (Steak & Potatoes with red wine) for Instagram.
    ```
*   **SaaS Outreach System**:
    ```text
    Execute the SaaS Outreach System. Sourcing 5 CTOs at early-stage AI startups in New York, and write personalized outbound LinkedIn DMs.
    ```
*   **Real Estate Lead Engine**:
    ```text
    Generate property descriptions using the Real Estate Lead Engine for 456 Oak Ave. Make it sound premium with a luxury pool description.
    ```
*   **Creative Content Lab**:
    ```text
    Create an SEO Blog Outline Writer task with the Creative Content Lab. Write an outline on 'How AI employees are transforming small businesses'.
    ```

---

## 7. Troubleshooting Common Errors

*   **"Waiting for primary AI API key" / No Response**:
    - *Cause*: The system has no brain to process the instructions.
    - *Solution*: Open API Settings in the top header and configure Claude or OpenAI. Alternatively, paste the key starting with `sk-ant-` or `sk-` directly into the chat prompt.
*   **Failed to Post to Instagram/Facebook**:
    - *Cause*: Token expired, wrong token type, or missing Page/Instagram Business link.
    - *Solution*: Re-connect via `/api/v1/meta/auth?tenant_id=...` or refresh with `POST /api/v1/meta/refresh-token?tenant_id=...`. Media is uploaded directly to Meta (no ngrok needed). Run Celery worker + beat.
*   **Approve does not post immediately**:
    - *Solution*: Use `POST /api/v1/marketing/posts/{id}/publish-now` or approve with `{"publish_now": true}`.
*   **Sourcing Returns Zero Leads**:
    - *Cause*: Missing Apollo/Hunter API keys or exceeded daily search limits.
    - *Solution*: Check your Lead Gen settings card for "Active" status, and check your credit balance in your provider's dashboard.
*   **Celery Worker Connection Refused**:
    - *Cause*: Redis or the Celery worker process is not running.
    - *Solution*: Ensure Redis is running (`redis-cli ping` returns `PONG`) and launch the worker in a terminal:
      ```bash
      celery -A app.worker.tasks worker --loglevel=info
      ```

