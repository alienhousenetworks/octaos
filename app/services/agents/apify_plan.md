# Upgrading Apify Lead Generation

Your system currently integrates Apify via direct API calls (`httpx`). However, based on your examples, we can upgrade the system to use the official `apify-client` and expand it to dynamically choose the best "legal" Apify scraper according to the user's specific service, product, and target audience.

## Proposed Changes

### 1. Install Apify Client
We will add `apify-client` to the project's dependencies to utilize the official SDK (which provides `ApifyClientAsync` for async execution).

### 2. Intelligent Scraper Routing (Dynamic Legal Sources)
Right now, the system only uses `compass/crawler-google-places` for local businesses and `website-content-crawler` for domains. We can expand the AI routing in `sales.py` to select the most appropriate Apify actor based on the user's profile:
- **Google Maps (`compass/crawler-google-places`)**: Best for local businesses (restaurants, plumbers, retail).
- **LinkedIn/B2B Scrapers**: Best for corporate/B2B services.
- **Instagram/Social Scrapers**: Best for ecommerce, influencers, or D2C brands.

### 3. Smarter Search Queries
The current implementation only passes the "query" (e.g., "ramen"). We will update the logic to construct a comprehensive `actor_input` by combining the user's industry, target countries/locations, and service details so that the search is highly targeted (like your example: `{"searchStringsArray": ["ramen"], "locationQuery": "New York, USA"}`).

### 4. Scheduling (Optional)
If you want the agent to automatically generate leads every day (like your Cron example), we can add a new action `schedule_lead_generation` that uses `apify_client.schedules().create(...)` to run the actor daily.

## Next Steps
Would you like me to proceed with implementing these upgrades using the `apify-client`? If so, should we focus on just Google Maps for now, or add other legal scrapers to the routing logic?
