# Email Webhook Configuration

NexusOS supports receiving inbound emails through an HTTP webhook. This is particularly useful for allowing the Support AI to read and respond to customer emails dynamically without having to poll an inbox via IMAP.

## Supported Providers

NexusOS supports receiving inbound email payloads via `multipart/form-data` and standard JSON formats. We recommend using one of the following providers:

### 1. SendGrid Inbound Parse

SendGrid allows you to receive emails via an MX record and forward them to a specific URL via POST request.

**Setup Instructions:**
1. Log in to your SendGrid dashboard.
2. Navigate to **Settings** > **Inbound Parse**.
3. Click **Add Host & URL**.
4. Set the **Receiving Domain** to the domain you want to receive emails for (e.g., `support.yourdomain.com`). Make sure you have configured the MX records for this domain in your DNS provider to point to `mx.sendgrid.net`.
5. Set the **Destination URL** to your NexusOS webhook endpoint:
   `https://<your-nexusos-domain>/api/v1/support/email/webhook/<your-tenant-id>`
6. Keep "Check incoming emails for spam" enabled if desired.
7. SendGrid will now POST `multipart/form-data` to your webhook containing `from`, `subject`, and `text` fields.

### 2. Mailgun Inbound Routing

Mailgun Routes can filter incoming emails and forward them to your webhook endpoint.

**Setup Instructions:**
1. Log in to your Mailgun dashboard.
2. Navigate to **Receiving** > **Routes**.
3. Click **Create Route**.
4. Set the Expression Type to `Match Recipient` and enter the email address you want to route (e.g., `support@yourdomain.com`).
5. Under **Forward**, select `Store and notify`.
6. Set the notify URL to:
   `https://<your-nexusos-domain>/api/v1/support/email/webhook/<your-tenant-id>`
7. Mailgun will POST incoming emails using standard `multipart/form-data`.

### Verifying Delivery

You can monitor incoming payloads in your NexusOS dashboard under the specific tenant's Support Tickets view. When a new email arrives, it will automatically be parsed, linked to the `customer_contact`, and the Support Agent will generate a reply if auto-reply is enabled.
