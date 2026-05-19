import pandas as pd
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

df = pd.read_excel(r'analysis_input\Customer list 08052026.xlsx')

# Filter Tamil Nadu only
tn = df[df['State'].str.contains('Tamil Nadu', case=False, na=False)]

# Count how many appear to be restaurants/food businesses
food_keywords = ['hotel', 'restaurant', 'cafe', 'bakery', 'kitchen', 'food', 'sweet',
                 'catering', 'biryani', 'mess', 'dosa', 'dhaba', 'canteen', 'idly',
                 'snack', 'ice cream', 'juice', 'pizza', 'burger', 'chicken', 'mutton',
                 'fish', 'cakes', 'confectionery', 'bistro', 'brasserie', 'grill',
                 'bar', 'pub', 'brew', 'lounge', 'resort', 'club', 'dine', 'eatery',
                 'tiffin', 'parotta', 'chef', 'cook', 'meals', 'organic', 'health',
                 'fresh', 'farm', 'dairy', 'spice', 'masala', 'curry', 'tandoori',
                 'noodle', 'wok', 'sushi', 'ramen', 'chaat', 'samosa', 'paneer',
                 'pavilion', 'feast', 'express', 'family']

mask = tn['Particulars'].str.lower().str.contains('|'.join(food_keywords), na=False)
food_biz = tn[mask]

print(f"Total rows: {len(df)}")
print(f"Tamil Nadu rows: {len(tn)}")
print(f"Likely food businesses: {len(food_biz)}")
print()
print("ALL FOOD BUSINESSES:")
for i, row in food_biz.iterrows():
    name = row['Particulars']
    addr = str(row['Address'])[:120] if pd.notna(row['Address']) else 'N/A'
    print(f"  {i:4d}. {name}  |  {addr}")
print()
print(f"\nTotal food businesses to process: {len(food_biz)}")
