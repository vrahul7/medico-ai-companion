import requests
import json

r = requests.get("http://localhost:8000/api/research/feed", params={"page": 1, "topic": "pediatrics"})
print("Status:", r.status_code)
data = r.json()
print("Total found:", data.get("total_found"))
print("Has more:", data.get("has_more"))
print()
for a in data.get("articles", []):
    print(f"[{a['pmid']}] {a['title'][:70]}...")
    print(f"  Summary: {a['summary'][:120]}...")
    print(f"  URL: {a['pubmed_url']}")
    print()
