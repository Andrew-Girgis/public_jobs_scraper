"""
Quick test to verify browser launches properly
"""

from playwright.sync_api import sync_playwright
import time

print("Starting browser test...")

with sync_playwright() as p:
    print("Launching browser with headless=False...")
    browser = p.chromium.launch(
        headless=False,
        slow_mo=1000  # 1 second delay between actions
    )
    
    print("Browser launched! Creating page...")
    page = browser.new_page()
    
    print("Navigating to UK job site...")
    page.goto("https://findajob.dwp.gov.uk/")
    
    print("Waiting 5 seconds so you can see the browser...")
    time.sleep(5)
    
    print("Closing browser...")
    browser.close()
    
print("Test complete! Did you see the browser window?")
