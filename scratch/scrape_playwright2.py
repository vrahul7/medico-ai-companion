from playwright.sync_api import sync_playwright
import time
import re

def scrape_all():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("https://www.mohfw-dohfw.gov.in/documents/guidelines", timeout=60000)
        time.sleep(5)
        html = page.content()
        with open("scratch/output.html", "w", encoding="utf-8") as f:
            f.write(html)
        browser.close()
        # find all pdf links
        matches = re.finditer(r'<a[^>]*href=["\']([^"\']*\.pdf)["\'][^>]*>(.*?)</a>', html, re.IGNORECASE)
        count = 0
        for m in matches:
            print("FOUND PDF:", m.group(1), m.group(2).strip()[:50])
            count += 1
        print("Total pure .pdf matches:", count)
if __name__ == '__main__':
    scrape_all()
