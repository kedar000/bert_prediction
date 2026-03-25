from transformers import BertForSequenceClassification, BertTokenizer

model = BertForSequenceClassification.from_pretrained("./results/checkpoint-600")
tokenizer = BertTokenizer.from_pretrained("bert-base-uncased")

model.save_pretrained("./model")
tokenizer.save_pretrained("./model")

print("✅ Final model saved")