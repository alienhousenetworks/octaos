import sys
import os

sys.path.append(os.getcwd())
from app.db.session import SessionLocal
from app.models.base import Tenant

def remove_empty_tenants():
    db = SessionLocal()
    try:
        tenants = db.query(Tenant).all()
        deleted = 0
        for t in tenants:
            if "Alien" in t.name and len(t.users) == 0:
                print(f"Deleting empty tenant: {t.name} ({t.company_email})")
                db.delete(t)
                deleted += 1
        db.commit()
        print(f"Deleted {deleted} empty duplicate companies.")
    except Exception as e:
        print("Error:", e)
    finally:
        db.close()

if __name__ == "__main__":
    remove_empty_tenants()
