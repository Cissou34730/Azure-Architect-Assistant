import { test, expect } from '@playwright/test';

test('diagnose roger project waf checklist', async ({ page }) => {
  // Log all console messages from the browser
  page.on('console', msg => {
    console.log(`[BROWSER CONSOLE] ${msg.type()}: ${msg.text()}`);
  });

  // Intercept and log the project API response
  page.on('response', async response => {
    if (response.url().includes('/api/projects/df1a9feb-a194-4c9e-b35b-def938f7f1af')) {
      console.log(`[API] ${response.url()} - Status: ${response.status()}`);
      try {
        const body = await response.json();
        const hasWaf = !!body.wafChecklist;
        const itemsCount = body.wafChecklist?.items?.length ?? 0;
        console.log(`[API DATA] hasWaf: ${hasWaf}, items: ${itemsCount}`);
        if (hasWaf) {
            console.log(`[API DATA] pillars: ${JSON.stringify(body.wafChecklist.pillars)}`);
        }
      } catch (e) {
        console.log(`[API ERROR] Parse failure: ${e.message}`);
      }
    }
  });

  console.log('Navigating to Roger...');
  await page.goto('/project/df1a9feb-a194-4c9e-b35b-def938f7f1af');

  // Increase timeout for slow loading
  await page.waitForTimeout(5000);

  // Click WAF Checklist tab in sidebar
  console.log('Clicking WAF Checklist tab in sidebar...');
  const wafSidebarButton = page.getByRole('button', { name: 'WAF Checklist' });
  await wafSidebarButton.click();
  
  await page.waitForTimeout(2000);

  // Check WAF Checklist View title in the center panel
  const centerTitle = page.locator('p.text-sm.font-semibold.text-gray-900', { hasText: 'WAF Checklist' });
  const isTitleVisible = await centerTitle.first().isVisible();
  console.log(`UI: WAF Checklist title visible in center: ${isTitleVisible}`);

  // Check for "No checklist items available"
  const emptyMessage = page.getByText('No checklist items available.');
  const isEmptyVisible = await emptyMessage.isVisible();
  console.log(`UI: Empty message visible: ${isEmptyVisible}`);

  // The user asked about percentage. Let's look for ANY percentage on the screen.
  const allText = await page.innerText('body');
  const percentages = allText.match(/\d+%/g);
  console.log(`UI: Visible percentages: ${percentages ? percentages.join(', ') : 'None'}`);

  await expect(wafSidebarButton).toBeVisible();
});
