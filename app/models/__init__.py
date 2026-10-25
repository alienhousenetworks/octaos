"""Import all models so that Base.metadata contains the full table schema."""
from app.models.base import Base, Tenant, User, Invitation, APICredential, ProviderUsage, AIBatchJob, SystemSetting
from app.models.rbac import Permission, Group, group_permissions, user_groups, user_permissions
from app.models.teams import AITeam, InstalledApp, AgentMetric
from app.models.agents import ActivityLog, KnowledgeDocument
from app.models.verticals import (
    ContentPost, Lead, Candidate, Contract, Transaction, VirtualInfluencerProfile, CampaignArtifact, CampaignArtifactVersion,
    Ticket, TicketMessage, AgentMeeting, BusinessProfile
)
from app.models.workflows import Workflow, WorkflowTask
from app.models.video import VideoProject, VideoAsset, VideoRender
from app.models.deal_room import (
    DealRoom, BuyingCommitteeMember, AccountSignal,
    DealObjection, DealActivity, SuppressionRecord,
    EvidenceRecord, CompanySalesContext, SalesOutboxItem
)
from app.models.learning import (
    DecisionRecord, StrategyPerformance, NegativePatternMemory,
    GlobalStrategyRegistry, GlobalFailurePattern, GlobalSkillPackage
)
from app.models.memory import GlobalMemory, EpisodicMemory, CrossAgentContext, ManagerFeedback
from app.models import enterprise
from app.models.boardroom_events import (
    MeetingEvent, MeetingEvidence, MeetingAction,
    DecisionCharter, MeetingOption, MeetingPosition,
    DissentRecord, DecisionOutcome
)
from app.models import flow_engine
from app.models import sales_intelligence
from app.models import hr as hr_models
from app.models import hr_core as hr_core_models
from app.models import hr_workforce as hr_workforce_models
from app.models import search_v4 as search_v4_models
from app.models import knowledge_connectors
from app.models import executive
from app.models import objectives
from app.models import decision_cases
from app.models import mcp
from app.models.rooms import SectionRoom
from app.models import agent_runtime
from app.models import real_estate
from app.models import field_sales
from app.models import sales_workflow as sales_workflow_models
from app.models import lifecycle
