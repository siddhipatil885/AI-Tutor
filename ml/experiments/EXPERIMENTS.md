# Re:Learn Misconception Detection — Experiment Tracking

## Dataset
- **Source**: McMiner benchmark (`ml/data/raw/mcminer/`)
- **Total usable examples**: 1,050 (after deduplication)
- **Classes**: 67 misconception categories
- **Train / Val / Test**: 854 / 98 / 98
- **Random seed**: 42

## Leakage Rules (enforced in ALL experiments)
- `reasoning` is EXCLUDED from all features (leaks the target label)
- `global_misconception_index` is the target only, never an input
- `exhibits_misconception` tag is excluded (IS the label)
- Test set was never used for tuning

---

## Results Table

| Experiment | Representation | Classifier | Macro F1 | Weighted F1 | Top-1 Acc | Top-3 Acc |
|---|---|---|---:|---:|---:|---:|
| Exp1 (val)  | TF-IDF char 2-5grams | LogReg (balanced) | 0.1737 | 0.2109 | 0.2143 | 0.3367 |
| Exp1 (test) | TF-IDF char 2-5grams | LogReg (balanced) | 0.1290 | 0.1344 | 0.1429 | 0.2245 |
| Exp2 (val)  | MiniLM-L6-v2 (384d) | SVM RBF (balanced) | 0.0459 | 0.0602 | 0.0510 | 0.1531 |
| Exp2 (test) | MiniLM-L6-v2 (384d) | SVM RBF (balanced) | 0.0191 | 0.0187 | 0.0204 | 0.1531 |
| Exp3 (val)  | CodeBERT-base CLS (768d) | SVM RBF (balanced) | — | — | — | — |
| Exp3 (test) | CodeBERT-base CLS (768d) | SVM RBF (balanced) | — | — | — | — |
| Exp4 (val)  | Tree-sitter AST (55 feats) | GradBoost (200 est) | 0.0304 | 0.0354 | 0.0306 | 0.0306 |
| Exp4 (test) | Tree-sitter AST (55 feats) | GradBoost (200 est) | 0.0268 | 0.0255 | 0.0204 | 0.0204 |
| Exp5 (val)  | MiniLM emb \|\| TS features | LogReg (balanced) | 0.2759 | 0.3288 | 0.3367 | 0.5918 |
| Exp5 (test) | MiniLM emb \|\| TS features | LogReg (balanced) | 0.2340 | 0.2739 | 0.2959 | 0.5000 |
| Exp5-PD     | MiniLM emb \|\| TS (problem-disjoint) | LogReg | 0.1714 | 0.1714 | 0.1493 | 0.2836 |
| Exp6 (val)  | MiniLM \|\| TS \|\| Compiler | LogReg (balanced) | 0.2701 | 0.3226 | 0.3265 | 0.5408 |
| Exp6 (test) | MiniLM \|\| TS \|\| Compiler | LogReg (balanced) | 0.2199 | 0.2560 | 0.2755 | 0.5000 |

*— = results pending. Run `python -m src.train_embedding` and `python -m src.train_fusion`.*

---

## Experiment Descriptions

### Exp1 — TF-IDF + Logistic Regression (Baseline)
- **Representation**: Character n-gram TF-IDF (2-5 gram, 20k features)
- **Rationale**: Char n-grams capture code token patterns without tokenization.
- **Class handling**: `class_weight='balanced'`

### Exp2 — MiniLM-L6-v2 Embeddings + SVM
- **Model**: `sentence-transformers/all-MiniLM-L6-v2` (22M params, 384-dim)
- **Rationale**: General semantic baseline; fast and strong on downstream tasks.
- **Embeddings are frozen** (no fine-tuning due to small dataset).

### Exp3 — CodeBERT Embeddings + SVM
- **Model**: `microsoft/codebert-base` (125M params, 768-dim CLS token)
- **Rationale**: Explicitly pretrained on code+NL bimodal data from GitHub (Feng et al., EMNLP 2020).
- **Embeddings are frozen**.

### Exp4 — Tree-sitter Structural Features + Gradient Boosting
- **Features**: 55 AST-derived structural features (see `tree_sitter_features.py`)
- **Rationale**: Tests whether syntactic structure alone discriminates misconceptions.
- **Finding**: Structural features alone are insufficient — misconceptions are semantically similar code with subtle structural differences. Confirms the need for semantic representations.

### Exp5 — Feature Fusion (Embedding || Tree-sitter)
- **Fusion**: L2-normalised MiniLM embeddings concatenated with Tree-sitter features.
- **Rationale**: Tests whether structural information adds predictive value on top of semantic embeddings.

### Exp5-PD — Problem-Disjoint Evaluation
- **Purpose**: Tests generalisation to unseen programming problem contexts.
- **Construction**: Held out 5/25 problems; remaining 20 used for training.
- **Key question**: Does the model learn the misconception pattern or memorise the problem context?

### Exp6 — Full Fusion (Embedding || TS || Compiler Signals)
- **Additional features**: `parse_success`, `feedback_loop_iterations`, `eval_confidence`
- **All features are valid at inference time** (available before label is known).

---

## Model Selection Criteria
The final model will be selected on:
1. **Macro F1** (primary — accounts for imbalance fairly)
2. **Problem-disjoint generalisation** (tests real-world robustness)
3. **Per-class F1** (identifies systematic weaknesses)
4. **Confidence calibration** (required for Re:Learn's confidence output)
5. **Computational cost** (must support real-time FastAPI inference)
6. **Interpretability** (fusion models allow evidence attribution)

---

## Key Findings
- TF-IDF baseline (Exp1): Val Macro F1 = 0.17, test drops to 0.13 — moderate generalisation gap expected for bag-of-chars approach.
- Tree-sitter alone (Exp4): Val Macro F1 = 0.03 — structural features alone are insufficient; this validates that semantic embeddings are critical.
- All details saved to `ml/experiments/results/*.json`.
