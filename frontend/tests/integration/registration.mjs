// Invoked only by the disposable PostgreSQL fixture; email never leaves the test process.
import { chromium } from '@playwright/test';
import { existsSync, readFileSync } from 'node:fs';
import { createHmac, randomUUID } from 'node:crypto';
import assert from 'node:assert/strict';
const origin = process.env.ARTHA_BROWSER_URL;
assert(origin && process.env.ARTHA_TEST_MAIL_CAPTURE);
function totp(secret) {
  const alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567';
  const bits = [...secret].map(c => alphabet.indexOf(c).toString(2).padStart(5, '0')).join('');
  const key = Buffer.from(bits.match(/.{8}/g).map(byte => parseInt(byte, 2)));
  const counter = Buffer.alloc(8);
  counter.writeBigUInt64BE(BigInt(Math.floor(Date.now() / 30000)));
  const digest = createHmac('sha1', key).update(counter).digest();
  const offset = digest[19] & 15;
  return ((digest.readUInt32BE(offset) & 0x7fffffff) % 1000000).toString().padStart(6, '0');
}
const browser = await chromium.launch(existsSync('/usr/bin/google-chrome') ? { executablePath: '/usr/bin/google-chrome' } : {});
try {
  for (const desktop of [false, true]) {
    const context = await browser.newContext();
    if (desktop) await context.addInitScript(() => {
      window.__TAURI_INTERNALS__ = { invoke: async () => ({ available: false, limitations: ['Synthetic test host'] }) };
    });
    const page = await context.newPage();
    await page.goto(origin);
    await page.getByRole('button', { name: 'Create an account' }).click();
    const email = `${randomUUID()}@example.com`;
    const password = `Synthetic${randomUUID()}123`;
    await page.getByLabel('Email', { exact: true }).fill(email);
    await page.getByLabel('Password', { exact: true }).fill(password);
    await page.getByRole('button', { name: 'Create account', exact: true }).click();
    await page.getByRole('button', { name: 'Resend verification email' }).waitFor();
    const token = readFileSync(process.env.ARTHA_TEST_MAIL_CAPTURE, 'utf8');
    const verification = await browser.newPage();
    await verification.goto(`${origin}/verify-email?token=${token}`);
    await verification.getByRole('status').filter({ hasText: 'Email verified' }).waitFor();
    assert(!verification.url().includes('token='));
    await page.getByRole('button', { name: 'Back to sign in' }).click();
    await page.getByLabel('Password', { exact: true }).fill(password);
    const enrollment = page.waitForResponse(response => response.url().endsWith('/api/auth/mfa/enrollment'));
    await page.getByRole('button', { name: 'Sign in securely' }).click();
    const setup = await (await enrollment).json();
    await page.getByLabel('Authenticator code', { exact: true }).fill(totp(setup.secret));
    await page.getByRole('button', { name: 'Enable MFA and sign in' }).click();
    await page.getByRole('button', { name: 'Enable MFA and sign in' }).waitFor({ state: 'hidden' });
    assert.equal(await page.getByLabel('Password', { exact: true }).count(), 0);
    await verification.close();
    await context.close();
  }
} finally {
  await browser.close();
}
