import pandas as pd
import requests
import time
import json
import os

INPUT_FILE = "analysis_output/SKU_Probability_Matrix_FINAL_v2.csv"
OUTPUT_FILE = "analysis_output/SKU_Probability_Matrix_FINAL_v2.csv"
SWIGGY_API_URL = "https://www.swiggy.com/dapi/restaurants/search/v3"

def get_swiggy_id(restaurant_name):
    params = {
        'lat': '13.0827',  # Chennai
        'lng': '80.2707',
        'str': restaurant_name,
        'trackingId': 'undefined',
        'submitAction': 'ENTER',
        'queryUniqueId': '123'
    }
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json',
        'Origin': 'https://www.swiggy.com',
        'Referer': 'https://www.swiggy.com/'
    }
    try:
        res = requests.get(SWIGGY_API_URL, params=params, headers=headers, timeout=10)
        if res.status_code == 200:
            data = res.json()
            for card in data.get('data', {}).get('cards', []):
                grouped = card.get('groupedCard', {}).get('cardGroupMap', {}).get('RESTAURANT', {})
                if grouped:
                    for c in grouped.get('cards', []):
                        info = c.get('card', {}).get('card', {}).get('info', {})
                        if info:
                            # Basic string matching: does search term appear in result name?
                            search_term = restaurant_name.lower().split()[0]
                            res_name = info.get('name', '').lower()
                            if search_term in res_name:
                                return info.get('id')
    except Exception as e:
        print(f"Error fetching {restaurant_name}: {e}")
    return ""

def main():
    print("="*60)
    print("PHASE 2: SWIGGY FOOD BATCH LOOKUP")
    print("="*60)
    
    df = pd.read_csv(INPUT_FILE)
    df["Swiggy_Food_ID"] = df["Swiggy_Food_ID"].fillna("").astype(str)
    
    # Filter for businesses with score > 0 that don't have an ID yet
    to_process = df[(df["Total_SKU_Score"] > 0) & (df["Swiggy_Food_ID"] == "")]
    print(f"Total businesses to search on Swiggy Food: {len(to_process)}")
    
    found_count = 0
    # Process only top 100 first to test safely
    for idx, row in to_process.iterrows():
        name = str(row["Restaurant"]).strip()
        print(f"Searching: {name[:40]:40s}", end="")
        
        swiggy_id = get_swiggy_id(name)
        if swiggy_id:
            df.at[idx, "Swiggy_Food_ID"] = str(swiggy_id)
            found_count += 1
            print(f" [FOUND] -> {swiggy_id}")
        else:
            print(" [MISS]")
            
        time.sleep(0.5) # Rate limiting
        
        # Save progress periodically
        if found_count % 10 == 0 and found_count > 0:
            try:
                df.to_csv(OUTPUT_FILE, index=False)
            except PermissionError:
                print(f"\n[WARNING] {OUTPUT_FILE} is open in another program. Saving to _alt.csv")
                df.to_csv(OUTPUT_FILE.replace(".csv", "_alt.csv"), index=False)
            
    try:
        df.to_csv(OUTPUT_FILE, index=False)
        print(f"\n--- LOOKUP COMPLETE ---")
        print(f"Newly found Swiggy Food IDs: {found_count}")
        print(f"Updated matrix saved to: {OUTPUT_FILE}")
    except PermissionError:
        alt_file = OUTPUT_FILE.replace(".csv", "_alt.csv")
        df.to_csv(alt_file, index=False)
        print(f"\n--- LOOKUP COMPLETE ---")
        print(f"Newly found Swiggy Food IDs: {found_count}")
        print(f"Updated matrix saved to: {alt_file} (Original file was locked)")

if __name__ == "__main__":
    main()
