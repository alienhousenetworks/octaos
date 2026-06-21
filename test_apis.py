import asyncio
from app.services.agents.sales import SalesAgent
from app.api.deps import get_db
from app.models.base import APICredential

async def main():
    db = next(get_db())
    tenant_id = "tenant1"  # Or find the tenant
    
    agent = SalesAgent(db, tenant_id)
    creds = db.query(APICredential).filter(APICredential.tenant_id == tenant_id).all()
    available = {c.provider: c.api_key for c in creds}
    
    print("Testing APIs with configured keys:")
    for provider in ["apollo", "hunter", "google_places"]:
        if provider in available:
            print(f"\n--- Testing {provider} ---")
            try:
                leads = await agent._fetch_real_leads(provider, available[provider], "tech startup", count=1)
                print(f"Success! Found {len(leads)} leads.")
            except Exception as e:
                print(f"FAILED: {str(e)}")
        else:
            print(f"\n--- {provider} (Not Configured) ---")

if __name__ == "__main__":
    asyncio.run(main())
