export interface AgentBlock {
  type: 'calculation' | 'missing_data' | 'warning' | 'cloud_explanation';
  fields?: string[];
  code?: string;
  calculation_id?: string;
  version?: string;
  result?: Record<string, unknown>;
  assumptions?: Record<string, unknown>;
  limitations?: string[];
  provider?: string;
  policy_bundle_version?: string;
  content?: string;
  data_categories?: string[];
}

export interface CloudAssistanceConsent {
  consent_id?: string;
  status: 'active' | 'revoked' | 'not_granted';
  provider: string;
  purpose: string;
  policy_bundle_version: string;
  data_categories: string[];
  excluded_categories: string[];
  retention_url: string;
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

export interface PlanningActionInput {
  action_type: 'reduce_monthly_expenses' | 'increase_monthly_savings' | 'increase_debt_payment';
  monthly_amount: string;
  feasibility: string;
  user_priority: string;
}

export interface RankedAction {
  action_type: string;
  monthly_amount: string;
  score: string;
  rationale: string;
  impact: Record<string, unknown>;
}

export interface ProactiveReview {
  review_id: string;
  finding_type: string;
  severity: string;
  status: 'open' | 'acknowledged' | 'dismissed' | 'converted';
  evidence: Record<string, unknown>;
  rule_version: string;
  created_at: string;
}

const API_ROOT = '/api/v1/agent';

export class ApiError extends Error {
  constructor(message: string, public readonly status: number) {
    super(message);
    this.name = 'ApiError';
  }
}

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
  if (response.status === 401) throw new ApiError('Your session has expired. Sign in again.', 401);
  if (!response.ok) {
    const payload = await response.json().catch(() => ({})) as { detail?: unknown };
    const message = typeof payload.detail === 'string'
      ? payload.detail
      : 'Check the scenario fields and try again.';
    throw new ApiError(message, response.status);
  }
  return response.json() as Promise<T>;
}

export async function createConversation(token: string): Promise<string> {
  const result = await request<{ conversation_id: string }>('/conversations', token, {
    method: 'POST', body: JSON.stringify({ title: 'My financial freedom plan' }),
  });
  return result.conversation_id;
}

export function sendMessage(token: string, conversationId: string, content: string, clientRequestId: string, freedomScenario?: FreedomScenario, coverageTarget?: string, signal?: AbortSignal, cloudAssistance = false): Promise<AgentMessage> {
  return request<AgentMessage>(`/conversations/${conversationId}/messages`, token, {
    method: 'POST', signal, body: JSON.stringify({ content, client_request_id: clientRequestId, freedom_scenario: freedomScenario, user_selected_coverage_target: coverageTarget || undefined, cloud_assistance: cloudAssistance }),
  });
}

export function getCloudAssistanceConsent(token: string, conversationId: string): Promise<CloudAssistanceConsent> {
  return request<CloudAssistanceConsent>(`/conversations/${conversationId}/cloud-assistance`, token);
}

export function grantCloudAssistanceConsent(token: string, conversationId: string): Promise<CloudAssistanceConsent> {
  return request<CloudAssistanceConsent>(`/conversations/${conversationId}/cloud-assistance`, token, {
    method: 'POST', body: JSON.stringify({ privacy_notice_version: 'render-singapore-pilot-v1' }),
  });
}

export function revokeCloudAssistanceConsent(token: string, conversationId: string): Promise<CloudAssistanceConsent> {
  return request<CloudAssistanceConsent>(`/conversations/${conversationId}/cloud-assistance`, token, { method: 'DELETE' });
}

export function listFinancialFacts(token: string): Promise<FinancialFact[]> {
  return request<FinancialFact[]>('/financial-facts', token);
}

export function createFinancialFact(
  token: string, factType: string, value: string,
  options?: { sourceType?: 'user_statement' | 'local_document_confirmation'; sourceId?: string; confidence?: string },
): Promise<FinancialFact> {
  return request<FinancialFact>('/financial-facts', token, {
    method: 'POST',
    body: JSON.stringify({
      fact_type: factType,
      value,
      unit: 'INR',
      source_type: options?.sourceType || 'user_statement',
      source_id: options?.sourceId,
      observed_at: new Date().toISOString(),
      confidence: options?.confidence || '1',
    }),
  });
}

export function decideFinancialFact(token: string, factId: string, decision: 'confirm' | 'reject'): Promise<FinancialFact> {
  return request<FinancialFact>(`/financial-facts/${factId}/decision`, token, {
    method: 'POST', body: JSON.stringify({ decision }),
  });
}

export async function rankPlanningActions(token: string, actions: PlanningActionInput[]): Promise<RankedAction[]> {
  const result = await request<{ actions: RankedAction[] }>('/planning/candidates', token, {
    method: 'POST', body: JSON.stringify({ actions }),
  });
  return result.actions;
}

export async function confirmAction(token: string, conversationId: string, actionType: string, actionPayload: Record<string, unknown>): Promise<string> {
  const result = await request<{ confirmation_id: string }>(`/conversations/${conversationId}/confirmations`, token, {
    method: 'POST', body: JSON.stringify({ action_type: actionType, action_payload: actionPayload }),
  });
  return result.confirmation_id;
}

export function createActionPlan(token: string, title: string, actions: PlanningActionInput[], confirmationId: string): Promise<{ plan_id: string }> {
  return request('/planning/plans', token, {
    method: 'POST', body: JSON.stringify({ title, actions, confirmation_id: confirmationId }),
  });
}

export function listProactiveReviews(token: string): Promise<ProactiveReview[]> {
  return request<ProactiveReview[]>('/reviews', token);
}

export function runProactiveReviews(token: string): Promise<ProactiveReview[]> {
  return request<ProactiveReview[]>('/reviews/run', token, { method: 'POST' });
}

export function decideProactiveReview(token: string, reviewId: string, decision: 'acknowledge' | 'dismiss'): Promise<ProactiveReview> {
  return request<ProactiveReview>(`/reviews/${reviewId}/${decision}`, token, { method: 'POST' });
}
