// @ts-check
const { defineConfig, devices } = require('@playwright/test');

module.exports = defineConfig({
  testDir: './tests/playwright',
  timeout: 45000,
  expect: {
    timeout: 10000
  },
  fullyParallel: false,
  workers: 1, // Single worker to avoid database race conditions on test DB
  reporter: [['list'], ['json', { outputFile: 'scratch/playwright_report.json' }]],
  use: {
    baseURL: 'http://127.0.0.1:5001',
    trace: 'off',
    screenshot: 'only-on-failure',
    video: 'off',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});
