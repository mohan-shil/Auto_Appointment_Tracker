import { defineConfig, devices } from '@playwright/test';


export default defineConfig({
  testDir: './tests',
  retries:  2 ,
  workers:  1,
  use: {
    trace: 'on-first-retry',
  },

  /* Configure projects for major browsers */
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },

  ],

});
