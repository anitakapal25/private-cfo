import React, { FormEvent, useMemo, useState } from 'react';
import Button from '@/components/ui/Button';
import InfoTooltip from '@/components/ui/InfoTooltip';
import { Check, ChevronDown, Clock3, ShieldCheck } from 'lucide-react';
import { createFinancialFactBatch, decideFinancialFact, decideFinancialFactBatch, type FinancialFact, type FinancialFactInput } from './api';

type PeriodKind = 'monthly' | 'as_of';

interface FieldDefinition {
  type: string;
  label: string;
  explanation: string;
  example: string;
  periodKind: PeriodKind;
}

const groups: Array<{ title: string; description: string; fields: FieldDefinition[] }> = [
  { title: 'Monthly money', description: 'Enter what actually happened in the selected calendar month.', fields: [
    { type: 'monthly_income', label: 'Monthly income', explanation: 'Money you received during this month after deductions. Include salary and other income received.', example: '₹50,000 received in September 2026.', periodKind: 'monthly' },
    { type: 'monthly_expenses', label: 'Monthly expenses', explanation: 'Money you spent during this month, including bills, food, rent, travel, and other spending.', example: '₹30,000 spent in September 2026.', periodKind: 'monthly' },
    { type: 'monthly_debt_payments', label: 'Monthly loan payments', explanation: 'The total loan and EMI payments you made during this month.', example: '₹12,000 paid toward a home and vehicle loan.', periodKind: 'monthly' },
  ] },
  { title: 'What you own and owe', description: 'These are snapshots of your position on the selected date.', fields: [
    { type: 'total_assets', label: 'Total assets', explanation: 'The combined value of everything valuable you own on this date.', example: '₹8,00,000 across savings, investments, gold, and property.', periodKind: 'as_of' },
    { type: 'liquid_assets', label: 'Money available quickly', explanation: 'Money you could access quickly, such as cash and bank savings.', example: '₹75,000 in cash and savings accounts.', periodKind: 'as_of' },
    { type: 'total_liabilities', label: 'Total debt', explanation: 'All money you owe on this date, including loans and unpaid credit-card balances.', example: '₹4,00,000 still owed across all loans.', periodKind: 'as_of' },
    { type: 'debt_outstanding', label: 'Loan balance', explanation: 'The amount still unpaid on the loans you want Artha to analyse.', example: '₹2,50,000 remaining on a vehicle loan.', periodKind: 'as_of' },
  ] },
  { title: 'Goals and protection', description: 'Add current amounts as of the selected date.', fields: [
    { type: 'goal_current', label: 'Amount saved toward your goal', explanation: 'The amount already set aside for a financial goal.', example: '₹2,00,000 already saved for education.', periodKind: 'as_of' },
    { type: 'goal_target', label: 'Your goal amount', explanation: 'The total amount you chose for your goal. Artha does not choose this target for you.', example: 'A user-selected education goal of ₹10,00,000.', periodKind: 'as_of' },
    { type: 'insurance_coverage', label: 'Current insurance cover', explanation: 'The sum assured shown by your existing insurance policy.', example: '₹25,00,000 of current life cover.', periodKind: 'as_of' },
  ] },
];

const allFields = groups.flatMap(group => group.fields);
const statusLabels: Record<string, string> = {
  verified: 'Confirmed', unverified: 'Waiting for confirmation', conflict: 'Waiting for confirmation',
  superseded: 'Replaced', rejected: 'Rejected',
};

function localDateParts() {
  const now = new Date();
  const year = String(now.getFullYear());
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const day = String(now.getDate()).padStart(2, '0');
  return { year, month, day };
}
function today() { const value = localDateParts(); return `${value.year}-${value.month}-${value.day}`; }
function currentMonth() { const value = localDateParts(); return `${value.year}-${value.month}`; }
function periodFor(fact: FinancialFact, definition: FieldDefinition) {
  return fact.period_start || (definition.periodKind === 'monthly' ? fact.observed_at.slice(0, 7) + '-01' : fact.observed_at.slice(0, 10));
}
function formatPeriod(value: string, kind: PeriodKind) {
  const parsed = new Date(`${value}T00:00:00`);
  return new Intl.DateTimeFormat('en-IN', kind === 'monthly' ? { month: 'long', year: 'numeric' } : { day: 'numeric', month: 'short', year: 'numeric' }).format(parsed);
}
function formatMoney(value: string) {
  return `₹${new Intl.NumberFormat('en-IN', { maximumFractionDigits: 2 }).format(Number(value))}`;
}

interface FinancialMemoryProps {
  token: string;
  facts: FinancialFact[];
  initialField?: string;
  onFactsChanged: () => Promise<void>;
}

const FinancialMemory: React.FC<FinancialMemoryProps> = ({ token, facts, initialField, onFactsChanged }) => {
  const [month, setMonth] = useState(currentMonth());
  const [asOfDate, setAsOfDate] = useState(today());
  const [edits, setEdits] = useState<Record<string, string>>({});
  const [reviewing, setReviewing] = useState(false);
  const [confirmed, setConfirmed] = useState(false);
  const [pending, setPending] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const histories = useMemo(() => Object.fromEntries(allFields.map(field => [field.type, facts
    .filter(fact => fact.fact_type === field.type)
    .sort((a, b) => periodFor(b, field).localeCompare(periodFor(a, field)) || b.observed_at.localeCompare(a.observed_at))])), [facts]);
  const changedFields = allFields.filter(field => edits[field.type]?.trim());

  const startReview = (event: FormEvent) => {
    event.preventDefault();
    if (!changedFields.length) { setError('Enter at least one value before reviewing.'); return; }
    setError(''); setConfirmed(false); setReviewing(true);
  };

  const saveChanges = async () => {
    if (!confirmed || pending) return;
    setPending(true); setError(''); setMessage('');
    const observedAt = new Date().toISOString();
    const inputs: FinancialFactInput[] = changedFields.map(field => ({
      fact_type: field.type, value: edits[field.type], unit: 'INR', source_type: 'user_statement', observed_at: observedAt,
      period_start: field.periodKind === 'monthly' ? `${month}-01` : asOfDate,
    }));
    try {
      const candidates = await createFinancialFactBatch(token, inputs);
      await decideFinancialFactBatch(token, candidates.map(fact => fact.fact_id), 'confirm');
      setEdits({}); setReviewing(false); setConfirmed(false);
      setMessage(`${candidates.length} ${candidates.length === 1 ? 'value was' : 'values were'} confirmed.`);
      await onFactsChanged();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'The financial values could not be confirmed.');
      await onFactsChanged();
    } finally { setPending(false); }
  };

  const decideExisting = async (factId: string, decision: 'confirm' | 'reject') => {
    setPending(true); setError('');
    try { await decideFinancialFact(token, factId, decision); await onFactsChanged(); }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'The decision could not be saved.'); }
    finally { setPending(false); }
  };

  return <section className="financial-memory" aria-labelledby="financial-memory-title">
    <header className="memory-heading"><div><p className="eyebrow">YOUR CONFIRMED INFORMATION</p><h2 id="financial-memory-title">Financial Memory</h2><p>Add dated values so Artha can answer without guessing. Monthly calculations only combine information from the same month.</p></div><span className="memory-security"><ShieldCheck/> Only confirmed values are used</span></header>
    {message && <div className="agent-success" role="status">{message}</div>}
    {error && <div className="agent-error" role="alert">{error}</div>}
    {!reviewing ? <form onSubmit={startReview} className="memory-form">
      <div className="period-controls"><label>Month for monthly values<input type="month" max={currentMonth()} value={month} onChange={event => setMonth(event.target.value)} required/></label><label>As-of date for snapshots<input type="date" max={today()} value={asOfDate} onChange={event => setAsOfDate(event.target.value)} required/></label></div>
      {groups.map(group => <section className="memory-group" key={group.title}><div className="memory-group-heading"><h3>{group.title}</h3><p>{group.description}</p></div><div className="memory-fields">{group.fields.map(field => {
        const history = histories[field.type] as FinancialFact[];
        const latest = history.find(fact => fact.verification_status === 'verified');
        return <article className={`memory-field ${field.type === initialField ? 'requested-field' : ''}`} key={field.type}>
          <div className="memory-field-heading"><div><strong>{field.label}</strong><InfoTooltip term={field.label} explanation={field.explanation} example={field.example}/></div>{latest && <span className="memory-current"><Check/> {formatMoney(latest.value)} · {formatPeriod(periodFor(latest, field), field.periodKind)}</span>}</div>
          <label htmlFor={`memory-${field.type}`}>{latest ? 'Enter an updated value' : 'Add value'} (₹)</label><input id={`memory-${field.type}`} type="number" min="0" step="0.01" placeholder={latest ? formatMoney(latest.value) : '0'} value={edits[field.type] || ''} onChange={event => setEdits(current => ({ ...current, [field.type]: event.target.value }))}/>
          {history.length > 0 && <details className="memory-history"><summary>View history ({history.length}) <ChevronDown/></summary><ul>{history.map(fact => <li key={fact.fact_id}><span><strong>{formatMoney(fact.value)}</strong><small>{formatPeriod(periodFor(fact, field), field.periodKind)} · {statusLabels[fact.verification_status]}</small><small>{fact.source_type === 'local_document_confirmation' ? 'Confirmed from local document review' : 'Entered manually'} · observed {new Date(fact.observed_at).toLocaleDateString('en-IN')}{fact.verified_at ? ` · confirmed ${new Date(fact.verified_at).toLocaleDateString('en-IN')}` : ''}</small></span>{(fact.verification_status === 'unverified' || fact.verification_status === 'conflict') && <span className="history-actions"><button type="button" disabled={pending} onClick={() => void decideExisting(fact.fact_id, 'confirm')}>Confirm</button><button type="button" disabled={pending} onClick={() => void decideExisting(fact.fact_id, 'reject')}>Reject</button></span>}</li>)}</ul></details>}
        </article>;
      })}</div></section>)}
      <div className="memory-submit"><Button disabled={!changedFields.length || pending}>Review {changedFields.length || ''} {changedFields.length === 1 ? 'change' : 'changes'}</Button><small>Nothing is used in calculations until you review and confirm it.</small></div>
    </form> : <section className="memory-review" aria-labelledby="review-title"><p className="eyebrow">REVIEW BEFORE CONFIRMING</p><h3 id="review-title">Check these values and dates</h3><p>A confirmed replacement keeps the older value in history.</p><ul>{changedFields.map(field => {
      const period = field.periodKind === 'monthly' ? `${month}-01` : asOfDate;
      const replaces = (histories[field.type] as FinancialFact[]).find(fact => fact.verification_status === 'verified' && (field.periodKind === 'as_of' || periodFor(fact, field) === period));
      return <li key={field.type}><span><strong>{field.label}</strong><small>{formatPeriod(period, field.periodKind)}</small></span><span><strong>{formatMoney(edits[field.type])}</strong>{replaces && <small>Replaces {formatMoney(replaces.value)} for this {field.periodKind === 'monthly' ? 'month' : 'field'}</small>}</span></li>;
    })}</ul><label className="scenario-confirm"><input type="checkbox" checked={confirmed} onChange={event => setConfirmed(event.target.checked)}/> I confirm these values, dates, and periods are mine and correct.</label><div className="memory-review-actions"><Button type="button" variant="secondary" disabled={pending} onClick={() => setReviewing(false)}>Back to edit</Button><Button type="button" disabled={!confirmed || pending} onClick={() => void saveChanges()}>{pending ? 'Confirming…' : 'Confirm values'}</Button></div></section>}
    <footer className="memory-note"><Clock3/> Replaced values remain available in history and are never silently merged.</footer>
  </section>;
};

export default FinancialMemory;
