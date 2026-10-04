# McMiner Dataset Exploration

## Overview
This directory is intended for the machine learning component of the Re:Learn AI-Tutor system, specifically focusing on misconception detection using the McMiner dataset.

## Dataset Location and Source
The user indicated that the McMiner dataset was added to the repository. Upon inspection, the provided folder is located at:
`../Project_CodeNet-main`

However, this folder corresponds to the GitHub repository for **IBM's Project CodeNet** (which McMiner is built upon), rather than the McMiner misconception dataset itself. 

## Dataset Format & Available Fields
- **Actual Content:** The added folder contains the source code, tools, and documentation for Project CodeNet (e.g., `tools/`, `model-experiments/`, `notebooks/`, `README.md`). 
- **Missing Data:** The actual dataset files (`data/` containing raw source files and `metadata/` containing `.csv` tables with submissions and problem descriptions) are **not present** in the directory. The only data files found are a few experimental `.csv` splits containing indices under `model-experiments/gnn-based-experiments/data/`, but they lack code or metadata.
- **Fields/Columns & Misconception Taxonomy:** N/A (the raw `.csv` or `.json` metadata tables containing the misconception labels and source code are missing).
- **Programming Languages:** Project CodeNet technically supports 50+ languages (with C++, C, Java, Python being dominant), but no source code examples are physically present in the added folder.

## Dataset Quality and Known Limitations
- **Usable Examples:** 0. 
- **Class Distribution & Missing Values:** Cannot be computed as the dataset payload is missing.
- **Limitations for Re:Learn:** The current directory only contains the repository's scaffolding and tooling scripts. The actual data payload (which is normally ~7.8GB for Project CodeNet, or a separate download for McMiner) is not included. 

## Recommendation
**Do NOT use this folder as-is for training.** It is highly recommended to:
1. Verify the source of the McMiner dataset. The dataset itself needs to be downloaded (typically as a `.zip`, `.tar.gz`, or a set of `.csv`/JSON files containing the actual labeled student code and misconceptions).
2. Once the actual data payload is acquired, place it strictly inside `ml/data/raw/` to preserve data integrity and prevent repository clutter.
3. Use the tools provided in `Project_CodeNet-main` (like the tokenizer or SPT generator) if necessary during preprocessing, but they cannot replace the raw data itself.
