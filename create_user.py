import sys
import argparse
from app.db.session import SessionLocal
from app.models.base import User, Tenant
from app.core.security import get_password_hash
from app.services.subscription_service import SubscriptionService

def create_or_update_user(email: str, password: str = "A@alien123456", company_name: str = None, is_admin: bool = True):
    email = email.strip().lower()
    if not company_name:
        company_name = f"{email.split('@')[0].capitalize()} Organization"

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()

        if user:
            print(f"[*] User {email} already exists. Updating credentials and status...")
            user.hashed_password = get_password_hash(password)
            user.is_active = True
            user.is_verified = True
            user.is_superuser = is_admin
            user.is_system_admin = is_admin
            user.role = "admin" if is_admin else "member"
            user.otp = None
            user.otp_expires_at = None
            tenant_id = user.tenant_id
        else:
            print(f"[*] Creating new tenant '{company_name}'...")
            tenant = db.query(Tenant).filter(Tenant.name == company_name).first()
            if not tenant:
                tenant = Tenant(name=company_name)
                db.add(tenant)
                db.commit()
                db.refresh(tenant)
            tenant_id = tenant.id

            print(f"[*] Creating user {email} (verified, active, no OTP)...")
            user = User(
                email=email,
                hashed_password=get_password_hash(password),
                tenant_id=tenant_id,
                is_superuser=is_admin,
                is_system_admin=is_admin,
                is_verified=True,
                is_active=True,
                role="admin" if is_admin else "member",
                otp=None,
                otp_expires_at=None,
            )
            db.add(user)

        db.commit()
        db.refresh(user)

        # Ensure trial subscription is provisioned
        try:
            SubscriptionService(db).ensure_trial(tenant_id)
            print("[*] Trial subscription ensured.")
        except Exception as e:
            print(f"[!] Warning: Could not ensure trial subscription: {e}")

        print("\n" + "=" * 50)
        print(" USER READY (NO OTP REQUIRED)")
        print("=" * 50)
        print(f" Email:       {user.email}")
        print(f" Password:    {password}")
        print(f" Tenant ID:   {user.tenant_id}")
        print(f" Active:      {user.is_active}")
        print(f" Verified:    {user.is_verified}")
        print(f" Superuser:   {user.is_superuser}")
        print(f" Sys Admin:   {user.is_system_admin}")
        print("=" * 50 + "\n")

    except Exception as e:
        db.rollback()
        print(f"[x] Error creating/updating user: {e}")
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create or update user with verified status (no OTP).")
    parser.add_argument("email", nargs="?", default="admin@octaos.com", help="User email address (default: admin@octaos.com)")
    parser.add_argument("--password", "-p", default="A@alien123456", help="User password (default: A@alien123456)")
    parser.add_argument("--company", "-c", default=None, help="Company / Tenant name")
    
    args = parser.parse_args()
    create_or_update_user(email=args.email, password=args.password, company_name=args.company)
