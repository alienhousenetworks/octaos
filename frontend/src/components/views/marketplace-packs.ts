export interface MarketplacePack {
  name: string;
  desc: string;
  icon: string;
  category: string;
  complexity: string;
  timeSaved: string;
  features: string[];
}

export const marketplacePacks: MarketplacePack[] = [
  { 
    name: "Restaurant Growth Pack", 
    desc: "Automates Yelp reviews, daily Instagram specials, and local lead gen.", 
    icon: "🍔",
    category: "Local Marketing",
    complexity: "Beginner",
    timeSaved: "12h/week",
    features: ["Yelp Review Auto-Responder", "Instagram Daily Specials Scheduler", "Local Community Lead Scraper"]
  },
  { 
    name: "SaaS Outreach System", 
    desc: "End-to-end cold email sequencing, LinkedIn DMs, and demo booking.", 
    icon: "🚀",
    category: "B2B Outbound",
    complexity: "Advanced",
    timeSaved: "35h/week",
    features: ["Cold Email Sequencing", "LinkedIn DM Personalizer", "Demo Booking Scheduler"]
  },
  { 
    name: "Real Estate Lead Engine", 
    desc: "Property listing auto-generation, Zillow scraping, and client follow-ups.", 
    icon: "🏡",
    category: "Real Estate",
    complexity: "Intermediate",
    timeSaved: "20h/week",
    features: ["Property Description Generator", "Zillow Agent Scraper", "Client Lead Follow-up Agent"]
  },
  { 
    name: "E-Commerce Growth Autopilot", 
    desc: "SEO product desc generator, competitor price monitor, and abandoned cart SMS sequences.", 
    icon: "🛍️",
    category: "E-Commerce",
    complexity: "Intermediate",
    timeSaved: "25h/week",
    features: ["SEO Product Description Writer", "Competitor Price Monitor", "Cart Abandonment SMS Sequence"]
  },
  { 
    name: "Medical Clinic Receptionist", 
    desc: "Automates patient scheduling, SMS check-in reminders, and insurance triage ticketing.", 
    icon: "🏥",
    category: "Healthcare",
    complexity: "Intermediate",
    timeSaved: "18h/week",
    features: ["Patient Calendar Sync", "SMS Confirmation Reminder", "Insurance Eligibility Triage"]
  },
  { 
    name: "Law Firm Document Automator", 
    desc: "Scans contracts for liability clauses, extracts renewal dates, and drafts legal response letters.", 
    icon: "⚖️",
    category: "LegalTech",
    complexity: "Advanced",
    timeSaved: "30h/week",
    features: ["Contract Clause Scanner", "Renewal Date Extractor", "Legal Correspondence Drafter"]
  },
  { 
    name: "FinTech Compliance Suite", 
    desc: "Automates quarterly audits, flags suspicious transactions, and prepares anti-money laundering compliance drafts.", 
    icon: "📊",
    category: "Fintech",
    complexity: "Advanced",
    timeSaved: "40h/week",
    features: ["Quarterly Audit Automator", "AML Pattern Detection", "Transaction Anomaly Flagger"]
  },
  { 
    name: "Creative Content Lab", 
    desc: "Converts raw video transcripts into social media clips, generates blog outlines, and autogenerates Pinterest pins.", 
    icon: "🎨",
    category: "Creative Agency",
    complexity: "Beginner",
    timeSaved: "15h/week",
    features: ["Video-to-Text Snippet Generator", "SEO Blog Outline Writer", "Pinterest Graphic Auto-Pinner"]
  },
  { 
    name: "HR Recruiter & Onboarding System", 
    desc: "Screens resumes against job specs, runs preliminary interactive screening tests, and coordinates onboarding calendars.", 
    icon: "👔",
    category: "Human Resources",
    complexity: "Intermediate",
    timeSaved: "28h/week",
    features: ["CV Parser & Score Matcher", "Interactive Interview Simulator", "Onboarding Schedule Coordinator"]
  }
];
