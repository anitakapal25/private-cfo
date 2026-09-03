export interface AgentBlock {
  type: 'calculation' | 'missing_data' | 'warning' | 'cloud_explanation';
  fields?: string[];
  period_start?: string;
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
  period_kind?: 'monthly' | 'as_of';
  period_start?: string;
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

export type AuthStart =
  | { state: 'authenticated'; accessToken: string; refreshToken?: string }
  | { state: 'email_verification_required' }
  | { state: 'mfa_required'; challengeToken: string; enrollmentRequired: boolean };

interface TokenPair {
  access_token: string;
  refresh_token?: string;
}

async function authRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/auth${path}`, init);
  const payload = await response.json().catch(() => ({})) as T & { detail?: unknown };
  if (!response.ok) throw new Error(typeof payload.detail === 'string' ? payload.detail : 'The security request could not be completed.');
  return payload;
}

export async function login(email: string, password: string): Promise<AuthStart> {
  const body = new URLSearchParams({ username: email, password });
  const payload = await authRequest<TokenPair & { email_verification_required?: boolean; mfa_required?: boolean; mfa_enrollment_required?: boolean; mfa_challenge_token?: string }>('/token', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body,
  });
  if (payload.access_token) return { state: 'authenticated', accessToken: payload.access_token, refreshToken: payload.refresh_token };
  if (payload.email_verification_required) return { state: 'email_verification_required' };
  if (payload.mfa_challenge_token) return { state: 'mfa_required', challengeToken: payload.mfa_challenge_token, enrollmentRequired: Boolean(payload.mfa_enrollment_required) };
  throw new Error('The sign-in response was incomplete.');
}

export function register(email: string, password: string, fullName: string): Promise<{ detail: string }> {
  return authRequest('/register', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email, password, full_name: fullName || undefined }) });
}

export function verifyEmail(token: string): Promise<{ detail: string }> {
  return authRequest('/verify-email', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ token }) });
}

export function requestPasswordReset(email: string): Promise<{ detail: string }> {
  return authRequest('/password-reset', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email }) });
}

export function confirmPasswordReset(token: string, password: string): Promise<{ detail: string }> {
  return authRequest('/password-reset/confirm', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ token, password }) });
}

export function beginMfaEnrollment(challengeToken: string): Promise<{ secret: string; issuer: string; account_name: string }> {
  return authRequest('/mfa/enrollment', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ challenge_token: challengeToken }) });
}

export async function confirmMfaEnrollment(challengeToken: string, code: string): Promise<AuthStart> {
  const payload = await authRequest<TokenPair>('/mfa/enrollment/confirm', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ challenge_token: challengeToken, code }) });
  return { state: 'authenticated', accessToken: payload.access_token, refreshToken: payload.refresh_token };
}

export async function verifyMfa(challengeToken: string, code: string): Promise<AuthStart> {
  const payload = await authRequest<TokenPair>('/mfa/verify', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ challenge_token: challengeToken, code }) });
  return { state: 'authenticated', accessToken: payload.access_token, refreshToken: payload.refresh_token };
}

export async function logout(token: string): Promise<void> {
  await authRequest('/logout', { method: 'POST', headers: { Authorization: `Bearer ${token}` } });
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
      : 'The request could not be completed. Please try again.';
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
  options?: { sourceType?: 'user_statement' | 'local_document_confirmation'; sourceId?: string; confidence?: string; periodStart?: string },
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
      period_start: options?.periodStart,
      confidence: options?.confidence || '1',
    }),
  });
}

export interface FinancialFactInput {
  fact_type: string;
  value: string;
  unit: 'INR';
  source_type: 'user_statement';
  observed_at: string;
  period_start: string;
}

export function createFinancialFactBatch(token: string, facts: FinancialFactInput[]): Promise<FinancialFact[]> {
  return request<FinancialFact[]>('/financial-facts/batch', token, {
    method: 'POST', body: JSON.stringify({ facts }),
  });
}

export function decideFinancialFactBatch(token: string, factIds: string[], decision: 'confirm' | 'reject'): Promise<FinancialFact[]> {
  return request<FinancialFact[]>('/financial-facts/batch/decision', token, {
    method: 'POST', body: JSON.stringify({ fact_ids: factIds, decision }),
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
