import React, { useMemo, useRef, useState } from 'react';
import Button from '@/components/ui/Button';
import { ArrowRight, Check, ChevronRight, CircleAlert, FileCheck2, FilePlus2, FileText, FolderLock, LockKeyhole, SearchCheck, ShieldCheck } from 'lucide-react';
import type { FinancialFact } from '../api';
import type { LocalDocumentCandidate, LocalDocumentCapabilities, LocalDocumentSelection, SessionDocument } from '../desktop';

type DocumentFilter = 'all' | 'review' | 'insurance' | 'income' | 'tax' | 'investments';

const documentTypes = {
  salary_slip: { label: 'Salary slip', category: 'income', fact: 'Take-home income' },
  form_16: { label: 'Form 16', category: 'tax', fact: 'Annual gross income' },
  bank_statement: { label: 'Bank statement', category: 'investments', fact: 'Account closing balance' },
  epf_statement: { label: 'EPF statement', category: 'investments', fact: 'EPF closing balance' },
  insurance_policy: { label: 'Insurance policy', category: 'insurance', fact: 'Insurance coverage' },
} as const;

const factLabels: Record<string, string> = {
  monthly_income: 'Take-home income', annual_gross_income: 'Annual gross income',
  bank_account_balance: 'Bank account closing balance', epf_balance: 'EPF closing balance',
  insurance_coverage: 'Insurance coverage',
};

function formatMoney(value: string) {
  const amount = Number(value);
  return Number.isFinite(amount) ? `₹${new Intl.NumberFormat('en-IN', { maximumFractionDigits: 2 }).format(amount)}` : value;
}

function formatFileSize(bytes: number) {
  return bytes < 1024 * 1024 ? `${Math.max(1, Math.round(bytes / 1024))} KB` : `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

interface DocumentsPageProps {
  desktopHost: boolean;
  capabilities?: LocalDocumentCapabilities;
  selection?: LocalDocumentSelection;
  documentType: string;
  documents: SessionDocument[];
  facts: FinancialFact[];
  pending: boolean;
  onChoose: () => void;
  onDiscard: () => void;
  onProcess: () => void;
  onDocumentTypeChange: (type: string) => void;
  onCandidateDecision: (candidate: LocalDocumentCandidate, decision: 'confirm' | 'reject') => void;
  onAskArtha: (prompt: string) => void;
}

const DocumentsPage: React.FC<DocumentsPageProps> = ({
  desktopHost, capabilities, selection, documentType, documents, facts, pending,
  onChoose, onDiscard, onProcess, onDocumentTypeChange, onCandidateDecision, onAskArtha,
}) => {
  const [filter, setFilter] = useState<DocumentFilter>('all');
  const uploadCard = useRef<HTMLElement>(null);
  const documentFacts = facts.filter(fact => fact.source_type === 'local_document_confirmation' && fact.verification_status === 'verified');
  const needsReview = documents.flatMap(document => document.candidates).filter(candidate => candidate.status === 'candidate').length;
  const filteredDocuments = useMemo(() => documents.filter(document => {
    if (filter === 'all') return true;
    if (filter === 'review') return document.candidates.some(candidate => candidate.status === 'candidate');
    return documentTypes[document.document_type as keyof typeof documentTypes]?.category === filter;
  }), [documents, filter]);

  const startAdd = () => {
    uploadCard.current?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    onChoose();
  };

  return <section className="documents-page" aria-labelledby="documents-page-title">
    <header className="documents-header">
      <div><p className="eyebrow">PRIVATE DOCUMENT REVIEW</p><h2 id="documents-page-title">Documents</h2><p>Give Artha your financial documents. Artha extracts important information — you decide what enters your Financial Memory.</p></div>
      <div className="documents-header-actions"><Button type="button" onClick={startAdd} disabled={pending || !capabilities?.available}><FilePlus2/> Add document</Button><span className="private-processing"><LockKeyhole/> Private processing</span></div>
    </header>

    <details className="documents-privacy"><summary><ShieldCheck/> Your PDF stays on this device <span>How this works</span></summary><p>The desktop app scans and reads the PDF locally. Artha receives only a structured value after you explicitly confirm it; the filename, path, and extracted text are not sent to the server.</p></details>

    <section className="document-summary" aria-label="Document summary">
      <div><strong>{documents.length}</strong><span>Documents this session</span></div>
      <div><strong>{documentFacts.length}</strong><span>Verified facts</span></div>
      <button type="button" className={needsReview ? 'needs-review' : ''} onClick={() => setFilter('review')}><strong>{needsReview}</strong><span>Need review</span></button>
    </section>

    <nav className="document-filters" aria-label="Filter documents">
      {([['all', 'All'], ['review', 'Needs review'], ['insurance', 'Insurance'], ['income', 'Income'], ['tax', 'Tax'], ['investments', 'Investments']] as const).map(([id, label]) => <button type="button" key={id} className={filter === id ? 'active' : ''} aria-pressed={filter === id} onClick={() => setFilter(id)}>{label}{id === 'review' && needsReview > 0 ? ` ${needsReview}` : ''}</button>)}
    </nav>

    <article className="document-upload-card" ref={uploadCard}>
      <span className="document-upload-icon"><FolderLock/></span>
      <div className="document-upload-copy"><h3>{selection ? selection.display_name : 'Add a PDF from this device'}</h3><p>{selection ? `${formatFileSize(selection.file_size_bytes)} · Ready for local review` : 'Choose a PDF first. If Artha cannot classify it reliably, you select the document type before extraction.'}</p></div>
      {!desktopHost ? <div className="document-blocked" role="alert">The supported desktop application is required. Browser uploads are disabled.</div>
        : capabilities && !capabilities.available ? <div className="document-blocked" role="alert"><strong>Local processing is unavailable</strong>{capabilities.limitations.map(item => <span key={item}>{item}</span>)}</div>
          : selection ? <div className="document-type-step"><label htmlFor="local-document-type">What kind of document is this?<select id="local-document-type" value={documentType} onChange={event => onDocumentTypeChange(event.target.value)}><option value="salary_slip">Salary slip</option><option value="form_16">Form 16</option><option value="bank_statement">Bank statement</option><option value="epf_statement">EPF statement</option><option value="insurance_policy">Insurance policy</option></select></label><div><Button type="button" disabled={pending} onClick={onProcess}><SearchCheck/> {pending ? 'Processing locally…' : 'Scan and find financial facts'}</Button><button type="button" className="secondary-text-action" disabled={pending} onClick={onDiscard}>Choose a different PDF</button></div></div>
            : <Button type="button" variant="secondary" disabled={pending || !capabilities?.available} onClick={onChoose}><FilePlus2/> Choose PDF</Button>}
    </article>

    <section className="document-review-section" aria-labelledby="review-title">
      <div className="section-heading"><div><p className="eyebrow">NEEDS YOUR REVIEW</p><h3 id="review-title">What Artha found</h3></div>{needsReview > 0 && <span className="review-count"><CircleAlert/> {needsReview} {needsReview === 1 ? 'fact' : 'facts'}</span>}</div>
      {needsReview === 0 ? <div className="document-empty-state"><Check/><div><strong>Nothing needs your attention</strong><p>Newly extracted facts will appear here before anything enters Financial Memory.</p></div></div>
        : documents.filter(document => document.candidates.some(candidate => candidate.status === 'candidate')).map(document => <DocumentReviewCard key={document.document_id} document={document} facts={facts} pending={pending} onDecision={onCandidateDecision}/>)}
    </section>

    <section className="document-library" aria-labelledby="library-title">
      <div className="section-heading"><div><p className="eyebrow">THIS APP SESSION</p><h3 id="library-title">Your documents</h3></div><small>Document names are kept only in this open desktop session.</small></div>
      {filteredDocuments.length === 0 ? <div className="document-empty-state muted"><FileText/><div><strong>No documents in this view</strong><p>Add a document or choose another filter.</p></div></div>
        : <div className="document-library-list">{filteredDocuments.map(document => <DocumentLibraryCard key={document.document_id} document={document}/>)}</div>}
    </section>

    {documentFacts.length > 0 && <aside className="document-handoff"><FileCheck2/><div><strong>Added to Financial Memory</strong><p>Artha can now use information you confirmed when helping you plan.</p></div><Button type="button" variant="secondary" onClick={() => onAskArtha('Help me understand the financial information I confirmed from my documents.')} >Ask Artha about this <ArrowRight/></Button></aside>}
  </section>;
};

function DocumentReviewCard({ document, facts, pending, onDecision }: { document: SessionDocument; facts: FinancialFact[]; pending: boolean; onDecision: (candidate: LocalDocumentCandidate, decision: 'confirm' | 'reject') => void }) {
  const pendingCandidates = document.candidates.filter(candidate => candidate.status === 'candidate');
  const type = documentTypes[document.document_type as keyof typeof documentTypes];
  return <article className="document-review-card"><header><span className="review-document-icon"><FileText/></span><div><h4>{type?.label || 'Financial document'}</h4><p>{document.display_name}</p></div><span className="status-pill review">Review</span></header><p>Artha found {pendingCandidates.length} {pendingCandidates.length === 1 ? 'financial fact' : 'financial facts'}.</p><div className="extracted-facts">{pendingCandidates.map(candidate => {
    const current = facts.find(fact => fact.fact_type === candidate.fact_type && fact.verification_status === 'verified');
    const differs = current && (Number(current.value) !== Number(candidate.value) || current.unit !== candidate.unit);
    return <article className={`extracted-fact ${differs ? 'has-conflict' : ''}`} key={candidate.evidence_id}><div><span>{factLabels[candidate.fact_type] || candidate.fact_type.replace(/_/g, ' ')}</span><strong>{formatMoney(candidate.value)}</strong>{current && !differs && <small className="fact-match"><Check/> This matches your Financial Memory.</small>}</div>{differs && <div className="conflict-comparison" role="alert"><strong><CircleAlert/> This is different from your Financial Memory</strong><dl><div><dt>Currently remembered</dt><dd>{formatMoney(current.value)}</dd></div><div><dt>This document says</dt><dd>{formatMoney(candidate.value)}</dd></div></dl></div>}<div className="review-actions"><Button type="button" size="sm" disabled={pending} onClick={() => onDecision(candidate, 'confirm')}>{differs ? 'Update Financial Memory' : 'Confirm'}</Button><button type="button" disabled={pending} onClick={() => onDecision(candidate, 'reject')}>{differs ? 'Keep existing value' : 'Do not add'}</button></div><details className="fact-evidence"><summary>Why does Artha think this? <ChevronRight/></summary><dl><div><dt>Extraction confidence</dt><dd>{Math.round(Number(candidate.confidence) * 100)}%</dd></div><div><dt>Source</dt><dd>{candidate.source_location.replace('local extracted text', 'Locally extracted PDF text')}</dd></div><div><dt>Method</dt><dd>Sandboxed deterministic PDF extraction</dd></div>{current && <div><dt>Previous Financial Memory value</dt><dd>{formatMoney(current.value)} · observed {new Date(current.observed_at).toLocaleDateString('en-IN')}</dd></div>}<div><dt>Evidence reference</dt><dd>{candidate.evidence_id}</dd></div></dl></details></article>;
  })}</div></article>;
}

function DocumentLibraryCard({ document }: { document: SessionDocument }) {
  const type = documentTypes[document.document_type as keyof typeof documentTypes];
  const confirmed = document.candidates.filter(candidate => candidate.status === 'confirmed').length;
  const pending = document.candidates.filter(candidate => candidate.status === 'candidate').length;
  const rejected = document.candidates.filter(candidate => candidate.status === 'rejected').length;
  const status = pending ? 'Review' : confirmed ? 'Verified' : 'Reviewed';
  return <details className="document-library-card"><summary><span className="library-document-icon"><FileText/></span><span><strong>{type?.label || 'Financial document'}</strong><small>{document.display_name}</small></span><span className={`status-pill ${pending ? 'review' : confirmed ? 'verified' : ''}`}>{confirmed ? <Check/> : null}{status}</span><ChevronRight/></summary><div className="library-document-details"><p>{confirmed ? `${confirmed} ${confirmed === 1 ? 'fact' : 'facts'} added to Financial Memory.` : rejected ? 'Extracted information was not added.' : 'No supported financial facts were found.'}</p><dl><div><dt>Processed</dt><dd>{new Date(document.processed_at).toLocaleString('en-IN')}</dd></div><div><dt>Type</dt><dd>{type?.label}</dd></div><div><dt>Size</dt><dd>{formatFileSize(document.file_size_bytes)}</dd></div></dl>{document.candidates.length > 0 && <ul>{document.candidates.map(candidate => <li key={candidate.evidence_id}><span>{factLabels[candidate.fact_type] || candidate.fact_type}</span><strong>{formatMoney(candidate.value)}</strong><small>{candidate.status === 'confirmed' ? 'Added to Financial Memory' : candidate.status === 'rejected' ? 'Not added' : 'Needs review'}</small></li>)}</ul>}</div></details>;
}

export default DocumentsPage;
