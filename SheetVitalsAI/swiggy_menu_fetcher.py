"""
Swiggy Menu Fetcher & Ingredient Probability Matrix Builder
============================================================
Processes the full Customer List, searches each on Swiggy,
fetches menus, infers ingredient probabilities using Gemini AI,
and outputs a Restaurant x Ingredient probability matrix.

Batch Size: 500 restaurants per batch
SKUs Tracked: 12 specialty/imported ingredients
"""

import pandas as pd
import json
import os
import time
import re
import sys
from pathlib import Path

# ============================================================
# CONFIGURATION
# ============================================================
INPUT_FILE = "analysis_input/Customer list 08052026.xlsx"
OUTPUT_DIR = "analysis_output"
SWIGGY_ADDRESS_ID = "ctsiksg7pv4oclr4vm00"  # Porur, Chennai
BATCH_SIZE = 500

TARGET_SKUS = [
    "Imported Avocado",
    "Blueberry",
    "Cherry Tomato",
    "Parsley",
    "Thai Asparagus",
    "Indian Asparagus",
    "Lemon Grass",
    "Thai Basil",
    "Italian Lemon",
    "Thai Bird Chilli",
    "Shiso Leaves",
    "Rosemary"
]

# ============================================================
# STEP 1: Load all businesses from Excel
# ============================================================
def load_customer_list():
    """Load ALL entries from the customer Excel file."""
    df = pd.read_excel(INPUT_FILE)
    print(f"[LOADED] {len(df)} businesses from {INPUT_FILE}")
    print(f"[COLUMNS] {list(df.columns)}")
    
    # Clean up names
    df['Particulars'] = df['Particulars'].astype(str).str.strip()
    df['Address'] = df['Address'].astype(str).str.strip()
    
    # Create a clean search name (remove legal suffixes for better Swiggy matching)
    df['search_name'] = df['Particulars'].apply(clean_search_name)
    
    return df

def clean_search_name(name):
    """Clean business name for better Swiggy search matching."""
    # Remove common legal suffixes
    suffixes = [
        r'\bPvt\.?\s*Ltd\.?', r'\bPrivate\s+Limited', r'\bLimited',
        r'\bLLP', r'\bLLC', r'\bInc\.?', r'\bCo\.?',
        r'\bInternational', r'\bIndia\b', r'\bEnterprises?\b',
        r'\bTrading\b', r'\bDistributors?\b', r'\bAgenc(?:y|ies)\b',
        r'\bServices?\b', r'\bSolutions?\b', r'\bIndustries?\b',
        r'\(.*?\)'  # Remove parenthetical content
    ]
    cleaned = name
    for suffix in suffixes:
        cleaned = re.sub(suffix, '', cleaned, flags=re.IGNORECASE)
    
    # Remove extra whitespace
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned

# ============================================================
# STEP 2: Results tracking
# ============================================================
def init_results_file():
    """Initialize the results tracking files."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Progress tracker
    progress_file = os.path.join(OUTPUT_DIR, "search_progress.json")
    if not os.path.exists(progress_file):
        with open(progress_file, 'w') as f:
            json.dump({
                "completed_indices": [],
                "matched_restaurants": [],
                "not_found": [],
                "errors": []
            }, f, indent=2)
    return progress_file

def load_progress(progress_file):
    """Load existing progress."""
    with open(progress_file, 'r') as f:
        return json.load(f)

def save_progress(progress_file, progress):
    """Save progress to file."""
    with open(progress_file, 'w') as f:
        json.dump(progress, f, indent=2, ensure_ascii=False)

# ============================================================
# STEP 3: Menu data storage
# ============================================================
def save_menu_data(restaurant_name, swiggy_id, menu_items, address):
    """Save raw menu data for a restaurant."""
    menu_dir = os.path.join(OUTPUT_DIR, "menus")
    os.makedirs(menu_dir, exist_ok=True)
    
    safe_name = re.sub(r'[^\w\s-]', '', restaurant_name)[:50]
    filepath = os.path.join(menu_dir, f"{safe_name}_{swiggy_id}.json")
    
    data = {
        "restaurant_name": restaurant_name,
        "swiggy_id": swiggy_id,
        "address": address,
        "menu_items": menu_items,
        "fetched_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    return filepath

# ============================================================
# STEP 4: Ingredient Probability Inference
# ============================================================

# High-confidence keyword mapping for each SKU
SKU_KEYWORDS = {
    "Imported Avocado": [
        "avocado", "guacamole", "avo toast", "avocado toast", "avo shake",
        "avocado smoothie", "avo salad", "california roll", "poke bowl"
    ],
    "Blueberry": [
        "blueberry", "blue berry", "berry smoothie", "berry pancake",
        "berry cheesecake", "mixed berry", "berry bowl", "acai bowl"
    ],
    "Cherry Tomato": [
        "cherry tomato", "bruschetta", "caprese", "mediterranean",
        "greek salad", "antipasti", "pesto pasta", "margherita"
    ],
    "Parsley": [
        "parsley", "chimichurri", "tabbouleh", "tabouleh",
        "mediterranean", "hummus plate", "falafel", "french"
    ],
    "Thai Asparagus": [
        "asparagus", "thai asparagus", "grilled asparagus",
        "stir fry asparagus", "pad asparagus"
    ],
    "Indian Asparagus": [
        "asparagus", "shatavari", "asparagus sabzi", "asparagus curry"
    ],
    "Lemon Grass": [
        "lemon grass", "lemongrass", "tom yum", "tom kha",
        "thai curry", "thai soup", "vietnamese", "pho",
        "laksa", "green curry", "red curry"
    ],
    "Thai Basil": [
        "thai basil", "pad krapow", "krapao", "holy basil",
        "basil chicken", "basil pork", "thai stir fry",
        "pad ka prao", "thai basil rice"
    ],
    "Italian Lemon": [
        "limoncello", "lemon risotto", "lemon pasta",
        "piccata", "lemon herb", "italian lemon",
        "amalfi", "sorrento"
    ],
    "Thai Bird Chilli": [
        "bird eye chilli", "thai chilli", "bird chilli",
        "prik", "nam prik", "thai hot", "som tum",
        "papaya salad", "thai spicy"
    ],
    "Shiso Leaves": [
        "shiso", "perilla", "japanese mint", "shiso leaf",
        "sashimi", "japanese", "sushi roll", "temaki"
    ],
    "Rosemary": [
        "rosemary", "herb crusted", "rosemary chicken",
        "rosemary lamb", "roasted rosemary", "herb roasted",
        "mediterranean grill", "italian herbs"
    ]
}

# Cuisine-based probability (if cuisine matches, assign base probability)
CUISINE_SKU_AFFINITY = {
    "Thai": {
        "Lemon Grass": 0.85, "Thai Basil": 0.80, "Thai Bird Chilli": 0.75,
        "Thai Asparagus": 0.30
    },
    "Japanese": {
        "Shiso Leaves": 0.40, "Imported Avocado": 0.50
    },
    "Italian": {
        "Cherry Tomato": 0.70, "Rosemary": 0.65, "Parsley": 0.60,
        "Italian Lemon": 0.40
    },
    "Mediterranean": {
        "Cherry Tomato": 0.65, "Rosemary": 0.55, "Parsley": 0.55
    },
    "Continental": {
        "Cherry Tomato": 0.40, "Rosemary": 0.45, "Parsley": 0.40,
        "Imported Avocado": 0.25, "Blueberry": 0.20
    },
    "Mexican": {
        "Imported Avocado": 0.80, "Cherry Tomato": 0.50
    },
    "French": {
        "Rosemary": 0.50, "Parsley": 0.55, "Cherry Tomato": 0.40
    },
    "Korean": {
        "Shiso Leaves": 0.30
    },
    "Vietnamese": {
        "Lemon Grass": 0.70, "Thai Basil": 0.50, "Thai Bird Chilli": 0.40
    },
    "Cafe": {
        "Blueberry": 0.35, "Imported Avocado": 0.30
    },
    "Bakery": {
        "Blueberry": 0.30, "Rosemary": 0.20
    },
    "European": {
        "Rosemary": 0.50, "Parsley": 0.45, "Cherry Tomato": 0.40
    },
    "Asian": {
        "Lemon Grass": 0.40, "Thai Basil": 0.30, "Thai Bird Chilli": 0.25
    }
}


def infer_sku_probability_from_menu(menu_items, cuisines_str=""):
    """
    Deterministic ingredient inference from menu item names.
    Uses keyword matching + cuisine affinity for probability scores.
    
    Returns dict of {sku: probability}
    """
    probabilities = {sku: 0.0 for sku in TARGET_SKUS}
    
    if not menu_items:
        return probabilities
    
    # Combine all menu item names into searchable text
    all_items_text = " ".join([
        item.get("name", "").lower() + " " + item.get("description", "").lower()
        for item in menu_items
    ]).lower()
    
    # Step 1: Direct keyword matching (high confidence)
    for sku, keywords in SKU_KEYWORDS.items():
        max_score = 0.0
        for keyword in keywords:
            if keyword in all_items_text:
                # Direct mention in menu = high probability
                max_score = max(max_score, 0.90)
                break
        probabilities[sku] = max(probabilities[sku], max_score)
    
    # Step 2: Cuisine-based affinity (medium confidence)
    cuisines = cuisines_str.lower() if cuisines_str else ""
    for cuisine, sku_map in CUISINE_SKU_AFFINITY.items():
        if cuisine.lower() in cuisines:
            for sku, base_prob in sku_map.items():
                # Only use cuisine affinity if keyword match didn't already score higher
                probabilities[sku] = max(probabilities[sku], base_prob)
    
    # Step 3: Count-based boost (if multiple menu items reference the ingredient)
    for sku, keywords in SKU_KEYWORDS.items():
        hit_count = sum(1 for keyword in keywords if keyword in all_items_text)
        if hit_count >= 3:
            probabilities[sku] = min(probabilities[sku] + 0.05, 1.0)
        elif hit_count >= 2:
            probabilities[sku] = min(probabilities[sku] + 0.03, 1.0)
    
    return probabilities


def build_probability_matrix(results):
    """Build the final Restaurant x Ingredient probability matrix."""
    rows = []
    for r in results:
        row = {
            "Restaurant": r["restaurant_name"],
            "Address": r["address"],
            "Swiggy_ID": r.get("swiggy_id", "NOT_FOUND"),
            "Swiggy_Match": r.get("swiggy_match_name", ""),
            "Cuisines": r.get("cuisines", ""),
            "Menu_Items_Count": r.get("menu_count", 0),
        }
        probs = r.get("probabilities", {})
        for sku in TARGET_SKUS:
            row[sku] = probs.get(sku, 0.0)
        rows.append(row)
    
    df = pd.DataFrame(rows)
    
    # Sort by highest total probability across all SKUs
    df['Total_SKU_Score'] = df[TARGET_SKUS].sum(axis=1)
    df = df.sort_values('Total_SKU_Score', ascending=False)
    
    return df


# ============================================================
# MAIN: Generate batch instructions
# ============================================================
if __name__ == "__main__":
    df = load_customer_list()
    progress_file = init_results_file()
    
    total = len(df)
    num_batches = (total + BATCH_SIZE - 1) // BATCH_SIZE
    
    print(f"\n{'='*60}")
    print(f"INGREDIENT PROBABILITY MATRIX PIPELINE")
    print(f"{'='*60}")
    print(f"Total businesses: {total}")
    print(f"Batch size: {BATCH_SIZE}")
    print(f"Number of batches: {num_batches}")
    print(f"Target SKUs: {len(TARGET_SKUS)}")
    print(f"Swiggy Address: Porur, Chennai ({SWIGGY_ADDRESS_ID})")
    print(f"{'='*60}")
    
    for batch_num in range(num_batches):
        start_idx = batch_num * BATCH_SIZE
        end_idx = min(start_idx + BATCH_SIZE, total)
        batch_df = df.iloc[start_idx:end_idx]
        
        print(f"\nBatch {batch_num + 1}: Rows {start_idx + 1} to {end_idx}")
        print(f"  First: {batch_df.iloc[0]['Particulars']}")
        print(f"  Last:  {batch_df.iloc[-1]['Particulars']}")
    
    # Export the full list for reference
    export_path = os.path.join(OUTPUT_DIR, "all_businesses_for_search.csv")
    df[['Particulars', 'search_name', 'Address']].to_csv(export_path, index=True)
    print(f"\n[EXPORTED] Full search list to: {export_path}")
    print(f"\nReady to begin Swiggy MCP lookups.")
