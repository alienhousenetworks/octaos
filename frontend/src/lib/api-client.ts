import { fetchWithSession } from '@/lib/auth-session';
import { isRecord } from '@/lib/contracts';

export class ApiError extends Error {
  readonly status: number;
  readonly detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
  }
}

export function errorDetail(payload: unknown, fallback: string): string {
  if (isRecord(payload) && typeof payload.detail === 'string') return payload.detail;
  if (typeof payload === 'string' && payload.trim()) return payload;
  return fallback;
}

export async function readJson<T>(response: Response, fallback: T): Promise<T> {
  if (!response.ok) return fallback;
  try {
    return (await response.json()) as T;
  } catch {
    return fallback;
  }
}

export async function requestJson<T>(
  url: string,
  options: RequestInit = {},
  apiUrl?: string,
): Promise<T> {
  const response = await fetchWithSession(url, options, apiUrl);
  let payload: unknown = null;
  try {
    payload = await response.json();
  } catch {
    // Empty 204 responses are valid for command endpoints.
  }
  if (!response.ok) {
    throw new ApiError(response.status, errorDetail(payload, `Request failed with status ${response.status}`));
  }
  return payload as T;
}
