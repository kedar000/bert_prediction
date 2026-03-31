import pandas as pd

# Load both Excel files
df1 = pd.read_excel("file1.xlsx")
df2 = pd.read_excel("file2.xlsx")

# Combine (row-wise)
combined_df = pd.concat([df1, df2], ignore_index=True)

# Save
combined_df.to_excel("combined.xlsx", index=False)

print("✅ Files combined successfully")