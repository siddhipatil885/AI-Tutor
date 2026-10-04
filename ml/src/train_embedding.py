"""
train_embedding.py -- Experiments 2 & 3: Pretrained embeddings -> classifier

Experiment 2: sentence-transformers/all-MiniLM-L6-v2 (general semantic)
Experiment 3: microsoft/codebert-base (code-specific)

For both, we embed the generated_code field and train an SVM / LogReg on top.
No fine-tuning -- embeddings are used as frozen features. This is justified because
the dataset is small (~850 training examples), and full fine-tuning would risk severe
over-fitting.

Models selected:
    Exp 2 -- all-MiniLM-L6-v2
        source  : sentence-transformers
        params  : 22M
        embedding: mean-pooled sentence embedding, 384-dim
        reason  : fast, strong general-purpose semantic baseline

    Exp 3 -- microsoft/codebert-base
        source  : HuggingFace (microsoft/codebert-base)
        params  : 125M (BERT-base scale)
        embedding: CLS token from RoBERTa + bimodal pretrain on code+NL pairs
        reason  : explicitly pretrained on GitHub Python/Java/Ruby/... code;
                  likely captures syntax-aware representations better than
                  general text models for our programming misconception task.

Run:
    python -m ml.src.train_embedding --exp 2    # MiniLM
    python -m ml.src.train_embedding --exp 3    # CodeBERT
    python -m ml.src.train_embedding            # both
"""
import os, sys, json, random, argparse
import numpy as np
import pandas as pd
from sklearn.svm import SVC
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.pipeline import Pipeline
import joblib

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
from src.evaluate import evaluate  # noqa

SEED = 42
random.seed(SEED)
np.random.seed(SEED)

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.join(_HERE, "..")
DATA_DIR    = os.path.join(_ROOT, "data", "processed")
MODELS_DIR  = os.path.join(_ROOT, "models")
RESULTS_DIR = os.path.join(_ROOT, "experiments", "results")
CONFIGS_DIR = os.path.join(_ROOT, "experiments", "configs")
os.makedirs(MODELS_DIR, exist_ok=True)

# ── Embedding configs ─────────────────────────────────────────────────────────
EXP_CONFIGS = {
    2: {
        "experiment": "exp2_minilm_svm",
        "model_name": "sentence-transformers/all-MiniLM-L6-v2",
        "model_source": "sentence-transformers hub",
        "param_size": "22M",
        "embedding_method": "mean-pooled sentence embedding (384-dim)",
        "computational_requirements": "CPU-friendly; ~1 min on 850 samples",
        "reason_for_selection":
            "Strong general-purpose semantic baseline. Fast inference, "
            "well-calibrated embeddings; serves as upper bound for "
            "non-code-aware representations.",
        "max_code_length": 512,
        "classifier": {
            "name": "SVC",
            "C": 10.0,
            "kernel": "rbf",
            "class_weight": "balanced",
            "probability": True,
        },
        "leakage_excluded": ["reasoning", "global_misconception_index"],
        "random_seed": SEED,
    },
    3: {
        "experiment": "exp3_codebert_svm",
        "model_name": "microsoft/codebert-base",
        "model_source": "HuggingFace (microsoft/codebert-base)",
        "param_size": "125M",
        "embedding_method":
            "CLS token of RoBERTa pretrained jointly on code (Python, Java, Ruby, "
            "Go, PHP, Javascript) and natural language docstrings",
        "computational_requirements":
            "GPU recommended; ~5–10 min on CPU for 850 samples",
        "reason_for_selection":
            "CodeBERT is explicitly pretrained on bimodal (code+NL) data from "
            "GitHub. It captures token-level syntax patterns and semantic meaning "
            "simultaneously. Superior to general LMs for code tasks (CodeBERT "
            "paper, Feng et al. 2020, EMNLP).",
        "max_code_length": 512,
        "classifier": {
            "name": "SVC",
            "C": 10.0,
            "kernel": "rbf",
            "class_weight": "balanced",
            "probability": True,
        },
        "leakage_excluded": ["reasoning", "global_misconception_index"],
        "random_seed": SEED,
    },
}
# ─────────────────────────────────────────────────────────────────────────────


def embed_minilm(texts: list, model_name: str, max_len: int = 512) -> np.ndarray:
    """Embed with sentence-transformers (mean-pool CLS)."""
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(model_name)
    # Truncate to max_len tokens worth of chars (rough proxy)
    truncated = [t[:max_len * 4] for t in texts]
    embeddings = model.encode(truncated, show_progress_bar=True,
                              batch_size=32, normalize_embeddings=True)
    return embeddings


def embed_codebert(texts: list, max_len: int = 512) -> np.ndarray:
    """Embed with CodeBERT -- return CLS-token representation."""
    from transformers import RobertaTokenizer, RobertaModel
    import torch
    tokenizer = RobertaTokenizer.from_pretrained("microsoft/codebert-base")
    model = RobertaModel.from_pretrained("microsoft/codebert-base")
    model.eval()
    device = "cuda" if __import__("torch").cuda.is_available() else "cpu"
    model = model.to(device)

    embeddings = []
    batch_size = 16
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        enc = tokenizer(
            batch,
            padding=True,
            truncation=True,
            max_length=max_len,
            return_tensors="pt",
        ).to(device)
        with torch.no_grad():
            out = model(**enc)
        cls_emb = out.last_hidden_state[:, 0, :].cpu().numpy()
        embeddings.append(cls_emb)
        if (i // batch_size + 1) % 5 == 0:
            print(f"  CodeBERT embedded {i + len(batch)}/{len(texts)}")
    return np.vstack(embeddings)


def run_experiment(exp_id: int):
    cfg = EXP_CONFIGS[exp_id]
    exp_name = cfg["experiment"]
    print(f"\n{'='*60}")
    print(f"  Running {exp_name}")
    print(f"  Model: {cfg['model_name']}")
    print(f"{'='*60}")

    # ── Load data ────────────────────────────────────────────────────────────
    train = pd.read_csv(os.path.join(DATA_DIR, "train.csv"))
    val   = pd.read_csv(os.path.join(DATA_DIR, "validation.csv"))
    test  = pd.read_csv(os.path.join(DATA_DIR, "test.csv"))

    codes_train = train["generated_code"].fillna("").tolist()
    codes_val   = val["generated_code"].fillna("").tolist()
    codes_test  = test["generated_code"].fillna("").tolist()
    y_train = train["global_misconception_index"].values
    y_val   = val["global_misconception_index"].values
    y_test  = test["global_misconception_index"].values

    # ── Embed ────────────────────────────────────────────────────────────────
    emb_cache_train = os.path.join(MODELS_DIR, f"{exp_name}_emb_train.npy")
    emb_cache_val   = os.path.join(MODELS_DIR, f"{exp_name}_emb_val.npy")
    emb_cache_test  = os.path.join(MODELS_DIR, f"{exp_name}_emb_test.npy")

    if os.path.exists(emb_cache_train):
        print("  Loading cached embeddings...")
        Xtr = np.load(emb_cache_train)
        Xva = np.load(emb_cache_val)
        Xte = np.load(emb_cache_test)
    else:
        print("  Embedding training set...")
        if exp_id == 2:
            Xtr = embed_minilm(codes_train, cfg["model_name"], cfg["max_code_length"])
            Xva = embed_minilm(codes_val,   cfg["model_name"], cfg["max_code_length"])
            Xte = embed_minilm(codes_test,  cfg["model_name"], cfg["max_code_length"])
        else:
            Xtr = embed_codebert(codes_train, cfg["max_code_length"])
            Xva = embed_codebert(codes_val,   cfg["max_code_length"])
            Xte = embed_codebert(codes_test,  cfg["max_code_length"])

        np.save(emb_cache_train, Xtr)
        np.save(emb_cache_val,   Xva)
        np.save(emb_cache_test,  Xte)
        print(f"  Embeddings cached at {emb_cache_train}")

    # ── Encode labels ────────────────────────────────────────────────────────
    le = LabelEncoder()
    le.fit(y_train)
    ytr = le.transform(y_train)

    val_mask  = np.isin(y_val,  le.classes_)
    test_mask = np.isin(y_test, le.classes_)
    Xva_f, yva_f = Xva[val_mask],   le.transform(y_val[val_mask])
    Xte_f, yte_f = Xte[test_mask],  le.transform(y_test[test_mask])

    # ── Train SVM ────────────────────────────────────────────────────────────
    ccfg = cfg["classifier"]
    clf = Pipeline([
        ("scaler", StandardScaler()),
        ("svm",    SVC(
            C=ccfg["C"],
            kernel=ccfg["kernel"],
            class_weight=ccfg["class_weight"],
            probability=ccfg["probability"],
            random_state=SEED,
        )),
    ])
    print("  Training SVM classifier...")
    clf.fit(Xtr, ytr)

    # ── Evaluate ─────────────────────────────────────────────────────────────
    classes = list(range(len(le.classes_)))
    evaluate(yva_f, clf.predict(Xva_f), clf.predict_proba(Xva_f),
             classes, f"{exp_name}_val", RESULTS_DIR, extra=cfg)
    evaluate(yte_f, clf.predict(Xte_f), clf.predict_proba(Xte_f),
             classes, f"{exp_name}_test", RESULTS_DIR, extra=cfg)

    # ── Save ─────────────────────────────────────────────────────────────────
    joblib.dump({"clf": clf, "le": le}, os.path.join(MODELS_DIR, f"{exp_name}.pkl"))
    with open(os.path.join(CONFIGS_DIR, f"{exp_name}.json"), "w") as f:
        json.dump(cfg, f, indent=2)

    print(f"  {exp_name} done.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--exp", type=int, choices=[2, 3], default=None,
                        help="Which experiment to run (2=MiniLM, 3=CodeBERT). Omit to run both.")
    args = parser.parse_args()

    if args.exp is None:
        run_experiment(2)
        run_experiment(3)
    else:
        run_experiment(args.exp)
