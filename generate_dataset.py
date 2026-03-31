import re
import random
import pandas as pd
import os
from datasets import load_dataset
from sklearn.model_selection import train_test_split

os.makedirs("dataset_csv", exist_ok=True)

# =========================================================
# PREFIXES
# =========================================================
sub_prefixes = [
    "Answer multiple independent questions:",
    "Solve the following:", 
    "Answer all parts:",
    "Respond to each question:",
    "Answer the questions below:",
    "Provide answers for each of the following:",
    "Attempt all the questions:",
    "Answer the following set of questions:",
    "These are separate questions, answer each:",
    "Answer each question independently:",
    "Please answer the following:",
    "Questions:",
    "Solve:",
    "Can you answer these?",
    "Work through the following:",
    "Answer all questions individually:",
    "Respond separately to each question:",
    "Answer all:",
    "Do the following:",
    ""
]

# =========================================================
# CLEAN
# =========================================================
def clean_text(text):
    if text is None:
        return None
    text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", "", str(text))
    text = re.sub(r"\s+", " ", text)
    return text.strip()

# =========================================================
# PREFIX CHECK
# =========================================================
def has_prefix(text):
    if not text:
        return False

    text = text.lower().strip()

    patterns = [
        "answer", "solve", "respond", "questions",
        "attempt", "please", "do the following"
    ]

    return any(text.startswith(p) for p in patterns)

# =========================================================
# FORMAT
# =========================================================
def generate_labels(n):
    return [chr(97+i) for i in range(n)]

def get_format_style():
    return random.choice([
        lambda l, q: f"{l}) {q}",
        lambda l, q: f"({l}) {q}",
        lambda l, q: f"{l}. {q}",
        lambda l, q: f"{l.upper()}) {q}",
        lambda l, q: f"{l.upper()}. {q}"
    ])

def get_prefix():
    return "" if random.random() < 0.3 else random.choice(sub_prefixes)

# =========================================================
# PASSAGE
# =========================================================
race = load_dataset("ehovy/race", "all")
df_race = race["train"].to_pandas()

grouped = []
for article, group in df_race.groupby("article"):
    text = "Read the following passage and answer the questions:\n\n"
    text += clean_text(article) + "\n\n"

    for i, row in enumerate(group.itertuples(), 1):
        opts = "\n".join([
            f"{chr(65+j)}) {opt}" for j, opt in enumerate(row.options)
        ])
        text += f"Question {i}: {row.question}\nOptions:\n{opts}\n\n"

    grouped.append({"question": text.strip(), "question_type": "Passage"})

df_passage = pd.DataFrame(grouped)

# =========================================================
# MCQ
# =========================================================
mcq = load_dataset("LiSoviMa/M1_MCQ_generated_with_questions")
df_mcq = mcq["train"].to_pandas()

def extract_mcq(text):
    try:
        q = re.search(r"Question:\s*(.*?)\nOptions:", text, re.DOTALL)
        o = re.search(r"Options:\s*\[(.*?)\]", text, re.DOTALL)
        options = re.findall(r"'(.*?)'", o.group(1))

        opts = "\n".join([
            f"{chr(65+i)}) {opt}" for i, opt in enumerate(options)
        ])

        return clean_text(
            f"Choose the correct option:\n\nQuestion: {q.group(1)}\n\nOptions:\n{opts}"
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
# MAIN QUESTION
# =========================================================
quora = load_dataset("toughdata/quora-question-answer-dataset")
df_main = quora["train"].to_pandas()

df_main["question"] = df_main["question"].apply(clean_text)
df_main = df_main[df_main["question"].notnull()]

df_main_final = pd.DataFrame({
    "question": df_main["question"],
    "question_type": "mainQuestion"
})

# =========================================================
# SUB QUESTIONS (FIXED)
# =========================================================
def build_subquestion_group(questions):
    questions = [clean_text(q) for q in questions if q]
    if len(questions) < 3:
        return None

    labels = generate_labels(len(questions))
    format_style = get_format_style()

    # 🔥 PREFIX ADDED ONLY ONCE
    prefix = get_prefix()
    if prefix and not has_prefix(questions[0]):
        text = prefix.strip() + "\n\n"
    else:
        text = ""

    # 🔥 ALL QUESTIONS ADDED TO SAME BLOCK
    text += "\n".join([
        format_style(labels[i], questions[i])
        for i in range(len(questions))
    ])

    return text.strip()

# REAL SUB QUESTIONS
multi = load_dataset("mtc/multirc_train_all_answers")
df_sub = multi["train"].to_pandas()

grouped_sub = []
for doc, group in df_sub.groupby("document"):
    qs = list(dict.fromkeys(group["summary"].tolist()))

    text = build_subquestion_group(qs)
    if text:
        grouped_sub.append({
            "question": text,
            "question_type": "subQuestion"
        })

df_sub_final = pd.DataFrame(grouped_sub)

# AUGMENTED SUB QUESTIONS
df_main_sample = df_main_final.sample(frac=0.3)

augmented = []
data = df_main_sample["question"].tolist()
i = 0

while i < len(data):
    size = random.randint(3, 5)
    chunk = data[i:i+size]

    text = build_subquestion_group(chunk)
    if text:
        augmented.append({
            "question": text,
            "question_type": "subQuestion"
        })

    i += size

df_sub_aug = pd.DataFrame(augmented)

# =========================================================
# MERGE
# =========================================================
combined_df = pd.concat([
    df_passage,
    df_mcq_final,
    df_main_final,
    df_sub_final,
    df_sub_aug
], ignore_index=True)

combined_df = combined_df.drop_duplicates(subset=["question"])
combined_df = combined_df.sample(frac=1).reset_index(drop=True)

# =========================================================
# LABELS
# =========================================================
label_map = {
    "Passage": 0,
    "MCQ": 1,
    "mainQuestion": 2,
    "subQuestion": 3
}

combined_df["label"] = combined_df["question_type"].map(label_map)

# =========================================================
# SPLIT
# =========================================================
train_df, test_df = train_test_split(
    combined_df,
    test_size=0.1,
    stratify=combined_df["label"],
    random_state=42
)

train_df.to_csv("dataset_csv/train.csv", index=False)
test_df.to_csv("dataset_csv/test.csv", index=False)

# =========================================================
# 400 SAMPLE (100 EACH)
# =========================================================
samples_100 = []

for label_id in label_map.values():
    df_class = combined_df[combined_df["label"] == label_id]
    samples_100.append(df_class.sample(n=100, random_state=42))

sample_400 = pd.concat(samples_100).sample(frac=1)
sample_400[["question", "label"]].to_csv("dataset_csv/sample_400_final.csv", index=False)

# =========================================================
# 200 EACH TYPE
# =========================================================
for name, label_id in label_map.items():
    df_class = combined_df[combined_df["label"] == label_id]
    df_200 = df_class.sample(n=600, random_state=42)

    df_200[["question", "label"]].to_csv(
        f"dataset_csv/{name}_600.csv",
        index=False
    )

print("✅ FIXED: Subquestion grouping + datasets generated")