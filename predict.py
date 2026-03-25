from transformers import BertTokenizer, BertForSequenceClassification
import torch
import torch.nn.functional as F

# -----------------------
# Load model
# -----------------------
model_path = "./model"

tokenizer = BertTokenizer.from_pretrained(model_path)
model = BertForSequenceClassification.from_pretrained(model_path)

model.eval()

# -----------------------
# Label mapping (IMPORTANT: same as training)
# -----------------------
label_map = {
    0: "Passage",
    1: "MCQ",
    2: "mainQuestion",
    3: "subQuestion"
}

# -----------------------
# Prediction function
# -----------------------
def predict(text):
    inputs = tokenizer(
        text,
        return_tensors="pt",
        truncation=True,
        padding=True,
        max_length=128
    )

    with torch.no_grad():
        outputs = model(**inputs)

    logits = outputs.logits

    # Convert to probabilities
    probs = F.softmax(logits, dim=1)[0]

    # Get predicted class
    predicted_class = torch.argmax(probs).item()

    return {
        "prediction": label_map[predicted_class],
        "probabilities": {
            label_map[i]: float(probs[i])
            for i in range(len(probs))
        }
    }

# -----------------------
# Test examples
# -----------------------
if __name__ == "__main__":
    
    test_questions = [
        "What is the capital of India?\nA) Mumbai\nB) Delhi\nC) Chennai\nD) Kolkata",
        
        "Read the passage below and answer the questions that follow...",
        
        "Explain Newton's laws of motion.",
        
        "a) Define photosynthesis\nb) Explain its process\nc) State its importance"
    ]

    for q in test_questions:
        result = predict(q)
        print("\nQuestion:\n", q)
        print("Prediction:", result["prediction"])
        print("Probabilities:", result["probabilities"])