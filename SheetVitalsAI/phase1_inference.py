"""
Phase 1: Intelligent Inference Engine
Analyzes ALL 2,204 business names to infer SKU probabilities
based on cuisine type, business name keywords, and category mapping.
"""
import pandas as pd
import re
import os
import json

INPUT_FILE = "analysis_input/Customer list 08052026.xlsx"
OUTPUT_DIR = "analysis_output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

TARGET_SKUS = [
    "Imported Avocado", "Blueberry", "Cherry Tomato", "Parsley",
    "Thai Asparagus", "Indian Asparagus", "Lemon Grass", "Thai Basil",
    "Italian Lemon", "Thai Bird Chilli", "Shiso Leaves", "Rosemary"
]

# Cuisine detection from business name
CUISINE_PATTERNS = {
    "Thai": r"\bthai\b|bangkok|pattaya|pad\b|tom yum",
    "Japanese": r"\bjapan|sushi|ramen|izakaya|sakura|wasabi|tempura|teppan",
    "Italian": r"\bitalian|pizza|pasta|trattoria|osteria|risotto|gelato|napoli|tuscan",
    "Mediterranean": r"\bmediterranean|greek|hummus|falafel|mezze|levant",
    "Continental": r"\bcontinental|european|french|bistro|brasserie|grill\b",
    "Mexican": r"\bmexican|taco|burrito|nacho|quesadilla|enchilada|guacamole",
    "Korean": r"\bkorean|kimchi|bibimbap|bulgogi|seoul\b",
    "Vietnamese": r"\bvietnamese|pho\b|banh mi|saigon|hanoi",
    "Chinese": r"\bchinese|szechuan|sichuan|cantonese|dim sum|wok\b|dragon\b|oriental",
    "Cafe_Bakery": r"\bcafe|coffee|bakery|patisserie|boulangerie|brew|roast",
    "Fine_Dining": r"\brestaurant|kitchen|bistro|dine|dining|lounge|bar\b",
    "South_Indian": r"\budipi|bhavan|dosa|idli|saravana|ananda|chettinad",
    "North_Indian": r"\bpunjabi|mughlai|tandoor|dhaba|biryani|kebab|lucknow",
    "Pan_Asian": r"\basian|pan.?asian|fusion|wok|noodle|stir.?fry",
    "Seafood": r"\bseafood|fish|prawn|crab|lobster|oyster|marine",
    "Health_Organic": r"\bhealth|organic|vegan|salad|bowl|superfood|green|detox|smoothie",
    "Hotel_Star": r"\bhotel|inn\b|resort|marriott|hilton|hyatt|taj\b|itc\b|leela|oberoi|novotel|radisson|sheraton|westin|park\b.*hotel",
    "Sweets": r"\bsweet|mithai|halwa|ladoo|laddu",
    "Fast_Food": r"\bburger|pizza|fries|sandwich|wrap|roll\b|quick|express",
    "Arabian": r"\barabian|shawarma|al\b.*\b(buhari|baik|taza)|lebanese|turkish|kebab",
}

# Cuisine -> SKU probability mapping
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
    "South_Indian":  {},  # Traditional South Indian rarely uses these SKUs
    "North_Indian":  {},
    "Sweets":        {"Rosemary": 0.05},
    "Fast_Food":     {"Cherry Tomato": 0.15, "Imported Avocado": 0.10},
    "Arabian":       {"Parsley": 0.40, "Cherry Tomato": 0.25, "Lemon Grass": 0.10},
}

# Direct name keyword boosters
NAME_BOOSTERS = {
    "avocado": {"Imported Avocado": 0.95},
    "blueberry": {"Blueberry": 0.90},
    "berry": {"Blueberry": 0.40},
    "poke": {"Imported Avocado": 0.80, "Shiso Leaves": 0.30},
    "sushi": {"Imported Avocado": 0.60, "Shiso Leaves": 0.50},
    "ramen": {"Shiso Leaves": 0.30},
    "thai": {"Lemon Grass": 0.70, "Thai Basil": 0.65, "Thai Bird Chilli": 0.60},
    "italian": {"Rosemary": 0.60, "Parsley": 0.55, "Cherry Tomato": 0.60, "Italian Lemon": 0.40},
    "french": {"Rosemary": 0.55, "Parsley": 0.50, "Cherry Tomato": 0.40},
    "mediterranean": {"Cherry Tomato": 0.60, "Rosemary": 0.50, "Parsley": 0.50},
    "mexican": {"Imported Avocado": 0.80},
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
}


def detect_cuisines(name):
    """Detect cuisine types from business name."""
    name_lower = name.lower()
    detected = []
    for cuisine, pattern in CUISINE_PATTERNS.items():
        if re.search(pattern, name_lower):
            detected.append(cuisine)
    return detected


def infer_probabilities(name, address=""):
    """Infer SKU probabilities from business name and address."""
    probs = {sku: 0.0 for sku in TARGET_SKUS}
    name_lower = name.lower()
    
    # Step 1: Cuisine-based inference
    cuisines = detect_cuisines(name)
    for cuisine in cuisines:
        sku_map = CUISINE_SKU_MAP.get(cuisine, {})
        for sku, prob in sku_map.items():
            probs[sku] = max(probs[sku], prob)
    
    # Step 2: Direct name keyword boosters
    for keyword, boosts in NAME_BOOSTERS.items():
        if keyword in name_lower:
            for sku, prob in boosts.items():
                probs[sku] = max(probs[sku], prob)
    
    # Step 3: Round all values
    probs = {k: round(v, 2) for k, v in probs.items()}
    
    return probs, cuisines


def main():
    print("=" * 60)
    print("PHASE 1: INTELLIGENT INFERENCE ENGINE")
    print("=" * 60)
    
    df = pd.read_excel(INPUT_FILE)
    print(f"Loaded {len(df)} businesses")
    
    results = []
    cuisine_counts = {}
    
    for idx, row in df.iterrows():
        name = str(row.get('Particulars', '')).strip()
        address = str(row.get('Address', '')).strip()
        gstin = str(row.get('GSTIN/UIN', '')).strip()
        
        probs, cuisines = infer_probabilities(name, address)
        
        for c in cuisines:
            cuisine_counts[c] = cuisine_counts.get(c, 0) + 1
        
        result = {
            "Sl_No": idx + 1,
            "Restaurant": name,
            "Address": address,
            "GSTIN": gstin,
            "Detected_Cuisines": ", ".join(cuisines) if cuisines else "Unknown",
            "Swiggy_Food_ID": "",
            "Swiggy_Dineout_ID": "",
        }
        result.update(probs)
        
        # Total score for sorting
        result["Total_SKU_Score"] = round(sum(probs.values()), 2)
        results.append(result)
    
    # Build DataFrame
    cols = ["Sl_No", "Restaurant", "Address", "GSTIN", "Detected_Cuisines",
            "Swiggy_Food_ID", "Swiggy_Dineout_ID"] + TARGET_SKUS + ["Total_SKU_Score"]
    
    result_df = pd.DataFrame(results, columns=cols)
    result_df = result_df.sort_values("Total_SKU_Score", ascending=False)
    
    # Save outputs
    excel_path = os.path.join(OUTPUT_DIR, "ingredient_probability_matrix_phase1.xlsx")
    csv_path = os.path.join(OUTPUT_DIR, "ingredient_probability_matrix_phase1.csv")
    result_df.to_excel(excel_path, index=False, sheet_name="SKU Probability Matrix")
    result_df.to_csv(csv_path, index=False)
    
    # Stats
    has_score = result_df[result_df["Total_SKU_Score"] > 0]
    high_score = result_df[result_df["Total_SKU_Score"] >= 2.0]
    
    print(f"\n--- RESULTS ---")
    print(f"Total businesses: {len(result_df)}")
    print(f"With SKU probability > 0: {len(has_score)} ({len(has_score)*100//len(result_df)}%)")
    print(f"High probability (score >= 2.0): {len(high_score)}")
    print(f"\nCuisine detection breakdown:")
    for cuisine, count in sorted(cuisine_counts.items(), key=lambda x: -x[1]):
        print(f"  {cuisine}: {count}")
    
    print(f"\n--- TOP 30 HIGH-PROBABILITY RESTAURANTS ---")
    top30 = result_df.head(30)
    for _, r in top30.iterrows():
        print(f"  [{r['Total_SKU_Score']:.1f}] {r['Restaurant'][:45]:45s} | {r['Detected_Cuisines']}")
    
    print(f"\nSaved: {excel_path}")
    print(f"Saved: {csv_path}")
    
    # Save high-priority list for Phase 2 Swiggy lookup
    priority_df = result_df[result_df["Total_SKU_Score"] > 0].copy()
    priority_path = os.path.join(OUTPUT_DIR, "phase2_swiggy_lookup_queue.csv")
    priority_df[["Sl_No", "Restaurant", "Address", "Detected_Cuisines", "Total_SKU_Score"]].to_csv(priority_path, index=False)
    print(f"Phase 2 lookup queue: {len(priority_df)} restaurants -> {priority_path}")


if __name__ == "__main__":
    main()
