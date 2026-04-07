from fastapi import FastAPI
from pydantic import BaseModel
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch

app = FastAPI()

MODEL_PATH = "8_512_weighted_loss_model/bert_question_type_model"

tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
model = AutoModelForSequenceClassification.from_pretrained(MODEL_PATH)

model.eval()

class Request(BaseModel):
    text: str

label_map = {
    0: "PASSAGE",
    1: "MCQ",
    2: "MAIN",
    3: "SUB"
}

@app.post("/predict")
def predict(req: Request):
    inputs = tokenizer(req.text, return_tensors="pt", truncation=True)

    with torch.no_grad():
        outputs = model(**inputs)

    probs = torch.softmax(outputs.logits, dim=1)
    pred = torch.argmax(probs, dim=1).item()

    return {
        "label": label_map[pred],
        "confidence": float(probs[0][pred])
    }
    
    

# pip install fastapi uvicorn transformers torch
# uvicorn bert_api:app --host 0.0.0.0 --port 8000
# POST http://localhost:8000/predict
# {
#   "text": "What is AI?"
# }
    
    