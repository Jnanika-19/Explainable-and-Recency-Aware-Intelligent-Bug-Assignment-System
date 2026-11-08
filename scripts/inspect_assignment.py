
import pandas as pd

file_path = "dataset/raw/JDT.csv"

columns = [
    "ID",
    "Summary",
    "Component",
    "Status",
    "Resolution",
    "Assigned to",
    "Assigned to detail",
    "History/Activity Log"
]

print("Inspecting assignment history...")

df = pd.read_csv(
    file_path,
    usecols=columns,
    nrows=10,
    low_memory=False
)

for index, row in df.iterrows():

    print("\n" + "=" * 70)

    print("BUG ID:", row["ID"])
    print("SUMMARY:", row["Summary"])
    print("COMPONENT:", row["Component"])
    print("STATUS:", row["Status"])
    print("RESOLUTION:", row["Resolution"])

    print("\nCURRENT ASSIGNEE:")
    print(row["Assigned to"])

    print("\nASSIGNEE DETAILS:")
    print(row["Assigned to detail"])

    history = row["History/Activity Log"]

    print("\nACTIVITY HISTORY:")

    if pd.isna(history):
        print("No history available")
    else:
        print("History length:", len(str(history)))
        print(str(history)[:3000])

print("\nInspection completed!")
