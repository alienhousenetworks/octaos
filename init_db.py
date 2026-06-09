from app.db.session import engine
from app.models.base import Base
# Import all models to ensure they are registered with Base.metadata
from app.models.teams import AITeam, InstalledApp, AgentMetric
from app.models.agents import ActivityLog, KnowledgeDocument
from app.models.verticals import ContentPost, Lead, Candidate
from app.models.workflows import Workflow, WorkflowTask

def init_db():
    print("Creating all tables...")
    Base.metadata.create_all(bind=engine)
    print("Done.")

if __name__ == "__main__":
    init_db()
