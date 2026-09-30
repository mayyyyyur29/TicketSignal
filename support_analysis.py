import pandas as pd

df = pd.read_csv(r"C:\Users\PRASHANT\OneDrive\Desktop\task\support_tickets.csv")

print("Total rows:", len(df))
print("Unresolved tickets:", (df["status"] == "Open").sum())
print("average rating of the tickets:", df[df["category"] == "technical"]["customer_rating"].mean())
print(df.describe())