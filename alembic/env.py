import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

from app.core.config import settings
from app.models.base import Base
from app.models.teams import AITeam, InstalledApp, AgentMetric
from app.models.agents import ActivityLog, KnowledgeDocument
from app.models.verticals import ContentPost, Lead, Candidate, Contract, Transaction, Ticket, TicketMessage, AgentMeeting, BusinessProfile
from app.models.workflows import Workflow, WorkflowTask
from app.models.video import VideoProject, VideoAsset, VideoRender
from app.models.deal_room import DealRoom, BuyingCommitteeMember, AccountSignal, DealObjection, DealActivity, SuppressionRecord, EvidenceRecord, CompanySalesContext
from app.models.learning import DecisionRecord, StrategyPerformance, NegativePatternMemory, GlobalStrategyRegistry, GlobalFailurePattern, GlobalSkillPackage
from app.models.memory import GlobalMemory, EpisodicMemory, CrossAgentContext, ManagerFeedback
from app.models import enterprise  # noqa: F401
from app.models.boardroom_events import (MeetingEvent, MeetingEvidence, MeetingAction, DecisionCharter, MeetingOption, MeetingPosition, DissentRecord, DecisionOutcome)
from app.models import flow_engine  # noqa: F401
from app.models import sales_intelligence  # noqa: F401
from app.models import hr as hr_models  # noqa: F401
from app.models import hr_core as hr_core_models  # noqa: F401
from app.models import hr_workforce as hr_workforce_models  # noqa: F401
from app.models import search_v4 as search_v4_models  # noqa: F401
from app.models import knowledge_connectors  # noqa: F401
from app.models import executive  # noqa: F401
from app.models import objectives  # noqa: F401
from app.models import decision_cases  # noqa: F401
from app.models import data_intelligence  # noqa: F401 — durable Orchestra analysis runs
from app.models import workforce_events  # noqa: F401 — durable tenant-scoped workforce event stream

target_metadata = Base.metadata
config.set_main_option("sqlalchemy.url", settings.SQLALCHEMY_DATABASE_URI)


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True,
                      dialect_opts={"paramstyle": "named"}, render_as_batch=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(config.get_section(config.config_ini_section, {}),
                                     prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, render_as_batch=True)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
