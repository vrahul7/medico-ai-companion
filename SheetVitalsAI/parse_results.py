import json, os

base = r'C:\Users\NC24008_Rahul\.gemini\antigravity\brain\343f052d-cd8f-4b58-adf3-68f0c4ed1210\.system_generated\steps'
searches = {
    '364': 'Lemon Tree Hotel',
    '365': 'Buhari Hotel', 
    '366': 'Novotel Chennai',
    '367': 'Oriental Hotels'
}

matches = {}
for step, query in searches.items():
    fp = os.path.join(base, step, 'output.txt')
    with open(fp, 'r', encoding='utf-8') as f:
        data = json.load(f)
    if data.get('success') and data.get('data', {}).get('restaurants'):
        rests = data['data']['restaurants']
        print(f"Query: {query} -> {len(rests)} results")
        for r in rests[:3]:
            cuis = ", ".join(r.get("cuisine", []))
            print(f"  ID={r['id']} | {r['name']} | {cuis} | {r.get('locality','')}")
            # Check for name match
            if query.lower().split()[0] in r['name'].lower():
                matches[query] = {"id": r['id'], "name": r['name'], "cuisine": r.get("cuisine",[])}
    print()

print("\n--- MATCHES FOUND ---")
for q, m in matches.items():
    print(f"  {q} -> Dineout ID: {m['id']} ({m['name']})")
