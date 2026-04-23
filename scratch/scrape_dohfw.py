import requests
import re
import urllib3
urllib3.disable_warnings()

url = "https://www.mohfw-dohfw.gov.in/documents/guidelines?page=1"
res = requests.get(url, verify=False)
html = res.text

matches = re.finditer(r'<a[^>]*href=["\']([^"\']+.pdf)["\'][^>]*>(.*?)</a>', html, re.IGNORECASE)
for m in matches:
    print(f"PDF LINK: {m.group(1)}\nTEXT: {m.group(2).strip()}\n---")
