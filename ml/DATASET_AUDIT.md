# Dataset Audit: `Project_CodeNet-main`

## Dataset Overview
The directory `Project_CodeNet-main` contains the source code, toolchains, and documentation for IBM's **Project CodeNet**. However, it **does not contain the actual dataset payload** (student submissions, metadata, execution results, or misconception labels). The repository is strictly the scaffolding for data preprocessing, parsing, and baseline model experiments.

## Available Data
The following data-related files were identified by exhaustively scanning the folder for `.csv`, `.json`, `.txt`, and archives:

| File | Records | Important fields | Useful for ML? |
| --- | --- | --- | --- |
| `doc/problem_descriptions.tar.gz` | ~4,000 HTML files | Problem statements, constraints, sample inputs/outputs | **Yes**. Essential for providing the LLM/RAG with context on what the student was attempting to solve. |
| `model-experiments/.../split/random/*.csv` (e.g., `train.csv`, `test.csv`) | Varies (e.g., `small/split/random/train.csv` has 1,000) | A single column of numerical indices | **No**. These are just pre-computed train/test split indices for baseline experiments. They do not contain code or labels. |
| `tools/json-graph/*.json` (e.g., `spt-schema.json`) | N/A | JSON schema definitions | **No**. These define the graph structure for parsers, not dataset examples. |
| `tools/tokenizer/std-C-lib-funcs.txt` | 135 | C standard library function names | **No**. Used as a vocabulary reference for the tokenizer. |

*Note: There are absolutely no files containing student source code, verdicts, or misconception labels in this directory.*

### File Details:
**1. Problem Descriptions**
- **Path**: `Project_CodeNet-main/Project_CodeNet-main/doc/problem_descriptions.tar.gz`
- **File Type**: Compressed Archive (`.tar.gz`) containing HTML
- **File Size**: ~3.49 MB
- **Contains Source Code**: No
- **Contains Problem Information**: Yes
- **Contains Correctness/Verdict**: No
- **Contains Misconception Signal**: No

**2. Baseline Data Splits**
- **Path**: `Project_CodeNet-main/Project_CodeNet-main/model-experiments/gnn-based-experiments/data/small/split/random/train.csv` (and others)
- **File Type**: `.csv`
- **Example Record**: `384` (just a row ID)
- **Contains Source Code**: No
- **Contains Problem Information**: No
- **Contains Correctness/Verdict**: No
- **Contains Misconception Signal**: No

## Potential ML Target
From the *existing* files in this repository, **we cannot predict any target**. There are no labels, no source code, and no execution verdicts. We only have the problem descriptions (the prompts the students were given) without any student responses. 

## Missing Information
To perform the intended misconception detection (Student Code → Code/Text Features → ML Model → Misconception Category), the following are strictly required but **currently missing**:
- **Student Code Files**: The raw submission files (`.py`, `.cpp`, `.java`, etc.).
- **Submission Metadata**: CSVs linking submission IDs to problem IDs, verdicts, and languages.
- **Outcome/Error Signals**: Statuses like *Wrong Answer*, *Compile Error*, *Runtime Error*. (Note: As requested, these are outcome signals, not misconception labels).
- **Actual Misconception Labels**: The core of the McMiner dataset (e.g., explicit classifications like `M001-off-by-one-loop-boundary`). 

## Recommendation
**Do not proceed with model training or preprocessing on this directory.** 
The current `Project_CodeNet-main` folder only contains the parsing tools (like the Simplified Parse Tree generator) and problem descriptions. 

**Next Step:** You must retrieve and add the actual McMiner `.csv` / `.json` dataset payload (which contains the mapped student code, problem IDs, and misconception labels) to the workspace before any ML pipeline can be constructed.
