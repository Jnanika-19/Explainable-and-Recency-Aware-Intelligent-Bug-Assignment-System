
import pandas as pd

file_path = "dataset/raw/JDT.csv"

print("Inspecting Eclipse JDT dataset...")

# Read only 5 records, not the entire 5.9 GB file
df = pd.read_csv(file_path, nrows=5)

print("\nCOLUMN NAMES:")
for column in df.columns:
    print("-", column)

print("\nFIRST 5 RECORDS:")
print(df.head().to_string())

print("\nTOTAL COLUMNS:", len(df.columns))
