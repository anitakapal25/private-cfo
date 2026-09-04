import React from 'react';
import Button from '@/components/ui/Button';
import InfoTooltip from '@/components/ui/InfoTooltip';
import { Check, ChevronDown, CircleAlert, FileText, Minus } from 'lucide-react';
import type { FinancialFact } from '../api';
import type { SessionDocument } from '../desktop';
import { formatMoney, formatPeriod, periodFor, sourceLabel, type FieldDefinition } from './model';

interface MemoryValueCardProps {
  field: FieldDefinition;
  current?: FinancialFact;
  pendingFact?: FinancialFact;
  history: FinancialFact[];
  documents: SessionDocument[];
  editing: boolean;
  editValue: string;
  disabled: boolean;
  requested: boolean;
  onStartEdit: () => void;
  onCancelEdit: () => void;
  onEditValue: (value: string) => void;
  onPendingDecision: (factId: string, decision: 'confirm' | 'reject') => void;
  onOpenDocuments: () => void;
}

const statusLabels: Record<FinancialFact['verification_status'], string> = {
  verified: 'Confirmed', unverified: 'Needs review', conflict: 'Needs review',
  superseded: 'Replaced', rejected: 'Not added',
};

function linkedDocument(fact: FinancialFact | undefined, documents: SessionDocument[]) {
  if (!fact?.source_id) return undefined;
  return documents.find(document => document.candidates.some(candidate => candidate.evidence_id === fact.source_id));
}

const MemoryValueCard: React.FC<MemoryValueCardProps> = ({
  field, current, pendingFact, history, documents, editing, editValue, disabled, requested,
  onStartEdit, onCancelEdit, onEditValue, onPendingDecision, onOpenDocuments,
}) => {
  const document = linkedDocument(current, documents);
  const hasPending = Boolean(pendingFact);
  const state = hasPending ? 'review' : current ? 'confirmed' : 'missing';

  return <article id={`memory-card-${field.type}`} className={`memory-value-card state-${state} ${requested ? 'requested-field' : ''}`}>
    <header><div><h4>{field.label}</h4><span className="formal-term">{field.formalLabel}<InfoTooltip term={field.formalLabel} explanation={field.explanation} example={field.example}/></span></div>{state === 'confirmed' ? <span className="memory-state confirmed"><Check/> Confirmed</span> : state === 'review' ? <span className="memory-state review"><CircleAlert/> Needs review</span> : <span className="memory-state missing"><Minus/> Not added</span>}</header>

    {pendingFact ? <div className="pending-memory-value"><strong>{formatMoney(pendingFact.value)}</strong><p>{current ? `Your confirmed value remains ${formatMoney(current.value)} until you decide.` : 'This value is not available to Artha until you confirm it.'}</p><div><Button type="button" size="sm" disabled={disabled} onClick={() => onPendingDecision(pendingFact.fact_id, 'confirm')}>{current ? 'Use this value' : 'Confirm'}</Button><button type="button" disabled={disabled} onClick={() => onPendingDecision(pendingFact.fact_id, 'reject')}>{current ? 'Keep confirmed value' : 'Do not add'}</button></div></div>
      : current ? <div className="known-memory-value"><strong>{formatMoney(current.value)}</strong><dl><div><dt>From</dt><dd>{document ? <><FileText/> {document.display_name}</> : sourceLabel(current)}</dd></div><div><dt>{current.source_type === 'local_document_confirmation' ? 'Confirmed' : 'Updated'}</dt><dd>{new Date(current.verified_at || current.observed_at).toLocaleDateString('en-IN')}</dd></div></dl></div>
        : <div className="unknown-memory-value"><strong>Not added</strong><p>{field.missingHelp}</p></div>}

    {editing ? <div className="memory-inline-editor"><label htmlFor={`memory-${field.type}`}>{current ? `Update ${field.label.toLowerCase()}` : `Add ${field.label.toLowerCase()}`} (₹)<input id={`memory-${field.type}`} type="number" min="0" step="0.01" autoFocus value={editValue} onChange={event => onEditValue(event.target.value)}/></label><button type="button" onClick={onCancelEdit}>Cancel</button></div>
      : !hasPending && <div className="memory-card-actions">{document && <button type="button" onClick={onOpenDocuments}>View source</button>}<button type="button" onClick={onStartEdit}>{current ? 'Update' : '+ Add'}</button></div>}

    {history.length > 0 && <details className="memory-history"><summary>History ({history.length}) <ChevronDown/></summary><ul>{history.map(fact => <li key={fact.fact_id}><span><strong>{formatMoney(fact.value)}</strong><small>{formatPeriod(periodFor(fact, field), field.periodKind)}</small></span><span><small>{statusLabels[fact.verification_status]}</small><small>{sourceLabel(fact)} · {new Date(fact.verified_at || fact.observed_at).toLocaleDateString('en-IN')}</small></span></li>)}</ul></details>}
  </article>;
};

export default MemoryValueCard;
