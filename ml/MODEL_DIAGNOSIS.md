c# Model Diagnosis Report

This report presents a deep diagnosis of our current best-performing model (Experiment 5: MiniLM embeddings + Tree-sitter AST features → Logistic Regression), which achieved a validation Macro F1 of 0.2759 and test Macro F1 of 0.2340. The detailed diagnostic outputs can be found in `ml/notebooks/05_model_diagnosis.ipynb`.

## 1. Which misconceptions does the model recognize well?
The model performs reasonably well on misconceptions that are characterized by highly distinct lexical markers or structural signatures. Classes with higher F1 scores generally have sufficient support in the training set (usually >15 examples). However, overall F1 remains low due to extreme class imbalance and semantic subtlety in many categories. 

*(Detailed per-class F1 metrics are saved in `per_class_metrics.csv`)*

## 2. Which does it fail to recognize?
The model fails drastically on the "long tail" of misconceptions. Specifically, there are several classes with 0.0 Precision and Recall. Example failures include:
- Misconception 1: "Student believes that range(n) produces values from 1 to n inclusive." (Top-3 Recall is 50%, but Top-1 is 0%).
- Misconception 2: "Student believes that `range(n - 1)` produces values from 1..."
- Misconception 16: "Student believes that the `=` operator is used for equality." (Top-3 recall is 100%, but exact prediction is often missed).

These failures share common themes:
- **Data Scarcity**: They suffer from critically low support (often only 1 or 2 examples in the test set).
- **Subtle syntax differences**: The difference between `==` and `=` or `range(n)` and `range(n-1)` is extremely small in terms of MiniLM embedding distance.

## 3. Which misconception pairs are confused?
The model struggles to differentiate between conceptually adjacent errors. Top confused pairs include:
- **15 vs 32**: List indexing starts at 1 (15) vs `return` conditionally exits (32).
- **5 vs 11**: Function return values are automatically printed (5) vs A `print` statement must be used to return values (11). *These are highly semantically similar in text and code.*
- **16 vs 22**: `=` used for equality (16) vs Functions called using square brackets (22). 
- **1 vs 15**: `range(n)` starts at 1 (1) vs List indexing starts at 1 (15). *Both revolve around the concept of "starting at 1 instead of 0".*

## 4. How much does sparse data affect performance?
Sparse data is severely impacting the model.
- **Classes with <10 examples**: 13 misconception classes
- **Classes with <5 examples**: 2 misconception classes
The model struggles immensely to learn robust decision boundaries for classes with fewer than 10 examples. The macro F1 metric is dragged down heavily by these minority classes.

## 5. How much does problem memorization affect performance?
Problem-disjoint evaluation (Exp5-PD) reveals that **Problem Memorization is a significant factor**.
- **Normal Test Macro F1**: 0.2340
- **Problem-Disjoint Test Macro F1**: 0.1714
The substantial drop indicates that the model is partially relying on problem-specific context (e.g., specific variable names or problem constraints) rather than purely extracting the abstract misconception logic. When tested on entirely unseen problem contexts, performance degrades, though it doesn't drop to zero.

## 6. Is the current representation the likely bottleneck?
Yes. The current representation bottleneck has two facets:
1. **Semantic Granularity**: MiniLM (frozen) is a general-purpose sentence transformer. It treats code as natural language and fails to distinguish critical single-token differences (like `=` vs `==` or `range(n)` vs `range(n-1)`), which are often the entire basis of a misconception.
2. **Context Ignorance**: The model only looks at the corrupted code. It does not know *what the student was trying to solve*. Without the `problem_description` or a known "correct" reference code, detecting subtle logic errors is incredibly difficult, even for human experts.

## 7. What are the 3 highest-value improvements to test next?
Based on this diagnosis, the most promising next steps are:

1. **Context-Aware Modeling (Target + Problem Context)**: We must provide the model with the problem description or the correct reference code. Misconceptions are defined by the *gap* between intention and implementation.
2. **Specialized Code LLM / Fine-Tuning**: Replace frozen MiniLM embeddings with representations from a fine-tuned Code LLM (e.g., CodeBERT or Llama-3-Code) that understands abstract syntax inherently, or try zero/few-shot classification with an LLM. 
3. **Data Augmentation for the Long Tail**: We have 13 classes with <10 examples. We should synthesize or oversample robust variations of these minority classes to help the classifier establish firm decision boundaries.
