import requests
import json

url = 'https://www.swiggy.com/dapi/restaurants/search/v3'
params = {'lat': '13.0827', 'lng': '80.2707', 'str': 'Cafe De Bangkok', 'trackingId': 'undefined', 'submitAction': 'ENTER', 'queryUniqueId': '123'}
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}

res = requests.get(url, params=params, headers=headers)
data = res.json()

for card in data.get('data', {}).get('cards', []):
    grouped = card.get('groupedCard', {}).get('cardGroupMap', {}).get('RESTAURANT', {})
    if grouped:
        for c in grouped.get('cards', []):
            info = c.get('card', {}).get('card', {}).get('info', {})
            if info:
                print(f"ID: {info.get('id')}, Name: {info.get('name')}, Cuisines: {info.get('cuisines')}")
