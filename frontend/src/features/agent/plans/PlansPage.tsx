import React, { FormEvent, useCallback, useEffect, useState } from 'react';
import Button from '@/components/ui/Button';
import { Archive, CalendarDays, Check, ChevronDown, Pause, PiggyBank, Play, Plus, Target } from 'lucide-react';
import { ApiError, changePlannedActionStatus, confirmAction, createActionCheckIn, createActionPlan, createConversation, getActiveActionPlan, rankPlanningActions, updatePlannedAction, type ActivePlanResponse, type PlannedAction, type PlanningActionInput, type RankedAction } from '../api';
import { formatMoney } from '../memory/model';

const labels = {
  increase_monthly_savings: 'Save more every month',
  reduce_monthly_expenses: 'Reduce monthly spending',
  increase_debt_payment: 'Pay extra toward debt',
};
const score = { low: '0.25', medium: '0.50', high: '0.75' } as const;
const feasibility = { easy: '0.75', manageable: '0.50', difficult: '0.25' } as const;
const today = () => new Date().toISOString().slice(0, 10);
const nextYear = () => { const value = new Date(); value.setFullYear(value.getFullYear() + 1); return value.toISOString().slice(0, 10); };

interface Props {
  token: string;
  conversationId?: string;
  onConversationCreated: (id: string) => void;
  onAsk: (prompt: string) => void;
}

type Draft = Required<Pick<PlanningActionInput, 'action_type' | 'monthly_amount' | 'priority_label' | 'difficulty_label' | 'start_date' | 'target_date'>>;
const initialDraft: Draft = { action_type: 'increase_monthly_savings', monthly_amount: '', priority_label: 'medium', difficulty_label: 'manageable', start_date: today(), target_date: nextYear() };
const planLoadError = (reason: unknown) => reason instanceof ApiError && reason.status === 404
  ? 'My Plan is temporarily unavailable. Your existing financial information is unchanged.'
  : reason instanceof Error ? reason.message : 'Your plan could not be loaded.';

const PlansPage: React.FC<Props> = ({ token, conversationId, onConversationCreated, onAsk }) => {
  const [data, setData] = useState<ActivePlanResponse>();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);
  const [creating, setCreating] = useState(false);
  const [draft, setDraft] = useState<Draft>(initialDraft);
  const [candidate, setCandidate] = useState<RankedAction>();
  const [confirmed, setConfirmed] = useState(false);
  const [checkInAction, setCheckInAction] = useState<PlannedAction>();
  const [checkInAmount, setCheckInAmount] = useState('');
  const [checkInNote, setCheckInNote] = useState('');
  const [editing, setEditing] = useState<PlannedAction>();

  const refresh = useCallback(async () => {
    try { setData(await getActiveActionPlan(token)); setError(''); }
    catch (reason) { setError(planLoadError(reason)); }
    finally { setLoading(false); }
  }, [token]);
  useEffect(() => {
    let current = true;
    getActiveActionPlan(token)
      .then(result => { if (current) { setData(result); setError(''); } })
      .catch(reason => { if (current) setError(planLoadError(reason)); })
      .finally(() => { if (current) setLoading(false); });
    return () => { current = false; };
  }, [token]);

  const actionInput = (value: Draft): PlanningActionInput => ({ ...value, user_priority: score[value.priority_label], feasibility: feasibility[value.difficulty_label] });
  const ensureConversation = async () => {
    if (conversationId) return conversationId;
    const id = await createConversation(token); onConversationCreated(id); return id;
  };
  const compare = async (event: FormEvent) => {
    event.preventDefault(); setBusy(true); setError(''); setConfirmed(false);
    try { setCandidate((await rankPlanningActions(token, [actionInput(draft)]))[0]); }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'The action could not be reviewed.'); }
    finally { setBusy(false); }
  };
  const create = async () => {
    if (!candidate || !confirmed) return;
    setBusy(true); setError('');
    try {
      const action = actionInput(draft); const title = 'My financial action plan';
      const confirmationId = await confirmAction(token, await ensureConversation(), 'create_action_plan', { title, actions: [action] });
      await createActionPlan(token, title, [action], confirmationId);
      setCreating(false); setCandidate(undefined); setConfirmed(false); setDraft(initialDraft); setMessage('Your confirmed action was added to My Plan.'); await refresh();
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'The action could not be added.'); }
    finally { setBusy(false); }
  };
  const statusChange = async (action: PlannedAction, status: PlannedAction['status']) => {
    if (status === 'archived' && !window.confirm('Archive this action? It will leave your active plan but remain in history.')) return;
    setBusy(true); setError('');
    try {
      let confirmationId: string | undefined;
      if (status === 'archived') confirmationId = await confirmAction(token, await ensureConversation(), 'archive_planned_action', { action_id: action.action_id, status });
      await changePlannedActionStatus(token, action.action_id, status, confirmationId);
      setMessage(status === 'archived' ? 'The action was archived and remains in history.' : `The action is now ${status}.`); await refresh();
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'The action could not be updated.'); }
    finally { setBusy(false); }
  };
  const saveCheckIn = async (event: FormEvent) => {
    event.preventDefault(); if (!checkInAction) return; setBusy(true);
    try { await createActionCheckIn(token, checkInAction.action_id, checkInAmount, today(), checkInNote); setCheckInAction(undefined); setCheckInAmount(''); setCheckInNote(''); setMessage('Your check-in was added. Progress is based only on your check-ins.'); await refresh(); }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'The check-in could not be added.'); }
    finally { setBusy(false); }
  };
  const saveEdit = async (event: FormEvent) => {
    event.preventDefault(); if (!editing || !window.confirm('Confirm these changes to your action?')) return; setBusy(true);
    try {
      const input = { monthly_amount: editing.monthly_amount, priority_label: editing.priority_label, difficulty_label: editing.difficulty_label, start_date: editing.start_date, target_date: editing.target_date };
      const confirmationId = await confirmAction(token, await ensureConversation(), 'update_planned_action', { action_id: editing.action_id, ...input });
      await updatePlannedAction(token, editing.action_id, input, confirmationId); setEditing(undefined); setMessage('The confirmed action was updated.'); await refresh();
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'The action could not be updated.'); }
    finally { setBusy(false); }
  };

  if (loading) return <section className="plans-page" aria-busy="true"><p>Loading your plan…</p></section>;
  return <section className="plans-page" aria-labelledby="plans-title">
    <header className="plans-heading"><div><p className="eyebrow">MY PLAN</p><h2 id="plans-title">Turn intentions into manageable actions</h2><p>Track only the actions you choose and confirm. Progress is based on your check-ins.</p></div><span><Check/> Only confirmed actions are added</span></header>
    {error && <div className="agent-error" role="alert">{error} <button type="button" onClick={() => void refresh()}>Try again</button></div>}
    {message && <div className="agent-success" role="status">{message}</div>}
    <section className="plan-summary" aria-label="Plan summary"><div><Target/><span><strong>{data?.summary.active_count || 0}</strong>Active actions</span></div><div><PiggyBank/><span><strong>{formatMoney(data?.summary.monthly_commitment.amount || '0')}</strong>Monthly commitment</span></div><div><Check/><span><strong>{data?.summary.completed_count || 0}</strong>Completed</span></div></section>
    <div className="plans-layout"><div className="plan-actions"><div className="plan-section-title"><h3>Active actions</h3>{!creating && <Button type="button" size="sm" onClick={() => setCreating(true)}><Plus/> Create action</Button>}</div>
      {!data?.active_actions.length ? <div className="plan-empty"><Target/><h3>You don’t have an active action yet</h3><p>Start with one small change you feel ready to make.</p><Button type="button" onClick={() => setCreating(true)}>Create your first action</Button><button type="button" onClick={() => onAsk('Help me prepare a budgeting action for My Plan.')}>Ask Artha to help me prepare one</button></div>
      : data.active_actions.map(action => <ActionCard key={action.action_id} action={action} busy={busy} onCheckIn={setCheckInAction} onEdit={setEditing} onStatus={statusChange}/>) }
      {(data?.completed_actions.length || data?.archived_actions.length) ? <details className="plan-history"><summary>Completed and archived actions <ChevronDown/></summary>{[...(data?.completed_actions || []), ...(data?.archived_actions || [])].map(action => <ActionCard key={action.action_id} action={action} busy={busy} onCheckIn={setCheckInAction} onEdit={setEditing} onStatus={statusChange}/>)}</details> : null}
      {data && <details className="plan-evidence"><summary>Plan calculation evidence</summary><p>Calculation ID: {data.calculation_id}</p><p>Version: {data.version}</p>{data.limitations.map(item => <p key={item}>{item}</p>)}</details>}
    </div>
    <aside className="create-action-panel"><Plus/><h3>Create your next action</h3><p>Only actions you confirm are added to your plan.</p>{(['increase_monthly_savings', 'reduce_monthly_expenses', 'increase_debt_payment'] as const).map(type => <button type="button" key={type} onClick={() => { setDraft(current => ({ ...current, action_type: type })); setCreating(true); }}>{labels[type]}</button>)}<Button type="button" onClick={() => setCreating(true)}>Create an action</Button></aside></div>

    {creating && <div className="plan-dialog-backdrop"><section className="plan-dialog" role="dialog" aria-modal="true" aria-labelledby="create-action-title"><h3 id="create-action-title">{candidate ? 'Review your action' : 'Create an action'}</h3>{!candidate ? <ActionForm draft={draft} setDraft={setDraft} busy={busy} onSubmit={compare} onCancel={() => setCreating(false)}/> : <><dl><div><dt>Action</dt><dd>{labels[draft.action_type]}</dd></div><div><dt>Every month</dt><dd>{formatMoney(draft.monthly_amount)}</dd></div><div><dt>Dates</dt><dd>{draft.start_date} to {draft.target_date}</dd></div><div><dt>Expected effect</dt><dd>{String(candidate.impact.effect || candidate.rationale)}</dd></div></dl><label className="scenario-confirm"><input type="checkbox" checked={confirmed} onChange={event => setConfirmed(event.target.checked)}/> I confirm this is the action I want added to My Plan.</label><div className="dialog-actions"><Button type="button" variant="secondary" onClick={() => setCandidate(undefined)}>Back</Button><Button type="button" disabled={!confirmed || busy} onClick={() => void create()}>{busy ? 'Adding…' : 'Confirm and add'}</Button></div></>}</section></div>}
    {checkInAction && <div className="plan-dialog-backdrop"><form className="plan-dialog" role="dialog" aria-modal="true" onSubmit={saveCheckIn}><h3>Add a progress check-in</h3><p>{labels[checkInAction.action_type]}. This progress comes only from what you enter.</p><label>Amount completed (₹)<input type="number" min="0.01" step="0.01" required value={checkInAmount} onChange={event => setCheckInAmount(event.target.value)}/></label><label>Note (optional)<input maxLength={240} value={checkInNote} onChange={event => setCheckInNote(event.target.value)}/></label><div className="dialog-actions"><Button type="button" variant="secondary" onClick={() => setCheckInAction(undefined)}>Cancel</Button><Button disabled={busy}>Add check-in</Button></div></form></div>}
    {editing && <div className="plan-dialog-backdrop"><form className="plan-dialog" role="dialog" aria-modal="true" onSubmit={saveEdit}><h3>Edit confirmed action</h3><label>Monthly amount (₹)<input type="number" min="0.01" step="0.01" required value={editing.monthly_amount} onChange={event => setEditing({ ...editing, monthly_amount: event.target.value })}/></label><label>Start date<input type="date" required value={editing.start_date} onChange={event => setEditing({ ...editing, start_date: event.target.value })}/></label><label>Target date<input type="date" min={editing.start_date} required value={editing.target_date} onChange={event => setEditing({ ...editing, target_date: event.target.value })}/></label><div className="dialog-actions"><Button type="button" variant="secondary" onClick={() => setEditing(undefined)}>Cancel</Button><Button disabled={busy}>Review and save</Button></div></form></div>}
  </section>;
};

function ActionForm({ draft, setDraft, busy, onSubmit, onCancel }: { draft: Draft; setDraft: React.Dispatch<React.SetStateAction<Draft>>; busy: boolean; onSubmit: (event: FormEvent) => void; onCancel: () => void }) {
  return <form className="plan-form" onSubmit={onSubmit}><label>What do you want to do?<select value={draft.action_type} onChange={event => setDraft(current => ({ ...current, action_type: event.target.value as Draft['action_type'] }))}>{Object.entries(labels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label><label>Monthly amount (₹)<input type="number" min="0.01" step="0.01" required value={draft.monthly_amount} onChange={event => setDraft(current => ({ ...current, monthly_amount: event.target.value }))}/></label><div className="plan-form-grid"><label>Start date<input type="date" required value={draft.start_date} onChange={event => setDraft(current => ({ ...current, start_date: event.target.value }))}/></label><label>Target date<input type="date" min={draft.start_date} required value={draft.target_date} onChange={event => setDraft(current => ({ ...current, target_date: event.target.value }))}/></label><label>Priority<select value={draft.priority_label} onChange={event => setDraft(current => ({ ...current, priority_label: event.target.value as Draft['priority_label'] }))}><option value="low">Low</option><option value="medium">Medium</option><option value="high">High</option></select></label><label>Difficulty<select value={draft.difficulty_label} onChange={event => setDraft(current => ({ ...current, difficulty_label: event.target.value as Draft['difficulty_label'] }))}><option value="easy">Easy</option><option value="manageable">Manageable</option><option value="difficult">Difficult</option></select></label></div><div className="dialog-actions"><Button type="button" variant="secondary" onClick={onCancel}>Cancel</Button><Button disabled={busy}>{busy ? 'Reviewing…' : 'Review action'}</Button></div></form>;
}

function ActionCard({ action, busy, onCheckIn, onEdit, onStatus }: { action: PlannedAction; busy: boolean; onCheckIn: (action: PlannedAction) => void; onEdit: (action: PlannedAction) => void; onStatus: (action: PlannedAction, status: PlannedAction['status']) => void }) {
  return <article className={`plan-action-card status-${action.status}`}><span className="action-icon">{action.status === 'completed' ? <Check/> : action.status === 'paused' ? <Pause/> : <Target/>}</span><div className="action-body"><header><h4>{labels[action.action_type]}</h4><span>{action.status}</span></header><p><CalendarDays/> {action.start_date} to {action.target_date} · {formatMoney(action.monthly_amount)} monthly</p><div className="action-progress"><span style={{ width: `${Math.min(100, Number(action.progress.percentage))}%` }}/></div><small>{action.progress.percentage}% · {formatMoney(action.progress.progress_amount)} of {formatMoney(action.target_amount)} · Based on your check-ins</small></div><div className="action-controls">{(action.status === 'active' || action.status === 'paused') && <button type="button" disabled={busy} onClick={() => onCheckIn(action)}>Check in</button>}{action.status !== 'archived' && <button type="button" disabled={busy} onClick={() => onEdit(action)}>Edit</button>}{action.status === 'active' && <button type="button" disabled={busy} onClick={() => void onStatus(action, 'paused')}><Pause/> Pause</button>}{action.status === 'paused' && <button type="button" disabled={busy} onClick={() => void onStatus(action, 'active')}><Play/> Resume</button>}{(action.status === 'active' || action.status === 'paused') && <button type="button" disabled={busy} onClick={() => void onStatus(action, 'completed')}><Check/> Complete</button>}{action.status !== 'archived' && <button type="button" disabled={busy} onClick={() => void onStatus(action, 'archived')}><Archive/> Archive</button>}</div></article>;
}

export default PlansPage;
