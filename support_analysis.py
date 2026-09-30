import pandas as pd

df = pd.read_csv(r"C:\Users\PRASHANT\OneDrive\Desktop\task\support_tickets.csv")
df["created_at"] = pd.to_datetime(df["created_at"])
df["customer_rating"] = pd.to_numeric(df["customer_rating"], errors="coerce")

print("Total rows:", len(df))
print("Unresolved tickets:", (df["status"] != "Resolved").sum())
print("Average rating:", df["customer_rating"].mean())
print("Status value counts:\n", df["status"].value_counts())
print("Created_at min:", df["created_at"].min())
print("Created_at max:", df["created_at"].max())
print("Average Technical rating:", df[df["category"] == "Technical"]["customer_rating"].mean())
