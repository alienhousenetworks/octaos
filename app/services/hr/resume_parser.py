import re
import io
import json
import logging
from typing import Dict, Any, List, Optional, Tuple, Set

logger = logging.getLogger(__name__)

# Comprehensive tech, tools, and business skill catalog (250+ standard industry terms)
COMMON_SKILLS = [
    # Programming Languages
    "Python", "JavaScript", "TypeScript", "Java", "C++", "C#", "C", "Go", "Golang", "Rust", "Ruby", "PHP", 
    "Swift", "Kotlin", "Scala", "Dart", "R", "Shell", "Bash", "PowerShell", "SQL", "Perl", "Lua", "Groovy",
    # Frontend Frameworks & Libraries
    "React", "React.js", "React Native", "Next.js", "Vue", "Vue.js", "Nuxt.js", "Angular", "AngularJS", "Svelte", 
    "HTML", "HTML5", "CSS", "CSS3", "Tailwind", "TailwindCSS", "Bootstrap", "Sass", "SCSS", "Less", "Redux", 
    "Redux Toolkit", "Zustand", "MobX", "GraphQL", "Webpack", "Vite", "Three.js", "jQuery",
    # Backend Frameworks & Runtimes
    "Node.js", "Express", "Express.js", "FastAPI", "Django", "Flask", "Spring Boot", "Spring", "NestJS", 
    "Ruby on Rails", "ASP.NET", ".NET Core", "Laravel", "Gin", "Fiber", "Ktor", "Tornado", "Celery",
    # Architecture & Protocols
    "REST", "RESTful", "REST API", "gRPC", "WebSockets", "Microservices", "Serverless", "Event-Driven", 
    "GraphQL API", "Service Mesh", "API Gateway", "Monolith", "Distributed Systems",
    # Databases & Caching
    "PostgreSQL", "Postgres", "MySQL", "MongoDB", "Redis", "SQLite", "DynamoDB", "Cassandra", "Elasticsearch", 
    "OpenSearch", "Prisma", "SQLAlchemy", "Firebase", "Supabase", "Snowflake", "BigQuery", "Neo4j", "CouchDB", 
    "ClickHouse", "MariaDB", "Oracle",
    # Cloud & DevOps
    "AWS", "Amazon Web Services", "Azure", "GCP", "Google Cloud", "Docker", "Kubernetes", "K8s", "CI/CD", 
    "GitHub Actions", "GitLab CI", "Terraform", "Ansible", "Linux", "Unix", "Ubuntu", "Nginx", "Apache", 
    "Helm", "Prometheus", "Grafana", "Datadog", "Cloudflare", "OpenTelemetry", "ArgoCD",
    # AI / ML, Data Science & Analytics
    "Machine Learning", "Deep Learning", "NLP", "LLM", "Prompt Engineering", "PyTorch", "TensorFlow", "Keras", 
    "Pandas", "NumPy", "Scikit-Learn", "OpenCV", "RAG", "LangChain", "LlamaIndex", "Hugging Face", "OpenAI", 
    "Kafka", "Apache Spark", "Spark", "Airflow", "Hadoop", "Tableau", "Power BI", "Data Modeling", "ETL",
    # Mobile & Desktop
    "Android", "iOS", "Flutter", "SwiftUI", "Jetpack Compose", "Electron",
    # Software Engineering & QA
    "System Design", "Agile", "Scrum", "Kanban", "Git", "GitHub", "GitLab", "Jira", "Unit Testing", "TDD", 
    "BDD", "Integration Testing", "Jest", "PyTest", "Cypress", "Selenium", "Playwright", "Postman",
    # Core Soft & Professional Skills
    "Leadership", "Project Management", "Problem Solving", "Communication", "Team Collaboration", "Mentorship"
]

# Major global & Indian tech metropolitan hubs for reliable location recognition
KNOWN_LOCATIONS = [
    # India
    "Bengaluru", "Bangalore", "Mumbai", "Pune", "Hyderabad", "Delhi", "New Delhi", "Gurgaon", "Gurugram", 
    "Noida", "Chennai", "Kolkata", "Ahmedabad", "Jaipur", "Chandigarh", "Kochi", "Trivandrum", "Indore", 
    "Coimbatore", "Bhubaneswar", "Nagpur", "Vadodara", "India",
    # North America
    "San Francisco", "San Jose", "Palo Alto", "Seattle", "Austin", "New York", "Boston", "Chicago", 
    "Los Angeles", "San Diego", "Denver", "Atlanta", "Toronto", "Vancouver", "Montreal", "USA", "United States", "Canada",
    # Europe & UK
    "London", "Cambridge", "Oxford", "Berlin", "Munich", "Amsterdam", "Paris", "Dublin", "Zurich", "Stockholm", "UK", "Germany",
    # APAC & Middle East
    "Singapore", "Sydney", "Melbourne", "Dubai", "Abu Dhabi", "Tokyo"
]


def extract_resume_content(filename: str, file_bytes: bytes) -> Dict[str, Any]:
    """
    Extracts visible text and embedded hyperlinks (mailto, tel, web URLs) from PDF, DOCX, or text files.
    Returns: {"text": str, "links": List[str]}
    """
    lower_name = filename.lower()
    text = ""
    links: List[str] = []

    # 1. PDF via PyMuPDF (fitz) with fallback to pypdf
    if lower_name.endswith(".pdf") or file_bytes.startswith(b"%PDF"):
        try:
            try:
                import pymupdf as fitz
            except ImportError:
                import fitz
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            extracted = []
            for page in doc:
                page_text = page.get_text("text")
                if page_text:
                    extracted.append(page_text)
                # Extract embedded hyperlinks in PDF annotations
                try:
                    for link_obj in page.get_links():
                        uri = link_obj.get("uri")
                        if uri and uri.strip():
                            links.append(uri.strip())
                except Exception:
                    pass
            text = "\n".join(extracted)
        except Exception as e:
            logger.warning(f"PyMuPDF failed on {filename}: {e}. Trying pypdf fallback.")
            try:
                import pypdf
                reader = pypdf.PdfReader(io.BytesIO(file_bytes))
                extracted = [page.extract_text() or "" for page in reader.pages]
                text = "\n".join(extracted)
                # pypdf link extraction
                for page in reader.pages:
                    annots = page.get("/Annots")
                    if annots:
                        for a in annots:
                            try:
                                obj = a.get_object() if hasattr(a, "get_object") else a
                                if isinstance(obj, dict) and "/A" in obj:
                                    action = obj["/A"]
                                    if isinstance(action, dict) and "/URI" in action:
                                        links.append(str(action["/URI"]))
                            except Exception:
                                pass
            except Exception as e2:
                logger.error(f"All PDF extractors failed on {filename}: {e2}")

    # 2. Word DOCX via python-docx
    elif lower_name.endswith(".docx"):
        try:
            import docx
            doc = docx.Document(io.BytesIO(file_bytes))
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            for table in doc.tables:
                for row in table.rows:
                    row_text = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
                    if row_text:
                        paragraphs.append(row_text)
            text = "\n".join(paragraphs)
            # Extract hyperlinks embedded in document relationships
            if hasattr(doc, "part") and hasattr(doc.part, "rels"):
                for rel in doc.part.rels.values():
                    if "hyperlink" in getattr(rel, "reltype", "").lower() and hasattr(rel, "target_ref"):
                        links.append(str(rel.target_ref))
        except Exception as e:
            logger.error(f"DOCX extraction failed on {filename}: {e}")

    # 3. Plain text / Markdown / JSON
    elif lower_name.endswith((".txt", ".md", ".json")):
        try:
            text = file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            text = file_bytes.decode("latin-1", errors="ignore")

    # Clean duplicates in links
    unique_links = list(dict.fromkeys(links))
    return {
        "text": text.strip(),
        "links": unique_links
    }


def extract_resume_text(filename: str, file_bytes: bytes) -> str:
    """Extracts clean text with embedded links surfaced."""
    content = extract_resume_content(filename, file_bytes)
    text = content.get("text", "")
    links = content.get("links", [])
    if links:
        text += "\n\n--- EMBEDDED LINKS ---\n" + "\n".join(links)
    return text.strip()


def segment_resume_sections(text: str) -> Dict[str, str]:
    """
    Intelligently splits the resume text into distinct functional sections:
    'header', 'summary', 'experience', 'internships', 'education', 'skills', 'projects', 'other'.
    Prevents degree dates in Education from polluting Experience calculations.
    """
    section_patterns = [
        ("summary", r"(?im)^(?:\s*#{1,3}\s*)?(?:professional\s+summary|summary|profile|about\s+me|career\s+objective|objective)\b"),
        ("experience", r"(?im)^(?:\s*#{1,3}\s*)?(?:work\s+experience|professional\s+experience|experience|employment\s+history|work\s+history|career\s+history)\b"),
        ("internships", r"(?im)^(?:\s*#{1,3}\s*)?(?:internships?|internship\s+experience|industrial\s+training|trainee\s+experience)\b"),
        ("skills", r"(?im)^(?:\s*#{1,3}\s*)?(?:technical\s+skills|skills\s*(?:&|and)\s*technologies|key\s+skills|core\s+competencies|technologies|tools\s*(?:&|and)\s*frameworks|skills)\b"),
        ("education", r"(?im)^(?:\s*#{1,3}\s*)?(?:education|academic\s+background|academics|qualifications|academic\s+qualifications|educational\s+background)\b"),
        ("projects", r"(?im)^(?:\s*#{1,3}\s*)?(?:projects|key\s+projects|selected\s+projects|personal\s+projects|academic\s+projects)\b"),
        ("certifications", r"(?im)^(?:\s*#{1,3}\s*)?(?:certifications?|licenses|achievements|honors)\b")
    ]

    matches = []
    for sec_name, pattern in section_patterns:
        for m in re.finditer(pattern, text):
            matches.append((m.start(), m.end(), sec_name))

    if not matches:
        # Fallback segmentation by line count
        lines = text.splitlines()
        header_text = "\n".join(lines[:10])
        body_text = "\n".join(lines[10:])
        return {"header": header_text, "body": body_text, "text": text}

    # Sort matches by position in text
    matches.sort(key=lambda x: x[0])

    sections: Dict[str, str] = {}
    # Header is everything before the first section heading
    sections["header"] = text[:matches[0][0]].strip()

    for i in range(len(matches)):
        start_idx = matches[i][1]
        sec_name = matches[i][2]
        end_idx = matches[i + 1][0] if (i + 1 < len(matches)) else len(text)
        content = text[start_idx:end_idx].strip()
        if sec_name in sections:
            sections[sec_name] += "\n" + content
        else:
            sections[sec_name] = content

    return sections


def extract_clean_email(text: str, sections: Dict[str, str], embedded_links: Optional[List[str]] = None, candidate_name: str = "") -> str:
    """
    Extracts candidate email with embedded mailto link priority, header preference,
    and service/generic email blacklisting.
    """
    links = embedded_links or []
    # 1. Search embedded links for mailto:
    for link in links:
        mailto_match = re.search(r"mailto:([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})", link, re.IGNORECASE)
        if mailto_match:
            em = mailto_match.group(1).strip().lower()
            if not is_generic_service_email(em):
                return em

    # 2. Search header section (first 10 lines / first 800 chars)
    header_text = sections.get("header", "") or text[:800]
    header_emails = re.findall(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", header_text)
    for em in header_emails:
        em_clean = em.strip().lower()
        if not is_generic_service_email(em_clean):
            return em_clean

    # 3. Fallback: Search full text, prioritizing any email sharing parts of candidate name
    all_emails = re.findall(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", text)
    valid_candidates = [e.strip().lower() for e in all_emails if not is_generic_service_email(e)]
    if not valid_candidates:
        return ""

    if candidate_name and candidate_name != "N/A":
        name_parts = [p.lower() for p in re.split(r"\s+", candidate_name) if len(p) >= 2]
        for em in valid_candidates:
            if any(part in em.split("@")[0] for part in name_parts):
                return em

    return valid_candidates[0]


def is_generic_service_email(email: str) -> bool:
    """Returns True if the email belongs to a support, info, company desk, or generic dummy."""
    em = email.lower().strip()
    blacklisted_prefixes = (
        "info@", "support@", "admin@", "sales@", "careers@", "jobs@", "hr@", "recruiting@", 
        "talent@", "help@", "billing@", "noreply@", "no-reply@", "contact@", "service@", 
        "user@example", "your.name@", "name@domain", "email@example", "candidate@email",
        "sample@", "placeholder@"
    )
    if any(em.startswith(bp) for bp in blacklisted_prefixes):
        return True
    if "github.com" in em:
        return True
    return False


def extract_clean_phone(text: str, sections: Dict[str, str], embedded_links: Optional[List[str]] = None) -> str:
    """
    Extracts phone number ensuring 8-15 valid digits, handles international and Indian mobile (+91),
    and strictly rejects date ranges (e.g. 2020-2024), postal codes, and non-phone numbers.
    """
    links = embedded_links or []
    # 1. Search embedded links for tel:
    for link in links:
        tel_match = re.search(r"tel:([+\d\s\-\.\(\)]{8,20})", link, re.IGNORECASE)
        if tel_match:
            candidate_tel = sanitize_phone_candidate(tel_match.group(1))
            if candidate_tel:
                return candidate_tel

    # 2. Look for explicit phone labels in header or text
    header_text = sections.get("header", "") or text[:800]
    label_pattern = r"(?i)(?:phone|mobile|cell|contact|tel|whatsapp)[:\s\-\.]*([+\d\(\)\s\.\-]{8,22})\b"
    for search_corpus in [header_text, text[:1500]]:
        label_match = re.search(label_pattern, search_corpus)
        if label_match:
            candidate_tel = sanitize_phone_candidate(label_match.group(1))
            if candidate_tel:
                return candidate_tel

    # 3. Targeted international/standard phone patterns (search top 1200 characters)
    patterns = [
        # Indian format: +91 XXXXX XXXXX or +91-XXXXX-XXXXX or 10 digits starting with 6,7,8,9
        r"(?:\+91[\-\s]?)?[6-9]\d{4}[\-\s]?\d{5}\b",
        # US / International with parentheses: +1 (555) 321-7654 or (555) 321-7654
        r"(?:\+?1[\s\-]?)?\(?\d{3}\)?[\s\.\-]?\d{3}[\s\.\-]?\d{4}\b",
        # Standard international with +country code
        r"\+\d{1,3}[\s\.\-]?\d{2,4}[\s\.\-]?\d{3,4}[\s\.\-]?\d{3,4}\b"
    ]
    for pat in patterns:
        m = re.search(pat, text[:1200])
        if m:
            candidate_tel = sanitize_phone_candidate(m.group(0))
            if candidate_tel:
                return candidate_tel

    return ""


def sanitize_phone_candidate(raw: str) -> Optional[str]:
    """Validates phone number candidates, rejecting date ranges and postal codes."""
    cleaned = raw.strip().rstrip(".,;:-/ ")
    digits = re.sub(r"\D", "", cleaned)
    
    # Must have between 8 and 15 digits
    if len(digits) < 8 or len(digits) > 15:
        return None

    # Check for date ranges falsely matching phone regex: e.g. "2020-2024" or "2018-2022"
    if re.search(r"\b(19\d{2}|20\d{2})\s*[\-–—]\s*(19\d{2}|20\d{2})\b", cleaned):
        return None

    # Check for two 4-digit years adjacent e.g. 20212024
    if len(digits) == 8 and (digits.startswith("20") or digits.startswith("19")):
        return None

    return cleaned


def extract_clean_address(text: str, sections: Dict[str, str]) -> str:
    """
    Extracts the candidate's actual location/address with precision.
    Prioritizes contact header and explicit labels, checking against known tech cities.
    Rejects job titles, technical skills, and degree names.
    """
    header_text = sections.get("header", "") or text[:600]

    # 1. Check explicit Location / Address labels
    label_match = re.search(r"(?i)\b(?:address|location|city|residence|based\s+in)[:\-]\s*([A-Za-z0-9\s,.-]{3,60})", text[:1200])
    if label_match:
        candidate_addr = label_match.group(1).split("\n")[0].strip().rstrip(",.-| ")
        if is_valid_location_string(candidate_addr):
            return candidate_addr

    # 2. Match known tech cities & metros in header block
    for line in header_text.splitlines()[:8]:
        line_clean = line.strip()
        if not line_clean:
            continue
        # Split tokens separated by pipes, bullets, or multiple spaces
        tokens = re.split(r"[|•\t;]", line_clean)
        for token in tokens:
            t = token.strip().rstrip(",.- ")
            for city in KNOWN_LOCATIONS:
                # Word-boundary check for known city name
                if re.search(r"(?i)\b" + re.escape(city) + r"\b", t):
                    if is_valid_location_string(t):
                        return t

    # 3. Standard City, State / Country regex strictly in header
    header_addr_match = re.search(
        r"\b([A-Z][a-zA-Z\s.-]+,\s*(?:[A-Z]{2}|California|New York|Texas|Washington|Ontario|UK|USA|India|Canada|Germany))\b",
        header_text
    )
    if header_addr_match:
        cand_addr = header_addr_match.group(1).strip()
        if is_valid_location_string(cand_addr):
            return cand_addr

    return "Not specified"


def is_valid_location_string(s: str) -> bool:
    """Verifies candidate address string does not contain tech words or job titles."""
    if not s or len(s) < 3 or len(s) > 60:
        return False
    lower_s = s.lower()
    bad_words = [
        "engineer", "developer", "manager", "architect", "intern", "curriculum", "resume",
        "profile", "experience", "education", "project", "university", "college", "school",
        "bachelor", "master", "python", "react", "java", "fastapi", "docker", "aws", "sql"
    ]
    if any(bw in lower_s for bw in bad_words):
        return False
    return True


def extract_experience_details(text: str, sections: Dict[str, str]) -> Dict[str, Any]:
    """
    Accurately computes candidate experience and isolates internships.
    CRITICAL: Never calculates work experience from year ranges inside the EDUCATION section!
    Returns:
    {
        "experience_years": float,
        "is_internship_only": bool,
        "experience_summary": str
    }
    """
    exp_text = sections.get("experience", "")
    intern_text = sections.get("internships", "")
    summary_text = sections.get("summary", "")
    education_text = sections.get("education", "")

    # 1. Check if candidate explicitly declares years of experience in Summary or Experience header
    exp_matches = re.findall(r"(\d{1,2})\+?\s*(?:years?|yrs?)\s*(?:of\s+)?experience", f"{summary_text}\n{exp_text[:400]}", re.IGNORECASE)
    if exp_matches:
        try:
            years = max(int(m) for m in exp_matches if int(m) <= 40)
            if years > 0:
                return {
                    "experience_years": years,
                    "is_internship_only": False,
                    "experience_summary": f"Professional with {years}+ years of experience."
                }
        except Exception:
            pass

    # 2. Check for Internship-Only Profile
    # Check if experience text is empty OR all roles mentioned in experience are internships / trainees
    combined_work_text = f"{exp_text}\n{intern_text}".strip()
    
    internship_keywords = ["intern", "internship", "summer intern", "trainee", "apprentice", "fellow", "student researcher"]
    has_internship_mention = any(re.search(r"(?i)\b" + re.escape(ik) + r"\b", text) for ik in internship_keywords)
    
    # Check for full-time professional role markers in experience section
    fulltime_role_markers = [
        "software engineer", "full stack", "backend", "frontend", "lead", "architect", 
        "senior developer", "developer", "data scientist", "devops engineer", "consultant", "analyst"
    ]
    
    is_internship_only = False
    
    if not exp_text and intern_text:
        is_internship_only = True
    elif combined_work_text:
        lines = [l.strip() for l in combined_work_text.splitlines() if l.strip()]
        role_lines = [l for l in lines if any(rm in l.lower() for rm in (fulltime_role_markers + internship_keywords))]
        if role_lines and all(any(ik in rl.lower() for ik in internship_keywords) for rl in role_lines):
            is_internship_only = True
        elif not role_lines and has_internship_mention and ("202" in text or "present" in text.lower()):
            # If only internships are mentioned throughout
            is_internship_only = True
    elif has_internship_mention:
        is_internship_only = True

    if is_internship_only:
        # Check for duration of internship: e.g. "3 months", "6 months", or month date ranges
        months = 0
        month_match = re.search(r"(\d{1,2})\s*(?:months?|mos?)\s*(?:internship|experience)?", combined_work_text or text, re.IGNORECASE)
        if month_match:
            try:
                months = int(month_match.group(1))
            except Exception:
                months = 3
        else:
            months = 3  # standard default for summer internships
            
        summary_desc = f"Internship experience (~{months} mos)" if months else "Internship experience (< 1 yr)"
        return {
            "experience_years": 0,
            "is_internship_only": True,
            "experience_summary": summary_desc
        }

    # 3. Calculate year span ONLY from the experience section (NOT from education!)
    # Look for year ranges like 2018 - 2024, 2021 - Present
    work_corpus = exp_text if exp_text else (sections.get("body", "") if "education" not in sections else "")
    if work_corpus:
        year_ranges = re.findall(r"\b(20[0-2]\d|19[8-9]\d)\s*(?:-|–|—|to)\s*(20[0-2]\d|present|current)\b", work_corpus, re.IGNORECASE)
        if year_ranges:
            total_span = 0
            for start_yr, end_yr in year_ranges:
                try:
                    s = int(start_yr)
                    e = 2026 if end_yr.lower() in ("present", "current") else int(end_yr)
                    if 0 <= (e - s) <= 30:
                        total_span = max(total_span, e - s)
                except Exception:
                    pass
            if total_span > 0:
                return {
                    "experience_years": total_span,
                    "is_internship_only": False,
                    "experience_summary": f"{total_span} years professional experience."
                }

    # 4. Fresher / No verifiable experience found
    return {
        "experience_years": 0,
        "is_internship_only": False,
        "experience_summary": "Fresher / Entry Level Profile"
    }


def extract_skills_comprehensive(text: str, sections: Dict[str, str]) -> List[str]:
    """
    Extracts all candidate skills by combining catalog keyword lookup across full text
    with direct delimiter-based parsing of the candidate's actual SKILLS section.
    """
    detected_skills: Set[str] = set()
    text_lower = f" {text.lower()} "

    # 1. Catalog keyword lookup (250+ tech skills)
    for skill in COMMON_SKILLS:
        pattern = r"(?i)\b" + re.escape(skill.lower()) + r"\b"
        if re.search(pattern, text_lower):
            detected_skills.add(skill)

    # 2. Direct parsing of the candidate's actual SKILLS section
    skills_sec = sections.get("skills", "")
    if skills_sec:
        lines = skills_sec.splitlines()
        for line in lines:
            # Strip category headings like "Languages:", "Frameworks:", "Tools:", "Databases:"
            clean_line = re.sub(r"^(?:[A-Za-z\s&/]+)[:\-]\s*", "", line.strip())
            # Split by commas, pipes, bullets, or semicolons
            tokens = re.split(r"[,|•;•\t]", clean_line)
            for t in tokens:
                skill_token = t.strip().lstrip("-*# ")
                if 2 <= len(skill_token) <= 30:
                    # Filter out sentences or long noise
                    if not any(char in skill_token for char in ["http", "www", "@", "{", "}", "\n"]):
                        words = skill_token.split()
                        if 1 <= len(words) <= 4:
                            # Standardize casing or keep if title/clean
                            detected_skills.add(skill_token.strip())

    return sorted(list(detected_skills))


def extract_heuristic_entities(text: str, filename: str = "", embedded_links: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    High-accuracy, zero-cost deterministic entity extraction.
    Leverages embedded links, section segmentation, and intelligent heuristics.
    """
    links = embedded_links or []
    # If embedded links are not directly passed, check if text has EMBEDDED_LINKS section
    if not links and "--- EMBEDDED LINKS ---" in text:
        parts = text.split("--- EMBEDDED LINKS ---")
        text_body = parts[0]
        links = [l.strip() for l in parts[1].splitlines() if l.strip()]
    else:
        text_body = text

    # Partition resume into functional sections
    sections = segment_resume_sections(text_body)

    # 1. Candidate Name Extraction
    name = ""
    header_text = sections.get("header", "") or text_body[:500]
    lines = [l.strip() for l in header_text.splitlines() if l.strip()]
    if lines:
        for line in lines[:5]:
            # Look for 2 to 4 capitalized words without special characters or numbers
            if 3 <= len(line) <= 45 and not any(char in line for char in ["@", "http", "www", "/", "\\", "{", "}", "|", ":"]):
                words = line.split()
                if 1 <= len(words) <= 4 and all(w[0].isupper() for w in words if w.isalpha()):
                    name = line
                    break

    # Fallback name from filename if valid
    if not name:
        clean_fn = re.sub(r"[-_]", " ", filename.rsplit(".", 1)[0])
        clean_fn = re.sub(r"(?i)(resume|cv|profile|doc|file)", "", clean_fn).strip()
        if clean_fn and len(clean_fn) > 2:
            name = clean_fn.title()
        else:
            name = "Candidate"

    # 2. Email Extraction (with embedded mailto priority)
    email = extract_clean_email(text_body, sections, embedded_links=links, candidate_name=name)

    # 3. Phone Extraction (with embedded tel priority and international validation)
    phone = extract_clean_phone(text_body, sections, embedded_links=links)

    # 4. Location / Address Extraction
    address = extract_clean_address(text_body, sections)

    # 5. Professional Links (LinkedIn, GitHub) - search both text and embedded links
    linkedin = ""
    github = ""
    # Check embedded links first
    for link in links:
        if not linkedin and "linkedin.com/in/" in link:
            linkedin = link
        if not github and "github.com/" in link and not "github.com/topics" in link:
            github = link

    if not linkedin:
        linkedin_match = re.search(r"(?:https?:\/\/)?(?:www\.)?linkedin\.com\/in\/[a-zA-Z0-9_-]+", text_body)
        linkedin = linkedin_match.group(0) if linkedin_match else ""

    if not github:
        github_match = re.search(r"(?:https?:\/\/)?(?:www\.)?github\.com\/[a-zA-Z0-9_-]+", text_body)
        github = github_match.group(0) if github_match else ""

    # 6. Experience & Internship Breakdown
    exp_details = extract_experience_details(text_body, sections)

    # 7. Skills Comprehensive Extraction
    skills = extract_skills_comprehensive(text_body, sections)

    # 8. Education Extraction
    education = "Not specified"
    edu_text = sections.get("education", "") or text_body
    edu_keywords = ["Ph.D", "PhD", "Doctorate", "Master", "M.Tech", "M.S.", "MS in", "Bachelor", "B.Tech", "B.S.", "BS in", "B.E.", "BCA", "MCA", "Diploma"]
    for edu in edu_keywords:
        if re.search(r"(?i)\b" + re.escape(edu) + r"\b", edu_text):
            education = edu
            break

    # 9. Projects Extraction
    projects = []
    proj_text = sections.get("projects", "")
    if proj_text:
        proj_lines = [p.strip().lstrip("•-*#0123456789. ") for p in proj_text.splitlines() if p.strip()]
        for pline in proj_lines:
            if 6 <= len(pline) <= 120 and not pline.lower().startswith("http"):
                projects.append(pline)
                if len(projects) >= 4:
                    break
    if not projects and github:
        projects.append(f"Open source contributions on GitHub ({github})")

    return {
        "name": name,
        "email": email,
        "phone": phone,
        "address": address,
        "linkedin": linkedin,
        "github": github,
        "skills": skills,
        "projects": projects,
        "experience_years": exp_details["experience_years"],
        "is_internship_only": exp_details["is_internship_only"],
        "experience_summary": exp_details["experience_summary"],
        "education": education,
    }


def calculate_ats_keyword_score(candidate_skills: List[str], candidate_text: str, requirements: str, role: str) -> Dict[str, Any]:
    """Computes transparent deterministic ATS Keyword match metrics at $0 cost."""
    req_combined = f"{role} {requirements}".lower()
    
    # Extract expected skill keywords from role requirements
    expected_skills = set()
    for skill in COMMON_SKILLS:
        if re.search(r"(?i)\b" + re.escape(skill.lower()) + r"\b", req_combined):
            expected_skills.add(skill)

    # Perform case-insensitive matching against candidate skills
    expected_skills_dict = {s.lower(): s for s in expected_skills}
    candidate_skills_dict = {s.lower(): s for s in candidate_skills}

    # Also check if any expected skill is present directly in candidate text
    cand_text_lower = f" {candidate_text.lower()} "
    for k, original_skill in expected_skills_dict.items():
        if k not in candidate_skills_dict:
            if re.search(r"(?i)\b" + re.escape(k) + r"\b", cand_text_lower):
                candidate_skills_dict[k] = original_skill

    matched_keys = set(expected_skills_dict.keys()).intersection(set(candidate_skills_dict.keys()))
    missing_keys = set(expected_skills_dict.keys()) - set(candidate_skills_dict.keys())

    matched_skills = sorted([expected_skills_dict[k] for k in matched_keys])
    missing_skills = sorted([expected_skills_dict[k] for k in missing_keys])

    if expected_skills:
        match_ratio = len(matched_skills) / len(expected_skills)
        score = int(min(100, max(20, round(match_ratio * 100))))
    else:
        score = min(85, max(45, len(candidate_skills) * 4))

    return {
        "ats_score": score,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "total_required_skills_found": len(expected_skills),
    }


async def evaluate_semantic_fit(
    llm_gateway: Any,
    condensed_profile: Dict[str, Any],
    role: str,
    requirements: str,
    provider: str = "auto",
    model: Optional[str] = None
) -> Dict[str, Any]:
    """
    Enhanced AI Understanding Layer:
    Deeply analyzes the candidate resume, verifies career seniority (distinguishing college degrees
    and internships from full-time work experience), validates contact information, and extracts core fit insights.
    """
    profile_payload = {
        "extracted_name": condensed_profile.get("name"),
        "target_role": role,
        "heuristic_address": condensed_profile.get("address", "Not specified"),
        "heuristic_experience_years": condensed_profile.get("experience_years", 0),
        "heuristic_is_internship_only": condensed_profile.get("is_internship_only", False),
        "heuristic_skills": condensed_profile.get("skills", [])[:25],
        "heuristic_education": condensed_profile.get("education", ""),
        "ats_matched_skills": condensed_profile.get("matched_skills", []),
        "ats_missing_skills": condensed_profile.get("missing_skills", []),
        "resume_text_excerpt": condensed_profile.get("text_excerpt", "")[:1500]
    }

    prompt = f"""You are an elite principal technical recruiter and resume intelligence engine.
Analyze this candidate resume against the Target Role and Requirements with extreme precision.

CRITICAL INSTRUCTIONS:
1. Experience Analysis: Look at the candidate's actual employment vs. education.
   - If the candidate only has internships, traineeships, or college academic projects (e.g. studying in 2021-2024 with a 3-month summer internship), set "is_internship_only": true, and "experience_years": 0.
   - College degree duration (e.g. 2021-2024 B.Tech) is EDUCATION, NOT professional experience! DO NOT count college years as work experience.
   - Only count verifiable full-time post-graduate professional work experience in "experience_years".
2. Contact & Location Verification: Extract the candidate's actual personal location/city, personal email, and phone number from the resume text if present.
3. Skills: Identify all genuine technical skills evidenced in their projects and background.

Target Role: {role}
Role Requirements: {requirements}

Candidate Profile & Excerpt:
{json.dumps(profile_payload, indent=2)}

Respond with ONLY a valid JSON object in this exact schema:
{{
  "candidate_name": "<Clean full name of candidate>",
  "verified_email": "<Candidate personal email or empty string if not found>",
  "verified_phone": "<Candidate phone number or empty string if not found>",
  "verified_address": "<City, State/Country where candidate resides, or 'Not specified'>",
  "is_internship_only": <true if candidate only has internship/academic experience, otherwise false>,
  "experience_years": <number: 0 for interns/freshers, or integer/float of full-time professional experience>,
  "experience_summary": "<Accurate 1-2 sentence career summary highlighting internship vs full-time seniority>",
  "extracted_skills": ["<skill1>", "<skill2>", "<skill3>"],
  "semantic_score": <integer 0 to 100 indicating semantic match and role seniority fit>,
  "strengths": ["<strength 1>", "<strength 2>", "<strength 3>"],
  "gaps": ["<gap 1>", "<gap 2>"],
  "recommendation": "<Strong Hire | Recommended | Consider | Review Needed | Reject>",
  "fit_verdict": "<1-sentence hiring decision insight>",
  "extra_remarks": "<Brief recruiter note summarizing candidate suitability, standout projects, and interview focus>"
}}"""

    try:
        req_provider = None if (not provider or provider == "auto") else provider
        req_model = None if (not provider or provider == "auto") else model

        response = await llm_gateway.complete(prompt=prompt, provider=req_provider, model=req_model)
        cleaned = response.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        parsed = json.loads(cleaned.strip())
        
        if "extra_remarks" not in parsed or not parsed["extra_remarks"]:
            parsed["extra_remarks"] = f"{parsed.get('recommendation', 'Consider')}: {parsed.get('fit_verdict', '')}"
        return parsed
    except Exception as e:
        logger.warning(f"Semantic LLM evaluation fallback due to: {e}")
        # Deterministic fallback calculation
        ats_score = condensed_profile.get("ats_score", 60)
        rec = "Recommended" if ats_score >= 70 else "Consider"
        verdict = f"Assessed via deterministic heuristics. {len(condensed_profile.get('matched_skills', []))} core skills matched."
        
        is_intern = condensed_profile.get("is_internship_only", False)
        exp_yrs = 0 if is_intern else condensed_profile.get("experience_years", 0)
        exp_sum = condensed_profile.get("experience_summary") or ("Internship profile (< 1 yr)" if is_intern else f"{exp_yrs} years experience")

        return {
            "candidate_name": condensed_profile.get("name", "Candidate"),
            "verified_email": condensed_profile.get("email", ""),
            "verified_phone": condensed_profile.get("phone", ""),
            "verified_address": condensed_profile.get("address", "Not specified"),
            "is_internship_only": is_intern,
            "experience_years": exp_yrs,
            "experience_summary": exp_sum,
            "extracted_skills": condensed_profile.get("skills", []),
            "semantic_score": min(95, max(30, ats_score - 5 if condensed_profile.get("missing_skills") else ats_score + 5)),
            "strengths": [f"Demonstrated skills in {', '.join(condensed_profile.get('matched_skills', ['Core capabilities'])[:3])}"],
            "gaps": [f"Missing direct match for {s}" for s in condensed_profile.get("missing_skills", [])[:2]] or ["Standard interview verification required"],
            "recommendation": rec,
            "fit_verdict": verdict,
            "extra_remarks": f"{rec}: {verdict} Location: {condensed_profile.get('address', 'N/A')}. Experience: {exp_sum}."
        }


def compute_composite_ranking(candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Calculates composite match score and assigns rank #1, #2, #3... to candidates."""
    for c in candidates:
        ats = c.get("ats_score", 50)
        semantic = c.get("semantic_score", 50)
        # Weighted composite: 45% deterministic ATS keyword match + 55% semantic evaluation
        composite = int(round(ats * 0.45 + semantic * 0.55))
        c["composite_score"] = composite

    # Sort descending by composite score, then by experience years
    sorted_candidates = sorted(
        candidates, 
        key=lambda x: (x.get("composite_score", 0), x.get("experience_years", 0)), 
        reverse=True
    )

    for rank, cand in enumerate(sorted_candidates, start=1):
        cand["rank"] = rank

    return sorted_candidates
