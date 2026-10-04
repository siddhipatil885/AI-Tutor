import json
import os
import numpy as np
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    confusion_matrix,
    classification_report,
)


def top_k_accuracy(y_true: np.ndarray, proba: np.ndarray, k: int = 3) -> float:
    """Compute top-k accuracy given predicted probability matrix."""
    top_k = np.argsort(proba, axis=1)[:, -k:]
    correct = sum(1 for yt, topk in zip(y_true, top_k) if yt in topk)
    return correct / len(y_true)


def evaluate(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    proba: np.ndarray,
    classes: list,
    experiment_name: str,
    results_dir: str = "ml/experiments/results",
    extra: dict = None,
) -> dict:
    """
    Compute the full evaluation suite and save results.

    Parameters
    ----------
    y_true  : integer labels (ground truth)
    y_pred  : integer labels (predicted)
    proba   : float array (N, C) — predicted class probabilities
    classes : list of class integers in the same order as proba columns
    experiment_name : str  — used as filename prefix
    results_dir     : str  — directory to write JSON files
    extra           : dict — any extra metadata to store (hyperparams, etc.)

    Returns
    -------
    dict of all computed metrics
    """
    os.makedirs(results_dir, exist_ok=True)

    acc = accuracy_score(y_true, y_pred)
    macro_f1 = f1_score(y_true, y_pred, average="macro", zero_division=0)
    weighted_f1 = f1_score(y_true, y_pred, average="weighted", zero_division=0)
    macro_prec = precision_score(y_true, y_pred, average="macro", zero_division=0)
    macro_rec = recall_score(y_true, y_pred, average="macro", zero_division=0)
    top3 = top_k_accuracy(y_true, proba, k=3)

    per_class_report = classification_report(
        y_true, y_pred, labels=classes, output_dict=True, zero_division=0
    )
    # Convert per-class f1 to {class_id: f1}
    per_class_f1 = {
        str(cls): per_class_report.get(str(cls), {}).get("f1-score", 0.0)
        for cls in classes
    }

    cm = confusion_matrix(y_true, y_pred, labels=classes).tolist()

    results = {
        "experiment": experiment_name,
        "n_samples": int(len(y_true)),
        "n_classes": int(len(classes)),
        "accuracy": float(acc),
        "macro_f1": float(macro_f1),
        "weighted_f1": float(weighted_f1),
        "macro_precision": float(macro_prec),
        "macro_recall": float(macro_rec),
        "top3_accuracy": float(top3),
        "per_class_f1": per_class_f1,
        "confusion_matrix": cm,
        "class_order": [int(c) for c in classes],
    }
    if extra:
        results["config"] = extra

    out_path = os.path.join(results_dir, f"{experiment_name}.json")
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n{'='*60}")
    print(f"  {experiment_name}")
    print(f"{'='*60}")
    print(f"  Accuracy       : {acc:.4f}")
    print(f"  Macro F1       : {macro_f1:.4f}")
    print(f"  Weighted F1    : {weighted_f1:.4f}")
    print(f"  Macro Precision: {macro_prec:.4f}")
    print(f"  Macro Recall   : {macro_rec:.4f}")
    print(f"  Top-3 Accuracy : {top3:.4f}")
    print(f"  Saved -> {out_path}")
    print(f"{'='*60}\n")

    return results


def load_results(results_dir: str = "ml/experiments/results") -> dict:
    """Load all experiment result JSONs from the results directory."""
    all_results = {}
    for fn in os.listdir(results_dir):
        if fn.endswith(".json"):
            name = fn.replace(".json", "")
            with open(os.path.join(results_dir, fn)) as f:
                all_results[name] = json.load(f)
    return all_results
