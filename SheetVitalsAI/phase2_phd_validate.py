"""
PHD Phase 2: Swiggy ID Lookup + Menu Fetch + Gemini Ingredient Validation
=========================================================================
Automated pipeline that:
1. Searches Swiggy for each PHD restaurant (using lat/lng from the dataset)
2. Fetches the full menu for matched restaurants
3. Uses Gemini 2.5 Flash to analyze menus and detect SKU ingredient usage
4. Updates the probability matrix with validated scores + Swiggy RID
"""
import pandas as pd
import requests
import json
import time
import os
import re
import sys

# ── Gemini setup ─────────────────────────────────────────────────────────
from google import genai

GEMINI_API_KEY = "AIzaSyAN_9kjLpX-mF2dtAjAk_VpaxVFwARZWGg"
gemini_client = genai.Client(api_key=GEMINI_API_KEY)

INPUT_CSV = "analysis_output/PHD_SKU_Probability_Matrix.csv"
OUTPUT_CSV = "analysis_output/PHD_SKU_Probability_Matrix_Validated.csv"
OUTPUT_XLSX = "analysis_output/PHD_SKU_Probability_Matrix_Validated.xlsx"
PROGRESS_FILE = "analysis_output/phd_validation_progress.json"

TARGET_SKUS = [
    "Imported Avocado", "Blueberry", "Cherry Tomato", "Parsley",
    "Thai Asparagus", "Indian Asparagus", "Lemon Grass", "Thai Basil",
    "Italian Lemon", "Thai Bird Chilli", "Shiso Leaves", "Rosemary"
]

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'application/json',
    'Referer': 'https://www.swiggy.com/',
    'Origin': 'https://www.swiggy.com'
}

# City coordinates for fallback
CITY_COORDS = {
    'PTP_Bengaluru': (12.9716, 77.5946),
    'PTP_Chennai': (13.0827, 80.2707),
    'PTP_Hyderabad': (17.3850, 78.4867),
}


def search_swiggy(query, lat, lng, max_results=10):
    """Search Swiggy for a restaurant by name + coordinates."""
    url = 'https://www.swiggy.com/dapi/restaurants/search/v3'
    params = {'lat': str(lat), 'lng': str(lng), 'str': query, 'submitAction': 'ENTER'}
    try:
        r = requests.get(url, params=params, headers=HEADERS, timeout=10)
        results = []
        if r.status_code == 200:
            for card in r.json().get('data', {}).get('cards', []):
                gc = card.get('groupedCard', {})
                if gc:
                    for cs in gc.get('cardGroupMap', {}).get('RESTAURANT', {}).get('cards', [])[:max_results]:
                        info = cs.get('card', {}).get('card', {}).get('info', {})
                        if info:
                            results.append({
                                'rid': str(info.get('id', '')),
                                'name': info.get('name', ''),
                                'cuisines': info.get('cuisines', []),
                                'area': info.get('areaName', ''),
                            })
        return results
    except Exception as e:
        print(f"    [SEARCH ERROR] {e}")
        return []


def fetch_menu(rid, lat, lng):
    """Fetch full menu items from Swiggy by restaurant ID."""
    url = f'https://www.swiggy.com/dapi/menu/pl?page-type=REGULAR_MENU&complete-menu=true&lat={lat}&lng={lng}&restaurantId={rid}'
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
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
                        cats = ic.get('categories', []) or []
                        for cat in cats:
                            item_cards.extend(cat.get('itemCards', []) or [])
                        for itm in item_cards:
                            info = itm.get('card', {}).get('info', {})
                            if info:
                                items.append({
                                    'name': info.get('name', ''),
                                    'description': info.get('description', ''),
                                })
        return items
    except Exception as e:
        print(f"    [MENU ERROR] {e}")
        return []


def best_match(query_name, search_results):
    """Find the best matching restaurant from search results using fuzzy name matching."""
    query_lower = query_name.lower().strip()
    # Remove common suffixes for matching
    clean_query = re.sub(r'\s*[-|]\s*(hrbr|koramangala|indiranagar|jp\s*nagar|kondapur|banjara\s*hills|manikonda|dilshuknagar|gachibowli|cyberabad|kokapet|manyata|ub\s*city|nungambakkam|chennai|hyderabad|bangalore|bengaluru).*', '', query_lower, flags=re.I)
    clean_query = re.sub(r'\s*(warehouse|airport|marina\s*mall|phoenix\s*mall).*', '', clean_query, flags=re.I)
    clean_query = clean_query.strip()

    best = None
    best_score = 0
    for r in search_results:
        rname = r['name'].lower().strip()
        # Exact match
        if rname == clean_query:
            return r
        # Contains match
        if clean_query in rname or rname in clean_query:
            score = len(set(clean_query.split()) & set(rname.split())) / max(len(clean_query.split()), 1)
            if score > best_score:
                best_score = score
                best = r
        # Word overlap
        query_words = set(clean_query.split())
        result_words = set(rname.split())
        overlap = len(query_words & result_words)
        score = overlap / max(len(query_words), 1)
        if score > best_score and score >= 0.5:
            best_score = score
            best = r
    return best


def analyze_menu_with_gemini(restaurant_name, cuisines, menu_items):
    """Use Gemini to analyze menu and infer ingredient probabilities for 12 SKUs."""
    if not menu_items:
        return None

    # Build menu text (limit to first 80 items to avoid token overflow)
    menu_text = ""
    for item in menu_items[:80]:
        desc = f" - {item['description']}" if item.get('description') else ""
        menu_text += f"- {item['name']}{desc}\n"

    prompt = f"""You are a food ingredient expert. Analyze the following restaurant menu and estimate the probability (0.0 to 1.0) that this restaurant uses each of these 12 specialty ingredients in their kitchen.

Restaurant: {restaurant_name}
Cuisines: {', '.join(cuisines) if cuisines else 'Unknown'}

Menu Items:
{menu_text}

For each ingredient below, provide a probability score from 0.0 to 1.0:
1. Imported Avocado - used in sushi, poke bowls, Mexican dishes, salads
2. Blueberry - used in desserts, smoothies, bakery items, health bowls
3. Cherry Tomato - used in Italian, salads, continental, Mediterranean dishes
4. Parsley - used as garnish in Italian, Continental, Mediterranean, French dishes
5. Thai Asparagus - used in authentic Thai stir-fries
6. Indian Asparagus - used in continental, fine dining side dishes
7. Lemon Grass - used in Thai, Vietnamese soups and curries
8. Thai Basil - used in Thai, Vietnamese, Pan-Asian stir-fries
9. Italian Lemon - used in Italian, Mediterranean, seafood dishes
10. Thai Bird Chilli - used in Thai, Vietnamese, Mexican spicy dishes
11. Shiso Leaves - used in Japanese sushi, sashimi presentations
12. Rosemary - used in grills, steaks, Italian, Continental, roasted dishes

RESPOND ONLY with a valid JSON object mapping ingredient names to scores. Example:
{{"Imported Avocado": 0.7, "Blueberry": 0.1, "Cherry Tomato": 0.5, "Parsley": 0.4, "Thai Asparagus": 0.0, "Indian Asparagus": 0.1, "Lemon Grass": 0.3, "Thai Basil": 0.2, "Italian Lemon": 0.1, "Thai Bird Chilli": 0.2, "Shiso Leaves": 0.0, "Rosemary": 0.3}}
"""

    try:
        response = gemini_client.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt,
        )
        text = response.text.strip()
        # Extract JSON from response
        json_match = re.search(r'\{[^}]+\}', text, re.DOTALL)
        if json_match:
            scores = json.loads(json_match.group())
            # Validate and normalize
            result = {}
            for sku in TARGET_SKUS:
                val = scores.get(sku, 0.0)
                result[sku] = round(min(max(float(val), 0.0), 1.0), 2)
            return result
    except Exception as e:
        print(f"    [GEMINI ERROR] {e}")
    return None


def load_progress():
    """Load progress from previous run."""
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, 'r') as f:
            return json.load(f)
    return {}


def save_progress(progress):
    """Save progress."""
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progress, f, indent=2)


def main():
    print("=" * 65)
    print("PHD PHASE 2: SWIGGY ID + MENU + GEMINI VALIDATION PIPELINE")
    print("=" * 65)

    df = pd.read_csv(INPUT_CSV)
    print(f"Loaded {len(df)} customers from PHD matrix")

    # Add new columns if not present
    if 'Swiggy_RID' not in df.columns:
        df['Swiggy_RID'] = ''
    if 'Swiggy_Cuisines' not in df.columns:
        df['Swiggy_Cuisines'] = ''
    if 'Menu_Items_Count' not in df.columns:
        df['Menu_Items_Count'] = 0
    if 'Validation_Source' not in df.columns:
        df['Validation_Source'] = ''

    # Load progress
    progress = load_progress()
    processed_ids = set(progress.get('processed', []))

    # Process restaurants with score > 0 (or all if you want)
    candidates = df[df['Total_SKU_Score'] > 0].copy()
    print(f"Candidates to validate: {len(candidates)} (score > 0)")
    print(f"Already processed: {len(processed_ids)}")

    batch_count = 0
    save_interval = 10  # Save every 10 restaurants

    for idx, row in candidates.iterrows():
        cust_id = str(row.get('CustomerId', ''))
        if cust_id in processed_ids:
            continue

        name = str(row.get('Customer', '')).strip()
        city = str(row.get('City', ''))
        lat = row.get('Latitude', 0)
        lng = row.get('Longitude', 0)

        # Use restaurant lat/lng or fallback to city center
        if pd.isna(lat) or pd.isna(lng) or lat == 0 or lng == 0:
            lat, lng = CITY_COORDS.get(city, (12.9716, 77.5946))

        print(f"\n[{batch_count+1}] {name} ({city})")

        # Step 1: Search Swiggy
        print(f"  Searching Swiggy...")
        results = search_swiggy(name, lat, lng)
        time.sleep(0.5)  # Rate limiting

        match = best_match(name, results)
        if match:
            rid = match['rid']
            cuisines = match['cuisines']
            print(f"  MATCH: {match['name']} (RID: {rid}) | {', '.join(cuisines)} | {match['area']}")

            df.at[idx, 'Swiggy_RID'] = rid
            df.at[idx, 'Swiggy_Cuisines'] = ', '.join(cuisines)

            # Step 2: Fetch menu
            print(f"  Fetching menu...")
            menu_items = fetch_menu(rid, lat, lng)
            time.sleep(0.5)
            df.at[idx, 'Menu_Items_Count'] = len(menu_items)

            if menu_items:
                print(f"  Got {len(menu_items)} menu items. Running Gemini analysis...")

                # Step 3: Gemini validation
                gemini_scores = analyze_menu_with_gemini(name, cuisines, menu_items)
                time.sleep(0.3)  # Gemini rate limiting

                if gemini_scores:
                    # Update SKU scores with Gemini-validated values
                    for sku in TARGET_SKUS:
                        old_val = float(df.at[idx, sku]) if pd.notna(df.at[idx, sku]) else 0.0
                        new_val = gemini_scores.get(sku, 0.0)
                        # Use max of inference and Gemini (Gemini validates, doesn't reduce unless 0)
                        final_val = round(max(old_val, new_val), 2)
                        df.at[idx, sku] = final_val

                    new_total = round(sum(float(df.at[idx, sku]) for sku in TARGET_SKUS), 2)
                    df.at[idx, 'Total_SKU_Score'] = new_total
                    df.at[idx, 'Validation_Source'] = 'Gemini+Menu'
                    print(f"  Score: {row['Total_SKU_Score']:.2f} -> {new_total:.2f} [VALIDATED]")
                else:
                    df.at[idx, 'Validation_Source'] = 'Menu_Only'
                    print(f"  Gemini analysis failed, keeping inference score")
            else:
                df.at[idx, 'Validation_Source'] = 'Swiggy_ID_Only'
                print(f"  No menu data available (might be dineout-only)")
        else:
            print(f"  NO MATCH on Swiggy")
            df.at[idx, 'Validation_Source'] = 'Inference_Only'

        processed_ids.add(cust_id)
        batch_count += 1

        # Periodic save
        if batch_count % save_interval == 0:
            progress['processed'] = list(processed_ids)
            save_progress(progress)
            try:
                df.to_csv(OUTPUT_CSV, index=False)
                print(f"\n  [SAVED] Progress at {batch_count} restaurants")
            except PermissionError:
                alt_path = OUTPUT_CSV.replace('.csv', '_alt.csv')
                df.to_csv(alt_path, index=False)
                print(f"\n  [SAVED] Progress to {alt_path} (main file locked)")

    # Final save
    progress['processed'] = list(processed_ids)
    save_progress(progress)

    # Re-sort by total score
    df = df.sort_values('Total_SKU_Score', ascending=False)

    try:
        df.to_csv(OUTPUT_CSV, index=False)
        df.to_excel(OUTPUT_XLSX, index=False, sheet_name='PHD Validated Matrix')
    except PermissionError:
        alt_csv = OUTPUT_CSV.replace('.csv', '_alt.csv')
        alt_xlsx = OUTPUT_XLSX.replace('.xlsx', '_alt.xlsx')
        df.to_csv(alt_csv, index=False)
        df.to_excel(alt_xlsx, index=False, sheet_name='PHD Validated Matrix')
        print(f"\n[WARNING] Main files locked, saved to *_alt files")

    # Final stats
    print(f"\n{'='*65}")
    print(f"VALIDATION COMPLETE")
    print(f"{'='*65}")
    validated = df[df['Validation_Source'].str.contains('Gemini|Menu', na=False)]
    swiggy_found = df[df['Swiggy_RID'] != '']
    print(f"Total processed:          {batch_count}")
    print(f"Swiggy RID found:         {len(swiggy_found)}")
    print(f"Menu validated (Gemini):  {len(validated)}")
    print(f"Score >= 3.0 (Tier 1):    {len(df[df.Total_SKU_Score >= 3])}")
    print(f"Score >= 2.0 (Tier 2+):   {len(df[df.Total_SKU_Score >= 2])}")

    print(f"\nTop 15 validated customers:")
    for _, r in df.head(15).iterrows():
        src = r.get('Validation_Source', 'N/A')
        rid_str = f"RID:{r['Swiggy_RID']}" if r.get('Swiggy_RID') else "No RID"
        print(f"  {r['Total_SKU_Score']:5.2f}  {str(r['Customer'])[:40]:40s}  [{r['City']}]  {rid_str}  ({src})")

    print(f"\n[OK] Saved: {OUTPUT_CSV}")
    print(f"[OK] Saved: {OUTPUT_XLSX}")


if __name__ == "__main__":
    main()
