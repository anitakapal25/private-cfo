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

const API_ROOT = '/api/v1/agent';

async function request<T>(path: string, token: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_ROOT}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}`, ...init?.headers },
  });
  if (response.status === 401) throw new Error('Your session has expired. Sign in again.');
  if (!response.ok) {
    const payload = await response.json().catch(() => ({})) as { detail?: string };
    throw new Error(payload.detail ?? 'The agent could not complete this request.');
  }
  return response.json() as Promise<T>;
}

export async function createConversation(token: string): Promise<string> {
  const result = await request<{ conversation_id: string }>('/conversations', token, {
    method: 'POST', body: JSON.stringify({ title: 'My financial freedom plan' }),
  });
  return result.conversation_id;
}

export function sendMessage(token: string, conversationId: string, content: string): Promise<AgentMessage> {
  return request<AgentMessage>(`/conversations/${conversationId}/messages`, token, {
    method: 'POST', body: JSON.stringify({ content }),
  });
}
