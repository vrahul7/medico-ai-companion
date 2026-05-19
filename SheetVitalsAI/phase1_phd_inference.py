"""
PHD Active Customer List - SKU Probability Inference Engine
Runs the same cuisine-classification + ingredient-probability model
on the PHD dataset (259 active customers across BLR/CHN/HYD).
Retains: CustomerId, Customer, City, Facility, BusinessPartner,
         DeliveryAddress, KAM, Number of Outlets, Detected Cuisines,
         12 SKU columns, Total_SKU_Score.
"""
import pandas as pd
import re
import os

INPUT_FILE = "analysis_input/PHD_Active Customer List.xlsx"
OUTPUT_DIR = "analysis_output"

TARGET_SKUS = [
    "Imported Avocado", "Blueberry", "Cherry Tomato", "Parsley",
    "Thai Asparagus", "Indian Asparagus", "Lemon Grass", "Thai Basil",
    "Italian Lemon", "Thai Bird Chilli", "Shiso Leaves", "Rosemary"
]

# ── Cuisine detection patterns ──────────────────────────────────────────
CUISINE_PATTERNS = {
    "Thai": r"\bthai\b|bangkok|pattaya|pad\b|tom yum|lemongrass",
    "Japanese": r"\bjapan|sushi|ramen|izakaya|sakura|wasabi|tempura|teppan|bento|matcha|miso",
    "Italian": r"\bitalian?\b|pizza(?!.*(hut|domino))|pasta|trattoria|osteria|risotto|gelato|napoli|tuscan|italia|focaccia|tiramisu|gusto\s*italia",
    "Mediterranean": r"\bmediterranean|greek|hummus|falafel|mezze|levant|pita\b",
    "Continental": r"\bcontinental|european|french|bistro|brasserie|grill\b",
    "Mexican": r"\bmexican|taco|burrito|nacho|quesadilla|enchilada|guacamole|tex.?mex|california\s*burrito",
    "Korean": r"\bkorean|kimchi|bibimbap|bulgogi|seoul\b|kimbap|gochujang",
    "Vietnamese": r"\bvietnamese|pho\b|banh mi|saigon|hanoi",
    "Chinese": r"\bchinese|szechuan|sichuan|cantonese|dim sum|wok\b|dragon\b|oriental|manchurian",
    "Cafe_Bakery": r"\bcafe\b|coffee|bakery|patisserie|boulangerie|brew|roast|baking\b|sucre|croissant|macaron|roastery",
    "Fine_Dining": r"\brestaurant|kitchen|bistro|dine|dining|lounge|bar\b|cuisine|culinary|gastro|gourmet|deli\b",
    "South_Indian": r"\budipi|bhavan|dosa|idli|saravana|ananda|chettinad|appam",
    "North_Indian": r"\bpunjabi|mughlai|tandoor|dhaba|biryani|kebab|kabab|lucknow|nawab|biriyani",
    "Pan_Asian": r"\basian|pan.?asian|fusion|wok|noodle|stir.?fry|chopstick|foo\b",
    "Seafood": r"\bseafood|fish|prawn|crab|lobster|oyster|marine|sea\s*salt|fisherman",
    "Health_Organic": r"\bhealth|organic|vegan|salad|bowl|superfood|green|detox|smoothie|wellness|nutrition|millet",
    "Hotel_Star": r"\bhotel\b|inn\b|resort|marriott|hilton|hyatt|taj\b|itc\b|leela|oberoi|novotel|radisson|sheraton|westin|park\b.*hotel|mansions|regency|palace\b|plaza\b|hospitality|grand\b|cove\b",
    "Sweets": r"\bsweet|mithai|halwa|ladoo|laddu",
    "Fast_Food": r"\bburger|fries|sandwich|wrap|roll\b|quick|express|subway|kfc\b|mcdonald",
    "Arabian": r"\barabian|shawarma|al\b.*\b(buhari|baik|taza)|lebanese|turkish|kebab|kabab|saffron",
    "French": r"\bfrench|patisserie|boulangerie|crepe|souffle|sucre|brasserie|maison|chez\b",
    "Catering": r"\bcater|caterer|catering|event|banquet|cloud\s*kitchen",
    "Food_Generic": r"\bfood|foods\b|agro\b|provisions|grocery|mart\b|store|market|departmental|warehouse",
    "Poke_Bowl": r"\bpoke\b|poké",
    "Sushi_Specific": r"\bsushi|maki|uramaki|sashimi|nigiri",
    "Steak_BBQ": r"\bsteak|steakhouse|bbq|barbecue|smoke\b|smoked|charcoal|grillhouse",
}

# ── Cuisine → SKU probability map ───────────────────────────────────────
CUISINE_SKU_MAP = {
    "Thai":          {"Lemon Grass": 0.85, "Thai Basil": 0.80, "Thai Bird Chilli": 0.75, "Thai Asparagus": 0.30, "Imported Avocado": 0.15},
    "Japanese":      {"Shiso Leaves": 0.45, "Imported Avocado": 0.50, "Rosemary": 0.10},
    "Italian":       {"Cherry Tomato": 0.70, "Rosemary": 0.65, "Parsley": 0.60, "Italian Lemon": 0.45, "Imported Avocado": 0.15},
    "Mediterranean": {"Cherry Tomato": 0.65, "Rosemary": 0.55, "Parsley": 0.55, "Italian Lemon": 0.30},
    "Continental":   {"Cherry Tomato": 0.45, "Rosemary": 0.50, "Parsley": 0.45, "Imported Avocado": 0.30, "Blueberry": 0.25, "Italian Lemon": 0.20, "Indian Asparagus": 0.25},
    "Mexican":       {"Imported Avocado": 0.85, "Cherry Tomato": 0.55, "Thai Bird Chilli": 0.30},
    "Korean":        {"Shiso Leaves": 0.35, "Thai Bird Chilli": 0.20},
    "Vietnamese":    {"Lemon Grass": 0.75, "Thai Basil": 0.55, "Thai Bird Chilli": 0.45},
    "Chinese":       {"Lemon Grass": 0.15, "Thai Bird Chilli": 0.10},
    "Cafe_Bakery":   {"Blueberry": 0.40, "Imported Avocado": 0.35, "Rosemary": 0.25, "Cherry Tomato": 0.20},
    "Fine_Dining":   {"Cherry Tomato": 0.40, "Rosemary": 0.40, "Parsley": 0.35, "Imported Avocado": 0.30, "Blueberry": 0.20, "Italian Lemon": 0.20, "Indian Asparagus": 0.20, "Lemon Grass": 0.15},
    "Pan_Asian":     {"Lemon Grass": 0.50, "Thai Basil": 0.40, "Thai Bird Chilli": 0.35, "Shiso Leaves": 0.15},
    "Health_Organic": {"Imported Avocado": 0.70, "Blueberry": 0.60, "Cherry Tomato": 0.55, "Rosemary": 0.30, "Parsley": 0.30, "Indian Asparagus": 0.35, "Thai Asparagus": 0.25},
    "Hotel_Star":    {"Cherry Tomato": 0.55, "Rosemary": 0.50, "Parsley": 0.45, "Imported Avocado": 0.40, "Blueberry": 0.30, "Italian Lemon": 0.25, "Lemon Grass": 0.30, "Thai Basil": 0.20, "Indian Asparagus": 0.25, "Shiso Leaves": 0.10},
    "Seafood":       {"Parsley": 0.35, "Cherry Tomato": 0.30, "Italian Lemon": 0.25, "Rosemary": 0.20, "Lemon Grass": 0.20},
    "French":        {"Rosemary": 0.55, "Parsley": 0.50, "Cherry Tomato": 0.45, "Italian Lemon": 0.35, "Blueberry": 0.30, "Imported Avocado": 0.20},
    "South_Indian":  {},
    "North_Indian":  {"Parsley": 0.10},
    "Sweets":        {"Rosemary": 0.05},
    "Fast_Food":     {"Cherry Tomato": 0.15, "Imported Avocado": 0.10},
    "Arabian":       {"Parsley": 0.40, "Cherry Tomato": 0.25, "Lemon Grass": 0.10},
    "Catering":      {"Cherry Tomato": 0.20, "Rosemary": 0.15, "Parsley": 0.15},
    "Food_Generic":  {},
    "Poke_Bowl":     {"Imported Avocado": 0.80, "Shiso Leaves": 0.30, "Cherry Tomato": 0.25},
    "Sushi_Specific": {"Imported Avocado": 0.60, "Shiso Leaves": 0.50, "Rosemary": 0.10},
    "Steak_BBQ":     {"Rosemary": 0.65, "Parsley": 0.40, "Cherry Tomato": 0.35},
}

# ── Name-keyword boosters ───────────────────────────────────────────────
NAME_BOOSTERS = {
    "avocado": {"Imported Avocado": 0.95},
    "blueberry": {"Blueberry": 0.90},
    "berry": {"Blueberry": 0.40},
    "poke": {"Imported Avocado": 0.80, "Shiso Leaves": 0.30},
    "sushi": {"Imported Avocado": 0.60, "Shiso Leaves": 0.50},
    "ramen": {"Shiso Leaves": 0.30},
    "thai": {"Lemon Grass": 0.70, "Thai Basil": 0.65, "Thai Bird Chilli": 0.60},
    "italian": {"Rosemary": 0.60, "Parsley": 0.55, "Cherry Tomato": 0.60, "Italian Lemon": 0.40},
    "italia": {"Rosemary": 0.60, "Parsley": 0.55, "Cherry Tomato": 0.60, "Italian Lemon": 0.40},
    "french": {"Rosemary": 0.55, "Parsley": 0.50, "Cherry Tomato": 0.40},
    "mediterranean": {"Cherry Tomato": 0.60, "Rosemary": 0.50, "Parsley": 0.50},
    "mexican": {"Imported Avocado": 0.80},
    "burrito": {"Imported Avocado": 0.85, "Cherry Tomato": 0.50, "Thai Bird Chilli": 0.25},
    "california": {"Imported Avocado": 0.80, "Cherry Tomato": 0.45},
    "organic": {"Imported Avocado": 0.50, "Blueberry": 0.45, "Cherry Tomato": 0.50},
    "salad": {"Cherry Tomato": 0.60, "Imported Avocado": 0.45, "Parsley": 0.35},
    "bowl": {"Imported Avocado": 0.50, "Cherry Tomato": 0.40},
    "smoothie": {"Blueberry": 0.55, "Imported Avocado": 0.45},
    "grill": {"Rosemary": 0.50, "Parsley": 0.35, "Cherry Tomato": 0.30},
    "steak": {"Rosemary": 0.65, "Parsley": 0.40},
    "herb": {"Rosemary": 0.55, "Parsley": 0.50, "Thai Basil": 0.25, "Lemon Grass": 0.20},
    "fusion": {"Imported Avocado": 0.35, "Cherry Tomato": 0.35, "Lemon Grass": 0.30, "Rosemary": 0.30},
    "continental": {"Rosemary": 0.50, "Parsley": 0.45, "Cherry Tomato": 0.45, "Imported Avocado": 0.25},
    "european": {"Rosemary": 0.50, "Parsley": 0.45, "Cherry Tomato": 0.40, "Italian Lemon": 0.25},
    "gourmet": {"Cherry Tomato": 0.45, "Rosemary": 0.40, "Parsley": 0.35, "Imported Avocado": 0.30, "Blueberry": 0.20},
    "cheese": {"Cherry Tomato": 0.40, "Rosemary": 0.30, "Parsley": 0.25, "Italian Lemon": 0.20},
    "patisserie": {"Blueberry": 0.40, "Rosemary": 0.30},
    "sea salt": {"Parsley": 0.35, "Cherry Tomato": 0.30, "Italian Lemon": 0.25, "Rosemary": 0.20},
    "wellness": {"Imported Avocado": 0.40, "Blueberry": 0.40, "Cherry Tomato": 0.35},
    "taj": {"Cherry Tomato": 0.55, "Rosemary": 0.50, "Parsley": 0.45, "Imported Avocado": 0.40, "Blueberry": 0.30, "Italian Lemon": 0.25, "Lemon Grass": 0.30, "Thai Basil": 0.20, "Indian Asparagus": 0.25, "Shiso Leaves": 0.10},
    "itc": {"Cherry Tomato": 0.55, "Rosemary": 0.50, "Parsley": 0.45, "Imported Avocado": 0.40, "Blueberry": 0.30, "Italian Lemon": 0.25, "Lemon Grass": 0.30, "Thai Basil": 0.20, "Indian Asparagus": 0.25, "Shiso Leaves": 0.10},
    "marriott": {"Cherry Tomato": 0.55, "Rosemary": 0.50, "Parsley": 0.45, "Imported Avocado": 0.40, "Blueberry": 0.30, "Italian Lemon": 0.25, "Lemon Grass": 0.30, "Indian Asparagus": 0.25},
    "hilton": {"Cherry Tomato": 0.55, "Rosemary": 0.50, "Parsley": 0.45, "Imported Avocado": 0.40, "Blueberry": 0.30, "Italian Lemon": 0.25, "Lemon Grass": 0.30},
    "novotel": {"Cherry Tomato": 0.50, "Rosemary": 0.45, "Parsley": 0.40, "Imported Avocado": 0.35, "Blueberry": 0.25, "Lemon Grass": 0.25},
    "hyatt": {"Cherry Tomato": 0.55, "Rosemary": 0.50, "Parsley": 0.45, "Imported Avocado": 0.40, "Blueberry": 0.30, "Italian Lemon": 0.25, "Lemon Grass": 0.30},
    "leela": {"Cherry Tomato": 0.55, "Rosemary": 0.50, "Parsley": 0.45, "Imported Avocado": 0.40, "Blueberry": 0.30, "Italian Lemon": 0.25, "Lemon Grass": 0.30, "Shiso Leaves": 0.15},
    "fisherman": {"Parsley": 0.40, "Cherry Tomato": 0.35, "Italian Lemon": 0.30, "Rosemary": 0.25, "Lemon Grass": 0.25, "Imported Avocado": 0.30},
    "dou": {"Cherry Tomato": 0.30, "Rosemary": 0.25, "Parsley": 0.25},
    "roastery": {"Blueberry": 0.35, "Imported Avocado": 0.30, "Rosemary": 0.20},
    "coffee": {"Blueberry": 0.30, "Imported Avocado": 0.25},
    "pizza": {"Cherry Tomato": 0.55, "Rosemary": 0.40, "Parsley": 0.35, "Italian Lemon": 0.20},
    "pasta": {"Cherry Tomato": 0.60, "Rosemary": 0.50, "Parsley": 0.50, "Italian Lemon": 0.35},
}


def detect_cuisines(name):
    name_lower = name.lower()
    detected = []
    for cuisine, pattern in CUISINE_PATTERNS.items():
        if re.search(pattern, name_lower):
            detected.append(cuisine)
    return detected


def infer_probabilities(name):
    probs = {sku: 0.0 for sku in TARGET_SKUS}
    name_lower = name.lower()

    # Step 1: Cuisine-based scoring
    cuisines = detect_cuisines(name)
    for cuisine in cuisines:
        sku_map = CUISINE_SKU_MAP.get(cuisine, {})
        for sku, prob in sku_map.items():
            probs[sku] = max(probs[sku], prob)

    # Step 2: Keyword boosters
    for keyword, boosts in NAME_BOOSTERS.items():
        if keyword in name_lower:
            for sku, prob in boosts.items():
                probs[sku] = max(probs[sku], prob)

    return {k: round(v, 2) for k, v in probs.items()}, cuisines


def main():
    print("=" * 60)
    print("PHASE 1 (PHD): SKU PROBABILITY INFERENCE ENGINE")
    print("=" * 60)

    df = pd.read_excel(INPUT_FILE)
    print(f"Loaded {len(df)} active customers from PHD list")
    print(f"Cities: {df['City'].value_counts().to_dict()}")

    # Outlet count per customer name
    outlet_counts = df['Customer'].value_counts().to_dict()

    results = []
    for idx, row in df.iterrows():
        name = str(row.get('Customer', '')).strip()
        cust_id = str(row.get('CustomerId', '')).strip()
        city = str(row.get('City', '')).strip()
        facility = str(row.get('Facility', '')).strip()
        bp = str(row.get('BusinessPartner', '')).strip()
        addr = str(row.get('DeliveryAddress', '')).strip()
        kam = str(row.get('KAM', '')).strip()
        lat = row.get('Latitude', '')
        lng = row.get('Longitude', '')

        probs, cuisines = infer_probabilities(name)

        # Also check BusinessPartner name for extra signals
        bp_probs, bp_cuisines = infer_probabilities(bp)
        for sku in TARGET_SKUS:
            probs[sku] = max(probs[sku], bp_probs.get(sku, 0.0))
        all_cuisines = list(set(cuisines + bp_cuisines))

        result = {
            "CustomerId": cust_id,
            "Customer": name,
            "City": city,
            "Facility": facility,
            "BusinessPartner": bp,
            "DeliveryAddress": addr,
            "KAM": kam,
            "Latitude": lat,
            "Longitude": lng,
            "Number of Outlets": outlet_counts.get(name, 1),
            "Detected_Cuisines": ", ".join(all_cuisines) if all_cuisines else "Unclassified",
        }
        result.update(probs)
        result["Total_SKU_Score"] = round(sum(probs.values()), 2)
        results.append(result)

    cols = [
        "CustomerId", "Customer", "City", "Facility", "BusinessPartner",
        "DeliveryAddress", "KAM", "Latitude", "Longitude",
        "Number of Outlets", "Detected_Cuisines"
    ] + TARGET_SKUS + ["Total_SKU_Score"]

    result_df = pd.DataFrame(results, columns=cols)
    result_df = result_df.sort_values("Total_SKU_Score", ascending=False)

    # Save outputs
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    excel_path = os.path.join(OUTPUT_DIR, "PHD_SKU_Probability_Matrix.xlsx")
    csv_path = os.path.join(OUTPUT_DIR, "PHD_SKU_Probability_Matrix.csv")
    result_df.to_excel(excel_path, index=False, sheet_name="PHD SKU Matrix")
    result_df.to_csv(csv_path, index=False)

    # ── Stats ────────────────────────────────────────────────────────────
    has_score = result_df[result_df["Total_SKU_Score"] > 0]
    print(f"\n{'-'*50}")
    print(f"RESULTS SUMMARY")
    print(f"{'-'*50}")
    print(f"Total active customers:    {len(result_df)}")
    print(f"With SKU probability > 0:  {len(has_score)} ({len(has_score)*100//len(result_df)}%)")
    print(f"Score >= 2.0 (Tier 2+):    {len(result_df[result_df.Total_SKU_Score >= 2])}")
    print(f"Score >= 3.0 (Tier 1):     {len(result_df[result_df.Total_SKU_Score >= 3])}")
    print(f"Score >= 4.0 (Premium):    {len(result_df[result_df.Total_SKU_Score >= 4])}")

    print(f"\nPer-SKU coverage:")
    for s in TARGET_SKUS:
        ct = len(result_df[result_df[s] > 0])
        print(f"  {s:22s}: {ct:>4}")

    print(f"\nCity breakdown (Score >= 2.0):")
    tier2 = result_df[result_df.Total_SKU_Score >= 2]
    for city, count in tier2['City'].value_counts().items():
        print(f"  {city:22s}: {count:>4}")

    print(f"\nTop 15 customers:")
    for _, r in result_df.head(15).iterrows():
        print(f"  {r['Total_SKU_Score']:5.2f}  {r['Customer'][:45]:45s}  [{r['City']}]")

    print(f"\n[OK] Saved: {excel_path}")
    print(f"[OK] Saved: {csv_path}")


if __name__ == "__main__":
    main()
