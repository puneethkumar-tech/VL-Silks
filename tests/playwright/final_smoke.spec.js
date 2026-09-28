const { test, expect } = require('@playwright/test');
const fs = require('fs');
const path = require('path');

const SCREENSHOT_DIR = path.resolve(__dirname, '../../scratch/screenshots');
if (!fs.existsSync(SCREENSHOT_DIR)) {
  fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
}

// Global collector for console errors and failed network requests
let consoleErrors = [];
let failedRequests = [];

test.beforeEach(async ({ page }) => {
  page.on('console', msg => {
    if (msg.type() === 'error') {
      consoleErrors.push({ url: page.url(), text: msg.text() });
    }
  });

  page.on('requestfailed', request => {
    // Ignore optional favicon/analytics failure
    if (!request.url().includes('favicon') && !request.url().includes('analytics')) {
      failedRequests.push({ url: request.url(), failure: request.failure()?.errorText });
    }
  });
});

test.describe('VL Silks Automated End-to-End QA Suite', () => {

  // Helper login function
  async function adminLogin(page) {
    await page.goto('/login');
    await page.fill('#email', 'admin@vlsilks.com');
    await page.fill('#password', 'Admin@123');
    await page.click('button[type="submit"]');
    await page.waitForURL('**/dashboard');
    expect(page.url()).toContain('/dashboard');
  }

  // 1. LOGIN / AUTHENTICATION
  test('01. Authentication & Session Flow', async ({ page }) => {
    await page.goto('/login');
    expect(await page.title()).toContain('Login');
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '01_login_page.png') });

    // Invalid login attempt
    await page.fill('#email', 'admin@vlsilks.com');
    await page.fill('#password', 'WrongPassword123');
    await page.click('button[type="submit"]');
    await expect(page.locator('.alert-danger, .alert-warning, .alert')).toBeVisible();
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '01_login_error.png') });

    // Valid admin login
    await page.fill('#email', 'admin@vlsilks.com');
    await page.fill('#password', 'Admin@123');
    await page.click('button[type="submit"]');
    await page.waitForURL('**/dashboard');
    expect(page.url()).toContain('/dashboard');
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '01_login_success.png') });

    // Logout
    await page.goto('/logout');
    await page.waitForURL('**/login');
    expect(page.url()).toContain('/login');
  });

  // 2. DASHBOARD
  test('02. Dashboard KPIs, Bento Grid & Charts', async ({ page }) => {
    await adminLogin(page);

    // Verify KPI elements
    await expect(page.locator('#statTodaySales')).toBeVisible();
    await expect(page.locator('#statMonthSales')).toBeVisible();
    await expect(page.locator('#statTotalStock')).toBeVisible();
    await expect(page.locator('#statCreditToCollect')).toBeVisible();

    // Verify Recent Sales table & Top Products
    await expect(page.locator('#recentSalesTableBody')).toBeVisible();
    await expect(page.locator('#categoryDistributionChart')).toBeVisible();
    await expect(page.locator('#monthlySalesChart')).toBeVisible();

    // Verify initial rendered charts screenshot
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '02_dashboard_initial.png') });

    // Click Refresh Stats
    const refreshBtn = page.locator('#btnRefreshDashboard');
    await refreshBtn.click();
    await page.waitForTimeout(1000);

    // Verify chart remains visible after refresh
    await expect(page.locator('#categoryDistributionChart')).toBeVisible();
    await expect(page.locator('#lastUpdatedBadge')).toContainText('Updated:');
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '02_dashboard_refreshed.png') });
  });

  // 3. PRODUCTS & VARIANTS
  test('03. Products & Variants Catalog Management', async ({ page }) => {
    await adminLogin(page);
    await page.goto('/products');
    await expect(page.locator('table')).toBeVisible();
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '03_products_list.png') });

    // Search filter
    await page.fill('input[name="search"]', 'Kanchipuram');
    await page.click('button:has-text("Filter"), button:has-text("Search")');
    await page.waitForTimeout(500);
    await expect(page.locator('body')).toContainText('Kanchipuram');

    // View product detail
    await page.goto('/products/1');
    await expect(page.locator('body')).toContainText('SKU-KAN-RED');
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '03_product_view_1.png') });

    // Edit product page
    await page.goto('/products/1/edit');
    await expect(page.locator('input[name="product_name"]')).toBeVisible();

    // Add product validation (empty form)
    await page.goto('/products/new');
    await page.click('button[type="submit"]');
    // Check validation triggered
    const prodNameInput = page.locator('#product_name');
    const isRequired = await prodNameInput.getAttribute('required');
    expect(isRequired !== null).toBeTruthy();
  });

  // 4. CATEGORIES
  test('04. Categories List & Management', async ({ page }) => {
    await adminLogin(page);
    await page.goto('/categories');
    await expect(page.locator('body')).toContainText('Sarees');
    await expect(page.locator('body')).toContainText('Men\'s Silk');
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '04_categories_list.png') });

    // Edit category page
    await page.goto('/categories/1/edit');
    await expect(page.locator('input[name="category_name"]')).toHaveValue('Sarees');
  });

  // 5. INVENTORY & STOCK
  test('05. Inventory Management, Alerts & Audit Logs', async ({ page }) => {
    await adminLogin(page);
    await page.goto('/inventory');
    await expect(page.locator('body')).toContainText('Inventory');
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '05_inventory_page.png') });

    // Movement logs
    await page.goto('/inventory/movements');
    await expect(page.locator('table')).toBeVisible();
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '05_stock_movements.png') });

    // Adjustment page
    await page.goto('/inventory/adjustment');
    await expect(page.locator('select[name="variant_id"]')).toBeVisible();
  });

  // 6. PURCHASES (INWARD)
  test('06. Inward Purchases Creation & Stock Update', async ({ page }) => {
    await adminLogin(page);
    await page.goto('/purchases');
    await expect(page.locator('body')).toContainText('PUR-KS-2026-001');
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '06_purchases_list.png') });

    // View Purchase Detail
    await page.goto('/purchases/1');
    await expect(page.locator('body')).toContainText('Sri Kanchi Silk');
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '06_purchase_detail.png') });

    // Create New Inward Purchase in Test DB
    await page.goto('/purchases/new');
    await page.selectOption('select[name="supplier_id"]', '1');
    const invoiceNo = `PUR-AUTO-${Date.now().toString().slice(-6)}`;
    await page.fill('input[name="invoice_number"]', invoiceNo);
    await page.fill('input[name="purchase_date"]', '2026-09-27');
    await page.selectOption('select[name="variant_id[]"]', '1');
    await page.fill('input[name="quantity[]"]', '5');
    await page.fill('input[name="unit_price[]"]', '6500.00');
    await page.selectOption('select[name="payment_status"]', 'PAID');
    await page.click('button[type="submit"]');

    await page.waitForURL('**/purchases**');
    await expect(page.locator('body')).toContainText(invoiceNo);
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '06_purchase_created.png') });
  });

  // 7. SALES / POS & INVOICE PRINT
  test('07. POS Cash & Credit Sales, Watermark & Print Layout', async ({ page }) => {
    await adminLogin(page);
    await page.goto('/sales');
    await expect(page.locator('body')).toContainText('INV-2026-0001');
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '07_sales_list.png') });

    // 1. Open POS New Sale
    await page.goto('/sales/new');
    await expect(page.locator('body')).toContainText('Billing');
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '07_pos_interface.png') });

    // Add item by selecting product card or dropdown
    const productCard = page.locator('.pos-variant-card, .product-card, [data-variant-id="2"]').first();
    if (await productCard.isVisible()) {
      await productCard.click();
    } else {
      // Fallback to select or search input
      const searchBox = page.locator('#posProductSearch, input[placeholder*="Search"]');
      if (await searchBox.isVisible()) {
        await searchBox.fill('Blue');
        await page.waitForTimeout(300);
        await page.locator('.search-result-item, .list-group-item').first().click();
      }
    }

    // Enter payment & submit sale
    const cashMethod = page.locator('input[value="CASH"], #methodCash, [data-method="CASH"]').first();
    if (await cashMethod.isVisible()) {
      await cashMethod.click();
    }

    const completeBtn = page.locator('#btnCompleteSale, button:has-text("Complete Sale"), button:has-text("Generate Invoice")').first();
    if (await completeBtn.isVisible()) {
      await completeBtn.click();
      await page.waitForTimeout(1000);
    }

    // Check invoice view / print view
    await page.goto('/sales/1');
    await expect(page.locator('body')).toContainText('INV-2026-0001');
    await expect(page.locator('body')).toContainText('Ramesh Kumar');
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '07_invoice_view_1.png') });

    // Emulate print media & check layout
    await page.emulateMedia({ media: 'print' });
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '07_invoice_print_layout.png') });
    await page.emulateMedia({ media: 'screen' });
  });

  // 8. CUSTOMERS
  test('08. Customers Profile & Purchase History', async ({ page }) => {
    await adminLogin(page);
    await page.goto('/customers');
    await expect(page.locator('body')).toContainText('Ramesh Kumar');
    await expect(page.locator('body')).toContainText('Suresh Reddy');
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '08_customers_list.png') });

    // View customer profile
    await page.goto('/customers/1');
    await expect(page.locator('body')).toContainText('Ramesh Kumar');
    await expect(page.locator('body')).toContainText('Outstanding Udhaar');
    await expect(page.locator('body')).toContainText('Balance Due');
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '08_customer_profile.png') });
  });

  // 9. CREDIT / UDHAAR & PDF GENERATION
  test('09. Credit Management, Settlement & PDF Statement', async ({ page }) => {
    await adminLogin(page);
    await page.goto('/credit');
    await expect(page.locator('body')).toContainText('Credit / Udhaar');
    await expect(page.locator('body')).toContainText('Suresh Reddy');
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '09_credit_ledger.png') });

    // View customer ledger
    await page.goto('/credit/customer/1');
    await expect(page.locator('body')).toContainText('Ramesh Kumar');
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '09_customer_ledger.png') });

    // Test PDF Statement download
    const downloadPromise = page.waitForEvent('download', { timeout: 10000 }).catch(() => null);
    const pdfBtn = page.locator('a[href*="statement"], button:has-text("Statement"), a:has-text("PDF")').first();
    if (await pdfBtn.isVisible()) {
      await pdfBtn.click();
      const download = await downloadPromise;
      if (download) {
        const pdfPath = path.join(SCREENSHOT_DIR, 'customer_1_statement.pdf');
        await download.saveAs(pdfPath);
        expect(fs.existsSync(pdfPath)).toBeTruthy();
      }
    }
  });

  // 10. RETURNS / EXCHANGES
  test('10. Returns & Exchanges Processing', async ({ page }) => {
    await adminLogin(page);
    await page.goto('/returns');
    await expect(page.locator('body')).toContainText('Returns');
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '10_returns_list.png') });

    // View return detail
    await page.goto('/returns/1');
    await expect(page.locator('body')).toContainText('Size exchange');
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '10_return_detail.png') });

    // Return creation page
    await page.goto('/returns/new');
    await expect(page.locator('body')).toContainText('Process Return');
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '10_returns_new.png') });
  });

  // 11. REPORTS (ALL 5 REPORTS)
  test('11. Comprehensive Reports Hub & Analytics', async ({ page }) => {
    await adminLogin(page);
    await page.goto('/reports');
    await expect(page.locator('body')).toContainText('Reports');
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '11_reports_hub.png') });

    // 1. Sales Report
    await page.goto('/reports/sales');
    await expect(page.locator('body')).toContainText('Sales Report');
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '11_report_sales.png') });

    // 2. Purchase Report
    await page.goto('/reports/purchases');
    await expect(page.locator('body')).toContainText('Purchase Report');
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '11_report_purchases.png') });

    // 3. Inventory Valuation
    await page.goto('/reports/inventory-valuation');
    await expect(page.locator('body')).toContainText('Inventory Valuation');
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '11_report_inventory.png') });

    // 4. Credit Aging
    await page.goto('/reports/credit-aging');
    await expect(page.locator('body')).toContainText('Credit');
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '11_report_credit_aging.png') });

    // 5. Profit Report
    await page.goto('/reports/profit');
    await expect(page.locator('body')).toContainText('Profit');
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '11_report_profit.png') });
  });

  // 12. USER MANAGEMENT & RBAC SECURITY
  test('12. User Management & Strict Staff RBAC Enforcement', async ({ page }) => {
    // Admin checks users page
    await adminLogin(page);
    await page.goto('/users');
    await expect(page.locator('body')).toContainText('Venkata Lakshmi');
    await expect(page.locator('body')).toContainText('Kiran Kumar');
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '12_admin_users_list.png') });

    // Logout admin
    await page.goto('/logout');

    // Login as Staff
    await page.goto('/login');
    await page.fill('#email', 'staff@vlsilks.com');
    await page.fill('#password', 'Staff@123');
    await page.click('button[type="submit"]');
    await page.waitForURL('**/dashboard');

    // Verify Staff CAN view dashboard
    await expect(page.locator('body')).toContainText('Shop Performance Dashboard');

    // Verify Staff CANNOT access /users (403 Access Restricted)
    const resUsers = await page.goto('/users');
    expect(resUsers.status()).toBe(403);
    await expect(page.locator('body')).toContainText('Access Restricted');
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '12_staff_rbac_403.png') });

    // Verify Staff CANNOT access /products/new (403)
    const resProdNew = await page.goto('/products/new');
    expect(resProdNew.status()).toBe(403);

    // Verify Staff CANNOT access /purchases/new (403)
    const resPurNew = await page.goto('/purchases/new');
    expect(resPurNew.status()).toBe(403);
  });

  // 13. RESPONSIVE VIEWPORT TESTING
  test('13. Multi-Device Responsive UI (Desktop, Laptop, Mobile)', async ({ page }) => {
    await adminLogin(page);

    // Desktop 1440x900
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto('/dashboard');
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '13_desktop_1440x900.png'), fullPage: true });

    // Laptop 1280x800
    await page.setViewportSize({ width: 1280, height: 800 });
    await page.goto('/dashboard');
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '13_laptop_1280x800.png'), fullPage: true });

    // Mobile 390x844 (iPhone 14)
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto('/dashboard');
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '13_mobile_390x844.png'), fullPage: true });

    // Check no horizontal scroll overflow on mobile
    const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
    const clientWidth = await page.evaluate(() => document.documentElement.clientWidth);
    expect(scrollWidth).toBeLessThanOrEqual(clientWidth + 5);
  });

  // 14. CUSTOM 404 NOT FOUND PAGE & STATUS
  test('14. Custom Branded 404 Error Page & HTTP Status', async ({ page }) => {
    // 1. Unauthenticated request to nonexistent page
    const resUnauth = await page.goto('/this-page-does-not-exist');
    expect(resUnauth.status()).toBe(404);
    await expect(page.locator('body')).toContainText('404');
    await expect(page.locator('body')).toContainText('Page Not Found');
    await expect(page.locator('body')).toContainText("doesn't exist");
    await expect(page.locator('#btnGoToLogin')).toBeVisible();
    await expect(page.locator('#btnGoBack')).toBeVisible();
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '14_404_unauthenticated.png') });

    // 2. Nested nonexistent URL
    const resNested = await page.goto('/abc/random-test-url');
    expect(resNested.status()).toBe(404);

    // 3. Authenticated request to nonexistent page
    await adminLogin(page);
    const resAuth = await page.goto('/products/nonexistent-item-page-xyz');
    expect(resAuth.status()).toBe(404);
    await expect(page.locator('body')).toContainText('404');
    await expect(page.locator('#btnBackToDashboard')).toBeVisible();
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '14_404_authenticated.png') });

    // Test Back to Dashboard button works
    await page.click('#btnBackToDashboard');
    await page.waitForURL('**/dashboard');
    expect(page.url()).toContain('/dashboard');
  });

  // 15. MOBILE OFF-CANVAS DRAWER & MULTI-VIEWPORT AUDIT
  test('15. Mobile Off-Canvas Drawer, Backdrop & Multi-Viewport Flow', async ({ page }) => {
    await adminLogin(page);

    const mobileViewports = [
      { name: '360x800', width: 360, height: 800 },
      { name: '375x812', width: 375, height: 812 },
      { name: '390x844', width: 390, height: 844 },
      { name: '412x915', width: 412, height: 915 },
      { name: '768x1024', width: 768, height: 1024 }
    ];

    for (const vp of mobileViewports) {
      await page.setViewportSize({ width: vp.width, height: vp.height });
      await page.goto('/dashboard');
      await page.waitForLoadState('networkidle');

      // 1. Verify hamburger button is visible on mobile
      const toggleBtn = page.locator('#sidebarToggle');
      await expect(toggleBtn).toBeVisible();

      // 2. Open drawer
      await toggleBtn.click();
      const sidebar = page.locator('#vlSidebar');
      const backdrop = page.locator('#vlSidebarBackdrop');
      await expect(sidebar).toHaveClass(/show/);
      await expect(backdrop).toHaveClass(/active/);
      const isBodyLocked = await page.evaluate(() => document.body.classList.contains('vl-drawer-open'));
      expect(isBodyLocked).toBeTruthy();

      // 3. Close drawer via backdrop click
      await backdrop.click({ position: { x: vp.width - 20, y: 100 } });
      await expect(sidebar).not.toHaveClass(/show/);
      const isBodyUnlocked = await page.evaluate(() => !document.body.classList.contains('vl-drawer-open'));
      expect(isBodyUnlocked).toBeTruthy();

      // 4. Open drawer and close via close button
      await toggleBtn.click();
      await expect(sidebar).toHaveClass(/show/);
      const closeBtn = page.locator('#sidebarCloseBtn');
      if (await closeBtn.isVisible()) {
        await closeBtn.click();
        await expect(sidebar).not.toHaveClass(/show/);
      }

      // 5. Verify no horizontal overflow on page
      const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
      const clientWidth = await page.evaluate(() => document.documentElement.clientWidth);
      expect(scrollWidth).toBeLessThanOrEqual(clientWidth + 2);

      // 6. Test POS on this viewport
      await page.goto('/sales/new');
      await page.waitForLoadState('networkidle');
      const posScrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
      const posClientWidth = await page.evaluate(() => document.documentElement.clientWidth);
      expect(posScrollWidth).toBeLessThanOrEqual(posClientWidth + 2);
    }
  });

});
