import getpass
import sys
from app.db.session import SessionLocal
from app.models.base import User, Tenant
from app.core.security import get_password_hash

def create_superuser():
    print("--- Create Superuser ---")
    email = input("Email: ").strip()
    if not email:
        print("Error: Email is required.")
        sys.exit(1)

    db = SessionLocal()
    try:
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user:
            print(f"Error: User with email {email} already exists.")
            sys.exit(1)

        password = getpass.getpass("Password: ")
        if not password:
            print("Error: Password is required.")
            sys.exit(1)

        confirm_password = getpass.getpass("Confirm Password: ")
        if password != confirm_password:
            print("Error: Passwords do not match.")
            sys.exit(1)

        company_name = input("Company Name (Tenant): ").strip()
        if not company_name:
            company_name = f"{email.split('@')[0]}'s Company"
            print(f"Using default Company Name: {company_name}")

        # Create or find tenant
        tenant = db.query(Tenant).filter(Tenant.name == company_name).first()
        if not tenant:
            tenant = Tenant(name=company_name)
            db.add(tenant)
            db.commit()
            db.refresh(tenant)
            print(f"Created new Tenant (Company): {company_name}")
        else:
            print(f"Found existing Tenant (Company): {company_name}")

        # Create superuser
        user = User(
            email=email,
            hashed_password=get_password_hash(password),
            tenant_id=tenant.id,
            is_superuser=True,
            is_verified=True,
            is_active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        print(f"Successfully created superuser: {email}")

    finally:
        db.close()

if __name__ == "__main__":
    create_superuser()
