import requests
import json

def test():
    try:
        print("Testing health check...")
        r = requests.get("http://127.0.0.1:8000/api/health")
        print(f"Health Status: {r.status_code}")
        print(json.dumps(r.json(), indent=2))
        
        print("\nTesting scholarly feed (Pediatrics topic)...")
        r_feed = requests.get("http://127.0.0.1:8000/api/research/scholarly?page=1&topic=pediatrics")
        print(f"Scholarly Feed Status: {r_feed.status_code}")
        data = r_feed.json()
        print(f"Total articles found: {len(data.get('articles', []))}")
        if data.get('articles'):
            print("First article sample:")
            print(json.dumps(data['articles'][0], indent=2))
            
        print("\nTesting guidelines feed...")
        r_guide = requests.get("http://127.0.0.1:8000/api/research/guidelines?page=1")
        print(f"Guidelines Feed Status: {r_guide.status_code}")
        guide_data = r_guide.json()
        print(f"Total guidelines found: {len(guide_data.get('guidelines', []))}")
        if guide_data.get('guidelines'):
            print("First guideline sample:")
            print(json.dumps(guide_data['guidelines'][0], indent=2))
            
    except Exception as e:
        print(f"Error during testing: {e}")

if __name__ == '__main__':
    test()
