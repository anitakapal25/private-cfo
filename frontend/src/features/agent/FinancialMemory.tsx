import React, { useEffect, useMemo, useState } from 'react';
import Button from '@/components/ui/Button';
import { ArrowRight, Calculator, CircleAlert, Clock3, Database, Lightbulb, ShieldCheck } from 'lucide-react';
import { createFinancialFactBatch, decideFinancialFact, decideFinancialFactBatch, getFinancialMemoryMonthlySummary, type FinancialFact, type FinancialFactInput, type FinancialMemoryMonthlySummary } from './api';
import type { SessionDocument } from './desktop';
import MemoryValueCard from './memory/MemoryValueCard';
import { allMemoryFields, coreMemoryFields, formatMoney, formatPeriod, memoryGroups, periodFor, type FieldDefinition } from './memory/model';

function localDateParts() {
  const now = new Date();
  return { year: String(now.getFullYear()), month: String(now.getMonth() + 1).padStart(2, '0'), day: String(now.getDate()).padStart(2, '0') };
}
function today() { const value = localDateParts(); return `${value.year}-${value.month}-${value.day}`; }
function currentMonth() { const value = localDateParts(); return `${value.year}-${value.month}`; }

interface FinancialMemoryProps {
  token: string;
  facts: FinancialFact[];
  documents: SessionDocument[];
  initialField?: string;
  onFactsChanged: () => Promise<void>;
  onAsk: (prompt: string) => void;
  onOpenDocuments: () => void;
}

const FinancialMemory: React.FC<FinancialMemoryProps> = ({ token, facts, documents, initialField, onFactsChanged, onAsk, onOpenDocuments }) => {
  const [month, setMonth] = useState(currentMonth());
  const [asOfDate, setAsOfDate] = useState(today());
  const [edits, setEdits] = useState<Record<string, string>>({});
  const [editing, setEditing] = useState<Set<string>>(() => initialField ? new Set([initialField]) : new Set());
  const [reviewing, setReviewing] = useState(false);
  const [confirmed, setConfirmed] = useState(false);
  const [pending, setPending] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [monthlySummary, setMonthlySummary] = useState<FinancialMemoryMonthlySummary>();
  const [monthlySummaryUnavailable, setMonthlySummaryUnavailable] = useState(false);

  const histories = useMemo(() => Object.fromEntries(allMemoryFields.map(field => [field.type, facts
    .filter(fact => fact.fact_type === field.type)
    .sort((a, b) => periodFor(b, field).localeCompare(periodFor(a, field)) || b.observed_at.localeCompare(a.observed_at))])), [facts]);

  const currentFor = (field: FieldDefinition) => (histories[field.type] as FinancialFact[]).find(fact =>
    fact.verification_status === 'verified' && (field.periodKind === 'monthly' ? periodFor(fact, field) === `${month}-01` : periodFor(fact, field) <= asOfDate));
  const pendingFor = (field: FieldDefinition) => (histories[field.type] as FinancialFact[]).find(fact =>
    (fact.verification_status === 'unverified' || fact.verification_status === 'conflict') && (field.periodKind === 'monthly' ? periodFor(fact, field) === `${month}-01` : periodFor(fact, field) <= asOfDate));
  const changedFields = allMemoryFields.filter(field => edits[field.type]?.trim() !== undefined && edits[field.type]?.trim() !== '');
  const completed = coreMemoryFields.filter(field => currentFor(field)).length;
  const confirmedRecords = facts.filter(fact => fact.verification_status === 'verified').length;
  const reviewCount = facts.filter(fact => fact.verification_status === 'unverified' || fact.verification_status === 'conflict').length;
  const missingCore = coreMemoryFields.filter(field => !currentFor(field) && !pendingFor(field));

  useEffect(() => {
    let current = true;
    getFinancialMemoryMonthlySummary(token, month)
      .then(result => { if (current) { setMonthlySummary(result); setMonthlySummaryUnavailable(false); } })
      .catch(() => { if (current) setMonthlySummaryUnavailable(true); });
    return () => { current = false; };
  }, [token, month, facts]);

  useEffect(() => {
    if (!initialField || !allMemoryFields.some(field => field.type === initialField)) return;
    requestAnimationFrame(() => document.querySelector(`#memory-card-${initialField}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' }));
  }, [initialField]);

  const startEdit = (type: string) => setEditing(current => new Set(current).add(type));
  const cancelEdit = (type: string) => {
    setEditing(current => { const next = new Set(current); next.delete(type); return next; });
    setEdits(current => { const next = { ...current }; delete next[type]; return next; });
  };
  const discardChanges = () => { setEdits({}); setEditing(new Set()); setReviewing(false); setConfirmed(false); };

  const saveChanges = async () => {
    if (!confirmed || pending || !changedFields.length) return;
    setPending(true); setError(''); setMessage('');
    const observedAt = new Date().toISOString();
    const inputs: FinancialFactInput[] = changedFields.map(field => ({
      fact_type: field.type, value: edits[field.type], unit: 'INR', source_type: 'user_statement', observed_at: observedAt,
      period_start: field.periodKind === 'monthly' ? `${month}-01` : asOfDate,
    }));
    try {
      const candidates = await createFinancialFactBatch(token, inputs);
      await decideFinancialFactBatch(token, candidates.map(fact => fact.fact_id), 'confirm');
      discardChanges();
      setMessage(`${candidates.length} ${candidates.length === 1 ? 'value was' : 'values were'} confirmed and added to Financial Memory.`);
      await onFactsChanged();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'The financial values could not be confirmed.');
      await onFactsChanged();
    } finally { setPending(false); }
  };

  const decideExisting = async (factId: string, decision: 'confirm' | 'reject') => {
    setPending(true); setError('');
    try {
      await decideFinancialFact(token, factId, decision);
      setMessage(decision === 'confirm' ? 'The value is now confirmed in Financial Memory.' : 'The value was not added to Financial Memory.');
      await onFactsChanged();
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'The decision could not be saved.'); }
    finally { setPending(false); }
  };

  const addFirstMissing = () => {
    const field = missingCore[0];
    if (!field) return;
    startEdit(field.type);
    requestAnimationFrame(() => document.querySelector(`#memory-card-${field.type}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' }));
  };

  return <section className="financial-memory" aria-labelledby="financial-memory-title">
    <header className="memory-heading"><div><p className="eyebrow">FINANCIAL MEMORY</p><h2 id="financial-memory-title">What Artha knows about you</h2><p>Only information you’ve confirmed is used to give personalized insights. Artha never fills financial gaps with assumptions.</p></div><span className="memory-security"><ShieldCheck/> Only confirmed values are used</span></header>
    {message && <div className="agent-success" role="status">{message}</div>}
    {error && <div className="agent-error" role="alert">{error}</div>}

    {!reviewing ? <>
      <section className="memory-summary" aria-label="Financial Memory summary"><div><strong>{completed} / {coreMemoryFields.length}</strong><span>Key areas completed</span></div><div><strong>{confirmedRecords}</strong><span>Confirmed values</span></div><div className={reviewCount ? 'needs-review' : ''}><strong>{reviewCount}</strong><span>Need review</span></div></section>

      {memoryGroups.map(group => {
        if (group.id === 'documents' && !group.fields.some(field => (histories[field.type] as FinancialFact[]).length)) return null;
        const isMonthly = group.id === 'monthly';
        const summaryLoading = isMonthly && !monthlySummaryUnavailable && monthlySummary?.month !== month;
        return <section className={`memory-section memory-section-${group.id}`} key={group.id} aria-labelledby={`memory-${group.id}-title`}><header className="memory-section-heading"><div><h3 id={`memory-${group.id}-title`}>{isMonthly ? `${group.title} · ${formatPeriod(`${month}-01`, 'monthly')}` : group.title}</h3><p>{group.description}</p></div>{group.id === 'monthly' ? <label>Choose month<input type="month" max={currentMonth()} value={month} onChange={event => setMonth(event.target.value)} /></label> : group.id === 'position' ? <label>Position on<input type="date" max={today()} value={asOfDate} onChange={event => setAsOfDate(event.target.value)} /></label> : null}</header><div className="memory-value-grid">{group.fields.map(field => <MemoryValueCard key={field.type} field={field} current={currentFor(field)} pendingFact={pendingFor(field)} history={histories[field.type] as FinancialFact[]} documents={documents} editing={editing.has(field.type)} editValue={edits[field.type] || ''} disabled={pending} requested={field.type === initialField} onStartEdit={() => startEdit(field.type)} onCancelEdit={() => cancelEdit(field.type)} onEditValue={value => setEdits(current => ({ ...current, [field.type]: value }))} onPendingDecision={(factId, decision) => void decideExisting(factId, decision)} onOpenDocuments={onOpenDocuments}/>)}</div>{isMonthly && <article className="money-left-card"><span className="calculated-icon"><Calculator/></span><div><span>Money left this month</span>{summaryLoading ? <strong>Calculating…</strong> : monthlySummary?.status === 'complete' && monthlySummary.money_left && !monthlySummaryUnavailable ? <strong>{formatMoney(monthlySummary.money_left.amount)}</strong> : <strong aria-label="Not enough confirmed information">—</strong>}<p>{monthlySummaryUnavailable ? 'Monthly calculation is temporarily unavailable. Your confirmed values are unchanged.' : monthlySummary?.status === 'complete' ? 'Income minus expenses and loan payments, using confirmed values for this month.' : `Will be calculated after you add ${monthlySummary?.missing.map(type => allMemoryFields.find(field => field.type === type)?.label.toLowerCase()).join(', ') || 'the required monthly values'}.`}</p></div>{monthlySummary?.status === 'complete' && !monthlySummaryUnavailable && <details><summary>Calculation evidence</summary><small>Calculation ID: {monthlySummary.calculation_id}</small><small>Version: {monthlySummary.version}</small><small>Calculated: {monthlySummary.timestamp ? new Date(monthlySummary.timestamp).toLocaleString('en-IN') : ''}</small></details>}</article>}</section>;
      })}

      <aside className="memory-missing-cta"><Lightbulb/><div><strong>{missingCore.length ? 'Add more information' : 'Your key areas are complete'}</strong><p>{missingCore.length ? 'Share only what you’re comfortable with. More confirmed information can help Artha give more relevant planning context.' : 'You can update any value when your situation changes.'}</p></div>{missingCore.length > 0 && <Button type="button" variant="secondary" onClick={addFirstMissing}>+ Add missing information</Button>}</aside>
      <aside className="memory-ask-cta"><Database/><div><h3>Ask Artha about your finances</h3><p>Use your confirmed Financial Memory to ask questions in everyday language.</p><div className="memory-prompt-chips"><button type="button" onClick={() => onAsk('Show my monthly cash flow')}>Where does my money go?</button><button type="button" onClick={() => onAsk('Show my goal progress')}>Am I on track for my goal?</button><button type="button" onClick={() => onAsk('Compare my insurance cover with a target I choose')}>Help me understand my insurance</button></div></div><Button type="button" onClick={() => onAsk('Help me understand my confirmed financial information.')}>Go to Ask Artha <ArrowRight/></Button></aside>

      {changedFields.length > 0 && <aside className="memory-pending-bar" role="status"><div><CircleAlert/><span><strong>{changedFields.length} {changedFields.length === 1 ? 'change' : 'changes'} waiting for confirmation</strong><small>Artha cannot use these values yet.</small></span></div><div><button type="button" onClick={discardChanges}>Discard</button><Button type="button" onClick={() => { setConfirmed(false); setReviewing(true); }}>Review {changedFields.length} {changedFields.length === 1 ? 'change' : 'changes'} <ArrowRight/></Button></div></aside>}
    </> : <section className="memory-review" aria-labelledby="memory-review-title"><p className="eyebrow">REVIEW BEFORE CONFIRMING</p><h3 id="memory-review-title">Review changes</h3><p>These values will become part of your confirmed Financial Memory. Existing values are kept in history.</p><ul>{changedFields.map(field => { const current = currentFor(field); const period = field.periodKind === 'monthly' ? `${month}-01` : asOfDate; return <li key={field.type}><span><strong>{field.label}</strong><small>{formatPeriod(period, field.periodKind)}</small></span><span className="review-value-change"><small>{current ? formatMoney(current.value) : 'Not added'}</small><ArrowRight/><strong>{formatMoney(edits[field.type])}</strong></span></li>; })}</ul><label className="scenario-confirm"><input type="checkbox" checked={confirmed} onChange={event => setConfirmed(event.target.checked)}/> I confirm these values and their dates are mine and correct.</label><div className="memory-review-actions"><Button type="button" variant="secondary" disabled={pending} onClick={() => setReviewing(false)}>Go back</Button><Button type="button" disabled={!confirmed || pending} onClick={() => void saveChanges()}>{pending ? 'Confirming…' : 'Confirm changes'}</Button></div></section>}
    <footer className="memory-note"><Clock3/> Replaced values remain in history and are never silently overwritten.</footer>
  </section>;
};

export default FinancialMemory;
