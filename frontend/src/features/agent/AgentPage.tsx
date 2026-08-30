import React, { FormEvent, useState } from 'react';
import Button from '@/components/ui/Button';
import { createConversation, createFinancialFact, decideFinancialFact, listFinancialFacts, login, sendMessage, type AgentBlock, type AgentMessage, type FinancialFact, type FreedomScenario } from './api';

const emptyScenario = {
  current_age: '', target_age: '', current_monthly_lifestyle_expenses: '',
  current_investable_corpus: '', monthly_contribution: '', annual_inflation_rate: '',
  annual_return_rate: '', withdrawal_rate: '',
};

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
  const [token, setToken] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [conversationId, setConversationId] = useState<string>();
  const [messages, setMessages] = useState<AgentMessage[]>([starter]);
  const [draft, setDraft] = useState('');
  const [error, setError] = useState('');
  const [pending, setPending] = useState(false);
  const [showScenario, setShowScenario] = useState(false);
  const [scenarioConfirmed, setScenarioConfirmed] = useState(false);
  const [scenario, setScenario] = useState(emptyScenario);
  const [coverageTarget, setCoverageTarget] = useState('');
  const [facts, setFacts] = useState<FinancialFact[]>([]);
  const [factType, setFactType] = useState('monthly_income');
  const [factValue, setFactValue] = useState('');
  const [factConfirmed, setFactConfirmed] = useState(false);

  const connect = async (event: FormEvent) => {
    event.preventDefault();
    if (!email.trim() || !password) return;
    setPending(true); setError('');
    try {
      const accessToken = await login(email.trim(), password);
      setToken(accessToken);
      setFacts(await listFinancialFacts(accessToken));
      setPassword('');
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Sign-in failed.');
    } finally { setPending(false); }
  };

  const saveFact = async (event: FormEvent) => {
    event.preventDefault();
    if (!factValue || !factConfirmed || pending) return;
    setPending(true); setError('');
    try {
      await createFinancialFact(token, factType, factValue);
      setFacts(await listFinancialFacts(token));
      setFactValue(''); setFactConfirmed(false);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'The financial fact could not be saved.');
    } finally { setPending(false); }
  };

  const decideFact = async (factId: string, decision: 'confirm' | 'reject') => {
    setPending(true); setError('');
    try {
      await decideFinancialFact(token, factId, decision);
      setFacts(await listFinancialFacts(token));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'The decision could not be saved.');
    } finally { setPending(false); }
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    const content = draft.trim();
    if (!content || pending) return;
    if (showScenario && !scenarioConfirmed) {
      setError('Confirm that the scenario values and assumptions are yours before calculating.');
      return;
    }
    if (showScenario && Object.values(scenario).some(value => value.trim() === '')) {
      setError('Complete every scenario field before calculating.');
      return;
    }
    setDraft(''); setError(''); setPending(true);
    setMessages(current => [...current, { message_id: crypto.randomUUID(), role: 'user', content, blocks: [], created_at: new Date().toISOString() }]);
    try {
      const activeConversation = conversationId ?? await createConversation(token);
      setConversationId(activeConversation);
      const freedomScenario: FreedomScenario | undefined = showScenario ? {
        current_age: Number(scenario.current_age), target_age: Number(scenario.target_age),
        current_monthly_lifestyle_expenses: scenario.current_monthly_lifestyle_expenses,
        current_investable_corpus: scenario.current_investable_corpus,
        monthly_contribution: scenario.monthly_contribution,
        annual_inflation_rate: scenario.annual_inflation_rate,
        annual_return_rate: scenario.annual_return_rate,
        withdrawal_rate: scenario.withdrawal_rate,
      } : undefined;
      const response = await sendMessage(token, activeConversation, content, freedomScenario, coverageTarget);
      setMessages(current => [...current, response]);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'The agent could not respond.');
    } finally { setPending(false); }
  };

  if (!token) {
    return <main className="agent-shell auth-shell"><section className="agent-card"><p className="eyebrow">PRIVATE CFO</p><h1>Your financial-freedom agent</h1><p>Sign in to access only your financial context, conversations, and calculations.</p>{error && <div className="agent-error" role="alert">{error}</div>}<form onSubmit={connect}><label htmlFor="email">Email</label><input id="email" type="email" value={email} onChange={event => setEmail(event.target.value)} autoComplete="username" required/><label htmlFor="password">Password</label><input id="password" type="password" value={password} onChange={event => setPassword(event.target.value)} autoComplete="current-password" required/><Button>{pending ? 'Signing in…' : 'Sign in securely'}</Button></form></section></main>;
  }

  return (
    <main className="agent-shell">
      <header className="agent-header"><div><p className="eyebrow">PRIVATE CFO</p><h1>Financial Freedom Agent</h1></div><button className="text-button" onClick={() => { setToken(''); setConversationId(undefined); setMessages([starter]); }}>Sign out</button></header>
      <section className="boundary">Planning assistance, not guaranteed financial or product advice. Financial values come from verified records and deterministic tools.</section>
      <details className="scenario-card"><summary>Verified financial memory</summary><p>Add a value as a candidate and explicitly confirm it. A changed value supersedes the previous confirmed value; it never merges silently.</p><form onSubmit={saveFact} className="fact-form"><label>Financial field<select value={factType} onChange={event => { setFactType(event.target.value); setFactConfirmed(false); }}>{[
        ['monthly_income', 'Monthly income'], ['monthly_expenses', 'Monthly expenses'],
        ['total_assets', 'Total assets'], ['total_liabilities', 'Total liabilities'],
        ['liquid_assets', 'Liquid assets'], ['monthly_debt_payments', 'Monthly debt payments'],
        ['debt_outstanding', 'Debt outstanding'], ['goal_current', 'Current goal amount'],
        ['goal_target', 'Goal target'], ['insurance_coverage', 'Insurance coverage'],
      ].map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label><label>Value (₹)<input type="number" min="0" step="0.01" value={factValue} onChange={event => { setFactValue(event.target.value); setFactConfirmed(false); }} required/></label><label className="scenario-confirm"><input type="checkbox" checked={factConfirmed} onChange={event => setFactConfirmed(event.target.checked)}/> I confirm this candidate value is mine and should be submitted for review.</label><Button disabled={!factConfirmed || pending}>Submit candidate</Button></form>{facts.length === 0 ? <p>No financial facts yet.</p> : <ul className="fact-list">{facts.map(fact => <li key={fact.fact_id}><span>{fact.fact_type.replace(/_/g, ' ')}</span><strong>₹{fact.value}</strong><small>{fact.verification_status} · {fact.source_type}</small>{(fact.verification_status === 'unverified' || fact.verification_status === 'conflict') && <div className="fact-actions"><button type="button" onClick={() => decideFact(fact.fact_id, 'confirm')} disabled={pending}>Confirm</button><button type="button" onClick={() => decideFact(fact.fact_id, 'reject')} disabled={pending}>Reject</button></div>}</li>)}</ul>}</details>
      <section className="quick-prompts" aria-label="Planning questions"><button type="button" onClick={() => setDraft('Show my debt and EMI metrics')}>Debt metrics</button><button type="button" onClick={() => setDraft('Show my 12-month cash flow forecast')}>Cash-flow forecast</button><button type="button" onClick={() => setDraft('Show my goal progress')}>Goal progress</button></section>
      <section className="conversation" aria-live="polite">
        {messages.map(message => <article key={message.message_id} className={`message ${message.role}`}><span className="message-role">{message.role === 'assistant' ? 'Private CFO' : 'You'}</span><p>{message.content}</p>{message.blocks.map((block, index) => <Evidence key={`${message.message_id}-${index}`} block={block}/>)}</article>)}
        {pending && <article className="message assistant"><span className="message-role">Private CFO</span><p>Reviewing your verified financial context…</p></article>}
      </section>
      {error && <div className="agent-error" role="alert">{error}</div>}
      <button className="text-button scenario-toggle" type="button" onClick={() => setShowScenario(value => !value)} aria-expanded={showScenario}>{showScenario ? 'Hide scenario inputs' : 'Add confirmed freedom scenario inputs'}</button>
      {showScenario && <section className="scenario-card" aria-labelledby="scenario-title"><h2 id="scenario-title">Freedom scenario</h2><p>Enter your own values and assumptions. Private CFO does not choose these rates for you.</p><div className="scenario-grid">
        {[
          ['current_age', 'Current age'], ['target_age', 'Target age'],
          ['current_monthly_lifestyle_expenses', 'Monthly lifestyle expenses (₹)'],
          ['current_investable_corpus', 'Investable corpus (₹)'],
          ['monthly_contribution', 'Monthly contribution (₹)'],
          ['annual_inflation_rate', 'Annual inflation rate (decimal)'],
          ['annual_return_rate', 'Annual return rate (decimal)'],
          ['withdrawal_rate', 'Withdrawal rate (decimal)'],
        ].map(([key, label]) => <label key={key}>{label}<input required type="number" step="any" value={scenario[key as keyof typeof scenario]} onChange={event => { setScenario(current => ({ ...current, [key]: event.target.value })); setScenarioConfirmed(false); }}/></label>)}
      </div><label className="scenario-confirm"><input type="checkbox" checked={scenarioConfirmed} onChange={event => setScenarioConfirmed(event.target.checked)}/> I confirm these are my scenario values and assumptions.</label></section>}
      <details className="scenario-card"><summary>Optional insurance coverage comparison</summary><p>Enter a coverage target you selected yourself. Private CFO will only compare it with stored coverage.</p><label>Coverage target (₹)<input type="number" min="0" step="0.01" value={coverageTarget} onChange={event => setCoverageTarget(event.target.value)}/></label></details>
      <form className="composer" onSubmit={submit}><label htmlFor="agent-message" className="sr-only">Ask about your finances</label><textarea id="agent-message" value={draft} onChange={event => setDraft(event.target.value)} placeholder="Ask about your finances or describe your freedom goal…" maxLength={4000}/><Button>{pending ? 'Working…' : 'Send'}</Button></form>
    </main>
  );
};

export default AgentPage;
