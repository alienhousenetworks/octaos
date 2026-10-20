import pytest
from app.services.hr.resume_parser import (
    extract_heuristic_entities,
    calculate_ats_keyword_score,
    compute_composite_ranking,
)
from app.services.hr.contract_service import (
    get_available_templates,
    render_contract_document,
    generate_offer_email_content,
)

SAMPLE_RESUME_TEXT = """
Sarah Jenkins
San Francisco, CA | sarah.jenkins@example.com | (555) 987-6543
LinkedIn: linkedin.com/in/sarahjenkins-dev | GitHub: github.com/sarah-j

PROFESSIONAL SUMMARY
Results-driven Senior Full Stack Software Engineer with 6+ years of experience designing, building, and deploying scalable distributed web applications.

TECHNICAL SKILLS
- Languages: Python, JavaScript, TypeScript, SQL
- Frontend: React, Next.js, TailwindCSS, Redux
- Backend: FastAPI, Node.js, Express, PostgreSQL, Redis
- Cloud & DevOps: Docker, AWS, CI/CD, Git, Microservices

WORK EXPERIENCE
Senior Software Engineer | TechForward Inc. | 2021 – Present
- Architected microservices with FastAPI and PostgreSQL handling 5M daily requests.
- Developed real-time collaborative UI using Next.js, React, and WebSockets.

Software Engineer | CloudScale Labs | 2018 – 2021
- Built Python data pipelines and RESTful APIs.

EDUCATION
Bachelor of Science in Computer Science (B.S.) | University of California, Berkeley
"""

def test_heuristic_entity_extraction():
    entities = extract_heuristic_entities(SAMPLE_RESUME_TEXT, filename="Sarah_Jenkins_Resume.pdf")
    assert entities["name"] == "Sarah Jenkins"
    assert entities["email"] == "sarah.jenkins@example.com"
    assert "(555) 987-6543" in entities["phone"]
    assert "linkedin.com/in/sarahjenkins-dev" in entities["linkedin"]
    assert "github.com/sarah-j" in entities["github"]
    assert entities["experience_years"] >= 6
    assert "Python" in entities["skills"]
    assert "React" in entities["skills"]
    assert "FastAPI" in entities["skills"]
    assert "PostgreSQL" in entities["skills"]
    assert "B.S." in entities["education"] or "Bachelor" in entities["education"]

def test_ats_keyword_scoring():
    skills = ["Python", "FastAPI", "React", "PostgreSQL", "Docker", "AWS"]
    requirements = "We require strong expertise in Python, FastAPI, React, PostgreSQL, Docker, and Kubernetes."
    role = "Senior Full Stack Engineer"
    
    res = calculate_ats_keyword_score(skills, SAMPLE_RESUME_TEXT, requirements, role)
    assert res["ats_score"] >= 75
    assert "Python" in res["matched_skills"]
    assert "FastAPI" in res["matched_skills"]
    assert "Docker" in res["matched_skills"]
    assert "Kubernetes" in res["missing_skills"]

def test_composite_ranking():
    candidates = [
        {"name": "Alice", "ats_score": 90, "semantic_score": 85, "experience_years": 7},
        {"name": "Bob", "ats_score": 60, "semantic_score": 65, "experience_years": 2},
        {"name": "Charlie", "ats_score": 80, "semantic_score": 80, "experience_years": 4},
    ]
    ranked = compute_composite_ranking(candidates)
    assert ranked[0]["name"] == "Alice"
    assert ranked[0]["rank"] == 1
    assert ranked[1]["name"] == "Charlie"
    assert ranked[1]["rank"] == 2
    assert ranked[2]["name"] == "Bob"
    assert ranked[2]["rank"] == 3

def test_contract_templates_and_rendering():
    templates = get_available_templates()
    assert len(templates) >= 4
    template_ids = [t["id"] for t in templates]
    assert "full_time_standard" in template_ids
    assert "contractor_freelance" in template_ids
    assert "internship_offer" in template_ids
    assert "executive_senior" in template_ids

    doc = render_contract_document("full_time_standard", {
        "candidate_name": "Sarah Jenkins",
        "job_title": "Staff Engineer",
        "salary_amount": "175,000",
        "salary_currency": "USD",
        "start_date": "November 1, 2026",
        "work_mode": "Remote",
    })
    assert "Sarah Jenkins" in doc["plain_text"]
    assert "Staff Engineer" in doc["plain_text"]
    assert "175,000" in doc["plain_text"]
    assert "Remote" in doc["plain_text"]
    assert "<!DOCTYPE html>" in doc["html"]
    assert "EMPLOYMENT AGREEMENT" in doc["html"]

def test_offer_email_content_generator():
    subject, body = generate_offer_email_content(
        candidate_name="Sarah Jenkins",
        job_title="Staff Engineer",
        company_name="Acme Corp",
        start_date="November 1, 2026",
        salary_amount="175,000",
        salary_currency="USD"
    )
    assert "Offer of Employment: Staff Engineer at Acme Corp" in subject
    assert "Sarah Jenkins" in body
    assert "175,000" in body

def test_internship_only_candidate_does_not_get_3_years_experience():
    """Verify someone with college 2021-2024 and only internship is NOT assigned 3 years experience."""
    intern_resume = """
    Aman Gupta
    Bengaluru, India | aman.gupta@example.com | +91 98765 43210
    GitHub: github.com/aman-dev

    CAREER OBJECTIVE
    Enthusiastic computer science graduate eager to apply skills in full stack development.

    TECHNICAL SKILLS
    Languages: Python, JavaScript, SQL
    Frameworks: FastAPI, React, Node.js
    Tools: Git, Docker, Postman

    INTERNSHIPS & EXPERIENCE
    Software Engineering Intern | NextGen Cloud Solutions | May 2023 – July 2023
    - Built REST APIs using FastAPI and PostgreSQL for internal dashboards.
    - Collaborated with senior engineers on unit testing and Docker containerization.

    EDUCATION
    Bachelor of Technology in Computer Science (B.Tech) | 2020 – 2024
    Visvesvaraya Technological University, Bengaluru
    """
    entities = extract_heuristic_entities(intern_resume, filename="Aman_Gupta_CV.pdf")
    assert entities["name"] == "Aman Gupta"
    assert entities["email"] == "aman.gupta@example.com"
    assert "98765" in entities["phone"]
    assert "Bengaluru" in entities["address"]
    # CRITICAL: Experience must be 0 and marked as internship, NOT 4 or 3 years from college degree!
    assert entities["experience_years"] == 0
    assert entities["is_internship_only"] is True
    assert "intern" in entities["experience_summary"].lower()
    assert "FastAPI" in entities["skills"]
    assert "Docker" in entities["skills"]

def test_embedded_links_extraction_mailto_and_tel():
    """Verify embedded mailto and tel links are extracted and service emails ignored."""
    resume_with_embedded = """
    Priya Sharma
    Contact me via email or phone.
    For customer queries contact support@company.com or info@enterprise.org.
    
    WORK EXPERIENCE
    Software Developer | 2022 - Present
    - Developed backend systems with Django and Redis.

    --- EMBEDDED LINKS ---
    mailto:priya.sharma@personal.dev
    tel:+919876501234
    https://linkedin.com/in/priyasharma-code
    https://github.com/priya-sharma
    """
    entities = extract_heuristic_entities(resume_with_embedded, filename="Priya_Resume.pdf")
    # Must pick the personal embedded mailto, NOT support@company.com
    assert entities["email"] == "priya.sharma@personal.dev"
    assert "9876501234" in entities["phone"]
    assert "linkedin.com/in/priyasharma-code" in entities["linkedin"]
    assert "github.com/priya-sharma" in entities["github"]

def test_phone_sanitization_rejects_date_ranges():
    """Verify date ranges like 2020-2024 are rejected and not extracted as phone numbers."""
    resume_with_dates = """
    Alex Turner
    Software Engineer | alex@personalmail.com
    Experience: 2018 - 2022 at BigCorp, 2022 - 2024 at StartupX
    Phone: +1 (555) 234-5678
    """
    entities = extract_heuristic_entities(resume_with_dates, filename="Alex_Resume.txt")
    assert "555" in entities["phone"]
    assert "2018" not in entities["phone"]
    assert "2020" not in entities["phone"]

def test_address_extraction_rejects_job_titles_and_skills():
    """Verify address doesn't falsely grab 'Full Stack Developer' or 'React, Python'."""
    resume_text = """
    Vikram Malhotra
    vikram@example.com | +91 91234 56789
    Location: Hyderabad, India
    
    PROFESSIONAL SUMMARY
    Full Stack Developer, Engineering with expertise in React, Python, PostgreSQL, AWS.
    """
    entities = extract_heuristic_entities(resume_text, filename="Vikram_Resume.pdf")
    assert "Hyderabad" in entities["address"]
    assert "Full Stack Developer" not in entities["address"]
    assert "React" not in entities["address"]

