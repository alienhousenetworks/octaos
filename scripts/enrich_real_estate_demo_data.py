#!/usr/bin/env python3
"""
Enrich Real Estate Demo Data for OctaOS Field Sales & Web CRM.
Seeds projects, units, sales specialists, team allocations, high-intent leads, and scheduled visits.
"""
from __future__ import annotations
import os
import sys
from datetime import datetime, timedelta, timezone

# Ensure repository root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db.session import SessionLocal
from app.models.base import Tenant, User
from app.core.security import get_password_hash
from app.models.real_estate import (
    RealEstateProject,
    RealEstateUnit,
    RealEstateUnitHold,
    RealEstateSiteVisit,
    RealEstateProjectAssignment,
)
from app.models.field_sales import SalespersonFieldStatus
from app.models.verticals import Lead


def enrich_demo_data(target_email: str = "salesperson@octaos.com", password: str = "password123"):
    db = SessionLocal()
    try:
        print("[*] Starting OctaOS Real Estate & Field Sales Demo Data Enrichment...")

        # 1. Resolve or Create Primary Tenant
        tenant = db.query(Tenant).filter(Tenant.name == "OctaOS Prime Properties").first()
        if not tenant:
            tenant = db.query(Tenant).first()
        if not tenant:
            tenant = Tenant(name="OctaOS Prime Properties")
            db.add(tenant)
            db.commit()
            db.refresh(tenant)
        print(f"[*] Active Tenant: '{tenant.name}' (ID: {tenant.id})")

        # 2. Seed Sales Specialists
        specialists_data = [
            {
                "email": target_email.lower().strip(),
                "name": "Marcus Vance",
                "phone": "+919886099881",
                "designation": "Senior Luxury Property Specialist",
                "role": "admin",
                "is_shift_active": True,
                "status": "available",
                "working_hours_start": "09:00",
                "working_hours_end": "18:00",
                "max_visits_per_day": 6,
                "lat": 12.9784,
                "lng": 77.6408,
            },
            {
                "email": "priya.agent@octaos.com",
                "name": "Priya Sharma",
                "phone": "+919845011223",
                "designation": "Urban Residential Advisor",
                "role": "member",
                "is_shift_active": True,
                "status": "available",
                "working_hours_start": "09:30",
                "working_hours_end": "18:30",
                "max_visits_per_day": 6,
                "lat": 12.9698,
                "lng": 77.7499,
            },
            {
                "email": "rohit.advisor@octaos.com",
                "name": "Rohit Verma",
                "phone": "+919980055443",
                "designation": "Commercial & Villa Specialist",
                "role": "member",
                "is_shift_active": True,
                "status": "available",
                "working_hours_start": "10:00",
                "working_hours_end": "19:00",
                "max_visits_per_day": 5,
                "lat": 12.9165,
                "lng": 77.6833,
            },
        ]

        created_users = {}
        for sp in specialists_data:
            user = db.query(User).filter(User.email == sp["email"]).first()
            if not user:
                user = User(
                    tenant_id=tenant.id,
                    email=sp["email"],
                    name=sp["name"],
                    phone_no=sp["phone"],
                    hashed_password=get_password_hash(password),
                    role=sp["role"],
                    is_active=True,
                    is_verified=True,
                )
                db.add(user)
                db.commit()
                db.refresh(user)
                print(f"    [+] Created User: {user.name} ({user.email})")
            else:
                user.name = sp["name"]
                user.phone_no = sp["phone"]
                user.hashed_password = get_password_hash(password)
                user.is_active = True
                user.is_verified = True
                db.commit()
                print(f"    [*] Updated User: {user.name} ({user.email})")

            created_users[sp["email"]] = user

            # Telemetry status
            field_status = (
                db.query(SalespersonFieldStatus)
                .filter(
                    SalespersonFieldStatus.tenant_id == tenant.id,
                    SalespersonFieldStatus.user_id == user.id,
                )
                .first()
            )
            if not field_status:
                field_status = SalespersonFieldStatus(
                    tenant_id=tenant.id,
                    user_id=user.id,
                    is_shift_active=sp["is_shift_active"],
                    status=sp["status"],
                    working_hours_start=sp["working_hours_start"],
                    working_hours_end=sp["working_hours_end"],
                    max_visits_per_day=sp["max_visits_per_day"],
                    last_latitude=sp["lat"],
                    last_longitude=sp["lng"],
                    last_location_updated_at=datetime.now(timezone.utc),
                    battery_level=92,
                )
                db.add(field_status)
            else:
                field_status.is_shift_active = sp["is_shift_active"]
                field_status.status = sp["status"]
                field_status.working_hours_start = sp["working_hours_start"]
                field_status.working_hours_end = sp["working_hours_end"]
                field_status.max_visits_per_day = sp["max_visits_per_day"]
                field_status.last_latitude = sp["lat"]
                field_status.last_longitude = sp["lng"]
            db.commit()

        # 3. Seed Real Estate Projects
        projects_spec = [
            {
                "code": "azure_sovereign",
                "name": "The Azure Sovereign Residences",
                "location": "Indiranagar",
                "city": "Bengaluru",
                "address": "100 Feet Road, HAL 2nd Stage, Indiranagar, Bengaluru 560038",
                "latitude": 12.9784,
                "longitude": 77.6408,
                "rera_number": "PRM/KA/RERA/1251/310/PR/190824/005210",
                "amenities": ["Infinity Pool", "Clubhouse & Spa", "Private Sky Deck", "EV Fast Charging", "24/7 Concierge"],
                "total_units": 48,
                "available_units": 18,
                "units": [
                    {"num": "A-402", "type": "3BHK Luxury", "floor": 4, "carpet": 1850, "price": 24500000.0, "status": "available"},
                    {"num": "A-801", "type": "4BHK Sky Suite", "floor": 8, "carpet": 2650, "price": 38500000.0, "status": "available"},
                    {"num": "B-1201", "type": "Penthouse", "floor": 12, "carpet": 4100, "price": 68000000.0, "status": "available"},
                    {"num": "B-302", "type": "3BHK Luxury", "floor": 3, "carpet": 1850, "price": 24000000.0, "status": "confirmed_hold"},
                    {"num": "A-102", "type": "3BHK Garden", "floor": 1, "carpet": 1920, "price": 25500000.0, "status": "booked"},
                ],
                "assignments": [
                    {"email": target_email.lower(), "role": "primary_lead", "score": 96.0, "reason": "5-star luxury advisory track record"},
                    {"email": "priya.agent@octaos.com", "role": "site_specialist", "score": 88.0, "reason": "Proximity to Indiranagar"},
                ],
            },
            {
                "code": "prestige_tech_forest",
                "name": "Prestige Tech Forest Residences",
                "location": "Whitefield",
                "city": "Bengaluru",
                "address": "ECC Road, Near ITPL, Whitefield, Bengaluru 560066",
                "latitude": 12.9698,
                "longitude": 77.7499,
                "rera_number": "PRM/KA/RERA/1251/446/PR/201124/006421",
                "amenities": ["Co-working Lounge", "Badminton Arena", "Jogging Track", "Solar Grid", "Smart Automation"],
                "total_units": 120,
                "available_units": 45,
                "units": [
                    {"num": "TF-204", "type": "2BHK Smart", "floor": 2, "carpet": 1150, "price": 12800000.0, "status": "available"},
                    {"num": "TF-708", "type": "3BHK Executive", "floor": 7, "carpet": 1680, "price": 18500000.0, "status": "available"},
                    {"num": "TF-1102", "type": "3BHK Premium", "floor": 11, "carpet": 1750, "price": 19800000.0, "status": "available"},
                    {"num": "TF-501", "type": "2BHK Smart", "floor": 5, "carpet": 1150, "price": 13200000.0, "status": "confirmed_hold"},
                ],
                "assignments": [
                    {"email": "priya.agent@octaos.com", "role": "primary_lead", "score": 94.0, "reason": "Tech corridor client expert"},
                    {"email": target_email.lower(), "role": "site_specialist", "score": 89.0, "reason": "High velocity showing closer"},
                ],
            },
            {
                "code": "sovereign_marina",
                "name": "Sovereign Marina Greens & Villas",
                "location": "Sarjapur Road",
                "city": "Bengaluru",
                "address": "Sarjapur Main Road, Near Wipro Corporate Campus, Bengaluru 560035",
                "latitude": 12.9165,
                "longitude": 77.6833,
                "rera_number": "PRM/KA/RERA/1251/308/PR/220125/007100",
                "amenities": ["Lakefront Promenade", "Private Plunge Pool", "Tennis Court", "Golf Simulator", "Organic Garden"],
                "total_units": 36,
                "available_units": 14,
                "units": [
                    {"num": "Villa-07", "type": "4BHK Lake Villa", "floor": 1, "carpet": 3400, "price": 42500000.0, "status": "available"},
                    {"num": "Villa-14", "type": "5BHK Estate Villa", "floor": 1, "carpet": 4800, "price": 64000000.0, "status": "available"},
                    {"num": "Villa-02", "type": "4BHK Lake Villa", "floor": 1, "carpet": 3400, "price": 41500000.0, "status": "available"},
                ],
                "assignments": [
                    {"email": "rohit.advisor@octaos.com", "role": "primary_lead", "score": 93.0, "reason": "Villa community specialist"},
                    {"email": target_email.lower(), "role": "site_specialist", "score": 87.0, "reason": "Senior closer escort"},
                ],
            },
        ]

        saved_projects = {}
        for ps in projects_spec:
            proj = db.query(RealEstateProject).filter(
                RealEstateProject.tenant_id == tenant.id,
                RealEstateProject.code == ps["code"],
            ).first()
            if not proj:
                proj = RealEstateProject(
                    tenant_id=tenant.id,
                    name=ps["name"],
                    code=ps["code"],
                    location=ps["location"],
                    city=ps["city"],
                    address=ps["address"],
                    latitude=ps["latitude"],
                    longitude=ps["longitude"],
                    rera_number=ps["rera_number"],
                    amenities=ps["amenities"],
                    total_units=ps["total_units"],
                    available_units=ps["available_units"],
                    status="active",
                )
                db.add(proj)
                db.commit()
                db.refresh(proj)
                print(f"    [+] Created Project: {proj.name}")
            else:
                proj.name = ps["name"]
                proj.address = ps["address"]
                proj.latitude = ps["latitude"]
                proj.longitude = ps["longitude"]
                proj.rera_number = ps["rera_number"]
                proj.amenities = ps["amenities"]
                proj.total_units = ps["total_units"]
                proj.available_units = ps["available_units"]
                db.commit()
                print(f"    [*] Updated Project: {proj.name}")

            saved_projects[ps["code"]] = proj

            # Seed units
            for u in ps["units"]:
                existing_unit = db.query(RealEstateUnit).filter(
                    RealEstateUnit.tenant_id == tenant.id,
                    RealEstateUnit.project_id == proj.id,
                    RealEstateUnit.unit_number == u["num"],
                ).first()
                if not existing_unit:
                    new_u = RealEstateUnit(
                        tenant_id=tenant.id,
                        project_id=proj.id,
                        unit_number=u["num"],
                        unit_type=u["type"],
                        floor=u["floor"],
                        carpet_sqft=u["carpet"],
                        base_price=u["price"],
                        status=u["status"],
                        version=1,
                    )
                    db.add(new_u)
            db.commit()

            # Seed project team assignments
            for assign in ps["assignments"]:
                user_obj = created_users.get(assign["email"])
                if user_obj:
                    assign_row = (
                        db.query(RealEstateProjectAssignment)
                        .filter(
                            RealEstateProjectAssignment.tenant_id == tenant.id,
                            RealEstateProjectAssignment.project_id == proj.id,
                            RealEstateProjectAssignment.user_id == user_obj.id,
                        )
                        .first()
                    )
                    if not assign_row:
                        assign_row = RealEstateProjectAssignment(
                            tenant_id=tenant.id,
                            project_id=proj.id,
                            user_id=user_obj.id,
                            role=assign["role"],
                            is_active=True,
                            ai_recommended=True,
                            ai_match_score=assign["score"],
                            ai_recommendation_reason=assign["reason"],
                        )
                        db.add(assign_row)
                    else:
                        assign_row.role = assign["role"]
                        assign_row.is_active = True
                        assign_row.ai_match_score = assign["score"]
                        assign_row.ai_recommendation_reason = assign["reason"]
            db.commit()

        # 4. Seed High-Intent Inquiries & Leads
        primary_agent = created_users[target_email.lower()]
        leads_spec = [
            {
                "id": "lead_vikram_m",
                "name": "Vikram Malhotra",
                "phone": "+919886012345",
                "email": "vikram.m@techcorp.io",
                "score": 94,
                "project_code": "azure_sovereign",
                "unit_pref": "4BHK Sky Suite",
                "budget": "₹3.8 Cr - ₹4.5 Cr",
                "purpose": "Self-Use",
                "timeline": "Immediate (30 Days)",
                "why": "AI matched high-ticket buyer near Indiranagar cluster with primary lead Marcus Vance.",
                "status": "visit_scheduled",
            },
            {
                "id": "lead_ananya_d",
                "name": "Ananya Deshmukh",
                "phone": "+919876543211",
                "email": "ananya.d@investventures.com",
                "score": 89,
                "project_code": "prestige_tech_forest",
                "unit_pref": "3BHK Executive",
                "budget": "₹1.8 Cr - ₹2.2 Cr",
                "purpose": "Investment",
                "timeline": "45 Days",
                "why": "High purchasing power tech executive requesting private tour after office hours.",
                "status": "visit_scheduled",
            },
            {
                "id": "lead_dr_swami",
                "name": "Dr. Arvind Swaminathan",
                "phone": "+919845098765",
                "email": "dr.swami@apollohealth.org",
                "score": 91,
                "project_code": "sovereign_marina",
                "unit_pref": "4BHK Lake Villa",
                "budget": "₹4.0 Cr - ₹5.0 Cr",
                "purpose": "Self-Use",
                "timeline": "Immediate",
                "why": "Requested quiet waterfront residence close to medical corridor.",
                "status": "inquiry",
            },
            {
                "id": "lead_siddharth_k",
                "name": "Siddharth & Meera Kulkarni",
                "phone": "+919900112233",
                "email": "siddharth.k@consulting.com",
                "score": 86,
                "project_code": "azure_sovereign",
                "unit_pref": "3BHK Luxury",
                "budget": "₹2.4 Cr - ₹2.8 Cr",
                "purpose": "Self-Use",
                "timeline": "60 Days",
                "why": "Pre-approved loan sanction ready; requested walkthrough of amenities.",
                "status": "visit_scheduled",
            },
        ]

        saved_leads = {}
        for ls in leads_spec:
            proj = saved_projects[ls["project_code"]]
            lead = db.query(Lead).filter(
                Lead.tenant_id == tenant.id,
                Lead.email == ls["email"],
            ).first()
            if not lead:
                lead = Lead(
                    id=ls["id"],
                    tenant_id=tenant.id,
                    name=ls["name"],
                    phone=ls["phone"],
                    mobile_no=ls["phone"],
                    email=ls["email"],
                    company=proj.name,
                    need_of_what=ls["unit_pref"],
                    how_much=ls["budget"],
                    why=ls["why"],
                    score=ls["score"],
                    status=ls["status"],
                    assigned_to=primary_agent.name or primary_agent.email,
                    data={
                        "project_id": proj.id,
                        "project_name": proj.name,
                        "unit_preference": ls["unit_pref"],
                        "budget": ls["budget"],
                        "purchase_purpose": ls["purpose"],
                        "purchase_timeline": ls["timeline"],
                        "assigned_specialist_id": primary_agent.id,
                        "assigned_specialist_name": primary_agent.name,
                    },
                )
                db.add(lead)
                db.commit()
                db.refresh(lead)
                print(f"    [+] Created Lead: {lead.name} -> {proj.name}")
            else:
                lead.assigned_to = primary_agent.name or primary_agent.email
                lead.status = ls["status"]
                lead.score = ls["score"]
                lead.data = {
                    "project_id": proj.id,
                    "project_name": proj.name,
                    "unit_preference": ls["unit_pref"],
                    "budget": ls["budget"],
                    "purchase_purpose": ls["purpose"],
                    "purchase_timeline": ls["timeline"],
                    "assigned_specialist_id": primary_agent.id,
                    "assigned_specialist_name": primary_agent.name,
                }
                db.commit()
                print(f"    [*] Updated Lead: {lead.name}")

            saved_leads[ls["id"]] = lead

        # 5. Seed Site Visits for Today's Itinerary
        now = datetime.now(timezone.utc)
        today_1130 = now.replace(hour=6, minute=0, second=0, microsecond=0) + timedelta(hours=5, minutes=30)  # 11:30 AM local
        today_1500 = now.replace(hour=9, minute=30, second=0, microsecond=0) + timedelta(hours=5, minutes=30)  # 03:00 PM local
        today_completed = now.replace(hour=4, minute=0, second=0, microsecond=0) + timedelta(hours=5, minutes=30)  # 09:30 AM completed

        visits_spec = [
            {
                "id": "visit_today_completed_01",
                "lead_id": "lead_siddharth_k",
                "project_code": "azure_sovereign",
                "scheduled_at": today_completed,
                "duration": 45,
                "sequence": 1,
                "travel_mins": 10,
                "status": "completed",
                "check_in_verified": True,
                "interest": "high",
                "feedback": "Walked through 3BHK A-402. Buyers loved the balcony layout and club amenities.",
            },
            {
                "id": "visit_today_active_01",
                "lead_id": "lead_vikram_m",
                "project_code": "azure_sovereign",
                "scheduled_at": today_1130,
                "duration": 60,
                "sequence": 2,
                "travel_mins": 15,
                "status": "scheduled",
                "check_in_verified": False,
                "interest": "high",
                "feedback": "Touring 4BHK Penthouse. Interested in token reservation if floor plan matches.",
            },
            {
                "id": "visit_today_active_02",
                "lead_id": "lead_ananya_d",
                "project_code": "prestige_tech_forest",
                "scheduled_at": today_1500,
                "duration": 45,
                "sequence": 3,
                "travel_mins": 25,
                "status": "scheduled",
                "check_in_verified": False,
                "interest": "high",
                "feedback": "Evaluating rental yield on 3BHK Executive.",
            },
        ]

        for vs in visits_spec:
            lead = saved_leads.get(vs["lead_id"])
            proj = saved_projects.get(vs["project_code"])
            if not lead or not proj:
                continue

            v_row = db.query(RealEstateSiteVisit).filter(
                RealEstateSiteVisit.tenant_id == tenant.id,
                RealEstateSiteVisit.id == vs["id"],
            ).first()

            if not v_row:
                v_row = RealEstateSiteVisit(
                    id=vs["id"],
                    tenant_id=tenant.id,
                    lead_id=lead.id,
                    project_id=proj.id,
                    assigned_agent=primary_agent.id,
                    scheduled_at=vs["scheduled_at"],
                    duration_minutes=vs["duration"],
                    sequence_order=vs["sequence"],
                    estimated_travel_minutes=vs["travel_mins"],
                    status=vs["status"],
                    check_in_verified=vs["check_in_verified"],
                    buyer_interest_level=vs["interest"],
                    tour_feedback=vs["feedback"],
                    recovery_notes=f"Autonomous AI dispatch matched {lead.name} with project specialist {primary_agent.name}",
                )
                db.add(v_row)
            else:
                v_row.assigned_agent = primary_agent.id
                v_row.scheduled_at = vs["scheduled_at"]
                v_row.status = vs["status"]
                v_row.sequence_order = vs["sequence"]
                v_row.check_in_verified = vs["check_in_verified"]
                v_row.buyer_interest_level = vs["interest"]
                v_row.tour_feedback = vs["feedback"]

        db.commit()

        print("\n" + "=" * 60)
        print("  DEMO DATA ENRICHMENT COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print(f"Organization:       {tenant.name}")
        print(f"Mobile Agent Login: {primary_agent.email}")
        print(f"Password:           {password}")
        print(f"Projects Seeded:    {len(saved_projects)} (Indiranagar, Whitefield, Sarjapur)")
        print(f"Assigned Leads:     {len(saved_leads)}")
        print(f"Today's Showings:   {len(visits_spec)} (1 Completed, 2 Scheduled)")
        print("=" * 60 + "\n")

    except Exception as e:
        db.rollback()
        print(f"\n[!] Error during demo data enrichment: {e}")
        raise e
    finally:
        db.close()


if __name__ == "__main__":
    enrich_demo_data()
