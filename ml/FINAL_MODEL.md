# Final Model Decision

## Model Selection
Based on extensive experimentation and rigorous evaluation on problem-disjoint data splits, we have finalized our machine learning integration using the **Feature-Fusion Model (exp5_fusion)**.

- **Architecture:** `MiniLM embeddings` concatenated with `Tree-sitter structural features`, classified using Gradient Boosting (or SVM/Logistic depending on final tuning).
- **Dataset:** McMiner
- **Dataset Size:** 1,063 examples
- **Target Classes:** 67 misconception classes

## Performance Metrics

| Metric | Score |
| --- | --- |
| Test Macro F1 | 0.2340 |
| Weighted F1 | 0.2739 |
| Top-1 Accuracy | 0.2959 |
| Top-3 Accuracy | 0.5000 |
| Problem-Disjoint Macro F1 | 0.1714 |

## Why CodeBERT was NOT Selected
We ran a dedicated evaluation for the `CodeBERT` base model. While it demonstrated stronger raw predictive capabilities (Top-1 of 0.3061 and Top-3 of 0.5204) and marginally better generalization to unseen problems, it ultimately suffered in key operational metrics:

- **Macro F1:** 0.2111 (CodeBERT) vs 0.2340 (Feature-Fusion)
- **Weighted F1:** 0.2278 (CodeBERT) vs 0.2739 (Feature-Fusion)

CodeBERT underperformed on F1 because it succumbed heavily to class imbalance. Without explicit class balancing weights applied during its fine-tuning process, it achieved high accuracy by prioritizing the most frequent misconceptions and completely dropping (starving) the long-tail minority classes. The Feature-Fusion model maintained a better balance across all classes.

## Known Limitations
- **Severe Class Imbalance:** The training set features a heavily skewed long-tail distribution. Many of the 67 misconception classes have fewer than 5 examples.
- **Sparse Classes:** Because of the rarity of certain buggy patterns in the source data, the model's confidence on minority classes is structurally low.
- **Role of the Model:** The ML component must be treated as a **diagnosis assistant**, not a guaranteed ground-truth oracle. Its purpose is to augment the rule-based safety nets and provide helpful heuristics for the learner, rather than acting as a rigid gatekeeper.
