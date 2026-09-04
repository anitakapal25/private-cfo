import type { FinancialFact } from '../api';

export type PeriodKind = 'monthly' | 'as_of';

export interface FieldDefinition {
  type: string;
  label: string;
  formalLabel: string;
  explanation: string;
  example: string;
  missingHelp: string;
  periodKind: PeriodKind;
}

export interface MemoryGroup {
  id: string;
  title: string;
  description: string;
  fields: FieldDefinition[];
}

export const memoryGroups: MemoryGroup[] = [
  { id: 'monthly', title: 'This month', description: 'Your income, spending and loan payments for the selected month.', fields: [
    { type: 'monthly_income', label: 'Money coming in', formalLabel: 'Monthly income', explanation: 'Money you received during this month after deductions.', example: '₹50,000 received in September 2026.', missingHelp: 'Add your monthly income to help Artha understand your cash flow.', periodKind: 'monthly' },
    { type: 'monthly_expenses', label: 'Money going out', formalLabel: 'Monthly expenses', explanation: 'Money you spent during this month on bills, food, rent, travel, and other spending.', example: '₹30,000 spent in September 2026.', missingHelp: 'Add your monthly expenses to get better insights.', periodKind: 'monthly' },
    { type: 'monthly_debt_payments', label: 'Loan payments', formalLabel: 'Monthly loan payments', explanation: 'The total loan and EMI payments made during this month.', example: '₹12,000 paid toward home and vehicle loans.', missingHelp: 'Add loan payments for a complete monthly view.', periodKind: 'monthly' },
  ] },
  { id: 'position', title: 'What you own and owe', description: 'Your financial position on the selected date.', fields: [
    { type: 'total_assets', label: 'What you own', formalLabel: 'Total assets', explanation: 'The combined value of savings, investments, property, and other assets.', example: '₹8,00,000 across savings, investments, gold, and property.', missingHelp: 'Add your savings, investments, property, or other assets.', periodKind: 'as_of' },
    { type: 'liquid_assets', label: 'What you can access quickly', formalLabel: 'Liquid assets', explanation: 'Money you can access quickly, such as cash and bank savings.', example: '₹75,000 in cash and savings accounts.', missingHelp: 'Add cash and savings you can access quickly.', periodKind: 'as_of' },
    { type: 'total_liabilities', label: 'What you owe', formalLabel: 'Total debt', explanation: 'All money currently owed, including loans and unpaid credit-card balances.', example: '₹4,00,000 owed across all debts.', missingHelp: 'Add the total amount you currently owe.', periodKind: 'as_of' },
    { type: 'debt_outstanding', label: 'Loans remaining', formalLabel: 'Loan balance', explanation: 'The amount still unpaid on loans you want Artha to analyse.', example: '₹2,50,000 remaining on a vehicle loan.', missingHelp: 'Add the remaining balance of loans you want to track.', periodKind: 'as_of' },
  ] },
  { id: 'goals', title: 'Goals and protection', description: 'Your financial goals and insurance coverage.', fields: [
    { type: 'goal_current', label: 'Saved toward your goal', formalLabel: 'Current goal amount', explanation: 'The amount already set aside for a financial goal.', example: '₹2,00,000 already saved for education.', missingHelp: 'Add how much you have already saved toward a goal.', periodKind: 'as_of' },
    { type: 'goal_target', label: 'Your target', formalLabel: 'Goal target', explanation: 'The total amount you chose for your goal; Artha does not choose it for you.', example: 'A user-selected education goal of ₹10,00,000.', missingHelp: 'Add the amount you want to reach.', periodKind: 'as_of' },
    { type: 'insurance_coverage', label: 'Insurance protection', formalLabel: 'Current insurance cover', explanation: 'The sum assured shown by existing insurance policies.', example: '₹25,00,000 of current life cover.', missingHelp: 'Add the current cover shown on your policy.', periodKind: 'as_of' },
  ] },
  { id: 'documents', title: 'Document-specific values', description: 'Values kept separate so one document is never mistaken for your complete financial position.', fields: [
    { type: 'annual_gross_income', label: 'Annual gross income', formalLabel: 'Form 16 gross salary', explanation: 'The gross annual salary printed on a confirmed Form 16.', example: '₹11,40,000 gross salary.', missingHelp: 'Review a Form 16 to add this value.', periodKind: 'as_of' },
    { type: 'bank_account_balance', label: 'Bank account balance', formalLabel: 'Individual bank closing balance', explanation: 'The closing balance of one confirmed bank statement.', example: '₹1,71,100 in one account.', missingHelp: 'Review a bank statement to add this value.', periodKind: 'as_of' },
    { type: 'epf_balance', label: 'EPF balance', formalLabel: 'Provident fund closing balance', explanation: 'The closing provident-fund balance on a confirmed statement.', example: '₹5,34,500 in EPF.', missingHelp: 'Review an EPF statement to add this value.', periodKind: 'as_of' },
  ] },
];

export const allMemoryFields = memoryGroups.flatMap(group => group.fields);
export const coreMemoryFields = memoryGroups.filter(group => group.id !== 'documents').flatMap(group => group.fields);

export function periodFor(fact: FinancialFact, field: FieldDefinition) {
  return fact.period_start || (field.periodKind === 'monthly' ? `${fact.observed_at.slice(0, 7)}-01` : fact.observed_at.slice(0, 10));
}

export function formatPeriod(value: string, kind: PeriodKind) {
  const parsed = new Date(`${value}T00:00:00`);
  return new Intl.DateTimeFormat('en-IN', kind === 'monthly' ? { month: 'long', year: 'numeric' } : { day: 'numeric', month: 'short', year: 'numeric' }).format(parsed);
}

export function formatMoney(value: string) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? `₹${new Intl.NumberFormat('en-IN', { maximumFractionDigits: 2 }).format(parsed)}` : value;
}

export function sourceLabel(fact: FinancialFact) {
  return fact.source_type === 'local_document_confirmation' ? 'Local document review' : 'Manual entry';
}
