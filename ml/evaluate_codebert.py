import os
import json
import pandas as pd
import numpy as np
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, confusion_matrix
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import argparse

def compute_top_k_accuracy(probs, true_labels, k=3):
    correct = 0
    for p, y in zip(probs, true_labels):
        top_k = np.argsort(p)[::-1][:k]
        if y in top_k:
            correct += 1
    return correct / len(true_labels)

def compute_ece(probs, true_labels, n_bins=10):
    # Expected Calibration Error
    confidences = np.max(probs, axis=1)
    predictions = np.argmax(probs, axis=1)
    accuracies = (predictions == true_labels)
    
    ece = 0.0
    bin_boundaries = np.linspace(0, 1, n_bins + 1)
    
    for i in range(n_bins):
        bin_lower, bin_upper = bin_boundaries[i], bin_boundaries[i+1]
        in_bin = (confidences > bin_lower) & (confidences <= bin_upper)
        if np.sum(in_bin) > 0:
            bin_acc = np.mean(accuracies[in_bin])
            bin_conf = np.mean(confidences[in_bin])
            ece += np.sum(in_bin) / len(true_labels) * np.abs(bin_acc - bin_conf)
    return ece

def evaluate_split(model, tokenizer, device, df, batch_size=16):
    model.eval()
    all_probs = []
    all_preds = []
    all_true = df["global_misconception_index"].tolist()
    
    texts = ["Problem: \n\nCode:\n" + str(code) for code in df["generated_code"]]
    
    for i in range(0, len(texts), batch_size):
        batch_texts = texts[i:i+batch_size]
        inputs = tokenizer(batch_texts, return_tensors="pt", padding=True, truncation=True, max_length=512)
        inputs = {k: v.to(device) for k, v in inputs.items()}
        
        with torch.no_grad():
            outputs = model(**inputs)
            
        logits = outputs.logits
        probs = torch.nn.functional.softmax(logits, dim=-1).cpu().numpy()
        preds = np.argmax(probs, axis=1)
        
        all_probs.extend(probs)
        all_preds.extend(preds)
        print(f"\rEvaluated {min(i+batch_size, len(texts))}/{len(texts)}", end="")
    print()
    
    all_probs = np.array(all_probs)
    all_preds = np.array(all_preds)
    all_true = np.array(all_true)
    
    macro_f1 = f1_score(all_true, all_preds, average='macro', zero_division=0)
    weighted_f1 = f1_score(all_true, all_preds, average='weighted', zero_division=0)
    macro_prec = precision_score(all_true, all_preds, average='macro', zero_division=0)
    macro_rec = recall_score(all_true, all_preds, average='macro', zero_division=0)
    top1_acc = accuracy_score(all_true, all_preds)
    top3_acc = compute_top_k_accuracy(all_probs, all_true, k=3)
    per_class_f1 = f1_score(all_true, all_preds, average=None, zero_division=0).tolist()
    cm = confusion_matrix(all_true, all_preds).tolist()
    ece = compute_ece(all_probs, all_true)
    
    return {
        "macro_f1": macro_f1,
        "weighted_f1": weighted_f1,
        "macro_precision": macro_prec,
        "macro_recall": macro_rec,
        "top_1_accuracy": top1_acc,
        "top_3_accuracy": top3_acc,
        "per_class_f1": per_class_f1,
        "confusion_matrix": cm,
        "ece": ece
    }

def main():
    model_path = os.path.join(os.path.dirname(__file__), "models", "best_codebert")
    print(f"Loading model from {model_path}...")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    model = AutoModelForSequenceClassification.from_pretrained(model_path).to(device)
    
    data_dir = os.path.join(os.path.dirname(__file__), "data", "processed")
    test_df = pd.read_csv(os.path.join(data_dir, "test.csv"))
    pd_df = pd.read_csv(os.path.join(data_dir, "problem_disjoint_test.csv"))
    
    print("Evaluating on Test Split...")
    test_metrics = evaluate_split(model, tokenizer, device, test_df)
    
    print("Evaluating on Problem-Disjoint Split...")
    pd_metrics = evaluate_split(model, tokenizer, device, pd_df)
    
    # Example inference test
    sample_code = "for i in range(1, 10): print(i)"
    inputs = tokenizer("Problem: \n\nCode:\n" + sample_code, return_tensors="pt").to(device)
    with torch.no_grad():
        out = model(**inputs)
    pred_class = int(torch.argmax(out.logits, dim=1).item())
    
    results = {
        "test": test_metrics,
        "problem_disjoint": pd_metrics,
        "sample_inference_class": pred_class
    }
    
    out_path = os.path.join(os.path.dirname(__file__), "CODEBERT_EVAL_RAW.json")
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Done. Saved raw metrics to {out_path}")

if __name__ == "__main__":
    main()
