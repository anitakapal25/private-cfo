export interface AgentBlock {
  type: 'calculation' | 'missing_data' | 'warning';
  fields?: string[];
  code?: string;
  calculation_id?: string;
  version?: string;
  result?: Record<string, unknown>;
  assumptions?: Record<string, unknown>;
  limitations?: string[];
}

export interface AgentMessage {
  message_id: string;
  run_id?: string;
  role: 'user' | 'assistant';
  content: string;
  blocks: AgentBlock[];
  created_at: string;
}

export interface FreedomScenario {
  current_age: number;
  target_age: number;
  current_monthly_lifestyle_expenses: string;
  current_investable_corpus: string;
  monthly_contribution: string;
  annual_inflation_rate: string;
  annual_return_rate: string;
  withdrawal_rate: string;
}

export interface FinancialFact {
  fact_id: string;
  fact_type: string;
  value: string;
  unit: string;
  source_type: string;
  verification_status: 'unverified' | 'conflict' | 'verified' | 'rejected' | 'superseded';
  observed_at: string;
  verified_at?: string;
}

const API_ROOT = '/api/v1/agent';

export async function login(email: string, password: string): Promise<string> {
  const body = new URLSearchParams({ username: email, password });
  const response = await fetch('/api/auth/token', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body,
  });
  if (!response.ok) throw new Error('The email or password is incorrect.');
  const payload = await response.json() as { access_token: string };
  return payload.access_token;
}

async function request<T>(path: string, token: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_ROOT}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}`, ...init?.headers },
  });
  if (response.status === 401) throw new Error('Your session has expired. Sign in again.');
  if (!response.ok) {
    const payload = await response.json().catch(() => ({})) as { detail?: unknown };
    const message = typeof payload.detail === 'string'
      ? payload.detail
      : 'Check the scenario fields and try again.';
    throw new Error(message);
  }
  return response.json() as Promise<T>;
}

export async function createConversation(token: string): Promise<string> {
  const result = await request<{ conversation_id: string }>('/conversations', token, {
    method: 'POST', body: JSON.stringify({ title: 'My financial freedom plan' }),
  });
  return result.conversation_id;
}

export function sendMessage(token: string, conversationId: string, content: string, freedomScenario?: FreedomScenario, coverageTarget?: string): Promise<AgentMessage> {
  return request<AgentMessage>(`/conversations/${conversationId}/messages`, token, {
    method: 'POST', body: JSON.stringify({ content, freedom_scenario: freedomScenario, user_selected_coverage_target: coverageTarget || undefined }),
  });
}

export function listFinancialFacts(token: string): Promise<FinancialFact[]> {
  return request<FinancialFact[]>('/financial-facts', token);
}

export function createFinancialFact(token: string, factType: string, value: string): Promise<FinancialFact> {
  return request<FinancialFact>('/financial-facts', token, {
    method: 'POST',
    body: JSON.stringify({
      fact_type: factType,
      value,
      unit: 'INR',
      source_type: 'user_statement',
      observed_at: new Date().toISOString(),
      confidence: '1',
    }),
  });
}

export function decideFinancialFact(token: string, factId: string, decision: 'confirm' | 'reject'): Promise<FinancialFact> {
  return request<FinancialFact>(`/financial-facts/${factId}/decision`, token, {
    method: 'POST', body: JSON.stringify({ decision }),
  });
}
