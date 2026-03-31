import pandas as pd

# Load CSV safely (handles multiline + quotes)
df = pd.read_csv(
    "dataset_csv/subQuestion_600.csv",
    quotechar='"',
    escapechar='\\',
    engine="python"
)

# Keep only Question column (ignore old label)
df = df[["question"]]

# Rename column
df.columns = ["Question"]

# Add fixed label
df["label"] = "Sub Question"

# Save to Excel
df.to_excel("sub-question.xlsx", index=False)

print("✅ Excel created with 'Sub Question' label for all rows")