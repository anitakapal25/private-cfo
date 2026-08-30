import React, { FormEvent, useState } from 'react';
import Button from '@/components/ui/Button';
import { createConversation, sendMessage, type AgentBlock, type AgentMessage } from './api';

const starter: AgentMessage = {
  message_id: 'welcome', role: 'assistant', created_at: new Date().toISOString(), blocks: [],
  content: 'Tell me what financial freedom means to you. I will use only verified information and deterministic calculations, and I will show assumptions before suggesting planning actions.',
};

function Evidence({ block }: { block: AgentBlock }) {
  if (block.type === 'missing_data') {
    return <div className="evidence warning"><strong>Information needed</strong><ul>{block.fields?.map(field => <li key={field}>{field}</li>)}</ul></div>;
  }
  if (block.type === 'warning') return <div className="evidence warning">This request is outside the agent’s planning boundary.</div>;
  return (
    <details className="evidence">
      <summary>Calculation evidence · {block.version}</summary>
      <pre>{JSON.stringify(block.result, null, 2)}</pre>
      <p>Calculation ID: {block.calculation_id}</p>
      {block.limitations?.map(item => <p key={item}>{item}</p>)}
    </details>
  );
}

const AgentPage: React.FC = () => {
  const [token, setToken] = useState(() => sessionStorage.getItem('artha_token') ?? '');
  const [tokenDraft, setTokenDraft] = useState('');
  const [conversationId, setConversationId] = useState<string>();
  const [messages, setMessages] = useState<AgentMessage[]>([starter]);
  const [draft, setDraft] = useState('');
  const [error, setError] = useState('');
  const [pending, setPending] = useState(false);

  const connect = (event: FormEvent) => {
    event.preventDefault();
    const next = tokenDraft.trim();
    if (!next) return;
    sessionStorage.setItem('artha_token', next);
    setToken(next);
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    const content = draft.trim();
    if (!content || pending) return;
    setDraft(''); setError(''); setPending(true);
    setMessages(current => [...current, { message_id: crypto.randomUUID(), role: 'user', content, blocks: [], created_at: new Date().toISOString() }]);
    try {
      const activeConversation = conversationId ?? await createConversation(token);
      setConversationId(activeConversation);
      const response = await sendMessage(token, activeConversation, content);
      setMessages(current => [...current, response]);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'The agent could not respond.');
    } finally { setPending(false); }
  };

  if (!token) {
    return <main className="agent-shell auth-shell"><section className="agent-card"><p className="eyebrow">PRIVATE CFO</p><h1>Your financial-freedom agent</h1><p>Enter a development access token. Production authentication UI is not yet implemented.</p><form onSubmit={connect}><label htmlFor="access-token">Access token</label><input id="access-token" type="password" value={tokenDraft} onChange={event => setTokenDraft(event.target.value)} autoComplete="off"/><Button>Continue securely</Button></form></section></main>;
  }

  return (
    <main className="agent-shell">
      <header className="agent-header"><div><p className="eyebrow">PRIVATE CFO</p><h1>Financial Freedom Agent</h1></div><button className="text-button" onClick={() => { sessionStorage.removeItem('artha_token'); setToken(''); }}>Sign out</button></header>
      <section className="boundary">Planning assistance, not guaranteed financial or product advice. Financial values come from verified records and deterministic tools.</section>
      <section className="conversation" aria-live="polite">
        {messages.map(message => <article key={message.message_id} className={`message ${message.role}`}><span className="message-role">{message.role === 'assistant' ? 'Private CFO' : 'You'}</span><p>{message.content}</p>{message.blocks.map((block, index) => <Evidence key={`${message.message_id}-${index}`} block={block}/>)}</article>)}
        {pending && <article className="message assistant"><span className="message-role">Private CFO</span><p>Reviewing your verified financial context…</p></article>}
      </section>
      {error && <div className="agent-error" role="alert">{error}</div>}
      <form className="composer" onSubmit={submit}><label htmlFor="agent-message" className="sr-only">Ask about your finances</label><textarea id="agent-message" value={draft} onChange={event => setDraft(event.target.value)} placeholder="Ask about your finances or describe your freedom goal…" maxLength={4000}/><Button>{pending ? 'Working…' : 'Send'}</Button></form>
    </main>
  );
};

export default AgentPage;
