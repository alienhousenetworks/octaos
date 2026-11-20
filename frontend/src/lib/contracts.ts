export type JsonPrimitive = string | number | boolean | null;
export type JsonValue = JsonPrimitive | JsonObject | JsonValue[];
export type JsonObject = { [key: string]: JsonValue | undefined };

export type UserProfile = {
  id?: string;
  tenant_id?: string | null;
  organization_id?: string | null;
  name?: string | null;
  email?: string | null;
  role?: string | null;
  is_system_admin?: boolean;
  allowed_sections?: string[] | null;
  allowed_agents?: string[] | null;
};

export type QueueRecord = Record<string, unknown>;

export type WorkspaceQueue = {
  posts: QueueRecord[];
  leads: QueueRecord[];
};

export type WorkspaceTimelineItem = QueueRecord & {
  id?: string;
  status?: string;
  created_at?: string | null;
};

export type WorkspaceMetrics = Record<string, unknown>;

export type WorkspaceTeam = QueueRecord & {
  id?: string;
  name?: string;
};

export type InstalledApp = QueueRecord & {
  id?: string;
  name?: string;
  app_name?: string;
};

export type WorkspaceSettings = {
  logo_url?: string | null;
  favicon_url?: string | null;
};

export type OrganizationMembership = {
  tenant_id: string;
  tenant_name?: string | null;
  is_current?: boolean;
};

export type ConfiguredProvider = string | { provider?: string | null };

export function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

export function isUserProfile(value: unknown): value is UserProfile {
  return isRecord(value) && (typeof value.email === 'string' || typeof value.id === 'string');
}

export function asRecordList(value: unknown): QueueRecord[] {
  return Array.isArray(value) ? value.filter(isRecord) : [];
}

export function asStringList(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string') : [];
}

export function asObject(value: unknown): Record<string, unknown> {
  return isRecord(value) ? value : {};
}
