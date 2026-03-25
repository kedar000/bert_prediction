from transformers import (
    BertTokenizer,
    BertForSequenceClassification,
    Trainer,
    TrainingArguments,
    EarlyStoppingCallback
)
from datasets import Dataset
import pandas as pd
import torch
from sklearn.metrics import accuracy_score

# -----------------------
# Load dataset
# -----------------------
train_df = pd.read_csv("dataset_csv/train.csv")
test_df = pd.read_csv("dataset_csv/test.csv")

train_df = train_df[["question", "label"]]
test_df = test_df[["question", "label"]]

train_dataset = Dataset.from_pandas(train_df)
test_dataset = Dataset.from_pandas(test_df)

# -----------------------
# Tokenizer
# -----------------------
tokenizer = BertTokenizer.from_pretrained("bert-base-uncased")

def tokenize(example):
    return tokenizer(
        example["question"],
        truncation=True,
        padding="max_length",
        max_length=256   # increased slightly for better context
    )

train_dataset = train_dataset.map(tokenize, batched=True)
test_dataset = test_dataset.map(tokenize, batched=True)

# -----------------------
# Model
# -----------------------
model = BertForSequenceClassification.from_pretrained(
    "bert-base-uncased",
    num_labels=4
)

# -----------------------
# Metrics (Evaluation)
# -----------------------
def compute_metrics(eval_pred):
    logits, labels = eval_pred
    preds = logits.argmax(axis=1)
    return {
        "accuracy": accuracy_score(labels, preds)
    }

# -----------------------
# Training Arguments
# -----------------------
training_args = TrainingArguments(
    output_dir="./results",
    eval_strategy="steps",
    save_strategy="steps",          # ✅ ADD THIS
    eval_steps=200,
    save_steps=200,                 # ✅ MATCH THIS
    logging_steps=50,
    learning_rate=2e-5,
    per_device_train_batch_size=2,
    per_device_eval_batch_size=2,
    num_train_epochs=3,
    weight_decay=0.01,
    dataloader_pin_memory=False,
    load_best_model_at_end=True
)

# -----------------------
# Trainer
# -----------------------
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset,
    eval_dataset=test_dataset,
    compute_metrics=compute_metrics,
    callbacks=[EarlyStoppingCallback(early_stopping_patience=2)]
)

# -----------------------
# Train
# -----------------------
trainer.train()

# -----------------------
# Save best model
# -----------------------
trainer.save_model("./model")
tokenizer.save_pretrained("./model")

print("✅ Training complete with evaluation & early stopping")