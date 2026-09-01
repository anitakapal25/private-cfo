import React, { FormEvent, useEffect, useRef, useState } from 'react';
import Button from '@/components/ui/Button';
import { Bell, Bot, Check, ChevronDown, CircleUserRound, Database, FolderLock, Gauge, Home, LockKeyhole, LogOut, Menu, MessageSquareText, Send, ShieldCheck, Sparkles, Target } from 'lucide-react';
import { ApiError, confirmAction, createActionPlan, createConversation, createFinancialFact, decideFinancialFact, decideProactiveReview, grantCloudAssistanceConsent, listFinancialFacts, listProactiveReviews, login, rankPlanningActions, revokeCloudAssistanceConsent, runProactiveReviews, sendMessage, type AgentBlock, type AgentMessage, type CloudAssistanceConsent, type FinancialFact, type FreedomScenario, type PlanningActionInput, type ProactiveReview, type RankedAction } from './api';
import { discardLocalDocumentSelection, getLocalDocumentCapabilities, isDesktopHost, processLocalDocument, selectLocalDocument, type LocalDocumentCandidate, type LocalDocumentCapabilities, type LocalDocumentSelection } from './desktop';

const emptyScenario = {
  current_age: '', target_age: '', current_monthly_lifestyle_expenses: '',
  current_investable_corpus: '', monthly_contribution: '', annual_inflation_rate: '',
  annual_return_rate: '', withdrawal_rate: '',
};

const starter: AgentMessage = {
  message_id: 'welcome', role: 'assistant', created_at: new Date().toISOString(), blocks: [],
  content: 'Tell me what financial freedom means to you. I will use only verified information and deterministic calculations, and I will show assumptions before suggesting planning actions.',
};

interface RetryableMessage {
  conversationId: string;
  clientRequestId: string;
  content: string;
  scenario?: FreedomScenario;
  coverageTarget?: string;
  cloudAssistance: boolean;
}

type WorkspaceSection = 'overview' | 'ask' | 'memory' | 'plans' | 'documents' | 'reviews';

const factLabels: Record<string, string> = {
  monthly_income: 'Monthly income', monthly_expenses: 'Monthly expenses', total_assets: 'Total assets',
  total_liabilities: 'Total liabilities', liquid_assets: 'Liquid assets', monthly_debt_payments: 'Monthly debt payments',
  debt_outstanding: 'Debt outstanding', goal_current: 'Current goal amount', goal_target: 'Goal target',
  insurance_coverage: 'Insurance coverage', monthly_contribution: 'Monthly contribution', investable_corpus: 'Investable corpus',
};

function formatFactValue(fact?: FinancialFact) {
  if (!fact) return 'Not added';
  const value = Number(fact.value);
  if (!Number.isFinite(value)) return `${fact.unit === 'INR' ? '₹' : ''}${fact.value}`;
  return `${fact.unit === 'INR' ? '₹' : ''}${new Intl.NumberFormat('en-IN', { maximumFractionDigits: 2 }).format(value)}`;
}

function Evidence({ block }: { block: AgentBlock }) {
  if (block.type === 'missing_data') {
    return <div className="evidence warning"><strong>Information needed</strong><ul>{block.fields?.map(field => <li key={field}>{field}</li>)}</ul></div>;
  }
  if (block.type === 'warning') return <div className="evidence warning">This request is outside the agent’s planning boundary.</div>;
  if (block.type === 'cloud_explanation') return <div className="evidence"><strong>Cloud-assisted explanation · {block.provider}</strong><p>{block.content}</p><small>Exact figures remain in the deterministic evidence card.</small></div>;
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
  const [statusMessage, setStatusMessage] = useState('');
  const [pending, setPending] = useState(false);
  const [showScenario, setShowScenario] = useState(false);
  const [scenarioConfirmed, setScenarioConfirmed] = useState(false);
  const [scenario, setScenario] = useState(emptyScenario);
  const [coverageTarget, setCoverageTarget] = useState('');
  const [facts, setFacts] = useState<FinancialFact[]>([]);
  const [factType, setFactType] = useState('monthly_income');
  const [factValue, setFactValue] = useState('');
  const [factConfirmed, setFactConfirmed] = useState(false);
  const [planAction, setPlanAction] = useState<PlanningActionInput>({ action_type: 'increase_monthly_savings', monthly_amount: '', feasibility: '0.5', user_priority: '0.5' });
  const [rankedActions, setRankedActions] = useState<RankedAction[]>([]);
  const [planConfirmed, setPlanConfirmed] = useState(false);
  const [reviews, setReviews] = useState<ProactiveReview[]>([]);
  const [documentType, setDocumentType] = useState('salary_slip');
  const [localSelection, setLocalSelection] = useState<LocalDocumentSelection>();
  const [localCandidates, setLocalCandidates] = useState<LocalDocumentCandidate[]>([]);
  const desktopHost = isDesktopHost();
  const [localCapabilities, setLocalCapabilities] = useState<LocalDocumentCapabilities>();
  const [chatPending, setChatPending] = useState(false);
  const [retryableMessage, setRetryableMessage] = useState<RetryableMessage>();
  const [activeSection, setActiveSection] = useState<WorkspaceSection>('overview');
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [cloudConsent, setCloudConsent] = useState<CloudAssistanceConsent>();
  const [cloudAssistance, setCloudAssistance] = useState(false);
  const requestController = useRef<AbortController>();

  useEffect(() => {
    if (!desktopHost) return;
    getLocalDocumentCapabilities()
      .then(setLocalCapabilities)
      .catch(() => setLocalCapabilities({ available: false, platform: 'unknown', scanner_available: false, sandbox_available: false, pdf_text_available: false, limitations: ['Local document security checks are unavailable'] }));
  }, [desktopHost]);

  const discardLocalSelection = async () => {
    if (localSelection) {
      try { await discardLocalDocumentSelection(localSelection.selection_token); }
      catch { /* An expired token contains no remaining usable selection. */ }
    }
    setLocalSelection(undefined);
  };

  const clearLocalDocumentState = async () => {
    await discardLocalSelection();
    setLocalCandidates([]);
  };

  const reportError = (reason: unknown, fallback: string) => {
    if (reason instanceof ApiError && reason.status === 401) {
      void clearLocalDocumentState();
      setToken(''); setConversationId(undefined); setMessages([starter]);
    }
    setError(reason instanceof Error ? reason.message : fallback);
  };

  const connect = async (event: FormEvent) => {
    event.preventDefault();
    if (!email.trim() || !password) return;
    setPending(true); setError('');
    try {
      const accessToken = await login(email.trim(), password);
      setToken(accessToken);
      setFacts(await listFinancialFacts(accessToken));
      setReviews(await listProactiveReviews(accessToken));
      setPassword('');
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Sign-in failed.');
    } finally { setPending(false); }
  };

  const chooseLocalDocument = async () => {
    setPending(true); setError('');
    try {
      await discardLocalSelection();
      setLocalSelection((await selectLocalDocument()) || undefined);
    }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'The local document could not be selected.'); }
    finally { setPending(false); }
  };

  const processSelectedDocument = async () => {
    if (!localSelection) return;
    setPending(true); setError('');
    try {
      const result = await processLocalDocument(localSelection.selection_token, documentType);
      setLocalCandidates(result.candidates.map(candidate => ({ ...candidate, status: 'candidate' })));
      setLocalSelection(undefined);
      setStatusMessage(result.candidates.length ? 'Local extraction completed. Review every candidate before confirmation.' : 'Local extraction completed without an eligible financial candidate.');
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'The local document could not be processed.'); }
    finally { setPending(false); }
  };

  const decideLocalCandidate = async (candidate: LocalDocumentCandidate, decision: 'confirm' | 'reject') => {
    if (decision === 'reject') {
      setLocalCandidates(current => current.map(item => item.evidence_id === candidate.evidence_id ? { ...item, status: 'rejected' } : item));
      return;
    }
    setPending(true); setError(''); setStatusMessage('');
    try {
      const fact = await createFinancialFact(token, candidate.fact_type, candidate.value, {
        sourceType: 'local_document_confirmation', sourceId: candidate.evidence_id,
        confidence: candidate.confidence,
      });
      await decideFinancialFact(token, fact.fact_id, 'confirm');
      setLocalCandidates(current => current.map(item => item.evidence_id === candidate.evidence_id ? { ...item, status: 'confirmed' } : item));
      setFacts(await listFinancialFacts(token));
      setStatusMessage('Only the confirmed structured value was saved. The document stayed on this device.');
    } catch (reason) { reportError(reason, 'The local candidate could not be confirmed.'); }
    finally { setPending(false); }
  };

  const refreshReviews = async () => {
    setPending(true); setError('');
    try {
      await runProactiveReviews(token);
      setReviews(await listProactiveReviews(token));
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'The proactive review could not run.'); }
    finally { setPending(false); }
  };

  const decideReview = async (reviewId: string, decision: 'acknowledge' | 'dismiss') => {
    setPending(true); setError('');
    try {
      await decideProactiveReview(token, reviewId, decision);
      setReviews(await listProactiveReviews(token));
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'The review decision could not be saved.'); }
    finally { setPending(false); }
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

  const compareAction = async (event: FormEvent) => {
    event.preventDefault(); setPending(true); setError(''); setPlanConfirmed(false);
    try { setRankedActions(await rankPlanningActions(token, [planAction])); }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'The action could not be compared.'); }
    finally { setPending(false); }
  };

  const savePlan = async () => {
    if (!planConfirmed || rankedActions.length === 0) return;
    setPending(true); setError(''); setStatusMessage('');
    try {
      const activeConversation = conversationId ?? await createConversation(token);
      setConversationId(activeConversation);
      const title = 'My confirmed financial freedom actions';
      const actionPayload = { title, actions: [planAction] };
      const confirmationId = await confirmAction(token, activeConversation, 'create_action_plan', actionPayload);
      await createActionPlan(token, title, [planAction], confirmationId);
      setPlanConfirmed(false);
      setStatusMessage('Your confirmed action was added to the plan.');
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'The plan could not be created.'); }
    finally { setPending(false); }
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
    setDraft(''); setError(''); setPending(true); setChatPending(true);
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
      const retryable = { conversationId: activeConversation, clientRequestId: crypto.randomUUID(), content, scenario: freedomScenario, coverageTarget: coverageTarget || undefined, cloudAssistance };
      setRetryableMessage(retryable);
      const controller = new AbortController();
      requestController.current = controller;
      const response = await sendMessage(token, activeConversation, content, retryable.clientRequestId, freedomScenario, coverageTarget, controller.signal, cloudAssistance);
      setMessages(current => [...current, response]);
      setRetryableMessage(undefined);
    } catch (reason) {
      if (reason instanceof DOMException && reason.name === 'AbortError') {
        setError('Response cancelled. Retry safely to retrieve the same idempotent request.');
      } else {
        reportError(reason, 'The agent could not respond.');
      }
    } finally { requestController.current = undefined; setPending(false); setChatPending(false); }
  };

  const retryMessage = async () => {
    if (!retryableMessage || pending) return;
    setPending(true); setChatPending(true); setError('');
    const controller = new AbortController();
    requestController.current = controller;
    try {
      const response = await sendMessage(
        token, retryableMessage.conversationId, retryableMessage.content,
        retryableMessage.clientRequestId, retryableMessage.scenario,
        retryableMessage.coverageTarget, controller.signal, retryableMessage.cloudAssistance,
      );
      setMessages(current => [...current, response]);
      setRetryableMessage(undefined);
    } catch (reason) {
      if (reason instanceof DOMException && reason.name === 'AbortError') {
        setError('Response cancelled. You can retry the same request again.');
      } else {
        reportError(reason, 'The retry could not complete.');
      }
    } finally { requestController.current = undefined; setPending(false); setChatPending(false); }
  };

  const enableCloudAssistance = async () => {
    setPending(true); setError('');
    try {
      const activeConversation = conversationId ?? await createConversation(token);
      setConversationId(activeConversation);
      const consent = await grantCloudAssistanceConsent(token, activeConversation);
      setCloudConsent(consent); setCloudAssistance(true);
      setStatusMessage('Cloud assistance is enabled only for this conversation. Raw documents and messages are excluded.');
    } catch (reason) { reportError(reason, 'Cloud assistance could not be enabled.'); }
    finally { setPending(false); }
  };

  const disableCloudAssistance = async () => {
    if (!conversationId) return;
    setPending(true); setError('');
    try {
      const consent = await revokeCloudAssistanceConsent(token, conversationId);
      setCloudConsent(consent); setCloudAssistance(false);
      setStatusMessage('Cloud assistance has been revoked for this conversation.');
    } catch (reason) { reportError(reason, 'Cloud assistance could not be revoked.'); }
    finally { setPending(false); }
  };

  if (!token) {
    return <main className="agent-shell auth-shell"><section className="agent-card auth-card"><div className="auth-brand"><ShieldCheck aria-hidden="true"/><span>Artha</span></div><p className="eyebrow">PRIVATE CFO</p><h1>Your financial-freedom agent</h1><p>Sign in to access only your financial context, conversations, and deterministic calculations.</p>{error && <div className="agent-error" role="alert">{error}</div>}<form onSubmit={connect}><label htmlFor="email">Email</label><input id="email" type="email" value={email} onChange={event => setEmail(event.target.value)} autoComplete="username" required/><label htmlFor="password">Password</label><input id="password" type="password" value={password} onChange={event => setPassword(event.target.value)} autoComplete="current-password" required/><Button>{pending ? 'Signing in…' : 'Sign in securely'}</Button></form><p className="auth-privacy"><LockKeyhole size={15}/> Your data stays bound to your signed-in account.</p></section></main>;
  }

  const verifiedFacts = facts.filter(fact => fact.verification_status === 'verified');
  const openReviews = reviews.filter(review => review.status === 'open');
  const navItems: Array<{ id: WorkspaceSection; label: string; icon: React.ReactNode }> = [
    { id: 'overview', label: 'Overview', icon: <Home/> }, { id: 'ask', label: 'Ask Artha', icon: <MessageSquareText/> },
    { id: 'memory', label: 'Financial memory', icon: <Database/> }, { id: 'plans', label: 'Plans', icon: <Target/> },
    { id: 'documents', label: 'Documents', icon: <FolderLock/> }, { id: 'reviews', label: 'Reviews', icon: <Sparkles/> },
  ];
  const selectSection = (section: WorkspaceSection) => { setActiveSection(section); setMobileNavOpen(false); setError(''); };

  return (
    <div className="app-shell">
      <a className="skip-link" href="#workspace-content">Skip to main content</a>
      <aside className={`app-sidebar ${mobileNavOpen ? 'open' : ''}`}><div><div className="app-logo"><ShieldCheck/><span>Artha</span></div><nav aria-label="Primary navigation">{navItems.map(item => <button type="button" key={item.id} className={activeSection === item.id ? 'active' : ''} onClick={() => selectSection(item.id)}>{item.icon}<span>{item.label}</span>{item.id === 'reviews' && openReviews.length > 0 && <b>{openReviews.length}</b>}</button>)}</nav></div><div className="sidebar-footer"><ShieldCheck/><span>Private by design</span></div></aside>
      <header className="app-header"><button type="button" className="menu-button" aria-label="Toggle navigation" aria-expanded={mobileNavOpen} onClick={() => setMobileNavOpen(value => !value)}><Menu/></button><h1>Financial Freedom Agent</h1><div className="header-actions"><span className="data-chip"><Check/> Data verified</span><button type="button" className="icon-button" aria-label="Notifications"><Bell/></button><span className="avatar"><CircleUserRound/></span><button type="button" className="sign-out" onClick={() => { void clearLocalDocumentState(); setToken(''); setConversationId(undefined); setMessages([starter]); }}><LogOut/><span>Sign out</span></button></div></header>
      <main id="workspace-content" className={`app-main section-${activeSection}`}>
      <section className="mobile-section-title"><p className="eyebrow">PRIVATE CFO</p><h2>{navItems.find(item => item.id === activeSection)?.label}</h2></section>
      {activeSection === 'overview' && <section className="overview-page"><header className="overview-heading"><div><p className="eyebrow">YOUR FINANCIAL HOME</p><h2>Good morning</h2><p>Here is where your verified financial context stands today.</p></div><Button type="button" onClick={() => selectSection('ask')}><Bot/> Ask Artha</Button></header><div className="dashboard-summary">{['total_assets', 'monthly_income', 'liquid_assets'].map((type, index) => { const fact = verifiedFacts.find(item => item.fact_type === type); const icons = [<Database key="a"/>, <Gauge key="i"/>, <ShieldCheck key="l"/>]; return <article className="dashboard-card" key={type}><div className="dashboard-card-head"><span className="metric-icon">{icons[index]}</span><span>{factLabels[type]}</span></div><strong className="metric-value">{formatFactValue(fact)}</strong><footer>{fact ? <><span className="verified-label"><Check/> Verified</span><small>Updated {new Date(fact.verified_at || fact.observed_at).toLocaleDateString()}</small></> : <button type="button" className="inline-link" onClick={() => selectSection('memory')}>Add verified value</button>}</footer></article>; })}</div><div className="dashboard-grid"><article className="dashboard-card plan-card"><div className="card-heading"><div><h3>Your planning workspace</h3><p>Use confirmed values for supported questions.</p></div><Bot/></div><div className="plan-summary"><div className="verified-orbit"><ShieldCheck/><strong>{verifiedFacts.length}</strong><span>verified values</span></div><div><h3>{verifiedFacts.length ? 'Your context is ready' : 'Build your verified context'}</h3><p>{verifiedFacts.length ? 'Artha can use these records with deterministic financial tools.' : 'Add and confirm values before requesting calculations.'}</p><button type="button" className="inline-link" onClick={() => selectSection('ask')}>Start a conversation →</button></div></div></article><article className="dashboard-card attention-card"><div className="card-heading"><div><h3>Needs your attention</h3><p>{openReviews.length} open reviews</p></div></div>{openReviews.length ? openReviews.slice(0, 2).map(review => <button type="button" className="attention-row" key={review.review_id} onClick={() => selectSection('reviews')}><span className="attention-icon">!</span><span><strong>{review.finding_type.replace(/_/g, ' ')}</strong><small>Deterministic review finding</small></span><ChevronDown/></button>) : <div className="clear-state"><Check/><span><strong>You are all caught up</strong><small>No reviews need a decision.</small></span></div>}</article><article className="dashboard-card ask-card"><h3>Ask Artha</h3><p>What would you like to understand?</p><div className="overview-prompts"><button onClick={() => { setDraft('Show my goal progress'); selectSection('ask'); }}>Can I reach my goal?</button><button onClick={() => { setDraft('Show my 12-month cash flow forecast'); selectSection('ask'); }}>Review my cash flow</button><button onClick={() => { setDraft('Show my debt and EMI metrics'); selectSection('ask'); }}>Explain my debt</button></div></article><article className="dashboard-card privacy-card"><h3>Privacy & evidence</h3><p><ShieldCheck/> Calculations use verified values</p><p><FolderLock/> Documents stay on this device</p><button type="button" className="inline-link" onClick={() => selectSection('documents')}>Local document review</button><button type="button" className="inline-link" onClick={() => selectSection('plans')}>Compare and confirm a planning action</button></article></div></section>}
      <section className="boundary">Planning assistance, not guaranteed financial or product advice. Financial values come from verified records and deterministic tools.</section>
      <details className="scenario-card"><summary>Local document review ({localCandidates.filter(candidate => candidate.status === 'candidate').length} awaiting confirmation)</summary><p>Your document never leaves this device. The desktop processor scans and extracts it locally; only a value you explicitly confirm is sent to your verified financial memory.</p>{desktopHost ? <>{localCapabilities && !localCapabilities.available && <div className="evidence warning" role="alert"><strong>Local document processing is blocked</strong>{localCapabilities.limitations.map(item => <p key={item}>{item}</p>)}</div>}<div className="fact-form"><label>Document type<select value={documentType} onChange={event => { void clearLocalDocumentState(); setDocumentType(event.target.value); }}><option value="salary_slip">Salary slip</option><option value="form_16">Form 16</option><option value="bank_statement">Bank statement</option><option value="epf_statement">EPF statement</option><option value="insurance_policy">Insurance policy</option></select></label><Button type="button" disabled={pending || !localCapabilities?.available} onClick={chooseLocalDocument}>Choose PDF from this device</Button>{localSelection && <div className="document-candidate"><strong>{localSelection.display_name}</strong><small>{localSelection.file_size_bytes} bytes · selected locally · path not exposed to the webview</small><div className="fact-actions"><Button type="button" disabled={pending} onClick={processSelectedDocument}>Scan and extract locally</Button><button type="button" disabled={pending} onClick={() => void discardLocalSelection()}>Discard selection</button></div></div>}</div>{localCandidates.length === 0 ? <p>No local candidates awaiting review.</p> : <ul className="fact-list">{localCandidates.map(candidate => { const conflict = facts.find(fact => fact.fact_type === candidate.fact_type && fact.verification_status === 'verified' && (fact.value !== candidate.value || fact.unit !== candidate.unit)); return <li key={candidate.evidence_id}><span>{candidate.fact_type.replace(/_/g, ' ')}</span><strong>{candidate.unit} {candidate.value}</strong><small>Local candidate · confidence {candidate.confidence} · {candidate.source_location}</small>{conflict && <p role="alert">Conflict: the current verified value is {conflict.unit} {conflict.value}, observed {new Date(conflict.observed_at).toLocaleDateString()}.</p>}{candidate.status === 'candidate' && <div className="fact-actions"><button type="button" disabled={pending} onClick={() => decideLocalCandidate(candidate, 'confirm')}>Confirm structured value</button><button type="button" disabled={pending} onClick={() => decideLocalCandidate(candidate, 'reject')}>Reject</button></div>}<small>Status: {candidate.status}</small></li>; })}</ul>}</> : <div className="evidence warning"><strong>Desktop application required</strong><p>Local document processing is unavailable in the browser. No upload will be sent to the server.</p></div>}</details>
      <details className="scenario-card"><summary>Proactive financial reviews ({reviews.filter(review => review.status === 'open').length} open)</summary><p>Reviews are deterministic notifications. They never change your records or plan.</p><Button type="button" disabled={pending} onClick={refreshReviews}>Run review now</Button>{reviews.length === 0 ? <p>No review findings.</p> : <ul className="fact-list">{reviews.map(review => <li key={review.review_id}><span>{review.finding_type.replace(/_/g, ' ')}</span><small>{review.severity} · {review.status} · {review.rule_version}</small><details><summary>Evidence</summary><pre>{JSON.stringify(review.evidence, null, 2)}</pre></details>{review.status === 'open' && <div className="fact-actions"><button type="button" disabled={pending} onClick={() => decideReview(review.review_id, 'acknowledge')}>Acknowledge</button><button type="button" disabled={pending} onClick={() => decideReview(review.review_id, 'dismiss')}>Dismiss</button></div>}</li>)}</ul>}</details>
      <details className="scenario-card"><summary>Verified financial memory</summary><p>Add a value as a candidate and explicitly confirm it. A changed value supersedes the previous confirmed value; it never merges silently.</p><form onSubmit={saveFact} className="fact-form"><label>Financial field<select value={factType} onChange={event => { setFactType(event.target.value); setFactConfirmed(false); }}>{[
        ['monthly_income', 'Monthly income'], ['monthly_expenses', 'Monthly expenses'],
        ['total_assets', 'Total assets'], ['total_liabilities', 'Total liabilities'],
        ['liquid_assets', 'Liquid assets'], ['monthly_debt_payments', 'Monthly debt payments'],
        ['debt_outstanding', 'Debt outstanding'], ['goal_current', 'Current goal amount'],
        ['goal_target', 'Goal target'], ['insurance_coverage', 'Insurance coverage'],
      ].map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label><label>Value (₹)<input type="number" min="0" step="0.01" value={factValue} onChange={event => { setFactValue(event.target.value); setFactConfirmed(false); }} required/></label><label className="scenario-confirm"><input type="checkbox" checked={factConfirmed} onChange={event => setFactConfirmed(event.target.checked)}/> I confirm this candidate value is mine and should be submitted for review.</label><Button disabled={!factConfirmed || pending}>Submit candidate</Button></form>{facts.length === 0 ? <p>No financial facts yet.</p> : <ul className="fact-list">{facts.map(fact => <li key={fact.fact_id}><span>{fact.fact_type.replace(/_/g, ' ')}</span><strong>₹{fact.value}</strong><small>{fact.verification_status} · {fact.source_type}</small>{(fact.verification_status === 'unverified' || fact.verification_status === 'conflict') && <div className="fact-actions"><button type="button" onClick={() => decideFact(fact.fact_id, 'confirm')} disabled={pending}>Confirm</button><button type="button" onClick={() => decideFact(fact.fact_id, 'reject')} disabled={pending}>Reject</button></div>}</li>)}</ul>}</details>
      <details className="scenario-card"><summary>Compare and confirm a planning action</summary><p>These are conditional cash-flow actions, not named-product recommendations or guaranteed outcomes.</p><form className="fact-form" onSubmit={compareAction}><label>Action<select value={planAction.action_type} onChange={event => setPlanAction(current => ({ ...current, action_type: event.target.value as PlanningActionInput['action_type'] }))}><option value="increase_monthly_savings">Increase monthly savings</option><option value="reduce_monthly_expenses">Reduce monthly expenses</option><option value="increase_debt_payment">Increase debt payment</option></select></label><label>Monthly amount (₹)<input type="number" min="0.01" step="0.01" required value={planAction.monthly_amount} onChange={event => setPlanAction(current => ({ ...current, monthly_amount: event.target.value }))}/></label><label>Feasibility (0–1)<input type="number" min="0" max="1" step="0.1" value={planAction.feasibility} onChange={event => setPlanAction(current => ({ ...current, feasibility: event.target.value }))}/></label><label>Your priority (0–1)<input type="number" min="0" max="1" step="0.1" value={planAction.user_priority} onChange={event => setPlanAction(current => ({ ...current, user_priority: event.target.value }))}/></label><Button disabled={pending}>Calculate impact</Button></form>{rankedActions.map(action => <div className="evidence" key={action.action_type}><strong>{action.action_type.replace(/_/g, ' ')}</strong><pre>{JSON.stringify(action.impact, null, 2)}</pre><p>{action.rationale}</p></div>)}{rankedActions.length > 0 && <><label className="scenario-confirm"><input type="checkbox" checked={planConfirmed} onChange={event => setPlanConfirmed(event.target.checked)}/> I confirm this action should be added to my plan.</label><Button type="button" disabled={!planConfirmed || pending} onClick={savePlan}>Create confirmed plan</Button></>}</details>
      <section className="quick-prompts" aria-label="Planning questions"><button type="button" onClick={() => setDraft('Show my debt and EMI metrics')}>Debt metrics</button><button type="button" onClick={() => setDraft('Show my 12-month cash flow forecast')}>Cash-flow forecast</button><button type="button" onClick={() => setDraft('Show my goal progress')}>Goal progress</button></section>
      <section className="conversation" aria-live="polite">
        {messages.map(message => <article key={message.message_id} className={`message ${message.role}`}><span className="message-role">{message.role === 'assistant' ? 'Private CFO' : 'You'}</span><p>{message.content}</p>{message.blocks.map((block, index) => <Evidence key={`${message.message_id}-${index}`} block={block}/>)}</article>)}
        {pending && <article className="message assistant"><span className="message-role">Private CFO</span><p>Reviewing your verified financial context…</p></article>}
      </section>
      {error && <div className="agent-error" role="alert">{error}{retryableMessage && !pending && <button type="button" className="retry-button" onClick={retryMessage}>Retry request</button>}</div>}
      {statusMessage && <div className="agent-success" role="status">{statusMessage}</div>}
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
      <section className="scenario-card" aria-labelledby="cloud-assistance-title"><h2 id="cloud-assistance-title">Cloud-assisted explanations</h2><p>Optional for this conversation. OpenAI receives only your agent intent, relevant verified facts, and deterministic evidence. It never receives original documents, extracted text, file paths, identifiers, unverified facts, or your raw message.</p>{cloudAssistance ? <><p><strong>Enabled for this conversation</strong> · {cloudConsent?.policy_bundle_version || 'cloud-explanation-v1'}</p><Button type="button" disabled={pending} onClick={disableCloudAssistance}>Revoke cloud assistance</Button></> : <Button type="button" disabled={pending} onClick={enableCloudAssistance}>Enable cloud assistance</Button>}<p><a href={cloudConsent?.retention_url || 'https://platform.openai.com/docs/models/default-usage-policies-by-endpoint'} target="_blank" rel="noreferrer">Read provider retention information</a></p></section>
      <form className="composer" onSubmit={submit}><label htmlFor="agent-message" className="sr-only">Ask about your finances</label><textarea id="agent-message" value={draft} onChange={event => setDraft(event.target.value)} placeholder="Ask about your finances…" maxLength={4000}/>{chatPending ? <Button type="button" onClick={() => requestController.current?.abort()}>Cancel</Button> : <Button className="send-button" aria-label="Send" disabled={pending}><Send/><span>Send</span></Button>}</form>
      <footer className="app-disclaimer"><ShieldCheck/> Planning guidance, not investment, tax, or insurance advice.</footer>
      </main>
    </div>
  );
};

export default AgentPage;
