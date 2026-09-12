import { expect, test } from '@playwright/test';

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
