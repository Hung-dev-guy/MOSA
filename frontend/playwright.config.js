import { defineConfig,devices } from '@playwright/test';
export default defineConfig({
  testDir:'./e2e',fullyParallel:false,workers:1,timeout:45000,
  reporter:[['list'],['json',{outputFile:'../docs/playwright-results.json'}]],
  use:{baseURL:'http://127.0.0.1:5099',screenshot:'only-on-failure',trace:'retain-on-failure'},
  projects:[{name:'desktop',use:{...devices['Desktop Chrome'],channel:'msedge',viewport:{width:1440,height:1000}}},{name:'mobile',use:{...devices['iPhone 13'],defaultBrowserType:'chromium',channel:'msedge'}}],
  webServer:{command:'..\\.venv\\Scripts\\python.exe ..\\scripts\\e2e_server.py',url:'http://127.0.0.1:5099/api/session',reuseExistingServer:false,timeout:30000}
});
