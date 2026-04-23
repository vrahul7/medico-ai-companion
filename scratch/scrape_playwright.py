from playwright.sync_api import sync_playwright
import time
import json

def scrape_dohfw():
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("https://www.mohfw-dohfw.gov.in/documents/guidelines", timeout=60000)
        
        # Wait for the network to be idle so dynamic content loads
        try:
            page.wait_for_selector('.pdf', timeout=15000)
        except Exception as e:
            print("Timeout waiting for .pdf class. Continuing anyway.")
        
        # Let JS render things
        time.sleep(3)
        
        # "classes of sections with a class pdf. Fetch the Title element as summary from those and href has pdf link attached"
        elements = page.query_selector_all('.pdf')
        for el in elements:
            # Try to see if this is an anchor, or if it contains an anchor
            tag_name = el.evaluate("el => el.tagName.toLowerCase()")
            if tag_name == 'a':
                a_tag = el
            else:
                a_tag = el.query_selector('a')
                
            if a_tag:
                title = a_tag.inner_text().strip()
                href = a_tag.get_attribute('href')
                results.append({"title": title, "url": href})
                
        # also try broader matching in case they meant the anchor itself has class pdf
        if not results:
            links = page.query_selector_all('a.pdf')
            for a_tag in links:
                title = a_tag.inner_text().strip()
                href = a_tag.get_attribute('href')
                results.append({"title": title, "url": href})
                
        browser.close()
        
        print(json.dumps(results, indent=2))

if __name__ == '__main__':
    scrape_dohfw()
