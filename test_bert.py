from transformers import BertTokenizer, BertForSequenceClassification
import torch
import torch.nn.functional as F

# Load pretrained tokenizer + model
tokenizer = BertTokenizer.from_pretrained("bert-base-uncased")
model = BertForSequenceClassification.from_pretrained("bert-base-uncased")

# Put model in evaluation mode
model.eval()

# Sample input
text = "What is the capital of India?"

# Tokenize input
inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True)

# Run model
with torch.no_grad():
    outputs = model(**inputs)

# Extract logits
logits = outputs.logits

print("Logits:", logits)
print("Shape:", logits.shape)

probs = F.softmax(logits, dim=1)
print("Probabilities:", probs)