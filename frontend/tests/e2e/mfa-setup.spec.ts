import { expect, test } from '@playwright/test';

test.beforeEach(async ({ page }) => {
  await page.route('**/api/auth/capabilities', route => route.fulfill({ json: {
    registration_available: true, password_reset_available: true,
  } }));
});

test('MFA enrollment shows a local QR and manual fallback and submits its challenge', async ({ page }) => {
  const secret = 'JBSWY3DPEHPK3PXP'; // Synthetic fixture only.
  const requests: string[] = [];
  page.on('request', request => requests.push(request.url()));
  await page.route('**/api/auth/token', route => route.fulfill({ json: {
    mfa_enrollment_required: true, mfa_challenge_token: 'synthetic-enrollment-challenge',
  } }));
  await page.route('**/api/auth/mfa/enrollment', route => route.fulfill({ json: {
    secret, issuer: 'Artha', account_name: 'qr-test@example.com',
  } }));
  await page.route('**/api/auth/mfa/enrollment/confirm', async route => {
    expect(route.request().postDataJSON()).toEqual({
      challenge_token: 'synthetic-enrollment-challenge', code: '123456',
    });
    await route.fulfill({ status: 401, json: { detail: 'Authenticator code is invalid' } });
  });
  await page.setViewportSize({ width: 375, height: 900 });
  await page.goto('/');
  await page.getByLabel('Email', { exact: true }).fill('qr-test@example.com');
  await page.getByLabel('Password', { exact: true }).fill('SyntheticPassword123');
  await page.getByRole('button', { name: 'Sign in securely' }).click();
  const qr = page.getByRole('img', { name: 'Scan to set up your authenticator' });
  await expect(qr).toBeVisible();
  expect(await qr.evaluate(element => element.tagName.toLowerCase())).toBe('svg');
  await expect(page.getByText(secret, { exact: true })).toBeHidden();
  await page.getByText('Can’t scan? Enter a setup key instead').click();
  await expect(page.getByText(secret, { exact: true })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.getByLabel('Authenticator code', { exact: true }).fill('123456');
  await page.getByRole('button', { name: 'Enable MFA and sign in' }).click();
  await expect(page.getByRole('alert')).toContainText('Authenticator code is invalid');
  expect(requests.every(url => !url.includes(secret) && !url.includes('otpauth'))).toBe(true);
});

test('registration availability, pending submission and resend verification', async ({ page }) => {
  await page.route('**/api/auth/capabilities', route => route.fulfill({ json: { registration_available: true, password_reset_available: true } }));
  let count = 0;
  await page.route('**/api/auth/register', async route => {
    count += 1;
    await route.fulfill({ status: 202, json: { detail: 'Check your inbox for a verification link.' } });
  });
  await page.route('**/api/auth/verification/resend', route => route.fulfill({ status: 202, json: { detail: 'If the account needs verification, an email will arrive shortly.' } }));
  await page.goto('/');
  await page.getByRole('button', { name: 'Create an account' }).click();
  await page.getByLabel('Email', { exact: true }).fill('synthetic@example.com');
  await page.getByLabel('Password', { exact: true }).fill('SyntheticPassword123');
  await page.getByRole('button', { name: 'Create account', exact: true }).click();
  await expect(page.getByRole('status')).toContainText('Check your inbox');
  expect(count).toBe(1);
  await page.getByRole('button', { name: 'Resend verification email' }).click();
  await expect(page.getByRole('status')).toContainText('If the account needs verification');
});

test('disabled registration hides account actions while sign-in remains available', async ({ page }) => {
  await page.route('**/api/auth/capabilities', route => route.fulfill({ json: { registration_available: false, password_reset_available: false } }));
  await page.goto('/');
  await expect(page.getByRole('button', { name: 'Sign in securely' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Create an account' })).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Forgot password?' })).toHaveCount(0);
});

test('email verification removes the token and guides desktop users back to the agent', async ({ page }) => {
  let count = 0;
  await page.route('**/api/auth/verify-email', async route => {
    count += 1;
    await route.fulfill({ json: { detail: 'Email verified. Sign in here or return to the desktop agent to sign in and set up your authenticator.' } });
  });
  await page.goto('/verify-email?token=synthetic-verification-token');
  await expect(page.getByRole('status')).toContainText('return to the desktop agent');
  expect(page.url()).not.toContain('token=');
  expect(count).toBe(1);
});
