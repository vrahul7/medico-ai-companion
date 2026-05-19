"""
PHD Phase 2B: Menu Fetch via Swiggy Web Scraper + Gemini Validation
===================================================================
Uses the Swiggy website menu page directly to fetch menu data,
then validates with Gemini. Picks up from Phase 2A results.
"""
import pandas as pd
import requests
import json
import time
import os
import re

from google import genai

GEMINI_API_KEY = "AIzaSyAN_9kjLpX-mF2dtAjAk_VpaxVFwARZWGg"
gemini_client = genai.Client(api_key=GEMINI_API_KEY)

INPUT_CSV = "analysis_output/PHD_SKU_Probability_Matrix_Validated.csv"
OUTPUT_CSV = "analysis_output/PHD_SKU_Probability_Matrix_Validated.csv"
OUTPUT_XLSX = "analysis_output/PHD_SKU_Probability_Matrix_Validated.xlsx"

TARGET_SKUS = [
    "Imported Avocado", "Blueberry", "Cherry Tomato", "Parsley",
    "Thai Asparagus", "Indian Asparagus", "Lemon Grass", "Thai Basil",
    "Italian Lemon", "Thai Bird Chilli", "Shiso Leaves", "Rosemary"
]

CITY_COORDS = {
    'PTP_Bengaluru': (12.9716, 77.5946),
    'PTP_Chennai': (13.0827, 80.2707),
    'PTP_Hyderabad': (17.3850, 78.4867),
}

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'en-US,en;q=0.9',
    'Referer': 'https://www.swiggy.com/',
    'Origin': 'https://www.swiggy.com',
}


def fetch_menu_v2(rid, city='PTP_Bengaluru'):
    """Fetch menu using multiple coordinate strategies."""
    coord_list = [
        CITY_COORDS.get(city, (12.9716, 77.5946)),
        (12.9716, 77.5946),  # BLR center
        (13.0827, 80.2707),  # CHN center
        (17.3850, 78.4867),  # HYD center
    ]

    for lat, lng in coord_list:
        url = f'https://www.swiggy.com/dapi/menu/pl?page-type=REGULAR_MENU&complete-menu=true&lat={lat}&lng={lng}&restaurantId={rid}'
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            if r.status_code == 200:
                data = r.json()
                items = extract_menu_items(data)
                if items:
                    return items, data
        except:
            pass
        time.sleep(0.3)

    return [], None


def extract_menu_items(data):
    """Extract all menu items from Swiggy menu API response."""
    items = []
    cards = data.get('data', {}).get('cards', [])

    for card in cards:
        gc = card.get('groupedCard', {})
        if gc:
            regular = gc.get('cardGroupMap', {}).get('REGULAR', {})
            for cat_card in regular.get('cards', []):
                ic = cat_card.get('card', {}).get('card', {})

                # Direct items
                item_cards = ic.get('itemCards', []) or []
                for itm in item_cards:
                    info = itm.get('card', {}).get('info', {})
                    if info:
                        items.append({
                            'name': info.get('name', ''),
                            'description': info.get('description', ''),
                            'category': ic.get('title', ''),
                        })

                # Nested categories
                cats = ic.get('categories', []) or []
                for cat in cats:
                    for itm in cat.get('itemCards', []) or []:
                        info = itm.get('card', {}).get('info', {})
                        if info:
                            items.append({
                                'name': info.get('name', ''),
                                'description': info.get('description', ''),
                                'category': cat.get('title', ''),
                            })
    return items


def analyze_menu_with_gemini(restaurant_name, cuisines_str, menu_items):
    """Use Gemini to analyze menu and infer ingredient probabilities."""
    if not menu_items:
        return None

    menu_text = ""
    for item in menu_items[:80]:
        desc = f" ({item['description'][:80]})" if item.get('description') else ""
        cat = f"[{item['category']}] " if item.get('category') else ""
        menu_text += f"- {cat}{item['name']}{desc}\n"

    prompt = f"""You are a food ingredient expert analyzing a real restaurant menu. Based on the dishes listed, estimate the probability (0.0 to 1.0) that this restaurant regularly uses each of these 12 specialty ingredients.

Restaurant: {restaurant_name}
Listed Cuisines: {cuisines_str}

Menu Items:
{menu_text}

Score each ingredient 0.0-1.0 based on EVIDENCE from the menu items above:
- 0.8-1.0: Directly mentioned or clearly required by multiple dishes
- 0.5-0.7: Highly likely based on cuisine type and dish names
- 0.2-0.4: Possible based on some dishes
- 0.0-0.1: No evidence or very unlikely

Ingredients:
1. Imported Avocado (sushi, poke, Mexican, health bowls)
2. Blueberry (desserts, smoothies, bakery, health bowls)
3. Cherry Tomato (Italian, salads, bruschetta, Mediterranean)
4. Parsley (garnish in Italian, Continental, French)
5. Thai Asparagus (Thai stir-fries only)
6. Indian Asparagus (continental sides, fine dining)
7. Lemon Grass (Thai/Vietnamese soups, curries)
8. Thai Basil (Thai/Vietnamese stir-fries, basil chicken)
9. Italian Lemon (Italian, Mediterranean, seafood)
10. Thai Bird Chilli (Thai, Vietnamese spicy dishes)
11. Shiso Leaves (Japanese sushi, sashimi, tempura)
12. Rosemary (grills, roasts, Italian, continental)

RESPOND ONLY with valid JSON:
{{"Imported Avocado": 0.0, "Blueberry": 0.0, "Cherry Tomato": 0.0, "Parsley": 0.0, "Thai Asparagus": 0.0, "Indian Asparagus": 0.0, "Lemon Grass": 0.0, "Thai Basil": 0.0, "Italian Lemon": 0.0, "Thai Bird Chilli": 0.0, "Shiso Leaves": 0.0, "Rosemary": 0.0}}"""

    try:
        response = gemini_client.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt,
        )
        text = response.text.strip()
        json_match = re.search(r'\{[^}]+\}', text, re.DOTALL)
        if json_match:
            scores = json.loads(json_match.group())
            result = {}
            for sku in TARGET_SKUS:
                val = scores.get(sku, 0.0)
                result[sku] = round(min(max(float(val), 0.0), 1.0), 2)
            return result
    except Exception as e:
        print(f"    [GEMINI ERROR] {e}")
    return None


def gemini_cuisine_analysis(restaurant_name, cuisines_str):
    """Use Gemini to validate scores based on cuisine info only (no menu)."""
    prompt = f"""You are a food ingredient procurement expert. Based ONLY on the restaurant name and cuisine type, estimate the probability (0.0 to 1.0) that this restaurant uses each ingredient.

Restaurant: {restaurant_name}
Swiggy Cuisines: {cuisines_str}

Be conservative - only score > 0.3 if the cuisine type strongly indicates usage.

Ingredients to score (0.0-1.0):
1. Imported Avocado, 2. Blueberry, 3. Cherry Tomato, 4. Parsley,
5. Thai Asparagus, 6. Indian Asparagus, 7. Lemon Grass, 8. Thai Basil,
9. Italian Lemon, 10. Thai Bird Chilli, 11. Shiso Leaves, 12. Rosemary

RESPOND ONLY with valid JSON mapping ingredient names to scores."""

    try:
        response = gemini_client.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt,
        )
        text = response.text.strip()
        json_match = re.search(r'\{[^}]+\}', text, re.DOTALL)
        if json_match:
            scores = json.loads(json_match.group())
            result = {}
            for sku in TARGET_SKUS:
                val = scores.get(sku, 0.0)
                result[sku] = round(min(max(float(val), 0.0), 1.0), 2)
            return result
    except Exception as e:
        print(f"    [GEMINI CUISINE ERROR] {e}")
    return None


def main():
    print("=" * 65)
    print("PHD PHASE 2B: MENU FETCH + GEMINI INGREDIENT VALIDATION")
    print("=" * 65)

    df = pd.read_csv(INPUT_CSV)
    print(f"Loaded {len(df)} customers")

    # Get restaurants that have Swiggy RID but no menu validation yet
    has_rid = df[(df['Swiggy_RID'].notna()) & (df['Swiggy_RID'] != '') & (df['Swiggy_RID'] != '0')]
    needs_menu = has_rid[has_rid['Validation_Source'] != 'Gemini+Menu']
    print(f"With Swiggy RID: {len(has_rid)}")
    print(f"Need menu validation: {len(needs_menu)}")

    # Also get restaurants with cuisines but no RID - use Gemini cuisine analysis
    no_rid = df[(df['Swiggy_RID'].isna()) | (df['Swiggy_RID'] == '') | (df['Swiggy_RID'] == '0')]
    has_cuisine_no_rid = no_rid[no_rid['Swiggy_Cuisines'].notna() & (no_rid['Swiggy_Cuisines'] != '')]

    menu_validated = 0
    cuisine_validated = 0

    # Phase A: Try to fetch menus for restaurants with RIDs
    print(f"\n--- Phase A: Menu fetch for {len(needs_menu)} restaurants with RIDs ---")
    for idx, row in needs_menu.iterrows():
        rid = str(row['Swiggy_RID']).strip()
        name = str(row['Customer']).strip()
        city = str(row.get('City', ''))
        cuisines_str = str(row.get('Swiggy_Cuisines', ''))

        print(f"\n  [{menu_validated+cuisine_validated+1}] {name} (RID: {rid})")

        # Try menu fetch
        items, raw = fetch_menu_v2(rid, city)
        if items:
            print(f"    Got {len(items)} menu items! Running Gemini...")
            df.at[idx, 'Menu_Items_Count'] = len(items)

            gemini_scores = analyze_menu_with_gemini(name, cuisines_str, items)
            time.sleep(0.5)

            if gemini_scores:
                for sku in TARGET_SKUS:
                    old_val = float(df.at[idx, sku]) if pd.notna(df.at[idx, sku]) else 0.0
                    new_val = gemini_scores.get(sku, 0.0)
                    df.at[idx, sku] = round(max(old_val, new_val), 2)

                new_total = round(sum(float(df.at[idx, sku]) for sku in TARGET_SKUS), 2)
                old_total = float(row['Total_SKU_Score'])
                df.at[idx, 'Total_SKU_Score'] = new_total
                df.at[idx, 'Validation_Source'] = 'Gemini+Menu'
                print(f"    Score: {old_total:.2f} -> {new_total:.2f} [MENU VALIDATED]")
                menu_validated += 1
            else:
                print(f"    Gemini failed, trying cuisine-only analysis...")
                gemini_scores = gemini_cuisine_analysis(name, cuisines_str)
                if gemini_scores:
                    for sku in TARGET_SKUS:
                        old_val = float(df.at[idx, sku]) if pd.notna(df.at[idx, sku]) else 0.0
                        new_val = gemini_scores.get(sku, 0.0)
                        df.at[idx, sku] = round(max(old_val, new_val), 2)
                    new_total = round(sum(float(df.at[idx, sku]) for sku in TARGET_SKUS), 2)
                    df.at[idx, 'Total_SKU_Score'] = new_total
                    df.at[idx, 'Validation_Source'] = 'Gemini+Cuisine'
                    cuisine_validated += 1
        else:
            # No menu - use Gemini cuisine-only analysis
            print(f"    No menu data. Using Gemini cuisine analysis...")
            gemini_scores = gemini_cuisine_analysis(name, cuisines_str)
            time.sleep(0.5)

            if gemini_scores:
                for sku in TARGET_SKUS:
                    old_val = float(df.at[idx, sku]) if pd.notna(df.at[idx, sku]) else 0.0
                    new_val = gemini_scores.get(sku, 0.0)
                    df.at[idx, sku] = round(max(old_val, new_val), 2)

                new_total = round(sum(float(df.at[idx, sku]) for sku in TARGET_SKUS), 2)
                old_total = float(row['Total_SKU_Score'])
                df.at[idx, 'Total_SKU_Score'] = new_total
                df.at[idx, 'Validation_Source'] = 'Gemini+Cuisine'
                print(f"    Score: {old_total:.2f} -> {new_total:.2f} [CUISINE VALIDATED]")
                cuisine_validated += 1

    # Phase B: Gemini cuisine analysis for remaining restaurants with no RID but with scores
    remaining = df[(df['Validation_Source'] == 'Inference_Only') & (df['Total_SKU_Score'] > 0)]
    print(f"\n--- Phase B: Gemini cuisine-only for {len(remaining)} remaining restaurants ---")

    for idx, row in remaining.iterrows():
        name = str(row['Customer']).strip()
        detected = str(row.get('Detected_Cuisines', ''))

        print(f"\n  [{menu_validated+cuisine_validated+1}] {name}")
        gemini_scores = gemini_cuisine_analysis(name, detected)
        time.sleep(0.5)

        if gemini_scores:
            for sku in TARGET_SKUS:
                old_val = float(df.at[idx, sku]) if pd.notna(df.at[idx, sku]) else 0.0
                new_val = gemini_scores.get(sku, 0.0)
                df.at[idx, sku] = round(max(old_val, new_val), 2)

            new_total = round(sum(float(df.at[idx, sku]) for sku in TARGET_SKUS), 2)
            old_total = float(row['Total_SKU_Score'])
            df.at[idx, 'Total_SKU_Score'] = new_total
            df.at[idx, 'Validation_Source'] = 'Gemini+Cuisine'
            print(f"    Score: {old_total:.2f} -> {new_total:.2f} [CUISINE VALIDATED]")
            cuisine_validated += 1

    # Final save
    df = df.sort_values('Total_SKU_Score', ascending=False)
    try:
        df.to_csv(OUTPUT_CSV, index=False)
        df.to_excel(OUTPUT_XLSX, index=False, sheet_name='PHD Validated Matrix')
    except PermissionError:
        df.to_csv(OUTPUT_CSV.replace('.csv', '_v2.csv'), index=False)
        df.to_excel(OUTPUT_XLSX.replace('.xlsx', '_v2.xlsx'), index=False, sheet_name='PHD Validated Matrix')
        print("\n[WARNING] Main file locked, saved to _v2 files")

    # Stats
    print(f"\n{'='*65}")
    print(f"FINAL VALIDATION RESULTS")
    print(f"{'='*65}")
    print(f"Menu validated (Gemini+Menu):    {menu_validated}")
    print(f"Cuisine validated (Gemini):      {cuisine_validated}")
    print(f"Total Gemini-validated:          {menu_validated + cuisine_validated}")
    print(f"Swiggy RIDs found:              {len(has_rid)}")
    print(f"Score >= 3.0 (Tier 1):          {len(df[df.Total_SKU_Score >= 3])}")
    print(f"Score >= 2.0 (Tier 2+):         {len(df[df.Total_SKU_Score >= 2])}")

    print(f"\nTop 20 validated customers:")
    for _, r in df.head(20).iterrows():
        src = str(r.get('Validation_Source', 'N/A'))[:15]
        rid_str = f"RID:{r['Swiggy_RID']}" if r.get('Swiggy_RID') and str(r['Swiggy_RID']).strip() else "No RID"
        print(f"  {r['Total_SKU_Score']:5.2f}  {str(r['Customer'])[:40]:40s}  [{r['City']}]  {rid_str}  ({src})")

    print(f"\n[OK] Saved: {OUTPUT_CSV}")
    print(f"[OK] Saved: {OUTPUT_XLSX}")


if __name__ == "__main__":
    main()
