from datasets import load_dataset
import pandas as pd
import re

# -------------------------------
# 1. Load dataset
# -------------------------------
dataset = load_dataset("toughdata/quora-question-answer-dataset")
df = dataset["train"].to_pandas()

# -------------------------------
# 2. Clean text (optional but safe)
# -------------------------------
def clean_text(text):
    if text is None:
        return None
    
    # Remove illegal Excel characters
    text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", "", text)
    
    return text.strip()

# Apply cleaning
df["question"] = df["question"].apply(clean_text)

# Remove null/empty questions
df = df[df["question"].notnull()]
df = df[df["question"] != ""]

# -------------------------------
# 3. Create final dataset
# -------------------------------
final_df = pd.DataFrame({
    "question": df["question"],
    "question_type": ["mainQuestion"] * len(df)
})

# -------------------------------
# 4. Save files
# -------------------------------

# CSV (safe)
final_df.to_csv("main_questions.csv", index=False)

# Excel
final_df.to_excel("main_questions.xlsx", index=False)

print("✅ Done!")
print("Saved:")
print("- main_questions.csv")
print("- main_questions.xlsx")