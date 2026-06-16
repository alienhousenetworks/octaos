import sys
import os

filepath = "/Users/sayantande/Downloads/jules_session_166401146785413967/app/api/v1/endpoints/auth.py"

with open(filepath, "r") as f:
    content = f.read()

# 1. Update LoginInitiateRequest
old_login_initiate_req = """class LoginInitiateRequest(BaseModel):
    email: EmailStr
    password: Optional[str] = None"""

new_login_initiate_req = """class LoginInitiateRequest(BaseModel):
    email: EmailStr
    password: Optional[str] = None
    tenant_id: Optional[str] = None"""

content = content.replace(old_login_initiate_req, new_login_initiate_req)

# 2. Update LoginVerifyRequest
old_login_verify_req = """class LoginVerifyRequest(BaseModel):
    email: EmailStr
    otp: str"""

new_login_verify_req = """class LoginVerifyRequest(BaseModel):
    email: EmailStr
    otp: str
    tenant_id: Optional[str] = None"""

content = content.replace(old_login_verify_req, new_login_verify_req)

# 3. Update signup_initiate
old_signup_initiate_body = """    # Check if user exists
    user = db.query(User).filter(User.email == signup_in.email).first()
    if user:
        if getattr(user, "is_verified", True):
            raise HTTPException(
                status_code=400,
                detail="The user with this email already exists in the system.",
            )
        # Unverified user: we can update details and send a new OTP
        user.name = signup_in.name
        user.phone_no = signup_in.phone_no
        user.hashed_password = get_password_hash(signup_in.password)
        # Update tenant name and metadata if provided
        if signup_in.company:
            tenant = db.query(Tenant).filter(Tenant.id == user.tenant_id).first()
            if tenant:
                tenant.name = signup_in.company
                tenant.company_website = signup_in.company_website
                tenant.company_email = signup_in.company_email
                tenant.company_address = signup_in.company_address
                db.add(tenant)
    else:
        # Create tenant (company)
        company_name = signup_in.company or f"{signup_in.name}'s Company"
        tenant = Tenant(
            name=company_name,
            company_website=signup_in.company_website,
            company_email=signup_in.company_email,
            company_address=signup_in.company_address
        )
        db.add(tenant)
        db.commit()
        db.refresh(tenant)

        # Create user (not verified yet)
        user = User(
            email=signup_in.email,
            hashed_password=get_password_hash(signup_in.password),
            tenant_id=tenant.id,
            name=signup_in.name,
            phone_no=signup_in.phone_no,
            is_verified=False,
            is_superuser=True,
            role="admin"
        )
        db.add(user)

    # Generate OTP
    otp = generate_otp()
    user.otp = otp
    user.otp_expires_at = datetime.utcnow() + timedelta(minutes=10)
    db.add(user)
    db.commit()"""

new_signup_initiate_body = """    if not signup_in.company_email:
        raise HTTPException(status_code=400, detail="Company email is required.")
        
    tenant = db.query(Tenant).filter(Tenant.company_email == signup_in.company_email).first()
    
    if tenant:
        # Check if the admin user is verified
        admin_user = db.query(User).filter(User.tenant_id == tenant.id, User.email == signup_in.email).first()
        if admin_user and getattr(admin_user, "is_verified", False):
            raise HTTPException(status_code=400, detail="A company with this email already exists and is verified.")
        elif not admin_user:
            raise HTTPException(status_code=400, detail="A company with this email already exists.")
            
        # Unverified user retrying: update details
        admin_user.name = signup_in.name
        admin_user.phone_no = signup_in.phone_no
        admin_user.hashed_password = get_password_hash(signup_in.password)
        tenant.name = signup_in.company or f"{signup_in.name}'s Company"
        tenant.company_website = signup_in.company_website
        tenant.company_address = signup_in.company_address
        db.add(tenant)
        user = admin_user
    else:
        # Create new tenant
        company_name = signup_in.company or f"{signup_in.name}'s Company"
        tenant = Tenant(
            name=company_name,
            company_website=signup_in.company_website,
            company_email=signup_in.company_email,
            company_address=signup_in.company_address
        )
        db.add(tenant)
        db.commit()
        db.refresh(tenant)

        # Create user (not verified yet)
        user = User(
            email=signup_in.email,
            hashed_password=get_password_hash(signup_in.password),
            tenant_id=tenant.id,
            name=signup_in.name,
            phone_no=signup_in.phone_no,
            is_verified=False,
            is_superuser=True,
            role="admin"
        )
        db.add(user)
        
        # Sync password for other existing user accounts with same email
        existing_users = db.query(User).filter(User.email == signup_in.email).all()
        for eu in existing_users:
            eu.hashed_password = user.hashed_password
            db.add(eu)

    # Generate OTP
    otp = generate_otp()
    user.otp = otp
    user.otp_expires_at = datetime.utcnow() + timedelta(minutes=10)
    db.add(user)
    db.commit()"""

content = content.replace(old_signup_initiate_body, new_signup_initiate_body)

# 4. Update accept_invite
old_accept_invite_check = """    # Check if user already exists
    existing_user = db.query(User).filter(User.email == accept_in.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="User with this email already exists")"""

new_accept_invite_check = """    # Check if user already exists in THIS tenant
    existing_user_in_tenant = db.query(User).filter(User.email == accept_in.email, User.tenant_id == invitation.tenant_id).first()
    if existing_user_in_tenant:
        raise HTTPException(status_code=400, detail="User with this email already exists in this organization")
        
    # Sync passwords for existing accounts with this email
    existing_users = db.query(User).filter(User.email == accept_in.email).all()
    hashed_pw = get_password_hash(accept_in.password)
    for eu in existing_users:
        eu.hashed_password = hashed_pw
        db.add(eu)"""

content = content.replace(old_accept_invite_check, new_accept_invite_check)

# 5. Update login_initiate
old_login_initiate_body = """    user = db.query(User).filter(User.email == login_in.email).first()
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    # If the user registered but never verified, tell them to verify using the signup verification flow
    if not getattr(user, "is_verified", False):
        raise HTTPException(
            status_code=403, 
            detail="Account email is unverified. Please verify your email first.",
            headers={"X-Verification-Required": "true"}
        )

    if login_in.password is not None and login_in.password != "":
        # PASSWORD LOGIN FLOW
        if not verify_password(login_in.password, user.hashed_password):
            raise HTTPException(status_code=400, detail="Incorrect email or password")
        
        access_token = create_access_token(subject=user.id, tenant_id=user.tenant_id, organization_id=user.organization_id)
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "tenant_id": user.tenant_id,
            "otp_required": False
        }
    else:
        # OTP LOGIN FLOW
        # Generate OTP
        otp = generate_otp()
        user.otp = otp
        user.otp_expires_at = datetime.utcnow() + timedelta(minutes=10)
        db.add(user)
        db.commit()

        # Send OTP
        send_otp(user.email, otp, purpose="login")
        return {"message": "Login OTP sent successfully", "email": user.email, "otp_required": True}"""

new_login_initiate_body = """    users = db.query(User).filter(User.email == login_in.email).all()
    if not users:
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    
    user = None
    if login_in.tenant_id:
        user = next((u for u in users if u.tenant_id == login_in.tenant_id), None)
        if not user:
            raise HTTPException(status_code=400, detail="Invalid tenant selection")
    else:
        if len(users) == 1:
            user = users[0]

    if login_in.password is not None and login_in.password != "":
        # PASSWORD LOGIN FLOW
        if not verify_password(login_in.password, users[0].hashed_password):
            raise HTTPException(status_code=400, detail="Incorrect email or password")
        
        if user is None:
            tenants = []
            for u in users:
                t = db.query(Tenant).filter(Tenant.id == u.tenant_id).first()
                if t and t.is_active:
                    tenants.append({"id": t.id, "name": t.name})
            if not tenants:
                 raise HTTPException(status_code=400, detail="No active tenants found for user")
            if len(tenants) == 1:
                 user = next(u for u in users if u.tenant_id == tenants[0]["id"])
            else:
                 return {
                     "needs_tenant_selection": True,
                     "tenants": tenants,
                     "otp_required": False
                 }

        if not user.is_active:
            raise HTTPException(status_code=400, detail="Inactive user")

        if not getattr(user, "is_verified", False):
            raise HTTPException(
                status_code=403, 
                detail="Account email is unverified. Please verify your email first.",
                headers={"X-Verification-Required": "true"}
            )
            
        access_token = create_access_token(subject=user.id, tenant_id=user.tenant_id, organization_id=user.organization_id)
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "tenant_id": user.tenant_id,
            "otp_required": False
        }
    else:
        # OTP LOGIN FLOW
        otp = generate_otp()
        for u in users:
            u.otp = otp
            u.otp_expires_at = datetime.utcnow() + timedelta(minutes=10)
            db.add(u)
        db.commit()

        send_otp(login_in.email, otp, purpose="login")
        return {"message": "Login OTP sent successfully", "email": login_in.email, "otp_required": True}"""

content = content.replace(old_login_initiate_body, new_login_initiate_body)

# 6. Update login_verify
old_login_verify_body = """    user = db.query(User).filter(User.email == verify_in.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    # Verification logic
    is_valid = False
    if settings.DEV and verify_in.otp == "123455":
        is_valid = True
    elif user.otp and user.otp == verify_in.otp:
        if user.otp_expires_at and _normalize_dt(user.otp_expires_at) > _normalize_dt(datetime.utcnow()):
            is_valid = True
        else:
            raise HTTPException(status_code=400, detail="OTP has expired.")
    else:
        raise HTTPException(status_code=400, detail="Invalid OTP code.")

    if not is_valid:
        raise HTTPException(status_code=400, detail="OTP verification failed.")

    # Clear OTP
    user.otp = None
    user.otp_expires_at = None
    db.add(user)
    db.commit()

    access_token = create_access_token(subject=user.id, tenant_id=user.tenant_id, organization_id=user.organization_id)
    return {"access_token": access_token, "token_type": "bearer", "tenant_id": user.tenant_id}"""

new_login_verify_body = """    users = db.query(User).filter(User.email == verify_in.email).all()
    if not users:
        raise HTTPException(status_code=404, detail="User not found.")

    user_for_otp = users[0]
    
    # Verification logic
    is_valid = False
    if settings.DEV and verify_in.otp == "123455":
        is_valid = True
    elif user_for_otp.otp and user_for_otp.otp == verify_in.otp:
        if user_for_otp.otp_expires_at and _normalize_dt(user_for_otp.otp_expires_at) > _normalize_dt(datetime.utcnow()):
            is_valid = True
        else:
            raise HTTPException(status_code=400, detail="OTP has expired.")
    else:
        raise HTTPException(status_code=400, detail="Invalid OTP code.")

    if not is_valid:
        raise HTTPException(status_code=400, detail="OTP verification failed.")

    user = None
    if verify_in.tenant_id:
        user = next((u for u in users if u.tenant_id == verify_in.tenant_id), None)
        if not user:
             raise HTTPException(status_code=400, detail="Invalid tenant selection")
    else:
        if len(users) == 1:
            user = users[0]

    if user is None:
        tenants = []
        for u in users:
            t = db.query(Tenant).filter(Tenant.id == u.tenant_id).first()
            if t and t.is_active:
                tenants.append({"id": t.id, "name": t.name})
        if not tenants:
             raise HTTPException(status_code=400, detail="No active tenants found for user")
        if len(tenants) == 1:
             user = next(u for u in users if u.tenant_id == tenants[0]["id"])
        else:
             return {
                 "needs_tenant_selection": True,
                 "tenants": tenants
             }

    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    # Clear OTP
    for u in users:
        u.otp = None
        u.otp_expires_at = None
        db.add(u)
    db.commit()

    access_token = create_access_token(subject=user.id, tenant_id=user.tenant_id, organization_id=user.organization_id)
    return {"access_token": access_token, "token_type": "bearer", "tenant_id": user.tenant_id}"""

content = content.replace(old_login_verify_body, new_login_verify_body)

# 7. Update resend_otp to handle multiple users
old_resend_otp_body = """    user = db.query(User).filter(User.email == resend_in.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    # Generate new OTP
    otp = generate_otp()
    user.otp = otp
    user.otp_expires_at = datetime.utcnow() + timedelta(minutes=10)
    db.add(user)
    db.commit()

    # Send OTP
    send_otp(user.email, otp, purpose="login")"""

new_resend_otp_body = """    users = db.query(User).filter(User.email == resend_in.email).all()
    if not users:
        raise HTTPException(status_code=404, detail="User not found.")
    
    if not users[0].is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    # Generate new OTP
    otp = generate_otp()
    for u in users:
        u.otp = otp
        u.otp_expires_at = datetime.utcnow() + timedelta(minutes=10)
        db.add(u)
    db.commit()

    # Send OTP
    send_otp(users[0].email, otp, purpose="login")"""

content = content.replace(old_resend_otp_body, new_resend_otp_body)

# 8. Update signup resend otp
old_signup_resend_body = """    user = db.query(User).filter(User.email == resend_in.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    
    if getattr(user, "is_verified", False):
        raise HTTPException(status_code=400, detail="User is already verified.")

    # Generate new OTP
    otp = generate_otp()
    user.otp = otp
    user.otp_expires_at = datetime.utcnow() + timedelta(minutes=10)
    db.add(user)
    db.commit()

    # Send OTP
    send_otp(user.email, otp, purpose="signup")"""

new_signup_resend_body = """    users = db.query(User).filter(User.email == resend_in.email).all()
    if not users:
        raise HTTPException(status_code=404, detail="User not found.")
    
    user = users[0]
    if getattr(user, "is_verified", False):
        raise HTTPException(status_code=400, detail="User is already verified.")

    # Generate new OTP
    otp = generate_otp()
    for u in users:
        u.otp = otp
        u.otp_expires_at = datetime.utcnow() + timedelta(minutes=10)
        db.add(u)
    db.commit()

    # Send OTP
    send_otp(user.email, otp, purpose="signup")"""

content = content.replace(old_signup_resend_body, new_signup_resend_body)


# 9. Update signup_verify
old_signup_verify_body = """    user = db.query(User).filter(User.email == verify_in.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    
    if getattr(user, "is_verified", False):
        raise HTTPException(status_code=400, detail="User is already verified.")

    # Verification logic
    is_valid = False
    if settings.DEV and verify_in.otp == "123455":
        is_valid = True
    elif user.otp and user.otp == verify_in.otp:
        if user.otp_expires_at and _normalize_dt(user.otp_expires_at) > _normalize_dt(datetime.utcnow()):
            is_valid = True
        else:
            raise HTTPException(status_code=400, detail="OTP has expired.")
    else:
        raise HTTPException(status_code=400, detail="Invalid OTP code.")

    if not is_valid:
        raise HTTPException(status_code=400, detail="OTP verification failed.")

    # Mark as verified
    user.is_verified = True
    user.otp = None
    user.otp_expires_at = None
    db.add(user)
    db.commit()
    db.refresh(user)

    access_token = create_access_token(subject=user.id, tenant_id=user.tenant_id, organization_id=user.organization_id)
    return {"access_token": access_token, "token_type": "bearer", "tenant_id": user.tenant_id}"""

new_signup_verify_body = """    users = db.query(User).filter(User.email == verify_in.email).all()
    if not users:
        raise HTTPException(status_code=404, detail="User not found.")
    
    user = users[0]
    if getattr(user, "is_verified", False):
        raise HTTPException(status_code=400, detail="User is already verified.")

    # Verification logic
    is_valid = False
    if settings.DEV and verify_in.otp == "123455":
        is_valid = True
    elif user.otp and user.otp == verify_in.otp:
        if user.otp_expires_at and _normalize_dt(user.otp_expires_at) > _normalize_dt(datetime.utcnow()):
            is_valid = True
        else:
            raise HTTPException(status_code=400, detail="OTP has expired.")
    else:
        raise HTTPException(status_code=400, detail="Invalid OTP code.")

    if not is_valid:
        raise HTTPException(status_code=400, detail="OTP verification failed.")

    # Mark as verified
    for u in users:
        u.is_verified = True
        u.otp = None
        u.otp_expires_at = None
        db.add(u)
    db.commit()
    db.refresh(user)

    access_token = create_access_token(subject=user.id, tenant_id=user.tenant_id, organization_id=user.organization_id)
    return {"access_token": access_token, "token_type": "bearer", "tenant_id": user.tenant_id}"""

content = content.replace(old_signup_verify_body, new_signup_verify_body)


with open(filepath, "w") as f:
    f.write(content)

print("auth.py updated successfully.")
