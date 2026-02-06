import { chromium } from 'playwright';

(async () => {
    const browser = await chromium.launch({ headless: true });
    const page = await browser.newPage();

    // Log console messages
    page.on('console', msg => {
        console.log(`[BROWSER CONSOLE] ${msg.type()}: ${msg.text()}`);
    });

    // Detailed network logging
    page.on('response', async response => {
        if (response.url().includes('/api/projects/df1a9feb-a194-4c9e-b35b-def938f7f1af')) {
            console.log(`[API RESPONSE] ${response.url()} status: ${response.status()}`);
            try {
                const body = await response.json();
                console.log(`[API RESPONSE BODY] wafChecklist keys: ${Object.keys(body.wafChecklist || {})}`);
                if (body.wafChecklist) {
                    console.log(`[API RESPONSE BODY] wafChecklist items count: ${body.wafChecklist.items?.length}`);
                }
            } catch (e) {
                console.log(`[API RESPONSE ERROR] Failed to parse JSON: ${e.message}`);
            }
        }
    });

    console.log("Navigating to Roger project...");
    try {
        await page.goto('http://localhost:5173/project/df1a9feb-a194-4c9e-b35b-def938f7f1af', { waitUntil: 'networkidle' });
        
        // Wait a bit for components to render
        await page.waitForTimeout(5000);

        // Take a screenshot
        await page.screenshot({ path: 'roger_debug.png', fullPage: true });
        console.log("Screenshot saved to roger_debug.png");

        // Check for specific UI elements
        const wafToggle = await page.getByText('WAF', { exact: false });
        if (await wafToggle.isVisible()) {
            console.log("WAF element found in UI");
            const text = await wafToggle.innerText();
            console.log(`WAF element text: "${text}"`);
        } else {
            console.log("WAF element NOT found in UI");
        }

    } catch (error) {
        console.error("Error during playwright test:", error);
    } finally {
        await browser.close();
    }
})();
