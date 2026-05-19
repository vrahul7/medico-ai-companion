"""
Test: Swiggy search for Foo Restaurant + Menu fetch + Dineout search
"""
import requests
import json

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'application/json',
    'Referer': 'https://www.swiggy.com/',
    'Origin': 'https://www.swiggy.com'
}

def search_swiggy(query, lat, lng):
    url = 'https://www.swiggy.com/dapi/restaurants/search/v3'
    params = {'lat': str(lat), 'lng': str(lng), 'str': query, 'submitAction': 'ENTER'}
    r = requests.get(url, params=params, headers=HEADERS)
    results = []
    if r.status_code == 200:
        for card in r.json().get('data', {}).get('cards', []):
            gc = card.get('groupedCard', {})
            if gc:
                for cs in gc.get('cardGroupMap', {}).get('RESTAURANT', {}).get('cards', []):
                    info = cs.get('card', {}).get('card', {}).get('info', {})
                    if info:
                        results.append({
                            'rid': info.get('id', ''),
                            'name': info.get('name', ''),
                            'cuisines': info.get('cuisines', []),
                            'area': info.get('areaName', ''),
                        })
    return results


def fetch_menu(rid, lat, lng):
    url = f'https://www.swiggy.com/dapi/menu/pl?page-type=REGULAR_MENU&complete-menu=true&lat={lat}&lng={lng}&restaurantId={rid}'
    r = requests.get(url, headers=HEADERS)
    items = []
    if r.status_code == 200:
        data = r.json()
        cards = data.get('data', {}).get('cards', [])
        for card in cards:
            gc = card.get('groupedCard', {})
            if gc:
                for cat_card in gc.get('cardGroupMap', {}).get('REGULAR', {}).get('cards', []):
                    ic = cat_card.get('card', {}).get('card', {})
                    item_cards = ic.get('itemCards', []) or []
                    # Also check categories
                    cats = ic.get('categories', []) or []
                    for cat in cats:
                        item_cards.extend(cat.get('itemCards', []) or [])
                    for itm in item_cards:
                        info = itm.get('card', {}).get('info', {})
                        if info:
                            items.append({
                                'name': info.get('name', ''),
                                'description': info.get('description', ''),
                                'price': info.get('price', 0) / 100 if info.get('price') else info.get('defaultPrice', 0) / 100,
                            })
    return items


# Test 1: Search for Foo Restaurant
print("=== Searching: Foo Restaurant ===")
results = search_swiggy("Foo Restaurant", 13.0127, 77.5548)
for r in results[:5]:
    print(f"  RID: {r['rid']} | {r['name']} | {r['area']} | {', '.join(r['cuisines'])}")

# Test 2: Fetch menu for Foo (known RID from BLR list: 874623)
print("\n=== Fetching Menu: Foo (RID 874623) ===")
menu = fetch_menu('874623', 12.9716, 77.5946)
print(f"  Total items: {len(menu)}")
for item in menu[:10]:
    desc = item['description'][:60] if item['description'] else ''
    print(f"  - {item['name']} (Rs {item['price']}) {desc}")

# Test 3: Search Dineout
print("\n=== Searching: Maiz Mexican Kitchen ===")
results = search_swiggy("Maiz Mexican Kitchen", 12.9410, 77.6244)
for r in results[:5]:
    print(f"  RID: {r['rid']} | {r['name']} | {r['area']} | {', '.join(r['cuisines'])}")
