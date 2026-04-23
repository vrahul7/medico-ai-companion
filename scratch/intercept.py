from playwright.sync_api import sync_playwright
import json

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        urls = []
        page.on("response", lambda response: urls.append(response.url))
        page.goto("https://www.mohfw-dohfw.gov.in/documents/guidelines", timeout=60000)
        page.wait_for_selector('a[href*=".pdf"]', timeout=15000)
        browser.close()
        
        for u in urls:
            if "json" in u or "api" in u or "cms" in u:
                print(u)

run()
