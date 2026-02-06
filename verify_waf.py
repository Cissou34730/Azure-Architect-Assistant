from playwright.sync_api import sync_playwright
import time

def verify():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        url = "http://localhost:5173/project/961ba7fd-7cb6-4f2e-a712-8d58d7464583"
        print(f"Navigating to {url}...")
        try:
            page.goto(url)
            page.wait_for_load_state("networkidle")
            time.sleep(5) # Extra wait for any async data loading
            
            # 1. Verify if WAF Checklist tab exists and click it if necessary
            # We might need to find the tab first.
            tabs = page.locator('button[role="tab"], [role="tab"]').all()
            print(f"Found {len(tabs)} tabs:")
            for tab in tabs:
                print(f"  Tab: {tab.inner_text()}")
            
            # Try to find WAF Checklist tab
            waf_tab = page.get_by_text("WAF Checklist", exact=False)
            if waf_tab.count() > 0:
                print("WAF Checklist tab found.")
                # waf_tab.first.click()
                # page.wait_for_load_state("networkidle")
            else:
                print("WAF Checklist tab NOT found by direct text.")

            # 2. Check sidebar for count
            # Sidebar often has items like "WAF Checklist (10/20)" or similar
            sidebar = page.locator('aside, .sidebar, [role="navigation"]').first
            sidebar_text = sidebar.inner_text() if sidebar.count() > 0 else "Sidebar not found"
            print("Sidebar Content Snippet:")
            print(sidebar_text[:500])
            
            # 3. Take screenshot for visual confirmation
            page.screenshot(path="verification_screenshot.png", full_page=True)
            print("Screenshot saved to verification_screenshot.png")
            
            # List all text on the page to find counts or percentages
            all_text = page.locator('body').inner_text()
            if "%" in all_text:
                print("Found percentage in text.")
            else:
                print("Percentage NOT found in text.")
            
        except Exception as e:
            print(f"Error: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    verify()
