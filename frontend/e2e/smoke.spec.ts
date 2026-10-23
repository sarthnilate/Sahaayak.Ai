import { test, expect } from '@playwright/test';

test.describe('Sahaayak AI Phase 2 - Auth, RBAC & Report Intake', () => {
  test.beforeEach(async ({ page }) => {
    // Clear cookies for test isolation
    await page.context().clearCookies();
  });

  test('unauthenticated user sees login screen with demo credentials hint', async ({ page }) => {
    await page.goto('http://127.0.0.1:5173');

    // Brand and login form
    await expect(page.locator('h1')).toContainText('SAHAAYAK.AI');
    await expect(page.locator('button[type="submit"]')).toBeVisible();
    await expect(page.getByText('Demo Credentials')).toBeVisible();
  });

  test('coordinator login loads full command center with all ops tabs', async ({ page }) => {
    await page.goto('http://127.0.0.1:5173');

    // Fill login
    await page.locator('#auth-email').fill('coordinator@sahaayak.ai');
    await page.locator('#auth-password').fill('CoordPass@2026');
    await page.locator('button[type="submit"]').click();

    // Verify coordinator session is active
    await expect(page.locator('nav')).toBeVisible({ timeout: 10000 });
    await expect(page.getByText('coordinator').first()).toBeVisible();

    // Verify coordinator has full operational tabs
    await expect(page.locator('nav button', { hasText: 'Dashboard' })).toBeVisible();
    await expect(page.locator('nav button', { hasText: 'Submit Report' })).toBeVisible();
    await expect(page.locator('nav button', { hasText: 'Reports Intake' })).toBeVisible();
    await expect(page.locator('nav button', { hasText: 'Incidents & Map' })).toBeVisible();
    await expect(page.locator('nav button', { hasText: 'Tasks & Dispatch' })).toBeVisible();
    await expect(page.locator('nav button', { hasText: 'Audit Trail' })).toBeVisible();
  });

  test('reporter login loads scoped intake view and allows incident submission', async ({ page }) => {
    await page.goto('http://127.0.0.1:5173');

    // Fill reporter login
    await page.locator('#auth-email').fill('reporter@sahaayak.ai');
    await page.locator('#auth-password').fill('ReporterPass@2026');
    await page.locator('button[type="submit"]').click();

    // Verify reporter session is active
    await expect(page.locator('nav')).toBeVisible({ timeout: 10000 });
    await expect(page.getByText('reporter').first()).toBeVisible();

    // Verify reporter only sees Submit Report tab (no admin/coordinator tabs)
    await expect(page.locator('nav button', { hasText: 'Submit Report' })).toBeVisible();
    await expect(page.locator('nav button', { hasText: 'Dashboard' })).toHaveCount(0);
    await expect(page.locator('nav button', { hasText: 'Tasks & Dispatch' })).toHaveCount(0);

    // Fill and submit a new report
    await page.locator('#report-text').fill('High flood water entering colony gate in Kurla West near railway bridge. Vehicles submerged.');
    await page.locator('#report-location').fill('Kurla West Railway Bridge, Mumbai');
    await page.locator('button[type="submit"]').click();

    // Verify reference code confirmation
    await expect(page.getByText('Report Submitted Successfully')).toBeVisible({ timeout: 10000 });
    await expect(page.getByText(/SAH-2026-/)).toBeVisible();
  });

  test('Phase 3: coordinator views dual-column AI extraction detail and tests retry', async ({ page }) => {
    await page.goto('http://127.0.0.1:5173');

    // Login as coordinator
    await page.locator('#auth-email').fill('coordinator@sahaayak.ai');
    await page.locator('#auth-password').fill('CoordPass@2026');
    await page.locator('button[type="submit"]').click();

    await expect(page.locator('nav')).toBeVisible({ timeout: 10000 });

    // Switch to Reports Intake tab
    await page.locator('nav button', { hasText: 'Reports Intake' }).click();

    // Verify global AI Mode badge is visible
    await expect(page.getByTestId('global-ai-mode-badge')).toContainText('DEMO MODE (simulated)');

    // Inspect the first report
    await page.getByText('INSPECT EXTRACTION').first().click();

    // Verify modal dialog opens
    const dialog = page.getByRole('dialog');
    await expect(dialog).toBeVisible();
    await expect(dialog.getByTestId('detail-demo-badge')).toBeVisible();

    // Verify 2 columns and all Phase 3 sections
    await expect(dialog.getByText('Reported (by the person)')).toBeVisible();
    await expect(dialog.getByText('Extracted by AI')).toBeVisible();
    await expect(dialog.getByText('Inferred by AI')).toBeVisible();
    await expect(dialog.getByText('Unknown / Missing')).toBeVisible();
    await expect(dialog.getByText('Needs Follow-Up')).toBeVisible();

    // Verify retry button with aria-live exists
    const retryBtn = dialog.getByTestId('retry-button');
    await expect(retryBtn).toBeVisible();
    await retryBtn.click();

    // Wait for retry completion
    await expect(dialog.getByText(/Retry succeeded!/i)).toBeVisible({ timeout: 10000 });

    // Close modal
    await dialog.getByText('CLOSE').click();
    await expect(dialog).not.toBeVisible();
  });
});
