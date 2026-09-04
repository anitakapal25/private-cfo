import React from 'react';
import Button from '@/components/ui/Button';
import InfoTooltip from '@/components/ui/InfoTooltip';
import { Bot, Check, ChevronRight, Circle, FileText, FolderLock, ShieldCheck } from 'lucide-react';
import type { FinancialFact, ProactiveReview } from './api';

interface GlossaryEntry { explanation: string; example?: string }

const glossary: Record<string, GlossaryEntry> = {
  monthly_income: { explanation: 'The money you receive in a typical month after deductions.', example: '₹50,000 received as take-home salary.' },
  monthly_expenses: { explanation: 'The money you usually spend each month on needs and regular bills.', example: '₹25,000 for rent, food, travel, and bills.' },
  total_assets: { explanation: 'Everything valuable you own.', example: '₹50,000 in savings plus a ₹3,00,000 investment.' },
  total_liabilities: { explanation: 'All the money you currently owe.', example: 'A ₹2,00,000 loan balance.' },
  liquid_assets: { explanation: 'Money you can access quickly, such as cash or bank savings.', example: '₹20,000 in a savings account.' },
  financial_review: { explanation: 'A check that points out information or decisions that may need your attention.' },
  goal: { explanation: 'Something you want to save or plan money for.', example: 'Building ₹5,00,000 for education.' },
  loan: { explanation: 'Money borrowed that you repay over time, usually with interest.', example: 'A home or vehicle loan paid every month.' },
  cash_flow: { explanation: 'A view of the money coming in and going out over a period.', example: 'Monthly income compared with monthly spending.' },
};

const setupItems = [
  { type: 'monthly_income', label: 'Monthly income', helper: 'Tell us how much you receive each month.' },
  { type: 'monthly_expenses', label: 'Monthly expenses', helper: 'Add your regular monthly spending.' },
  { type: 'total_assets', label: 'Total assets', helper: 'Add everything valuable you own.' },
  { type: 'total_liabilities', label: 'Total debt', helper: 'Add loans and other money you owe.' },
] as const;

const reviewLabels: Record<string, string> = {
  stale_financial_fact: 'Some information may be out of date',
  negative_recurring_cash_flow: 'Monthly spending may be higher than income',
  liquid_reserve_decline: 'Money available quickly has decreased',
  goal_progress_decline: 'Progress toward a goal has decreased',
  overdue_action: 'A planned action may be overdue',
};

function Term({ type, children }: { type: string; children: React.ReactNode }) {
  const entry = glossary[type];
  return <span className="financial-term">{children}<InfoTooltip term={String(children)} explanation={entry.explanation} example={entry.example}/></span>;
}

function formatFactValue(fact?: FinancialFact) {
  if (!fact) return 'Not added';
  const value = Number(fact.value);
  if (!Number.isFinite(value)) return `${fact.unit === 'INR' ? '₹' : ''}${fact.value}`;
  return `${fact.unit === 'INR' ? '₹' : ''}${new Intl.NumberFormat('en-IN', { maximumFractionDigits: 2 }).format(value)}`;
}

interface DashboardProps {
  verifiedFacts: FinancialFact[];
  openReviews: ProactiveReview[];
  documentReviewAvailable: boolean;
  onOpenFact: (factType: string) => void;
  onOpenDocuments: () => void;
  onOpenReviews: () => void;
  onAsk: (prompt?: string) => void;
}

const Dashboard: React.FC<DashboardProps> = ({ verifiedFacts, openReviews, documentReviewAvailable, onOpenFact, onOpenDocuments, onOpenReviews, onAsk }) => {
  const verifiedTypes = new Set(verifiedFacts.map(fact => fact.fact_type));
  const latestVerified = (type: string) => verifiedFacts
    .filter(fact => fact.fact_type === type)
    .sort((a, b) => (b.period_start || b.observed_at).localeCompare(a.period_start || a.observed_at))[0];
  const missingSetup = setupItems.filter(item => !verifiedTypes.has(item.type));
  const isSetupComplete = missingSetup.length === 0;
  const salaryDocumentConfirmed = verifiedFacts.some(fact => fact.fact_type === 'monthly_income' && fact.source_type === 'local_document_confirmation');
  const insuranceDocumentConfirmed = verifiedFacts.some(fact => fact.fact_type === 'insurance_coverage' && fact.source_type === 'local_document_confirmation');

  if (!isSetupComplete) {
    const completed = setupItems.length - missingSetup.length;
    return <section className="overview-page setup-dashboard">
      <header className="overview-heading"><div><p className="eyebrow">YOUR FINANCIAL HOME</p><h2>Welcome to Artha</h2><p>Let’s build a simple picture of your money so we can help you plan.</p></div></header>
      <article className="dashboard-card setup-card" aria-labelledby="setup-title">
        <div className="setup-card-heading"><span className="setup-heading-icon"><ShieldCheck/></span><div><h3 id="setup-title">Set up your financial picture</h3><p>{completed} of {setupItems.length} basics added</p></div></div>
        <progress value={completed} max={setupItems.length} aria-label={`${completed} of ${setupItems.length} basics added`}>{completed} of {setupItems.length}</progress>
        <div className="setup-columns">
          <section aria-labelledby="details-title"><h4 id="details-title">Start with these details</h4><ul className="setup-checklist">{setupItems.map(item => {
            const done = verifiedTypes.has(item.type);
            return <li key={item.type} className={done ? 'complete' : ''}>{done ? <Check aria-hidden="true"/> : <Circle aria-hidden="true"/>}<span><strong><Term type={item.type}>{item.label}</Term></strong><small>{done ? 'Added and confirmed' : item.helper}</small></span></li>;
          })}</ul><Button type="button" onClick={() => onOpenFact(missingSetup[0].type)}>Add your details</Button></section>
          <section className="optional-documents" aria-labelledby="documents-title"><h4 id="documents-title">Optional documents</h4><p>Documents can help confirm some values. You can also enter everything manually.</p>
            <div className={`document-guide ${salaryDocumentConfirmed ? 'complete' : ''}`}>{salaryDocumentConfirmed ? <Check aria-hidden="true"/> : <FileText aria-hidden="true"/>}<span><strong>Salary slip PDF</strong><small>{salaryDocumentConfirmed ? 'Reviewed and confirmed' : 'Can identify your take-home income'}</small></span></div>
            <div className={`document-guide ${insuranceDocumentConfirmed ? 'complete' : ''}`}>{insuranceDocumentConfirmed ? <Check aria-hidden="true"/> : <FileText aria-hidden="true"/>}<span><strong>Insurance policy PDF</strong><small>{insuranceDocumentConfirmed ? 'Reviewed and confirmed' : 'Can identify your insurance cover'}</small></span></div>
            {documentReviewAvailable ? <Button type="button" variant="secondary" onClick={onOpenDocuments}><FolderLock/> Review on this device</Button> : <p className="document-unavailable">Document review is available in the supported desktop app. You can enter all details manually here.</p>}
            <p className="privacy-note"><ShieldCheck/> Your original PDF stays on this device. Only values you confirm are saved.</p>
          </section>
        </div>
      </article>
      <article className="dashboard-card after-setup"><h3>What you can do after setup</h3><div><span><Term type="cash_flow">Understand where your money goes</Term></span><span>Plan for your <Term type="goal">goals</Term></span><span>Review <Term type="loan">loans</Term> and monthly payments</span></div></article>
    </section>;
  }

  const cards = [
    { type: 'monthly_income', label: 'Monthly income' },
    { type: 'total_assets', label: 'Total assets' },
    { type: 'liquid_assets', label: 'Money available quickly' },
  ];
  const missingHelpful = !verifiedTypes.has('liquid_assets');
  const nextAction = openReviews.length ? { title: 'Review an important update', text: 'A financial review needs your decision.', label: 'View review', action: onOpenReviews }
    : missingHelpful ? { title: 'Add money available quickly', text: 'This helps explain what you can access for near-term needs.', label: 'Add this value', action: () => onOpenFact('liquid_assets') }
      : { title: 'Ask your first planning question', text: 'Use your confirmed details to understand your next step.', label: 'Ask Artha', action: () => onAsk() };

  return <section className="overview-page">
    <header className="overview-heading"><div><p className="eyebrow">YOUR FINANCIAL HOME</p><h2>Good morning</h2><p>Here’s a simple view of your money today.</p></div><Button type="button" onClick={() => onAsk()}><Bot/> Ask Artha</Button></header>
    <section aria-labelledby="have-title"><h3 className="dashboard-section-title" id="have-title">What do I have?</h3><div className="dashboard-summary">{cards.map(card => { const fact = latestVerified(card.type); return <article className="dashboard-card" key={card.type}><div className="dashboard-card-head"><Term type={card.type}>{card.label}</Term></div><strong className="metric-value">{formatFactValue(fact)}</strong><footer>{fact ? <><span className="verified-label"><Check/> Confirmed</span><small>Updated {new Date(fact.verified_at || fact.observed_at).toLocaleDateString()}</small></> : <button type="button" className="inline-link" onClick={() => onOpenFact(card.type)}>Add this value</button>}</footer></article>; })}</div></section>
    <div className="dashboard-grid guided-grid">
      <article className="dashboard-card next-action-card"><p className="eyebrow">WHAT SHOULD I DO NEXT?</p><h3>{nextAction.title}</h3><p>{nextAction.text}</p><Button type="button" onClick={nextAction.action}>{nextAction.label}<ChevronRight/></Button></article>
      <article className="dashboard-card attention-card"><h3>What needs attention? <InfoTooltip term="financial review" explanation={glossary.financial_review.explanation}/></h3>{openReviews.length ? openReviews.slice(0, 2).map(review => <button type="button" className="attention-row" key={review.review_id} onClick={onOpenReviews}><span className="attention-icon">!</span><span><strong>{reviewLabels[review.finding_type] || 'A financial check needs your attention'}</strong><small>Open review</small></span><ChevronRight/></button>) : <div className="clear-state"><Check/><span><strong>You are all caught up</strong><small>No reviews need a decision.</small></span></div>}</article>
    </div>
    <article className="dashboard-card ask-card"><h3>Ask Artha</h3><p>Choose a question in everyday language.</p><div className="overview-prompts"><span className="overview-prompt"><button onClick={() => onAsk('Show my goal progress')}>Can I reach my goal?</button><InfoTooltip term="goal" explanation={glossary.goal.explanation} example={glossary.goal.example}/></span><button onClick={() => onAsk('Show my 12-month cash flow forecast')}>Where does my money go?</button><span className="overview-prompt"><button onClick={() => onAsk('Show my debt and EMI metrics')}>Help me understand my loans</button><InfoTooltip term="loans" explanation={glossary.loan.explanation} example={glossary.loan.example}/></span></div></article>
    <p className="dashboard-trust"><ShieldCheck/> Figures shown here use information you confirmed.</p>
  </section>;
};

export default Dashboard;
