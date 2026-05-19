"""
Phase 2: Update matrix with Swiggy IDs found so far.
Records all confirmed matches from MCP searches.
"""
import pandas as pd
import json

# Load the Phase 1 matrix
df = pd.read_excel("analysis_output/ingredient_probability_matrix_phase1.xlsx")
print(f"Loaded matrix: {len(df)} rows")

# Ensure ID columns are string type
df["Swiggy_Food_ID"] = df["Swiggy_Food_ID"].astype(str).replace("nan", "")
df["Swiggy_Dineout_ID"] = df["Swiggy_Dineout_ID"].astype(str).replace("nan", "")

# CONFIRMED SWIGGY FOOD MATCHES (from MCP searches)
food_matches = {
    "Achayathis Restaurant": {"food_id": "968291", "cuisines": "South Indian, Biryani, Seafood, Kerala"},
    "Adyar Ananda Bhavan Sweets India Pvt Ltd": {"food_id": "13481", "cuisines": "South Indian, Sweets, Chinese"},
    "Copper Kitchen": {"food_id": "13258", "cuisines": "Biryani, Barbecue, Chettinad, Chinese"},
    "Buhari Hotel - A Unit of M.B and Brothers": {"food_id": "50972", "cuisines": "Biryani, Chinese"},
}

# CONFIRMED SWIGGY DINEOUT MATCHES
dineout_matches = {
    "Achayathis Restaurant": {"dineout_id": "995338", "cuisines": "Kerala, Seafood"},
}

# Apply matches
food_updated = 0
dineout_updated = 0

for idx, row in df.iterrows():
    name = str(row["Restaurant"]).strip()
    
    # Check food matches (partial matching)
    for match_name, match_data in food_matches.items():
        if match_name.lower() in name.lower() or name.lower() in match_name.lower():
            df.at[idx, "Swiggy_Food_ID"] = match_data["food_id"]
            food_updated += 1
            break
    
    # Check dineout matches
    for match_name, match_data in dineout_matches.items():
        if match_name.lower() in name.lower() or name.lower() in match_name.lower():
            df.at[idx, "Swiggy_Dineout_ID"] = match_data["dineout_id"]
            dineout_updated += 1
            break

print(f"Food IDs updated: {food_updated}")
print(f"Dineout IDs updated: {dineout_updated}")

# Save updated matrix
df.to_excel("analysis_output/ingredient_probability_matrix_v2.xlsx", index=False, sheet_name="SKU Probability Matrix")
df.to_csv("analysis_output/ingredient_probability_matrix_v2.csv", index=False)
print("Saved v2 matrix")

# Show stats
has_food_id = df[df["Swiggy_Food_ID"].notna() & (df["Swiggy_Food_ID"] != "")].shape[0]
has_dineout_id = df[df["Swiggy_Dineout_ID"].notna() & (df["Swiggy_Dineout_ID"] != "")].shape[0]
has_any_id = df[(df["Swiggy_Food_ID"].notna() & (df["Swiggy_Food_ID"] != "")) | (df["Swiggy_Dineout_ID"].notna() & (df["Swiggy_Dineout_ID"] != ""))].shape[0]

print(f"\nCurrent Swiggy coverage:")
print(f"  Food IDs: {has_food_id}")
print(f"  Dineout IDs: {has_dineout_id}")
print(f"  Any ID: {has_any_id}")
print(f"  No ID: {len(df) - has_any_id}")

# Print top 20 with scores
print(f"\nTop 20 by SKU score:")
top = df.nlargest(20, "Total_SKU_Score")
for _, r in top.iterrows():
    fid = r.get("Swiggy_Food_ID", "")
    did = r.get("Swiggy_Dineout_ID", "")
    ids = f"F:{fid}" if fid else ""
    ids += f" D:{did}" if did else ""
    if not ids:
        ids = "NO_ID"
    print(f"  [{r['Total_SKU_Score']:.1f}] {str(r['Restaurant'])[:45]:45s} | {ids}")
