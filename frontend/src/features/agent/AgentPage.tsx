import React, { FormEvent, useEffect, useRef, useState } from 'react';
import Button from '@/components/ui/Button';
import InfoTooltip from '@/components/ui/InfoTooltip';
import Toast from '@/components/ui/Toast';
import { Bell, Check, CircleUserRound, Database, FolderLock, Home, LockKeyhole, LogOut, Menu, MessageSquareText, Send, ShieldCheck, Sparkles, Target } from 'lucide-react';
import { ApiError, beginMfaEnrollment, confirmMfaEnrollment, confirmPasswordReset, createConversation, createFinancialFact, decideFinancialFact, decideProactiveReview, listFinancialFacts, listProactiveReviews, login, logout, register, requestPasswordReset, runProactiveReviews, sendMessage, verifyEmail, verifyMfa, type AgentBlock, type AgentMessage, type FinancialFact, type FreedomScenario, type ProactiveReview } from './api';
import { discardLocalDocumentSelection, getLocalDocumentCapabilities, isDesktopHost, processLocalDocument, selectLocalDocument, type LocalDocumentCandidate, type LocalDocumentCapabilities, type LocalDocumentSelection, type SessionDocument } from './desktop';
import Dashboard from './Dashboard';
import FinancialMemory from './FinancialMemory';
import DocumentsPage from './documents/DocumentsPage';
import PlansPage from './plans/PlansPage';

const emptyScenario = {
  current_age: '', target_age: '', current_monthly_lifestyle_expenses: '',
  current_investable_corpus: '', monthly_contribution: '',
};

const scenarioFields = [
  { key: 'current_age', label: 'Your current age', explanation: 'Your age today sets the starting point for the projection.', example: 'If you are 34 years old, enter 34.' },
  { key: 'target_age', label: 'Age you want to plan for', explanation: 'The age when you want Artha to compare your projected savings with the estimated amount needed.', example: 'If you want to plan for age 50, enter 50.' },
  { key: 'current_monthly_lifestyle_expenses', label: 'Monthly living expenses (₹)', explanation: 'Your regular monthly spending today, excluding amounts you invest or save.', example: 'Rent, groceries, utilities and travel total ₹45,000.' },
  { key: 'current_investable_corpus', label: 'Savings and investments for this goal (₹)', explanation: 'Money already set aside that you want included in this financial-freedom projection.', example: 'Investments allocated to this goal total ₹8,50,000.' },
  { key: 'monthly_contribution', label: 'Amount you plan to add each month (₹)', explanation: 'The amount you expect to contribute toward this goal every month.', example: 'You plan to invest ₹15,000 each month.' },
] as const;

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
}

type WorkspaceSection = 'overview' | 'ask' | 'memory' | 'plans' | 'documents' | 'reviews';

const friendlyFieldLabels: Record<string, string> = {
  monthly_income: 'Monthly income', monthly_expenses: 'Monthly expenses', total_assets: 'Total assets',
  total_liabilities: 'Total debt', liquid_assets: 'Money available quickly', monthly_debt_payments: 'Monthly loan payments',
  debt_outstanding: 'Total loan balance', goal_current: 'Amount saved toward your goal', goal_target: 'Your goal amount',
  insurance_coverage: 'Current insurance cover', annual_gross_income: 'Annual gross income from Form 16',
  bank_account_balance: 'Bank account closing balance', epf_balance: 'EPF closing balance',
};

function Evidence({ block }: { block: AgentBlock }) {
  if (block.type === 'missing_data') {
    return <div className="evidence missing-information"><strong>I need a little more information</strong><p>Please provide or confirm the following so I can answer without guessing:</p><ul>{block.fields?.map(field => <li key={field}>{friendlyFieldLabels[field] || field}</li>)}</ul></div>;
  }
  if (block.type === 'warning') return <div className="evidence warning">This request is outside the agent’s planning boundary.</div>;
  if (block.type === 'cloud_explanation') return <div className="evidence"><strong>Cloud-assisted explanation · {block.provider}</strong><p>{block.content}</p><small>Exact figures remain in the deterministic evidence card.</small></div>;
  const rates = block.assumptions?.rates as Record<string, Record<string, string>> | undefined;
  const rateLabels: Record<string, { label: string; explanation: string }> = {
    annual_inflation_rate: { label: 'Inflation', explanation: 'Estimates how living costs may increase.' },
    annual_return_rate: { label: 'Expected return', explanation: 'A product-neutral planning assumption, not a guaranteed investment return.' },
    withdrawal_rate: { label: 'Withdrawal rate', explanation: 'Estimates annual retirement withdrawals; it is not a market price.' },
  };
  return (
    <details className="evidence">
      <summary>Calculation evidence · {block.version}</summary>
      <pre>{JSON.stringify(block.result, null, 2)}</pre>
      <p>Calculation ID: {block.calculation_id}</p>
      {rates && Object.keys(rates).length > 0 && <details className="assumption-details"><summary>Assumptions used</summary><ul>{Object.entries(rates).map(([key, rate]) => <li key={key}><strong>{rateLabels[key]?.label || key}: {(Number(rate.value) * 100).toFixed(1)}%</strong><span>{rateLabels[key]?.explanation}</span><small>{rate.methodology}</small><small>Effective {rate.effective_from} · reviewed {rate.reviewed_at} · review by {rate.review_by}</small><a href={rate.source_url} target="_blank" rel="noreferrer">View source</a></li>)}</ul></details>}
      {block.limitations?.map(item => <p key={item}>{item}</p>)}
    </details>
  );
}

const AgentPage: React.FC = () => {
  const [token, setToken] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [authMode, setAuthMode] = useState<'sign-in' | 'register' | 'reset-request' | 'reset-confirm' | 'mfa' | 'mfa-enroll'>(() => window.location.pathname === '/reset-password' && Boolean(new URLSearchParams(window.location.search).get('token')) ? 'reset-confirm' : 'sign-in');
  const [authNotice, setAuthNotice] = useState('');
  const [mfaChallengeToken, setMfaChallengeToken] = useState(() => window.location.pathname === '/reset-password' ? new URLSearchParams(window.location.search).get('token') || '' : '');
  const [mfaCode, setMfaCode] = useState('');
  const [mfaSecret, setMfaSecret] = useState('');
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
  const [factType, setFactType] = useState<string>();
  const [reviews, setReviews] = useState<ProactiveReview[]>([]);
  const [documentType, setDocumentType] = useState('salary_slip');
  const [localSelection, setLocalSelection] = useState<LocalDocumentSelection>();
  const [sessionDocuments, setSessionDocuments] = useState<SessionDocument[]>([]);
  const desktopHost = isDesktopHost();
  const [localCapabilities, setLocalCapabilities] = useState<LocalDocumentCapabilities>();
  const [chatPending, setChatPending] = useState(false);
  const [retryableMessage, setRetryableMessage] = useState<RetryableMessage>();
  const [activeSection, setActiveSection] = useState<WorkspaceSection>('overview');
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [coverageRequested, setCoverageRequested] = useState(false);
  const [followUpQuestion, setFollowUpQuestion] = useState('');
  const requestController = useRef<AbortController>();

  useEffect(() => {
    if (!desktopHost) return;
    getLocalDocumentCapabilities()
      .then(setLocalCapabilities)
      .catch(() => setLocalCapabilities({ available: false, platform: 'unknown', scanner_available: false, sandbox_available: false, pdf_text_available: false, limitations: ['Local document security checks are unavailable'] }));
  }, [desktopHost]);

  useEffect(() => {
    if (!statusMessage) return;
    const timeout = window.setTimeout(() => setStatusMessage(''), 6000);
    return () => window.clearTimeout(timeout);
  }, [statusMessage]);

  useEffect(() => {
    const url = new URL(window.location.href);
    const linkToken = url.searchParams.get('token');
    if (!linkToken) return;
    if (url.pathname === '/verify-email') {
      void verifyEmail(linkToken)
        .then(result => { setAuthNotice(result.detail); setAuthMode('sign-in'); window.history.replaceState({}, '', '/'); })
        .catch(reason => setError(reason instanceof Error ? reason.message : 'The verification link could not be used.'));
    }
  }, []);

  const discardLocalSelection = async () => {
    if (localSelection) {
      try { await discardLocalDocumentSelection(localSelection.selection_token); }
      catch { /* An expired token contains no remaining usable selection. */ }
    }
    setLocalSelection(undefined);
  };

  const clearLocalDocumentState = async () => {
    await discardLocalSelection();
  };

  const reportError = (reason: unknown, fallback: string) => {
    if (reason instanceof ApiError && reason.status === 401) {
      void clearLocalDocumentState();
      setSessionDocuments([]);
      setToken(''); setConversationId(undefined); setMessages([starter]);
    }
    setError(reason instanceof Error ? reason.message : fallback);
  };

  const finishAuthentication = async (accessToken: string) => {
    const [authenticatedFacts, authenticatedReviews] = await Promise.all([
      listFinancialFacts(accessToken),
      listProactiveReviews(accessToken),
    ]);
    setFacts(authenticatedFacts);
    setReviews(authenticatedReviews);
    setToken(accessToken);
    setPassword(''); setMfaCode(''); setMfaSecret(''); setMfaChallengeToken('');
  };

  const connect = async (event: FormEvent) => {
    event.preventDefault();
    if (!email.trim() || !password) return;
    setPending(true); setError('');
    try {
      const result = await login(email.trim(), password);
      if (result.state === 'authenticated') await finishAuthentication(result.accessToken);
      else if (result.state === 'email_verification_required') setAuthNotice('Check your email and verify your account before signing in.');
      else {
        setMfaChallengeToken(result.challengeToken);
        if (result.enrollmentRequired) {
          const enrollment = await beginMfaEnrollment(result.challengeToken);
          setMfaSecret(enrollment.secret); setAuthMode('mfa-enroll');
        } else setAuthMode('mfa');
      }
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Sign-in failed.');
    } finally { setPending(false); }
  };

  const createAccount = async (event: FormEvent) => {
    event.preventDefault(); setPending(true); setError(''); setAuthNotice('');
    try {
      const result = await register(email.trim(), password, fullName.trim());
      setAuthNotice(result.detail); setPassword(''); setAuthMode('sign-in');
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Registration could not be completed.'); }
    finally { setPending(false); }
  };

  const startPasswordReset = async (event: FormEvent) => {
    event.preventDefault(); setPending(true); setError(''); setAuthNotice('');
    try { setAuthNotice((await requestPasswordReset(email.trim())).detail); setAuthMode('sign-in'); }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Password-reset request could not be completed.'); }
    finally { setPending(false); }
  };

  const completePasswordReset = async (event: FormEvent) => {
    event.preventDefault(); setPending(true); setError('');
    try { setAuthNotice((await confirmPasswordReset(mfaChallengeToken, password)).detail); setPassword(''); setAuthMode('sign-in'); window.history.replaceState({}, '', '/'); }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Password reset could not be completed.'); }
    finally { setPending(false); }
  };

  const completeMfa = async (event: FormEvent) => {
    event.preventDefault(); setPending(true); setError('');
    try {
      const result = authMode === 'mfa-enroll'
        ? await confirmMfaEnrollment(mfaChallengeToken, mfaCode)
        : await verifyMfa(mfaChallengeToken, mfaCode);
      if (result.state === 'authenticated') await finishAuthentication(result.accessToken);
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Authenticator verification could not be completed.'); }
    finally { setPending(false); }
  };

  const signOut = async () => {
    try { await logout(token); }
    catch { /* The server may already have revoked the session. */ }
    await clearLocalDocumentState();
    setSessionDocuments([]);
    setToken(''); setConversationId(undefined); setMessages([starter]);
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
      const candidates = result.candidates.map(candidate => ({ ...candidate, status: 'candidate' as const }));
      setSessionDocuments(current => [{
        document_id: crypto.randomUUID(), display_name: localSelection.display_name,
        file_size_bytes: localSelection.file_size_bytes, document_type: documentType,
        processed_at: new Date().toISOString(), candidates,
      }, ...current]);
      setLocalSelection(undefined);
      setStatusMessage(result.candidates.length
        ? 'Local extraction completed. Review every candidate before confirmation.'
        : 'The document was processed locally, but no supported financial field was found. No data was saved.');
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'The local document could not be processed.'); }
    finally { setPending(false); }
  };

  const decideLocalCandidate = async (candidate: LocalDocumentCandidate, decision: 'confirm' | 'reject') => {
    if (decision === 'reject') {
      setSessionDocuments(current => current.map(document => ({ ...document, candidates: document.candidates.map(item => item.evidence_id === candidate.evidence_id ? { ...item, status: 'rejected' } : item) })));
      setStatusMessage('The extracted value was not added to Financial Memory.');
      return;
    }
    setPending(true); setError(''); setStatusMessage('');
    try {
      const fact = await createFinancialFact(token, candidate.fact_type, candidate.value, {
        sourceType: 'local_document_confirmation', sourceId: candidate.evidence_id,
        confidence: candidate.confidence, periodStart: candidate.period_start,
      });
      await decideFinancialFact(token, fact.fact_id, 'confirm');
      setSessionDocuments(current => current.map(document => ({ ...document, candidates: document.candidates.map(item => item.evidence_id === candidate.evidence_id ? { ...item, status: 'confirmed' } : item) })));
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

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    const content = draft.trim();
    if (!content || pending) return;
    setDraft(''); setError(''); setPending(true); setChatPending(true);
    setMessages(current => [...current, { message_id: crypto.randomUUID(), role: 'user', content, blocks: [], created_at: new Date().toISOString() }]);
    try {
      const activeConversation = conversationId ?? await createConversation(token);
      setConversationId(activeConversation);
      const scenarioComplete = Object.values(scenario).every(value => value.trim() !== '');
      const freedomScenario: FreedomScenario | undefined = showScenario && scenarioConfirmed && scenarioComplete ? {
        current_age: Number(scenario.current_age), target_age: Number(scenario.target_age),
        current_monthly_lifestyle_expenses: scenario.current_monthly_lifestyle_expenses,
        current_investable_corpus: scenario.current_investable_corpus,
        monthly_contribution: scenario.monthly_contribution,
      } : undefined;
      const selectedCoverageTarget = coverageRequested ? coverageTarget || undefined : undefined;
      const retryable = { conversationId: activeConversation, clientRequestId: crypto.randomUUID(), content, scenario: freedomScenario, coverageTarget: selectedCoverageTarget };
      setRetryableMessage(retryable);
      const controller = new AbortController();
      requestController.current = controller;
      const response = await sendMessage(token, activeConversation, content, retryable.clientRequestId, freedomScenario, selectedCoverageTarget, controller.signal);
      setMessages(current => [...current, response]);
      const missingFields = response.blocks.filter(block => block.type === 'missing_data').flatMap(block => block.fields || []);
      const needsScenario = missingFields.includes('current age');
      const needsCoverage = missingFields.includes('explicit user-selected coverage target');
      setShowScenario(needsScenario);
      setCoverageRequested(needsCoverage);
      if (needsScenario || needsCoverage) setFollowUpQuestion(content);
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
        retryableMessage.coverageTarget, controller.signal,
      );
      setMessages(current => [...current, response]);
      const missingFields = response.blocks.filter(block => block.type === 'missing_data').flatMap(block => block.fields || []);
      const needsScenario = missingFields.includes('current age');
      const needsCoverage = missingFields.includes('explicit user-selected coverage target');
      setShowScenario(needsScenario);
      setCoverageRequested(needsCoverage);
      if (needsScenario || needsCoverage) setFollowUpQuestion(retryableMessage.content);
      setRetryableMessage(undefined);
    } catch (reason) {
      if (reason instanceof DOMException && reason.name === 'AbortError') {
        setError('Response cancelled. You can retry the same request again.');
      } else {
        reportError(reason, 'The retry could not complete.');
      }
    } finally { requestController.current = undefined; setPending(false); setChatPending(false); }
  };

  if (!token) {
    const isMfa = authMode === 'mfa' || authMode === 'mfa-enroll';
    return <main className="agent-shell auth-shell"><section className="agent-card auth-card"><div className="auth-brand"><ShieldCheck aria-hidden="true"/><span>Artha</span></div><p className="eyebrow">PRIVATE CFO</p><h1>{isMfa ? 'Secure your sign-in' : 'Your financial-freedom agent'}</h1><p>{isMfa ? 'Use a current code from your authenticator app. Codes are never stored in this browser.' : 'Sign in to access only your financial context, conversations, and deterministic calculations.'}</p>{error && <div className="agent-error" role="alert">{error}</div>}{authNotice && <div role="status">{authNotice}</div>}{authMode === 'register' && <form onSubmit={createAccount}><label htmlFor="full-name">Name (optional)</label><input id="full-name" value={fullName} onChange={event => setFullName(event.target.value)} autoComplete="name"/><label htmlFor="email">Email</label><input id="email" type="email" value={email} onChange={event => setEmail(event.target.value)} autoComplete="email" required/><label htmlFor="password">Password</label><input id="password" type="password" value={password} onChange={event => setPassword(event.target.value)} autoComplete="new-password" minLength={12} required/><small>Use 12+ characters with upper-case, lower-case, and a number.</small><Button>{pending ? 'Creating account…' : 'Create account'}</Button><button type="button" className="inline-link" onClick={() => setAuthMode('sign-in')}>Back to sign in</button></form>}{authMode === 'reset-confirm' && <form onSubmit={completePasswordReset}><label htmlFor="password">New password</label><input id="password" type="password" value={password} onChange={event => setPassword(event.target.value)} autoComplete="new-password" minLength={12} required/><small>Use 12+ characters with upper-case, lower-case, and a number.</small><Button>{pending ? 'Resetting password…' : 'Reset password'}</Button></form>}{authMode === 'mfa-enroll' && <form onSubmit={completeMfa}><p>In your authenticator app, add a new time-based code and enter this setup key:</p><code>{mfaSecret}</code><label htmlFor="mfa-code">Authenticator code</label><input id="mfa-code" inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]{6}" maxLength={6} value={mfaCode} onChange={event => setMfaCode(event.target.value.replace(/\D/g, ''))} required/><Button>{pending ? 'Verifying…' : 'Enable MFA and sign in'}</Button></form>}{authMode === 'mfa' && <form onSubmit={completeMfa}><label htmlFor="mfa-code">Authenticator code</label><input id="mfa-code" inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]{6}" maxLength={6} value={mfaCode} onChange={event => setMfaCode(event.target.value.replace(/\D/g, ''))} required/><Button>{pending ? 'Verifying…' : 'Verify and sign in'}</Button></form>}{authMode === 'reset-request' && <form onSubmit={startPasswordReset}><label htmlFor="email">Email</label><input id="email" type="email" value={email} onChange={event => setEmail(event.target.value)} autoComplete="email" required/><Button>{pending ? 'Sending…' : 'Send reset link'}</Button><button type="button" className="inline-link" onClick={() => setAuthMode('sign-in')}>Back to sign in</button></form>}{authMode === 'sign-in' && <><form onSubmit={connect}><label htmlFor="email">Email</label><input id="email" type="email" value={email} onChange={event => setEmail(event.target.value)} autoComplete="username" required/><label htmlFor="password">Password</label><input id="password" type="password" value={password} onChange={event => setPassword(event.target.value)} autoComplete="current-password" required/><Button>{pending ? 'Signing in…' : 'Sign in securely'}</Button></form><div className="fact-actions"><button type="button" className="inline-link" onClick={() => setAuthMode('register')}>Create an account</button><button type="button" className="inline-link" onClick={() => setAuthMode('reset-request')}>Forgot password?</button></div></>}<p className="auth-privacy"><LockKeyhole size={15}/> Your data stays bound to your signed-in account.</p></section></main>;
  }

  const verifiedFacts = facts.filter(fact => fact.verification_status === 'verified');
  const openReviews = reviews.filter(review => review.status === 'open');
  const navItems: Array<{ id: WorkspaceSection; label: string; icon: React.ReactNode }> = [
    { id: 'overview', label: 'Overview', icon: <Home/> }, { id: 'ask', label: 'Ask Artha', icon: <MessageSquareText/> },
    { id: 'memory', label: 'Financial memory', icon: <Database/> }, { id: 'plans', label: 'My Plan', icon: <Target/> },
    { id: 'documents', label: 'Documents', icon: <FolderLock/> }, { id: 'reviews', label: 'Reviews', icon: <Sparkles/> },
  ];
  const selectSection = (section: WorkspaceSection) => { setActiveSection(section); setMobileNavOpen(false); setError(''); setStatusMessage(''); };
  const openFactEntry = (type: string) => { setFactType(type); selectSection('memory'); };
  const openAsk = (prompt?: string) => { if (prompt) setDraft(prompt); selectSection('ask'); };
  const continueFollowUp = () => {
    setDraft(followUpQuestion);
    requestAnimationFrame(() => document.querySelector<HTMLTextAreaElement>('#agent-message')?.focus());
  };

  return (
    <div className="app-shell">
      <a className="skip-link" href="#workspace-content">Skip to main content</a>
      <aside className={`app-sidebar ${mobileNavOpen ? 'open' : ''}`}><div><div className="app-logo"><ShieldCheck/><span>Artha</span></div><nav aria-label="Primary navigation">{navItems.map(item => <button type="button" key={item.id} className={activeSection === item.id ? 'active' : ''} onClick={() => { if (item.id === 'memory') setFactType(undefined); selectSection(item.id); }}>{item.icon}<span>{item.label}</span>{item.id === 'reviews' && openReviews.length > 0 && <b>{openReviews.length}</b>}</button>)}</nav></div><div className="sidebar-footer"><ShieldCheck/><span>Private by design</span></div></aside>
      <header className="app-header"><button type="button" className="menu-button" aria-label="Toggle navigation" aria-expanded={mobileNavOpen} onClick={() => setMobileNavOpen(value => !value)}><Menu/></button><h1>Financial Freedom Agent</h1><div className="header-actions"><span className="data-chip"><Check/> Data verified</span><button type="button" className="icon-button" aria-label="Notifications"><Bell/></button><span className="avatar"><CircleUserRound/></span><button type="button" className="sign-out" onClick={() => { void signOut(); }}><LogOut/><span>Sign out</span></button></div></header>
      {(error || statusMessage) && <aside className="app-toast-region" aria-label="Notifications">
        {error && <Toast tone="error" message={error} onDismiss={() => setError('')} action={retryableMessage && !pending ? <button type="button" className="retry-button" onClick={retryMessage}>Retry request</button> : undefined}/>
        }
        {statusMessage && <Toast tone="success" message={statusMessage} onDismiss={() => setStatusMessage('')}/>
        }
      </aside>}
      <main id="workspace-content" className={`app-main section-${activeSection}`}>
      <section className="mobile-section-title"><p className="eyebrow">PRIVATE CFO</p><h2>{navItems.find(item => item.id === activeSection)?.label}</h2></section>
      {activeSection === 'overview' && <Dashboard verifiedFacts={verifiedFacts} openReviews={openReviews} documentReviewAvailable={Boolean(desktopHost && localCapabilities?.available)} onOpenFact={openFactEntry} onOpenDocuments={() => selectSection('documents')} onOpenReviews={() => selectSection('reviews')} onAsk={openAsk}/>
      }
      {activeSection === 'documents' && <DocumentsPage desktopHost={desktopHost} capabilities={localCapabilities} selection={localSelection} documentType={documentType} documents={sessionDocuments} facts={facts} pending={pending} onChoose={() => void chooseLocalDocument()} onDiscard={() => void discardLocalSelection()} onProcess={() => void processSelectedDocument()} onDocumentTypeChange={setDocumentType} onCandidateDecision={(candidate, decision) => void decideLocalCandidate(candidate, decision)} onAskArtha={openAsk}/>
      }
      {activeSection === 'reviews' && <><section className="boundary">Reviews are deterministic notifications. They never change your records or plan.</section><details className="scenario-card" open><summary>Proactive financial reviews ({reviews.filter(review => review.status === 'open').length} open)</summary><Button type="button" disabled={pending} onClick={refreshReviews}>Run review now</Button>{reviews.length === 0 ? <p>No review findings.</p> : <ul className="fact-list">{reviews.map(review => <li key={review.review_id}><span>{review.finding_type.replace(/_/g, ' ')}</span><small>{review.severity} · {review.status} · {review.rule_version}</small><details><summary>Evidence</summary><pre>{JSON.stringify(review.evidence, null, 2)}</pre></details>{review.status === 'open' && <div className="fact-actions"><button type="button" disabled={pending} onClick={() => decideReview(review.review_id, 'acknowledge')}>Acknowledge</button><button type="button" disabled={pending} onClick={() => decideReview(review.review_id, 'dismiss')}>Dismiss</button></div>}</li>)}</ul>}</details></>}
      {activeSection === 'memory' && <FinancialMemory token={token} facts={facts} documents={sessionDocuments} initialField={factType} onFactsChanged={async () => setFacts(await listFinancialFacts(token))} onAsk={openAsk} onOpenDocuments={() => selectSection('documents')}/>
      }
      {activeSection === 'plans' && <PlansPage token={token} conversationId={conversationId} onConversationCreated={setConversationId} onAsk={openAsk}/>
      }
      {activeSection === 'ask' && <><section className="boundary">Ask in your own words. Artha uses information you confirmed and will ask when something important is missing.</section><section className="quick-prompts" aria-label="Planning questions"><button type="button" onClick={() => setDraft('Show my debt and EMI metrics')}>Debt metrics</button><button type="button" onClick={() => setDraft('Show my 12-month cash flow forecast')}>Cash-flow forecast</button><button type="button" onClick={() => setDraft('Show my goal progress')}>Goal progress</button><button type="button" onClick={() => setDraft('Help me prepare a budgeting action for My Plan')}>Prepare an action</button></section>
      <section className="conversation" aria-live="polite">
        {messages.map(message => <article key={message.message_id} className={`message ${message.role}`}><span className="message-role">{message.role === 'assistant' ? 'Private CFO' : 'You'}</span><p>{message.content}</p>{message.blocks.map((block, index) => <Evidence key={`${message.message_id}-${index}`} block={block}/>)}</article>)}
        {pending && <article className="message assistant"><span className="message-role">Private CFO</span><p>Reviewing your verified financial context…</p></article>}
      </section>
      {showScenario && <section className="scenario-card chat-followup-card" aria-labelledby="scenario-title"><p className="eyebrow">ARTHA NEEDS THESE DETAILS</p><h2 id="scenario-title">Tell me about the future you want to plan for</h2><p>Provide only your personal details. Artha will use current reviewed planning assumptions for inflation, expected return, and withdrawals.</p><div className="scenario-grid">
        {scenarioFields.map(field => <label key={field.key}><span className="scenario-label">{field.label}<InfoTooltip term={field.label} explanation={field.explanation} example={field.example}/></span><input required type="number" step="any" value={scenario[field.key]} onChange={event => { setScenario(current => ({ ...current, [field.key]: event.target.value })); setScenarioConfirmed(false); }}/></label>)}
      </div><label className="scenario-confirm"><input type="checkbox" checked={scenarioConfirmed} onChange={event => setScenarioConfirmed(event.target.checked)}/> I confirm these personal values are correct for this projection.</label><Button type="button" disabled={!scenarioConfirmed || Object.values(scenario).some(value => value.trim() === '')} onClick={continueFollowUp}>Continue my question</Button></section>}
      {coverageRequested && <section className="scenario-card chat-followup-card" aria-labelledby="coverage-title"><p className="eyebrow">ARTHA NEEDS ONE DETAIL</p><h2 id="coverage-title">What insurance cover amount do you want to compare?</h2><p>Choose the comparison amount yourself. Artha will not recommend a policy or decide the amount for you.</p><label><span className="scenario-label">Amount to compare (₹)<InfoTooltip term="insurance comparison amount" explanation="The cover amount you want compared with your currently confirmed insurance cover." example="Compare your current cover with ₹1,00,00,000."/></span><input type="number" min="0" step="0.01" value={coverageTarget} onChange={event => setCoverageTarget(event.target.value)}/></label><Button type="button" disabled={!coverageTarget} onClick={continueFollowUp}>Continue my question</Button></section>}
      <form className="composer" onSubmit={submit}><label htmlFor="agent-message" className="sr-only">Ask about your finances</label><textarea id="agent-message" value={draft} onChange={event => setDraft(event.target.value)} placeholder="Ask about your finances…" maxLength={4000}/>{chatPending ? <Button type="button" onClick={() => requestController.current?.abort()}>Cancel</Button> : <Button className="send-button" aria-label="Send" disabled={pending}><Send/><span>Send</span></Button>}</form></>}
      <footer className="app-disclaimer"><ShieldCheck/> Planning guidance, not investment, tax, or insurance advice.</footer>
      </main>
    </div>
  );
};

export default AgentPage;
