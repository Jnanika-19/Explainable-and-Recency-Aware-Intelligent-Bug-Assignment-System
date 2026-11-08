
import pandas as pd
import json

file_path = "dataset/raw/JDT.csv"

columns = [
    "ID",
    "Product",
    "Creation time",
    "Component",
    "Assigned to",
    "History/Activity Log"
]

target_ids = {
    "339984",
    "150657",
    "82251",
    "42519",
    "195810",
    "203964",
    "251865",
    "308820",
    "314170",
    "335029"
}

print("Inspecting initial assignment cases...\n")

found = set()

for chunk in pd.read_csv(
    file_path,
    usecols=columns,
    chunksize=1000,
    low_memory=False,
    dtype={"ID": str}
):

    selected = chunk[chunk["ID"].isin(target_ids)]

    for _, row in selected.iterrows():

        found.add(row["ID"])

        print("\n" + "=" * 70)
        print("BUG:", row["ID"])
        print("PRODUCT:", row["Product"])
        print("CREATED:", row["Creation time"])
        print("COMPONENT:", row["Component"])
        print("CURRENT ASSIGNEE:", row["Assigned to"])

        try:
            activities = json.loads(row["History/Activity Log"])

            activities.sort(
                key=lambda x: x.get("when", "")
            )
            print("\nASSIGNMENT AND PRODUCT CHANGE HISTORY:")

            for activity in activities:
                relevant_changes = [
                change
                for change in activity.get("changes", [])
                    if change.get("field_name") in ["assigned_to", "product"]
                ]

                if not relevant_changes:
                    continue

                print("\nDATE:", activity.get("when"))
                print("CHANGED BY:", activity.get("who"))

                for change in relevant_changes:
                    print(
                        change.get("field_name"),
                        "| OLD:",
                        change.get("removed"),
                        "| NEW:",
                        change.get("added")
                    )

        except Exception as error:
            print("Could not parse history:", error)

print("\nInspection completed!")
print("Records found:", len(found))
print("Records not found:", target_ids - found)
