const { test, expect } = require('@playwright/test');
const path = require('path');

const SCREENSHOT_DIR = path.join(__dirname, 'screenshots');

test.describe('VL Silks Login Page Mobile UX & Interactive Demo Tests', () => {

  const viewports = [
    { name: '360x800 Mobile', width: 360, height: 800 },
    { name: '390x844 Mobile (iPhone 14)', width: 390, height: 844 },
    { name: '768x1024 Tablet', width: 768, height: 1024 },
    { name: '1366x768 Desktop', width: 1366, height: 768 },
  ];

  for (const vp of viewports) {
    test(`Login Page Layout & Zero Overflow on ${vp.name}`, async ({ page }) => {
      const consoleErrors = [];
      page.on('console', msg => {
        if (msg.type() === 'error') consoleErrors.push(msg.text());
      });

      await page.setViewportSize({ width: vp.width, height: vp.height });
      const response = await page.goto('/login');
      expect(response.status()).toBe(200);

      // Verify no horizontal overflow
      const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
      const clientWidth = await page.evaluate(() => document.documentElement.clientWidth);
      expect(scrollWidth).toBeLessThanOrEqual(clientWidth + 2);

      // Verify essential visual elements
      await expect(page.locator('.vl-login-title')).toBeVisible();
      await expect(page.locator('#email')).toBeVisible();
      await expect(page.locator('#password')).toBeVisible();
      await expect(page.locator('#btnSubmitLogin')).toBeVisible();
      await expect(page.locator('#demoCredentialsSection')).toBeVisible();
      await expect(page.locator('#btnAdminDemo')).toBeVisible();
      await expect(page.locator('#btnStaffDemo')).toBeVisible();

      // On desktop, brand pane should be visible; on mobile/tablet it should be hidden cleanly
      if (vp.width >= 992) {
        await expect(page.locator('.vl-login-brand-pane')).toBeVisible();
      } else {
        await expect(page.locator('.vl-login-brand-pane')).toBeHidden();
      }

      // Check for zero console errors
      expect(consoleErrors.length).toBe(0);

      await page.screenshot({
        path: path.join(SCREENSHOT_DIR, `login_${vp.width}x${vp.height}.png`),
        fullPage: true
      });
    });
  }

  test('One-Tap Admin & Staff Demo Credentials Auto-Fill', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto('/login');

    const emailInput = page.locator('#email');
    const passInput = page.locator('#password');

    // Initial state: empty fields
    await emailInput.fill('');
    await passInput.fill('');

    // 1. Test "Use Admin Demo"
    await page.click('#btnAdminDemo');
    await expect(emailInput).toHaveValue('admin@vlsilks.com');
    await expect(passInput).toHaveValue('Admin@123');
    // Ensure form is NOT auto-submitted (URL is still /login)
    expect(page.url()).toContain('/login');
    await expect(page.locator('#btnAdminDemo')).toContainText('Filled!');

    // 2. Test "Use Staff Demo"
    await page.click('#btnStaffDemo');
    await expect(emailInput).toHaveValue('staff@vlsilks.com');
    await expect(passInput).toHaveValue('Staff@123');
    expect(page.url()).toContain('/login');
    await expect(page.locator('#btnStaffDemo')).toContainText('Filled!');

    // 3. Click Sign In and verify successful login
    await page.click('#btnSubmitLogin');
    await page.waitForURL('**/dashboard');
    expect(page.url()).toContain('/dashboard');
    await expect(page.locator('body')).toContainText('Shop Performance Dashboard');
  });

  test('Copy Buttons for Admin and Staff Credentials with Feedback State', async ({ page, context }) => {
    // Grant clipboard permissions
    await context.grantPermissions(['clipboard-read', 'clipboard-write']);
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto('/login');

    // 1. Copy Admin Email
    const copyAdminEmailBtn = page.locator('#btnCopyAdminEmail');
    await expect(copyAdminEmailBtn).toBeVisible();
    await copyAdminEmailBtn.click();
    await expect(copyAdminEmailBtn).toHaveClass(/copied/);

    // Verify clipboard content
    const clipboardEmail = await page.evaluate(() => navigator.clipboard.readText());
    expect(clipboardEmail).toBe('admin@vlsilks.com');

    // 2. Copy Admin Password
    const copyAdminPassBtn = page.locator('#btnCopyAdminPass');
    await copyAdminPassBtn.click();
    await expect(copyAdminPassBtn).toHaveClass(/copied/);
    const clipboardPass = await page.evaluate(() => navigator.clipboard.readText());
    expect(clipboardPass).toBe('Admin@123');

    // 3. Copy Staff Email
    const copyStaffEmailBtn = page.locator('#btnCopyStaffEmail');
    await copyStaffEmailBtn.click();
    await expect(copyStaffEmailBtn).toHaveClass(/copied/);
    const clipboardStaffEmail = await page.evaluate(() => navigator.clipboard.readText());
    expect(clipboardStaffEmail).toBe('staff@vlsilks.com');

    // 4. Copy Staff Password
    const copyStaffPassBtn = page.locator('#btnCopyStaffPass');
    await copyStaffPassBtn.click();
    await expect(copyStaffPassBtn).toHaveClass(/copied/);
    const clipboardStaffPass = await page.evaluate(() => navigator.clipboard.readText());
    expect(clipboardStaffPass).toBe('Staff@123');
  });

});
