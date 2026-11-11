
import pandas as pd

FILE_PATH = "dataset/raw/JDT.csv"

print("Inspecting JDT dataset...")

df = pd.read_csv(
    FILE_PATH,
    nrows=5,
    dtype=str,
    low_memory=False
)

print("\n========== JDT DATASET SCHEMA ==========")

print("Total columns:", len(df.columns))

for i, column in enumerate(df.columns, 1):
    print(f"{i}. {column}")

print("\n========== SAMPLE RECORDS ==========")

print(df.head().to_string())

print("\n========== COMPLETED ==========")
