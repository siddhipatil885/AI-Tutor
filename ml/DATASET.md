# McMiner Misconception Benchmark

## 1. Official Source
- **Repository**: [https://github.com/taisazero/mcminer](https://github.com/taisazero/mcminer)
- **Local Path**: `ml/data/raw/mcminer/`

## 2. Exact Dataset Files Used
The primary files used for supervised misconception classification are:
- `dataset/misconception_bank.json`: Contains the definitions of all misconception classes.
- `dataset/problems_processed.json`: Contains the metadata for programming problems.
- `dataset/corrupted_codes_best/*.json`: Contains the generated source-code examples linked to specific problem and misconception pairs.
- `dataset/corrupted_codes_best/filtering_report.json`: Contains statistics on the filtered subsets.

*Note: The old IBM Project CodeNet files are preserved in `ml/data/raw/project_codenet/` but are NOT used as the primary ML dataset.*

## 3. Dataset Size & Schema
- **Number of Examples**: 1,063 valid misconception-exhibiting code samples (post-filtering from 1,177 total samples, as per `filtering_report.json`).
- **Number of Misconception Classes**: 67 unique categories.
- **Programming Language**: The dataset primarily targets C++ and Python (based on standard McMiner generation practices), though exact language strings are implicitly tied to the problem domains.

### Schema of a Code Example
Each code example (found inside the `solutions` array of a JSON file) contains:
- `generated_code` (String): The actual source code containing the misconception.
- `problem_misconception_index` (Integer): Maps to the specific problem-misconception pair.
- `global_misconception_index` (Integer): The global label (1 to 67) for the misconception.
- `reasoning` (String): LLM reasoning for generating the misconception.
- `feedback_loop` (Object): Contains execution/compiler feedback (e.g. `is_compilable`).
- `parse_success` (Boolean): Indicates whether the syntax tree was successfully parsed.

## 4. Class Distribution & Limitations
- **Class Imbalance**: There is visible class imbalance. Some misconceptions (e.g., categories 11, 12, 17, 19) have up to 25 filtered examples, while others (e.g., categories 8, 9, 7) have fewer than 10.
- **Train/Test Split**: There is no explicit predefined train/test split field inside the JSONs; a custom split must be created (e.g., stratified split by misconception ID).
- **Missing Values**: Code generation metadata is robust; however, standard static test assertions or manual verified student traces are absent (since this relies on LLM-corrupted student code).
- **License**: The `LICENSE` file indicates standard usage permissions (typically MIT for academic repos), but relies on Project CodeNet's underlying terms for the problem statements.

## 5. Suitability for Re:Learn
This benchmark is highly suitable for Re:Learn because:
1. It contains explicit **misconception labels** (unlike generic compiler verdicts).
2. It provides exact source code that exhibits those specific misconceptions.
3. It maps directly to problem definitions, enabling our planned RAG + LLM Intervention pipeline.

The next step (post-audit) will be parsing these JSONs into a unified Pandas DataFrame to build features for the ML model.
