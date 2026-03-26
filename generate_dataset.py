from datasets import load_dataset
import pandas as pd
import re
import random
import string
import os
from sklearn.model_selection import train_test_split

os.makedirs("dataset_csv", exist_ok=True)

# -------------------------------
# Clean function
# -------------------------------
def clean_text(text):
    if text is None:
        return None
    text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

# -------------------------------
# Label variation
# -------------------------------
def format_option(label, text):
    styles = [
        f"{label}) {text}",
        f"({label}) {text}",
        f"{label}. {text}"
    ]
    return random.choice(styles)

def generate_labels(n):
    return [chr(97+i) for i in range(n)]  # a,b,c...

# =========================================================
# 1. PASSAGE
# =========================================================
race = load_dataset("ehovy/race", "all")
df_race = race["train"].to_pandas()

grouped = []
for article, group in df_race.groupby("article"):
    text = "Read the following passage and answer the questions:\n\n"
    text += clean_text(article) + "\n\n"

    for i, row in enumerate(group.itertuples(), 1):
        opts = "\n".join([
            format_option(chr(65+j), opt) 
            for j, opt in enumerate(row.options)
        ])
        text += f"Question {i}: {row.question}\nOptions:\n{opts}\n\n"

    grouped.append({"question": text.strip(), "question_type": "Passage"})

df_passage = pd.DataFrame(grouped)

# Convert some passage → MCQ (negative examples)
def extract_mcq_from_passage(text):
    matches = re.findall(
        r"Question \d+:\s*(.*?)\nOptions:\n(.*?)(?=\nQuestion|\Z)",
        text, re.DOTALL
    )
    return [
        {
            "question": clean_text(
                f"Choose the correct option:\n\nQuestion: {q}\n\nOptions:\n{opts}"
            ),
            "question_type": "MCQ"
        }
        for q, opts in matches
    ]

converted_mcq = []
for row in df_passage["question"].sample(frac=0.3):
    converted_mcq.extend(extract_mcq_from_passage(row))

df_converted_mcq = pd.DataFrame(converted_mcq)

# =========================================================
# 2. MCQ
# =========================================================
mcq = load_dataset("LiSoviMa/M1_MCQ_generated_with_questions")
df_mcq = mcq["train"].to_pandas()

def extract_mcq(text):
    try:
        q = re.search(r"Question:\s*(.*?)\nOptions:", text, re.DOTALL)
        o = re.search(r"Options:\s*\[(.*?)\]", text, re.DOTALL)
        options = re.findall(r"'(.*?)'", o.group(1)) if o else []
        if not options:
            return None

        opts = "\n".join([
            format_option(chr(65+i), opt)
            for i, opt in enumerate(options)
        ])

        prefix = random.choice([
            "Choose the correct option:",
            "Select the correct answer:",
            "Pick the right option:"
        ])

        return clean_text(
            f"{prefix}\n\nQuestion: {q.group(1)}\n\nOptions:\n{opts}"
        )
    except:
        return None

df_mcq["question"] = df_mcq["text"].apply(extract_mcq)
df_mcq = df_mcq[df_mcq["question"].notnull()]

df_mcq_final = pd.DataFrame({
    "question": df_mcq["question"],
    "question_type": "MCQ"
})

# =========================================================
# 3. MAIN QUESTIONS
# =========================================================
quora = load_dataset("toughdata/quora-question-answer-dataset")
df_main = quora["train"].to_pandas()

df_main["question"] = df_main["question"].apply(clean_text)
df_main = df_main[df_main["question"].notnull()]

df_main_final = pd.DataFrame({
    "question": df_main["question"].apply(
        lambda x: f"Answer the following question:\n\n{x}"
    ),
    "question_type": "mainQuestion"
})

# =========================================================
# 4. SUB QUESTIONS
# =========================================================
multi = load_dataset("mtc/multirc_train_all_answers")
df_sub = multi["train"].to_pandas()

df_sub["summary"] = df_sub["summary"].apply(clean_text)
df_sub = df_sub[df_sub["summary"].notnull()]

grouped_sub = []
for doc, group in df_sub.groupby("document"):
    qs = list(dict.fromkeys(group["summary"].tolist()))
    if len(qs) < 3:
        continue

    labels = generate_labels(len(qs))
    text = "Answer the following questions:\n\n"
    text += "\n".join([
        f"{random.choice([f'{l})', f'({l})', f'{l}.'])} {qs[i]}"
        for i, l in enumerate(labels)
    ])

    grouped_sub.append({
        "question": text,
        "question_type": "subQuestion"
    })

df_sub_final = pd.DataFrame(grouped_sub)

# =========================================================
# 5. AUGMENT SUB QUESTIONS
# =========================================================
df_main_sample = df_main_final.sample(frac=0.3)

def create_sub_groups(df):
    data = df["question"].tolist()
    results = []
    i = 0

    while i < len(data):
        size = random.randint(3, 5)
        chunk = data[i:i+size]

        if len(chunk) < 3:
            break

        labels = generate_labels(len(chunk))
        text = "Answer the following questions:\n\n"
        text += "\n".join([
            f"{labels[j]}) {chunk[j]}"
            for j in range(len(chunk))
        ])

        results.append({
            "question": text,
            "question_type": "subQuestion"
        })

        i += size

    return pd.DataFrame(results)

df_sub_aug = create_sub_groups(df_main_sample)

# =========================================================
# 6. MERGE + CLEAN
# =========================================================
combined_df = pd.concat([
    df_passage,
    df_mcq_final,
    df_converted_mcq,
    df_main_final,
    df_sub_final,
    df_sub_aug
], ignore_index=True)

# Remove duplicates
combined_df = combined_df.drop_duplicates(subset=["question"])

# Shuffle
combined_df = combined_df.sample(frac=1).reset_index(drop=True)

# =========================================================
# 7. BALANCE (WITHOUT OVERDUPLICATION)
# =========================================================
target_size = 8000
balanced = []

for label in combined_df["question_type"].unique():
    df_class = combined_df[combined_df["question_type"] == label]
    df_class = df_class.sample(n=min(len(df_class), target_size))
    balanced.append(df_class)

balanced_df = pd.concat(balanced).sample(frac=1).reset_index(drop=True)

# =========================================================
# 8. LABEL + SPLIT
# =========================================================
label_map = {
    "Passage": 0,
    "MCQ": 1,
    "mainQuestion": 2,
    "subQuestion": 3
}

balanced_df["label"] = balanced_df["question_type"].map(label_map)

train_df, test_df = train_test_split(
    balanced_df,
    test_size=0.1,
    stratify=balanced_df["label"],
    random_state=42
)

train_df.to_csv("dataset_csv/train.csv", index=False)
test_df.to_csv("dataset_csv/test.csv", index=False)

print("✅ DATASET FIXED & READY")
print(train_df["question_type"].value_counts())

# =========================================================
# 9. CREATE RANDOM 400 SAMPLE CSV (100 PER CLASS)
# =========================================================

samples = []

for label_name, label_id in label_map.items():
    df_class = balanced_df[balanced_df["label"] == label_id]
    
    # Randomly pick 100 samples
    df_sample = df_class.sample(n=100, random_state=42)
    samples.append(df_sample)

sample_400_df = pd.concat(samples).sample(frac=1).reset_index(drop=True)

# Keep only required columns
sample_400_df = sample_400_df[["question", "label"]]
sample_400_df.columns = ["Question", "label"]

# Save CSV
sample_400_df.to_csv("dataset_csv/sample_400.csv", index=False)

print("✅ sample_400.csv created with 400 balanced random questions")