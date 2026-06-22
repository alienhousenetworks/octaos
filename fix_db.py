import asyncio
from app.db.session import SessionLocal
from app.models.tenant import Tenant

async def main():
    async with SessionLocal() as db:
        result = await db.execute("SELECT * FROM tenants")
        tenants = result.all()
        for t in tenants:
            print(t)
            # Update the tenant dummy data
            await db.execute(f"UPDATE tenants SET name='AlienHouse Networks', company_email='devops@alienhousenetworks.com' WHERE name='AlienHouse Networksa'")
            await db.commit()

asyncio.run(main())
