import { expect, test, type Page } from '@playwright/test';

const conversationId = '11111111-1111-4111-8111-111111111111';

async function mockAuthenticatedShell(page: Page) {
  await page.route('**/api/auth/token', route => route.fulfill({
    status: 200, contentType: 'application/json',
    body: JSON.stringify({ access_token: 'browser-test-token' }),
  }));
  await page.route('**/api/v1/agent/financial-facts', route => route.fulfill({ status: 200, contentType: 'application/json', body: '[]' }));
  await page.route('**/api/v1/agent/reviews', route => route.fulfill({ status: 200, contentType: 'application/json', body: '[]' }));
  await page.route('**/api/v1/agent/conversations', route => route.fulfill({
    status: 201, contentType: 'application/json',
    body: JSON.stringify({ conversation_id: conversationId }),
  }));
}

test('browser host never uploads local financial documents', async ({ page }) => {
  await mockAuthenticatedShell(page);
  let documentRequests = 0;
  await page.route('**/api/v1/agent/documents**', route => {
    documentRequests += 1;
    return route.abort();
  });
  await signIn(page);
  await page.getByRole('button', { name: 'Documents' }).click();
  await page.getByText('Local document review').click();
  await expect(page.getByText('Desktop application required')).toBeVisible();
  await expect(page.getByText('No upload will be sent to the server.')).toBeVisible();
  expect(documentRequests).toBe(0);
});

test('cloud assistance requires explicit per-conversation consent and explains its boundary', async ({ page }) => {
  await mockAuthenticatedShell(page);
  let consentPayload: Record<string, unknown> | undefined;
  await page.route(`**/api/v1/agent/conversations/${conversationId}/cloud-assistance`, route => {
    if (route.request().method() === 'POST') {
      consentPayload = route.request().postDataJSON() as Record<string, unknown>;
    }
    return route.fulfill({
      status: 201,
      contentType: 'application/json',
      body: JSON.stringify({
        consent_id: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
        status: 'active',
        provider: 'OpenAI',
        purpose: 'Plain-language explanation of deterministic financial evidence',
        policy_bundle_version: 'cloud-explanation-v1',
        data_categories: ['agent_intent', 'verified_financial_facts', 'deterministic_calculation_evidence'],
        excluded_categories: ['original_documents', 'document_text', 'file_paths', 'user_identifiers', 'unverified_facts', 'raw_user_message'],
        retention_url: 'https://platform.openai.com/docs/models/default-usage-policies-by-endpoint',
      }),
    });
  });

  await signIn(page);
  await page.getByRole('navigation').getByRole('button', { name: 'Ask Artha' }).click();
  await expect(page.getByRole('heading', { name: 'Cloud-assisted explanations' })).toBeVisible();
  await expect(page.getByText('It never receives original documents, extracted text, file paths, identifiers, unverified facts, or your raw message.')).toBeVisible();
  await page.getByRole('button', { name: 'Enable cloud assistance' }).click();
  await expect(page.getByText('Enabled for this conversation')).toBeVisible();
  expect(consentPayload).toEqual({ privacy_notice_version: 'render-singapore-pilot-v1' });
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
  await page.getByRole('button', { name: 'Plans' }).click();
  await page.getByText('Compare and confirm a planning action').click();
  await page.getByLabel('Monthly amount (₹)').fill('5000');
  await page.getByRole('button', { name: 'Calculate impact' }).click();
  await expect(page.getByText('Based on your explicit feasibility and priority.')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Create confirmed plan' })).toBeDisabled();
  await page.getByLabel('I confirm this action should be added to my plan.').check();
  await page.getByRole('button', { name: 'Create confirmed plan' }).click();
  await expect(page.getByRole('status')).toContainText('added to the plan');
  expect(planPayload?.confirmation_id).toBe('77777777-7777-4777-8777-777777777777');
});
