import { expect, test, type Page } from '@playwright/test';

const conversationId = '11111111-1111-4111-8111-111111111111';

function financialFact(factType: string, value: string, verificationStatus = 'verified', sourceType = 'user_statement') {
  return {
    fact_id: `${factType}-fact`, fact_type: factType, value, unit: 'INR', source_type: sourceType,
    verification_status: verificationStatus, period_kind: factType.startsWith('monthly_') ? 'monthly' : 'as_of',
    period_start: factType.startsWith('monthly_') ? '2026-09-01' : '2026-09-04',
    observed_at: '2026-09-01T00:00:00Z', verified_at: '2026-09-01T00:00:00Z',
  };
}

async function mockAuthenticatedShell(page: Page, facts: ReturnType<typeof financialFact>[] = []) {
  await page.route('**/api/auth/token', route => route.fulfill({
    status: 200, contentType: 'application/json',
    body: JSON.stringify({ access_token: 'browser-test-token' }),
  }));
  await page.route('**/api/v1/agent/financial-facts', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(facts) }));
  await page.route('**/api/v1/agent/financial-memory/monthly-summary**', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ status: 'incomplete', month: '2026-09', missing: ['monthly_income', 'monthly_expenses', 'monthly_debt_payments'], money_left: null }) }));
  await page.route('**/api/v1/agent/planning/plans/active', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ plan: null, summary: { active_count: 0, monthly_commitment: { amount: '0.00', currency: 'INR' }, completed_count: 0 }, active_actions: [], completed_actions: [], archived_actions: [], calculation_id: 'plan-summary-calculation', version: 'action-tracking-v1', timestamp: '2026-09-04T00:00:00Z', assumptions: {}, limitations: [] }) }));
  await page.route('**/api/v1/agent/reviews', route => route.fulfill({ status: 200, contentType: 'application/json', body: '[]' }));
  await page.route('**/api/v1/agent/conversations', route => route.fulfill({
    status: 201, contentType: 'application/json',
    body: JSON.stringify({ conversation_id: conversationId }),
  }));
}

test('incomplete financial setup shows verified-only progress and selects the first missing field', async ({ page }) => {
  await mockAuthenticatedShell(page, [
    financialFact('monthly_income', '85000'),
    financialFact('monthly_expenses', '40000', 'unverified'),
    financialFact('total_assets', '1250000', 'conflict'),
  ]);
  await signIn(page);
  await expect(page.getByRole('heading', { name: 'Welcome to Artha' })).toBeVisible();
  await expect(page.getByText('1 of 4 basics added')).toBeVisible();
  await expect(page.getByText('Document review is available in the supported desktop app.')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Review on this device' })).toHaveCount(0);
  await page.getByRole('button', { name: 'Add your details' }).click();
  await expect(page.locator('.memory-value-card.requested-field')).toContainText('Monthly expenses');
});

test('Financial Memory groups dated values and confirms a reviewed batch', async ({ page }) => {
  await mockAuthenticatedShell(page);
  let candidatePayload: Record<string, unknown> | undefined;
  let decisionPayload: Record<string, unknown> | undefined;
  await page.route('**/api/v1/agent/financial-facts/batch', route => {
    candidatePayload = route.request().postDataJSON() as Record<string, unknown>;
    return route.fulfill({ status: 201, contentType: 'application/json', body: JSON.stringify([
      financialFact('monthly_income', '85000', 'unverified'), financialFact('monthly_expenses', '40000', 'unverified'),
    ]) });
  });
  await page.route('**/api/v1/agent/financial-facts/batch/decision', route => {
    decisionPayload = route.request().postDataJSON() as Record<string, unknown>;
    return route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
  });
  await signIn(page);
  await page.getByRole('button', { name: 'Financial memory' }).click();
  await expect(page.getByRole('heading', { name: 'What Artha knows about you' })).toBeVisible();
  await page.locator('#memory-card-monthly_income').getByRole('button', { name: '+ Add' }).click();
  await page.locator('#memory-card-monthly_expenses').getByRole('button', { name: '+ Add' }).click();
  await page.locator('#memory-monthly_income').fill('85000');
  await page.locator('#memory-monthly_expenses').fill('40000');
  await page.getByRole('button', { name: 'Review 2 changes' }).click();
  await page.getByLabel('I confirm these values and their dates are mine and correct.').check();
  await page.getByRole('button', { name: 'Confirm changes' }).click();
  await expect(page.getByRole('status')).toContainText('2 values were confirmed');
  expect((candidatePayload?.facts as unknown[])).toHaveLength(2);
  expect(decisionPayload?.decision).toBe('confirm');
});

test('Financial Memory is read-first, preserves unknown versus zero, and shows traced money left', async ({ page }) => {
  await mockAuthenticatedShell(page, [
    financialFact('monthly_income', '87600'), financialFact('monthly_expenses', '42000'),
    financialFact('monthly_debt_payments', '10000'), financialFact('total_liabilities', '0'),
  ]);
  await page.route('**/api/v1/agent/financial-memory/monthly-summary**', route => route.fulfill({
    status: 200, contentType: 'application/json', body: JSON.stringify({
      status: 'complete', month: '2026-09', missing: [], money_left: { amount: '35600.00', currency: 'INR' },
      calculation_id: '44444444-4444-4444-8444-444444444444', version: 'financial-memory-monthly-v1',
      timestamp: '2026-09-04T00:00:00Z', assumptions: { formula: 'monthly_income - monthly_expenses - monthly_debt_payments' },
    }),
  }));
  await signIn(page);
  await page.getByRole('button', { name: 'Financial memory' }).click();
  await expect(page.locator('#memory-card-monthly_income')).toContainText('₹87,600');
  await expect(page.locator('#memory-card-monthly_income').locator('input')).toHaveCount(0);
  await expect(page.locator('#memory-card-total_liabilities')).toContainText('₹0');
  await expect(page.locator('#memory-card-total_assets')).toContainText('Not added');
  await expect(page.locator('.money-left-card')).toContainText('₹35,600');
  await page.getByText('Calculation evidence').click();
  await expect(page.locator('.money-left-card')).toContainText('44444444-4444-4444-8444-444444444444');
});

test('Financial Memory does not expose a raw monthly-summary 404', async ({ page }) => {
  await mockAuthenticatedShell(page);
  await page.unroute('**/api/v1/agent/financial-memory/monthly-summary**');
  await page.route('**/api/v1/agent/financial-memory/monthly-summary**', route => route.fulfill({
    status: 404, contentType: 'application/json', body: JSON.stringify({ detail: 'Not Found' }),
  }));
  await signIn(page);
  await page.getByRole('button', { name: 'Financial memory' }).click();
  await expect(page.getByRole('heading', { name: 'What Artha knows about you' })).toBeVisible();
  await expect(page.getByRole('alert')).toHaveCount(0);
  await expect(page.getByText('Monthly calculation is temporarily unavailable. Your confirmed values are unchanged.')).toBeVisible();
  await expect(page.getByText('Not Found')).toHaveCount(0);
});

test('four verified basics including zero debt show the guided dashboard and accessible explanations', async ({ page }) => {
  await mockAuthenticatedShell(page, [
    financialFact('monthly_income', '85000'), financialFact('monthly_expenses', '40000'),
    financialFact('total_assets', '1250000'), financialFact('total_liabilities', '0'),
  ]);
  await signIn(page);
  await expect(page.getByRole('heading', { name: 'What do I have?' })).toBeVisible();
  await expect(page.getByText('Welcome to Artha')).toHaveCount(0);
  const explainIncome = page.getByRole('button', { name: 'Explain Monthly income' });
  await explainIncome.focus();
  await expect(page.getByRole('tooltip').filter({ hasText: 'money you receive' })).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(page.getByRole('tooltip').filter({ hasText: 'money you receive' })).not.toBeVisible();
});

test('browser host never uploads local financial documents', async ({ page }) => {
  await mockAuthenticatedShell(page);
  let documentRequests = 0;
  await page.route('**/api/v1/agent/documents**', route => {
    documentRequests += 1;
    return route.abort();
  });
  await signIn(page);
  await page.getByRole('button', { name: 'Documents' }).click();
  await expect(page.getByRole('heading', { name: 'Documents', exact: true })).toBeVisible();
  await expect(page.getByText('The supported desktop application is required. Browser uploads are disabled.')).toBeVisible();
  await expect(page.getByText('Your PDF stays on this device')).toBeVisible();
  expect(documentRequests).toBe(0);
});

test('Documents page summarizes confirmed document facts and hands off to Ask Artha', async ({ page }) => {
  await mockAuthenticatedShell(page, [
    financialFact('monthly_income', '87600', 'verified', 'local_document_confirmation'),
    financialFact('insurance_coverage', '5000000', 'verified', 'local_document_confirmation'),
  ]);
  await signIn(page);
  await page.getByRole('button', { name: 'Documents' }).click();
  await expect(page.getByText('Verified facts').locator('..').getByText('2')).toBeVisible();
  await expect(page.getByText('Added to Financial Memory')).toBeVisible();
  await page.getByRole('button', { name: /Ask Artha about this/ }).click();
  await expect(page.getByLabel('Ask about your finances')).toHaveValue('Help me understand the financial information I confirmed from my documents.');
});

test('registration UI requires a strong password and does not expose verification secrets', async ({ page }) => {
  await page.route('**/api/auth/register', route => route.fulfill({
    status: 202,
    contentType: 'application/json',
    body: JSON.stringify({ detail: 'Check your email for a verification link before signing in.' }),
  }));
  await page.goto('/');
  await page.getByRole('button', { name: 'Create an account' }).click();
  await page.getByLabel('Name (optional)').fill('Test User');
  await page.getByLabel('Email').fill('test@example.com');
  await page.getByLabel('Password').fill('LongerSecurePassword123');
  await page.getByRole('button', { name: 'Create account' }).click();
  await expect(page.getByRole('status')).toContainText('Check your email for a verification link');
  await expect(page.getByText('LongerSecurePassword123')).not.toBeVisible();
});

test('MFA sign-in requires an authenticator code before financial data loads', async ({ page }) => {
  await page.route('**/api/auth/token', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ mfa_required: true, mfa_enrollment_required: false, mfa_challenge_token: 'challenge-token-for-browser-test' }),
  }));
  await page.route('**/api/auth/mfa/verify', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ access_token: 'mfa-browser-test-token', refresh_token: 'refresh-browser-test-token' }),
  }));
  await page.route('**/api/v1/agent/financial-facts', route => route.fulfill({ status: 200, contentType: 'application/json', body: '[]' }));
  await page.route('**/api/v1/agent/reviews', route => route.fulfill({ status: 200, contentType: 'application/json', body: '[]' }));

  await page.goto('/');
  await page.getByLabel('Email').fill('test@example.com');
  await page.getByLabel('Password').fill('LongerSecurePassword123');
  await page.getByRole('button', { name: 'Sign in securely' }).click();
  await expect(page.getByRole('heading', { name: 'Secure your sign-in' })).toBeVisible();
  await expect(page.getByLabel('Authenticator code')).toBeVisible();
  await page.getByLabel('Authenticator code').fill('123456');
  await page.getByRole('button', { name: 'Verify and sign in' }).click();
  await expect(page.getByRole('heading', { name: 'Financial Freedom Agent' })).toBeVisible();
});

test('Ask Artha starts as simple chat and requests advanced details only when needed', async ({ page }) => {
  await mockAuthenticatedShell(page);
  await page.route(`**/api/v1/agent/conversations/${conversationId}/messages`, route => route.fulfill({
    status: 200, contentType: 'application/json',
    body: JSON.stringify({
      message_id: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa', role: 'assistant',
      content: 'I need a few details from you before I can calculate that.', created_at: new Date().toISOString(),
      blocks: [{ type: 'missing_data', fields: ['current age', 'target age', 'current monthly lifestyle expenses'] }],
    }),
  }));

  await signIn(page);
  await page.getByRole('navigation').getByRole('button', { name: 'Ask Artha' }).click();
  await expect(page.getByText('Add confirmed freedom scenario inputs')).toHaveCount(0);
  await expect(page.getByText('Cloud-assisted explanations')).toHaveCount(0);
  await expect(page.getByText('Optional insurance coverage comparison')).toHaveCount(0);
  await page.getByLabel('Ask about your finances').fill('Can I retire at 55?');
  await page.getByRole('button', { name: 'Send' }).click();
  await expect(page.getByText('I need a little more information')).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Tell me about the future you want to plan for' })).toBeVisible();
  await expect(page.getByText('Inflation rate you want to use')).toHaveCount(0);
  await expect(page.getByText('Return rate you want to test')).toHaveCount(0);
  await expect(page.getByText('Withdrawal rate you want to use')).toHaveCount(0);
  const expenseHelp = page.getByRole('button', { name: 'Explain Monthly living expenses (₹)' });
  await expect(expenseHelp).toBeVisible();
  await expenseHelp.hover();
  await expect(page.getByRole('tooltip')).toContainText('Your regular monthly spending today');
});

async function signIn(page: Page) {
  await page.goto('/');
  await page.getByLabel('Email').fill('test@example.com');
  await page.getByLabel('Password').fill('test-password');
  await page.getByRole('button', { name: 'Sign in securely' }).click();
  await expect(page.getByRole('heading', { name: 'Financial Freedom Agent' })).toBeVisible();
}

test('user can cancel and safely retry the same idempotent agent request', async ({ page }) => {
  await mockAuthenticatedShell(page);
  const requestIds: string[] = [];
  let attempts = 0;
  await page.route(`**/api/v1/agent/conversations/${conversationId}/messages`, async route => {
    attempts += 1;
    const payload = route.request().postDataJSON() as { client_request_id: string };
    requestIds.push(payload.client_request_id);
    if (attempts === 1) {
      await new Promise(resolve => setTimeout(resolve, 2_000));
    }
    await route.fulfill({
      status: 200, contentType: 'application/json',
      body: JSON.stringify({
        message_id: '22222222-2222-4222-8222-222222222222',
        run_id: '33333333-3333-4333-8333-333333333333', role: 'assistant',
        content: 'Your verified calculation is ready.', created_at: new Date().toISOString(),
        blocks: [{ type: 'calculation', calculation_id: '44444444-4444-4444-8444-444444444444', version: 'test-v1', result: { monthly_surplus: '1000.00' }, assumptions: {}, limitations: [] }],
      }),
    });
  });
  await signIn(page);
  await page.getByRole('navigation').getByRole('button', { name: 'Ask Artha' }).click();
  await page.getByLabel('Ask about your finances').fill('Show my monthly surplus');
  await page.getByRole('button', { name: 'Send' }).click();
  await page.getByRole('button', { name: 'Cancel' }).click();
  await expect(page.getByRole('alert')).toContainText('Response cancelled');
  await page.getByRole('button', { name: 'Retry request' }).click();
  await expect(page.getByText('Your verified calculation is ready.')).toBeVisible();
  await page.getByText('Calculation evidence · test-v1').click();
  await expect(page.getByText('Calculation ID: 44444444-4444-4444-8444-444444444444')).toBeVisible();
  expect(requestIds).toHaveLength(2);
  expect(requestIds[0]).toBe(requestIds[1]);
});

test('expired authorization returns the user to sign-in without exposing data', async ({ page }) => {
  await mockAuthenticatedShell(page);
  await page.route(`**/api/v1/agent/conversations/${conversationId}/messages`, route => route.fulfill({
    status: 401, contentType: 'application/json', body: JSON.stringify({ detail: 'Not authenticated' }),
  }));
  await signIn(page);
  await page.getByRole('navigation').getByRole('button', { name: 'Ask Artha' }).click();
  await page.getByLabel('Ask about your finances').fill('Show my net worth');
  await page.getByRole('button', { name: 'Send' }).click();
  await expect(page.getByRole('heading', { name: 'Your financial-freedom agent' })).toBeVisible();
  await expect(page.getByRole('alert')).toContainText('session has expired');
  await expect(page.getByText('Show my net worth')).not.toBeVisible();
});

test('partial agent failure is visible and retryable without duplicating the user message', async ({ page }) => {
  await mockAuthenticatedShell(page);
  let attempts = 0;
  await page.route(`**/api/v1/agent/conversations/${conversationId}/messages`, route => {
    attempts += 1;
    if (attempts === 1) {
      return route.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({ detail: 'A deterministic tool is temporarily unavailable' }) });
    }
    return route.fulfill({
      status: 200, contentType: 'application/json',
      body: JSON.stringify({ message_id: '55555555-5555-4555-8555-555555555555', run_id: '66666666-6666-4666-8666-666666666666', role: 'assistant', content: 'The retry completed.', blocks: [], created_at: new Date().toISOString() }),
    });
  });
  await signIn(page);
  await page.getByRole('navigation').getByRole('button', { name: 'Ask Artha' }).click();
  await page.getByLabel('Ask about your finances').fill('Review my cash flow');
  await page.getByRole('button', { name: 'Send' }).click();
  await expect(page.getByRole('alert')).toContainText('temporarily unavailable');
  await page.getByRole('button', { name: 'Retry request' }).click();
  await expect(page.getByText('The retry completed.')).toBeVisible();
  await expect(page.getByText('Review my cash flow')).toHaveCount(1);
});

test('planning action is persisted only through an explicit confirmation', async ({ page }) => {
  await mockAuthenticatedShell(page);
  await page.route('**/api/v1/agent/planning/candidates', route => route.fulfill({
    status: 200, contentType: 'application/json',
    body: JSON.stringify({ actions: [{ action_type: 'increase_monthly_savings', monthly_amount: '5000.00', score: '0.80', rationale: 'Based on your explicit feasibility and priority.', impact: { annual_cash_flow_change: '60000.00' } }] }),
  }));
  await page.route(`**/api/v1/agent/conversations/${conversationId}/confirmations`, route => route.fulfill({
    status: 201, contentType: 'application/json',
    body: JSON.stringify({ confirmation_id: '77777777-7777-4777-8777-777777777777' }),
  }));
  let planPayload: Record<string, unknown> | undefined;
  await page.route('**/api/v1/agent/planning/plans', route => {
    planPayload = route.request().postDataJSON() as Record<string, unknown>;
    return route.fulfill({ status: 201, contentType: 'application/json', body: JSON.stringify({ plan_id: '88888888-8888-4888-8888-888888888888' }) });
  });
  await signIn(page);
  await page.getByRole('button', { name: 'My Plan' }).click();
  await expect(page.getByRole('heading', { name: 'Turn intentions into manageable actions' })).toBeVisible();
  await page.getByRole('button', { name: 'Create your first action' }).click();
  await page.getByLabel('Monthly amount (₹)').fill('5000');
  await page.getByRole('button', { name: 'Review action' }).click();
  await expect(page.getByRole('button', { name: 'Confirm and add' })).toBeDisabled();
  await page.getByLabel('I confirm this is the action I want added to My Plan.').check();
  await page.getByRole('button', { name: 'Confirm and add' }).click();
  await expect(page.getByRole('status')).toContainText('added to My Plan');
  expect(planPayload?.confirmation_id).toBe('77777777-7777-4777-8777-777777777777');
});

test('My Plan shows trusted progress and supports explicit check-ins and pause', async ({ page }) => {
  await mockAuthenticatedShell(page);
  await page.unroute('**/api/v1/agent/planning/plans/active');
  const action = {
    action_id: '99999999-9999-4999-8999-999999999999', action_type: 'increase_monthly_savings',
    monthly_amount: '5000.00', target_amount: '60000.00', currency: 'INR', status: 'active',
    start_date: '2026-09-01', target_date: '2027-08-31', priority_label: 'high', difficulty_label: 'manageable',
    rationale: 'Based on your choices.', impact: {}, progress: { progress_amount: '15000.00', target_amount: '60000.00', percentage: '25.00', currency: 'INR' },
  };
  await page.route('**/api/v1/agent/planning/plans/active', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ plan: { plan_id: 'plan-1', title: 'My financial action plan', created_at: '2026-09-01T00:00:00Z' }, summary: { active_count: 1, monthly_commitment: { amount: '5000.00', currency: 'INR' }, completed_count: 0 }, active_actions: [action], completed_actions: [], archived_actions: [], calculation_id: 'summary-1', version: 'action-tracking-v1', timestamp: '2026-09-04T00:00:00Z', assumptions: {}, limitations: ['Progress is based on check-ins'] }) }));
  let checkInPayload: Record<string, unknown> | undefined;
  await page.route('**/api/v1/agent/planning/actions/*/check-ins', route => { checkInPayload = route.request().postDataJSON() as Record<string, unknown>; return route.fulfill({ status: 201, contentType: 'application/json', body: JSON.stringify({ progress: action.progress }) }); });
  let statusPayload: Record<string, unknown> | undefined;
  await page.route('**/api/v1/agent/planning/actions/*/status', route => { statusPayload = route.request().postDataJSON() as Record<string, unknown>; return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ...action, status: 'paused' }) }); });
  await signIn(page);
  await page.getByRole('button', { name: 'My Plan' }).click();
  await expect(page.getByText('25.00%')).toBeVisible();
  await expect(page.locator('.action-body small').filter({ hasText: 'Based on your check-ins' })).toBeVisible();
  await page.getByRole('button', { name: 'Check in' }).click();
  await page.getByLabel('Amount completed (₹)').fill('5000');
  await page.getByLabel('Note (optional)').fill('September transfer');
  await page.getByRole('button', { name: 'Add check-in' }).click();
  expect(checkInPayload?.amount).toBe('5000');
  await page.getByRole('button', { name: 'Pause' }).click();
  expect(statusPayload?.status).toBe('paused');
});

test('My Plan does not expose a raw active-plan 404', async ({ page }) => {
  await mockAuthenticatedShell(page);
  await page.unroute('**/api/v1/agent/planning/plans/active');
  await page.route('**/api/v1/agent/planning/plans/active', route => route.fulfill({ status: 404, contentType: 'application/json', body: JSON.stringify({ detail: 'Not Found' }) }));
  await signIn(page);
  await page.getByRole('button', { name: 'My Plan' }).click();
  await expect(page.getByRole('alert')).toContainText('My Plan is temporarily unavailable');
  await expect(page.getByText('Not Found')).toHaveCount(0);
});
