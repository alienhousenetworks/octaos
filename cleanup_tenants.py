import sys
import os

sys.path.append(os.getcwd())
from app.db.session import SessionLocal
from app.models.base import Tenant, User
import uuid

def clean_duplicates():
    db = SessionLocal()
    try:
        # Get all tenants
        tenants = db.query(Tenant).all()
        
        email_map = {}
        for t in tenants:
            if not t.company_email:
                t.company_email = f"dummy_{uuid.uuid4().hex[:8]}@example.com"
                db.add(t)
                db.commit()
            
            if t.company_email in email_map:
                email_map[t.company_email].append(t)
            else:
                email_map[t.company_email] = [t]
                
        # For duplicates, keep the one with users if possible, or just the first one
        for email, t_list in email_map.items():
            if len(t_list) > 1:
                # keep first
                to_keep = t_list[0]
                for t_dup in t_list[1:]:
                    print(f"Deleting duplicate tenant {t_dup.name} with email {email}")
                    # delete associated users
                    for u in t_dup.users:
                        db.delete(u)
                    db.delete(t_dup)
        db.commit()
        print("Cleanup completed.")
    except Exception as e:
        print("Error:", e)
    finally:
        db.close()

if __name__ == "__main__":
    clean_duplicates()
