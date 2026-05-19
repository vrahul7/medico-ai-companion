import pandas as pd
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

df = pd.read_excel(r'analysis_input\Customer list 08052026.xlsx')
pd.set_option('display.max_columns', None)
pd.set_option('display.max_colwidth', 100)
pd.set_option('display.width', 400)

print("SHAPE:", df.shape)
print()
print("COLUMNS:", list(df.columns))
print()

# Filter for Tamil Nadu / Chennai restaurants
tn = df[df['State'].str.contains('Tamil Nadu', case=False, na=False)]
print(f"Tamil Nadu rows: {len(tn)}")
print()
print("FIRST 50 TN ROWS:")
print(tn.head(50).to_string())
print()
print("UNIQUE STATES:", df['State'].dropna().unique().tolist())
