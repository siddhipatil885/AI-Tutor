"""
train_baseline.py — Experiment 1: TF-IDF → Logistic Regression

This is the simplest possible text-based baseline for misconception classification.
It treats source code as a bag-of-tokens and uses logistic regression with class weights
to handle class imbalance.

Run:
    python -m ml.src.train_baseline
"""
import os, sys, json, random
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import LabelEncoder
import joblib

# Project root on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
from src.evaluate import evaluate  # noqa: E402

SEED = 42
random.seed(SEED)
np.random.seed(SEED)

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.join(_HERE, "..")  # ml/
DATA_DIR    = os.path.join(_ROOT, "data", "processed")
MODELS_DIR  = os.path.join(_ROOT, "models")
RESULTS_DIR = os.path.join(_ROOT, "experiments", "results")
CONFIGS_DIR = os.path.join(_ROOT, "experiments", "configs")

os.makedirs(MODELS_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)
os.makedirs(CONFIGS_DIR, exist_ok=True)

# ── Config ────────────────────────────────────────────────────────────────────
CONFIG = {
    "experiment": "exp1_tfidf_logreg",
    "random_seed": SEED,
    "tfidf": {
        "analyzer": "char_wb",   # character n-grams capture code tokens better
        "ngram_range": [2, 5],
        "max_features": 20000,
        "sublinear_tf": True,
    },
    "classifier": {
        "name": "LogisticRegression",
        "C": 1.0,
        "class_weight": "balanced",
        "max_iter": 2000,
        "solver": "lbfgs",
    },
    "features_used": ["generated_code"],
    "leakage_excluded": ["reasoning", "global_misconception_index"],
}
# ─────────────────────────────────────────────────────────────────────────────


def main():
    # ── Load data ────────────────────────────────────────────────────────────
    train = pd.read_csv(os.path.join(DATA_DIR, "train.csv"))
    val   = pd.read_csv(os.path.join(DATA_DIR, "validation.csv"))
    test  = pd.read_csv(os.path.join(DATA_DIR, "test.csv"))

    X_train, y_train = train["generated_code"].fillna(""), train["global_misconception_index"]
    X_val,   y_val   = val["generated_code"].fillna(""),   val["global_misconception_index"]
    X_test,  y_test  = test["generated_code"].fillna(""),  test["global_misconception_index"]

    # ── Encode labels ────────────────────────────────────────────────────────
    le = LabelEncoder()
    le.fit(y_train)
    ytr = le.transform(y_train)
    yva = le.transform([y for y in y_val   if y in le.classes_])
    yte = le.transform([y for y in y_test  if y in le.classes_])
    # Keep only rows whose label is known in training
    val_mask  = y_val.isin(le.classes_)
    test_mask = y_test.isin(le.classes_)
    X_val, y_val_enc   = X_val[val_mask],  le.transform(y_val[val_mask])
    X_test, y_test_enc = X_test[test_mask], le.transform(y_test[test_mask])

    # ── Vectorise ────────────────────────────────────────────────────────────
    cfg = CONFIG["tfidf"]
    tfidf = TfidfVectorizer(
        analyzer=cfg["analyzer"],
        ngram_range=tuple(cfg["ngram_range"]),
        max_features=cfg["max_features"],
        sublinear_tf=cfg["sublinear_tf"],
    )
    Xtr = tfidf.fit_transform(X_train)
    Xva = tfidf.transform(X_val)
    Xte = tfidf.transform(X_test)

    # ── Train ────────────────────────────────────────────────────────────────
    ccfg = CONFIG["classifier"]
    clf = LogisticRegression(
        C=ccfg["C"],
        class_weight=ccfg["class_weight"],
        max_iter=ccfg["max_iter"],
        solver=ccfg["solver"],
        random_state=SEED,
    )
    clf.fit(Xtr, ytr)

    # ── Evaluate on validation ───────────────────────────────────────────────
    yva_pred  = clf.predict(Xva)
    yva_proba = clf.predict_proba(Xva)
    val_results = evaluate(
        y_val_enc, yva_pred, yva_proba,
        classes=list(range(len(le.classes_))),
        experiment_name="exp1_tfidf_logreg_val",
        results_dir=RESULTS_DIR,
        extra=CONFIG,
    )

    # ── Evaluate on test ─────────────────────────────────────────────────────
    yte_pred  = clf.predict(Xte)
    yte_proba = clf.predict_proba(Xte)
    test_results = evaluate(
        y_test_enc, yte_pred, yte_proba,
        classes=list(range(len(le.classes_))),
        experiment_name="exp1_tfidf_logreg_test",
        results_dir=RESULTS_DIR,
        extra=CONFIG,
    )

    # ── Save model + artefacts ───────────────────────────────────────────────
    joblib.dump({"tfidf": tfidf, "clf": clf, "le": le},
                os.path.join(MODELS_DIR, "exp1_tfidf_logreg.pkl"))
    with open(os.path.join(CONFIGS_DIR, "exp1_tfidf_logreg.json"), "w") as f:
        json.dump(CONFIG, f, indent=2)

    print("Exp1 done. Model saved.")
    return val_results, test_results


if __name__ == "__main__":
    main()
