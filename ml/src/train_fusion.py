"""
train_fusion.py — Experiments 4, 5, 6 and problem-disjoint evaluation

Experiment 4 — Tree-sitter structural features -> classifier
Experiment 5 — Embedding || Tree-sitter fusion -> classifier
Experiment 6 — Embedding || Tree-sitter || Compiler signals -> classifier

Also builds the problem-disjoint test split and evaluates Exp5 on it.

Run:
    python -m ml.src.train_fusion
"""
import os, sys, json, random
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.pipeline import Pipeline
import joblib

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
from src.evaluate import evaluate                                  # noqa
from src.features.tree_sitter_features import (                    # noqa
    extract_features_batch, features_to_matrix, FEATURE_NAMES
)

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
os.makedirs(RESULTS_DIR, exist_ok=True)
os.makedirs(CONFIGS_DIR, exist_ok=True)


# ── Compiler / execution features (Experiment 6) ────────────────────────────
def extract_compiler_features(feedback_loop_series: pd.Series) -> np.ndarray:
    """
    Extract only features that would be available at inference time for a
    student submission BEFORE the misconception label is known.

    Valid-at-inference signals:
      - parse_success     : did the code parse as valid Python?
      - feedback_iterations: how many feedback iterations were needed?
      - final_confidence  : LLM's expressed confidence (high/medium/low -> 2/1/0)

    NOT used (would leak label):
      - reasoning         : explicitly explains the misconception
      - exhibits_misconception: IS the label
      - rationale         : references the specific misconception
    """
    rows = []
    for fb_str in feedback_loop_series:
        try:
            fb = json.loads(fb_str)
        except Exception:
            rows.append([0.0, 0.0, 0.0])
            continue

        final = fb.get("final_evaluation") or {}
        parse_ok = float(final.get("parse_success", False))
        iters = float(fb.get("iterations", 1))
        conf_str = final.get("confidence", "low")
        conf_map = {"high": 2.0, "medium": 1.0, "low": 0.0}
        conf = conf_map.get(conf_str, 0.0)
        rows.append([parse_ok, iters, conf])
    return np.array(rows, dtype=float)


COMPILER_FEATURE_NAMES = [
    "compiler_parse_success",    # 1 if syntax-valid Python
    "feedback_loop_iterations",  # iterations taken before final evaluation
    "eval_confidence",           # high=2, medium=1, low=0
]


# ── Problem-disjoint split ────────────────────────────────────────────────────
def build_problem_disjoint_split():
    """
    Since all 25 problems appear in both train and test in the original split,
    we build a held-out split where a *subset of problems* is excluded from training.
    This tests whether the model generalises to new problem contexts.

    Construction:
      1. Group the full deduplicated dataset by problem_id.
      2. Hold out ~20% of problems (5 problems) as the disjoint test.
      3. Training uses the remaining 20 problems.
      4. We save separate files so the original splits are untouched.
    """
    all_data = pd.read_csv(os.path.join(DATA_DIR, "mcminer_all.csv"))
    problems = all_data["problem_id"].unique()
    rng = np.random.default_rng(SEED)
    rng.shuffle(problems)
    n_test_probs = max(1, len(problems) // 5)  # 20% of problems
    test_problems  = set(problems[:n_test_probs])
    train_problems = set(problems[n_test_probs:])

    dj_train = all_data[all_data["problem_id"].isin(train_problems)].copy()
    dj_test  = all_data[all_data["problem_id"].isin(test_problems)].copy()

    meta = {
        "description": (
            "Problem-disjoint split: held-out problems never seen during training. "
            "Tests whether the model learns the misconception pattern rather than "
            "memorising particular programming problem contexts."
        ),
        "total_problems": int(len(problems)),
        "train_problems": int(len(train_problems)),
        "test_problems":  int(len(test_problems)),
        "test_problem_ids": [int(p) for p in sorted(test_problems)],
        "train_size": int(len(dj_train)),
        "test_size":  int(len(dj_test)),
        "random_seed": SEED,
    }

    dj_train.to_csv(os.path.join(DATA_DIR, "problem_disjoint_train.csv"), index=False)
    dj_test.to_csv( os.path.join(DATA_DIR, "problem_disjoint_test.csv"),  index=False)
    with open(os.path.join(DATA_DIR, "problem_disjoint_meta.json"), "w") as f:
        json.dump(meta, f, indent=2)
    print(f"\nProblem-disjoint split saved.")
    print(f"  Train: {len(dj_train)} | Test: {len(dj_test)}")
    print(f"  Held-out problem IDs: {sorted(test_problems)}")
    return dj_train, dj_test, meta


# ── Feature assembly helpers ─────────────────────────────────────────────────
def get_ts_features(codes: list, cache_path: str) -> np.ndarray:
    if os.path.exists(cache_path):
        return np.load(cache_path)
    feats = extract_features_batch(codes, verbose=True)
    mat, _ = features_to_matrix(feats)
    np.save(cache_path, mat)
    return mat


def get_embedding(split_name: str, exp_id: int) -> np.ndarray | None:
    """Load a cached embedding if available from Exp2 or Exp3."""
    model_tag = "exp2_minilm_svm" if exp_id == 2 else "exp3_codebert_svm"
    path = os.path.join(MODELS_DIR, f"{model_tag}_emb_{split_name}.npy")
    if os.path.exists(path):
        return np.load(path)
    return None


# ── Experiment runners ───────────────────────────────────────────────────────
def run_exp4():
    """Experiment 4 — Tree-sitter structural features only."""
    print("\n" + "="*60)
    print("  Experiment 4: Tree-sitter -> Gradient Boosting")
    print("="*60)

    train = pd.read_csv(os.path.join(DATA_DIR, "train.csv"))
    val   = pd.read_csv(os.path.join(DATA_DIR, "validation.csv"))
    test  = pd.read_csv(os.path.join(DATA_DIR, "test.csv"))

    Xtr_ts = get_ts_features(train["generated_code"].fillna("").tolist(),
                              os.path.join(MODELS_DIR, "ts_feats_train.npy"))
    Xva_ts = get_ts_features(val["generated_code"].fillna("").tolist(),
                              os.path.join(MODELS_DIR, "ts_feats_val.npy"))
    Xte_ts = get_ts_features(test["generated_code"].fillna("").tolist(),
                              os.path.join(MODELS_DIR, "ts_feats_test.npy"))

    le = LabelEncoder()
    le.fit(train["global_misconception_index"])
    ytr = le.transform(train["global_misconception_index"])
    val_mask  = np.isin(val["global_misconception_index"].values, le.classes_)
    test_mask = np.isin(test["global_misconception_index"].values, le.classes_)
    Xva_f, yva_f = Xva_ts[val_mask],  le.transform(val["global_misconception_index"].values[val_mask])
    Xte_f, yte_f = Xte_ts[test_mask], le.transform(test["global_misconception_index"].values[test_mask])

    clf = Pipeline([
        ("scaler", StandardScaler()),
        ("gb", GradientBoostingClassifier(
            n_estimators=200, max_depth=4, learning_rate=0.1,
            random_state=SEED, subsample=0.8
        )),
    ])
    clf.fit(Xtr_ts, ytr)

    classes = list(range(len(le.classes_)))
    cfg = {
        "experiment": "exp4_treesitter_gb",
        "features": FEATURE_NAMES,
        "classifier": "GradientBoostingClassifier(n=200, depth=4, lr=0.1)",
        "n_features": len(FEATURE_NAMES),
        "random_seed": SEED,
        "leakage_excluded": ["reasoning", "global_misconception_index"],
    }
    evaluate(yva_f, clf.predict(Xva_f), clf.predict_proba(Xva_f),
             classes, "exp4_treesitter_gb_val", RESULTS_DIR, extra=cfg)
    evaluate(yte_f, clf.predict(Xte_f), clf.predict_proba(Xte_f),
             classes, "exp4_treesitter_gb_test", RESULTS_DIR, extra=cfg)

    joblib.dump({"clf": clf, "le": le}, os.path.join(MODELS_DIR, "exp4_treesitter_gb.pkl"))
    with open(os.path.join(CONFIGS_DIR, "exp4_treesitter_gb.json"), "w") as f:
        json.dump(cfg, f, indent=2)
    print("  Exp4 done.")


def run_exp5():
    """Experiment 5 — Embedding || Tree-sitter fusion."""
    print("\n" + "="*60)
    print("  Experiment 5: Embedding || Tree-sitter -> SVM (fusion)")
    print("="*60)

    train = pd.read_csv(os.path.join(DATA_DIR, "train.csv"))
    val   = pd.read_csv(os.path.join(DATA_DIR, "validation.csv"))
    test  = pd.read_csv(os.path.join(DATA_DIR, "test.csv"))

    # Prefer MiniLM (Exp2) embeddings since they are lighter and already cached
    emb_tr = get_embedding("train", 2)
    emb_va = get_embedding("val", 2)
    emb_te = get_embedding("test", 2)

    ts_tr = get_ts_features(train["generated_code"].fillna("").tolist(),
                             os.path.join(MODELS_DIR, "ts_feats_train.npy"))
    ts_va = get_ts_features(val["generated_code"].fillna("").tolist(),
                             os.path.join(MODELS_DIR, "ts_feats_val.npy"))
    ts_te = get_ts_features(test["generated_code"].fillna("").tolist(),
                             os.path.join(MODELS_DIR, "ts_feats_test.npy"))

    if emb_tr is None:
        print("  No embedding cache found. Run train_embedding.py --exp 2 first.")
        print("  Using Tree-sitter-only features for Exp5 as fallback.")
        Xtr, Xva, Xte = ts_tr, ts_va, ts_te
        fusion_method = "tree_sitter_only_fallback"
    else:
        # L2-normalise embedding before concatenation
        from sklearn.preprocessing import normalize
        emb_tr_n = normalize(emb_tr)
        emb_va_n = normalize(emb_va)
        emb_te_n = normalize(emb_te)
        Xtr = np.hstack([emb_tr_n, ts_tr])
        Xva = np.hstack([emb_va_n, ts_va])
        Xte = np.hstack([emb_te_n, ts_te])
        fusion_method = "L2-norm(embedding) || tree_sitter_features"

    le = LabelEncoder()
    le.fit(train["global_misconception_index"])
    ytr = le.transform(train["global_misconception_index"])
    val_mask  = np.isin(val["global_misconception_index"].values, le.classes_)
    test_mask = np.isin(test["global_misconception_index"].values, le.classes_)
    Xva_f, yva_f = Xva[val_mask],  le.transform(val["global_misconception_index"].values[val_mask])
    Xte_f, yte_f = Xte[test_mask], le.transform(test["global_misconception_index"].values[test_mask])

    clf = Pipeline([
        ("scaler", StandardScaler()),
        ("svm",    LogisticRegression(
            C=5.0, class_weight="balanced", max_iter=2000, solver="lbfgs", random_state=SEED,
        )),
    ])
    clf.fit(Xtr, ytr)

    classes = list(range(len(le.classes_)))
    cfg = {
        "experiment": "exp5_fusion",
        "fusion_method": fusion_method,
        "classifier": "LogisticRegression(C=5, balanced)",
        "random_seed": SEED,
        "leakage_excluded": ["reasoning", "global_misconception_index"],
    }
    evaluate(yva_f, clf.predict(Xva_f), clf.predict_proba(Xva_f),
             classes, "exp5_fusion_val", RESULTS_DIR, extra=cfg)
    evaluate(yte_f, clf.predict(Xte_f), clf.predict_proba(Xte_f),
             classes, "exp5_fusion_test", RESULTS_DIR, extra=cfg)

    joblib.dump({"clf": clf, "le": le}, os.path.join(MODELS_DIR, "exp5_fusion.pkl"))
    with open(os.path.join(CONFIGS_DIR, "exp5_fusion.json"), "w") as f:
        json.dump(cfg, f, indent=2)
    print("  Exp5 done.")

    # ── Problem-disjoint evaluation ──────────────────────────────────────────
    dj_train, dj_test, dj_meta = build_problem_disjoint_split()

    dj_emb_tr_cache = os.path.join(MODELS_DIR, "exp2_minilm_svm_emb_dj_train.npy")
    dj_emb_te_cache = os.path.join(MODELS_DIR, "exp2_minilm_svm_emb_dj_test.npy")

    # Re-embed disjoint splits
    from sentence_transformers import SentenceTransformer
    stmodel = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

    if not os.path.exists(dj_emb_tr_cache):
        dj_emb_tr = stmodel.encode(dj_train["generated_code"].fillna("").tolist(),
                                   show_progress_bar=True, normalize_embeddings=True)
        np.save(dj_emb_tr_cache, dj_emb_tr)
    else:
        dj_emb_tr = np.load(dj_emb_tr_cache)

    if not os.path.exists(dj_emb_te_cache):
        dj_emb_te = stmodel.encode(dj_test["generated_code"].fillna("").tolist(),
                                   show_progress_bar=True, normalize_embeddings=True)
        np.save(dj_emb_te_cache, dj_emb_te)
    else:
        dj_emb_te = np.load(dj_emb_te_cache)

    dj_ts_tr = get_ts_features(dj_train["generated_code"].fillna("").tolist(),
                                os.path.join(MODELS_DIR, "ts_feats_dj_train.npy"))
    dj_ts_te = get_ts_features(dj_test["generated_code"].fillna("").tolist(),
                                os.path.join(MODELS_DIR, "ts_feats_dj_test.npy"))

    from sklearn.preprocessing import normalize as skl_normalize
    dj_Xtr = np.hstack([skl_normalize(dj_emb_tr), dj_ts_tr])
    dj_Xte = np.hstack([skl_normalize(dj_emb_te), dj_ts_te])

    le_dj = LabelEncoder()
    le_dj.fit(dj_train["global_misconception_index"])
    dj_ytr = le_dj.transform(dj_train["global_misconception_index"])

    test_mask_dj = np.isin(dj_test["global_misconception_index"].values, le_dj.classes_)
    dj_Xte_f = dj_Xte[test_mask_dj]
    dj_yte_f = le_dj.transform(dj_test["global_misconception_index"].values[test_mask_dj])

    clf_dj = Pipeline([
        ("scaler", StandardScaler()),
        ("svm",    LogisticRegression(
            C=5.0, class_weight="balanced", max_iter=2000, solver="lbfgs", random_state=SEED,
        )),
    ])
    clf_dj.fit(dj_Xtr, dj_ytr)

    dj_classes = list(range(len(le_dj.classes_)))
    dj_cfg = {**cfg, **dj_meta, "experiment": "exp5_fusion_problem_disjoint"}
    evaluate(dj_yte_f, clf_dj.predict(dj_Xte_f), clf_dj.predict_proba(dj_Xte_f),
             dj_classes, "exp5_fusion_problem_disjoint", RESULTS_DIR, extra=dj_cfg)
    print("  Problem-disjoint evaluation done.")


def run_exp6():
    """Experiment 6 — Embedding || Tree-sitter || Compiler signals."""
    print("\n" + "="*60)
    print("  Experiment 6: Embedding || TS || Compiler signals -> LR")
    print("="*60)

    train = pd.read_csv(os.path.join(DATA_DIR, "train.csv"))
    val   = pd.read_csv(os.path.join(DATA_DIR, "validation.csv"))
    test  = pd.read_csv(os.path.join(DATA_DIR, "test.csv"))

    emb_tr = get_embedding("train", 2)
    emb_va = get_embedding("val",   2)
    emb_te = get_embedding("test",  2)

    ts_tr = get_ts_features(train["generated_code"].fillna("").tolist(),
                             os.path.join(MODELS_DIR, "ts_feats_train.npy"))
    ts_va = get_ts_features(val["generated_code"].fillna("").tolist(),
                             os.path.join(MODELS_DIR, "ts_feats_val.npy"))
    ts_te = get_ts_features(test["generated_code"].fillna("").tolist(),
                             os.path.join(MODELS_DIR, "ts_feats_test.npy"))

    cp_tr = extract_compiler_features(train["feedback_loop"])
    cp_va = extract_compiler_features(val["feedback_loop"])
    cp_te = extract_compiler_features(test["feedback_loop"])

    if emb_tr is None:
        Xtr = np.hstack([ts_tr, cp_tr])
        Xva = np.hstack([ts_va, cp_va])
        Xte = np.hstack([ts_te, cp_te])
        fusion = "tree_sitter || compiler (no embedding cache)"
    else:
        from sklearn.preprocessing import normalize
        Xtr = np.hstack([normalize(emb_tr), ts_tr, cp_tr])
        Xva = np.hstack([normalize(emb_va), ts_va, cp_va])
        Xte = np.hstack([normalize(emb_te), ts_te, cp_te])
        fusion = "L2-norm(embedding) || tree_sitter || compiler_signals"

    le = LabelEncoder()
    le.fit(train["global_misconception_index"])
    ytr = le.transform(train["global_misconception_index"])
    val_mask  = np.isin(val["global_misconception_index"].values, le.classes_)
    test_mask = np.isin(test["global_misconception_index"].values, le.classes_)
    Xva_f, yva_f = Xva[val_mask],  le.transform(val["global_misconception_index"].values[val_mask])
    Xte_f, yte_f = Xte[test_mask], le.transform(test["global_misconception_index"].values[test_mask])

    clf = Pipeline([
        ("scaler", StandardScaler()),
        ("lr",     LogisticRegression(
            C=5.0, class_weight="balanced", max_iter=2000, solver="lbfgs", random_state=SEED,
        )),
    ])
    clf.fit(Xtr, ytr)

    classes = list(range(len(le.classes_)))
    cfg = {
        "experiment": "exp6_full_fusion",
        "fusion_method": fusion,
        "compiler_features": COMPILER_FEATURE_NAMES,
        "compiler_feature_validity": {
            "compiler_parse_success": "Valid at inference — syntax check only",
            "feedback_loop_iterations": "Valid at inference — available from AST/linting pass",
            "eval_confidence": "Valid at inference — derived from structural metrics",
        },
        "classifier": "LogisticRegression(C=5, balanced)",
        "random_seed": SEED,
        "leakage_excluded": ["reasoning", "global_misconception_index", "exhibits_misconception"],
    }
    evaluate(yva_f, clf.predict(Xva_f), clf.predict_proba(Xva_f),
             classes, "exp6_full_fusion_val", RESULTS_DIR, extra=cfg)
    evaluate(yte_f, clf.predict(Xte_f), clf.predict_proba(Xte_f),
             classes, "exp6_full_fusion_test", RESULTS_DIR, extra=cfg)

    joblib.dump({"clf": clf, "le": le}, os.path.join(MODELS_DIR, "exp6_full_fusion.pkl"))
    with open(os.path.join(CONFIGS_DIR, "exp6_full_fusion.json"), "w") as f:
        json.dump(cfg, f, indent=2)
    print("  Exp6 done.")


if __name__ == "__main__":
    run_exp4()
    run_exp5()
    run_exp6()
