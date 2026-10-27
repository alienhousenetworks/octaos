/** Providers an agent can pin. Auto follows DEFAULT_AI_PROVIDER on the server. */
export const AGENT_AI_PROVIDERS: Array<{ value: string; label: string }> = [
  { value: 'auto', label: 'Auto' },
  { value: 'nvidia', label: 'NVIDIA NIM' },
  { value: 'openrouter', label: 'OpenRouter' },
  { value: 'groq', label: 'Groq' },
  { value: 'together', label: 'Together AI' },
  { value: 'grok', label: 'Grok (xAI)' },
  { value: 'openai', label: 'OpenAI' },
  { value: 'anthropic', label: 'Anthropic' },
  { value: 'gemini', label: 'Google Gemini' },
];

const LABELS = Object.fromEntries(AGENT_AI_PROVIDERS.map((item) => [item.value, item.label]));

export function normalizeAgentProvider(value?: string | null): string {
  const raw = (value || 'auto').trim().toLowerCase();
  if (!raw || raw === 'none' || raw === 'default') return 'auto';
  if (raw === 'nim' || raw === 'nvidia_nim') return 'nvidia';
  if (raw === 'google') return 'gemini';
  return raw;
}

export function providerDisplayName(value?: string | null): string {
  const key = normalizeAgentProvider(value);
  return LABELS[key] || key;
}

export function autoProviderLabel(envProvider?: string | null): string {
  if (!envProvider) return 'Auto (server environment)';
  return `Auto (${providerDisplayName(envProvider)})`;
}
