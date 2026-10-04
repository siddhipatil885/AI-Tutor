import os, json, glob, pandas as pd, numpy as np
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split

_HERE = os.path.dirname(os.path.abspath(__file__))
RAW_DIR = os.path.join(_HERE, 'data', 'raw', 'mcminer', 'corrupted_codes_best')
if not os.path.exists(RAW_DIR):
    RAW_DIR = os.path.join(_HERE, 'data', 'raw', 'mcminer', 'dataset', 'corrupted_codes_best')

PROCESSED_DIR = os.path.join(_HERE, 'data', 'processed')
os.makedirs(PROCESSED_DIR, exist_ok=True)

code_files = [f for f in glob.glob(os.path.join(RAW_DIR, '*.json')) if not f.endswith('filtering_report.json')]
records = []

for cf in code_files:
    with open(cf, 'r', encoding='utf-8') as f:
        data = json.load(f)
        if 'solutions' not in data: continue
        prob_id = data.get('problem_id')
        misc_id = data.get('misconception_id')
        for sol in data['solutions']:
            feedback = sol.get('feedback_loop', {})
            raw_response = feedback.get('raw_response', '')
            
            if '<exhibits_misconception>N</exhibits_misconception>' in raw_response:
                continue
            
            records.append({
                'example_id': f"{prob_id}_{sol.get('solution_index', '')}_{misc_id}",
                'problem_id': prob_id,
                'generated_code': sol.get('generated_code', ''),
                'global_misconception_index': misc_id,
                'problem_misconception_index': sol.get('problem_misconception_index'),
                'feedback_loop': json.dumps(feedback),
                'reasoning': sol.get('reasoning', ''),
                'is_compilable': feedback.get('parse_success', True)
            })

df = pd.DataFrame(records)
df.to_csv(os.path.join(PROCESSED_DIR, 'mcminer_all.csv'), index=False)

df_clean = df.drop_duplicates(subset=['generated_code']).copy()

class_counts = df_clean['global_misconception_index'].value_counts()
rare_classes = class_counts[class_counts < 10] # Push small classes to Train only to prevent split errors

rare_idx = df_clean['global_misconception_index'].isin(rare_classes.index)
df_rare = df_clean[rare_idx].copy()
df_main = df_clean[~rare_idx].copy()

train_main, temp_main = train_test_split(df_main, test_size=0.2, stratify=df_main['global_misconception_index'], random_state=42)
val_main, test_main = train_test_split(temp_main, test_size=0.5, stratify=temp_main['global_misconception_index'], random_state=42)

df_train = pd.concat([train_main, df_rare]).sample(frac=1, random_state=42).reset_index(drop=True)
df_val = val_main.reset_index(drop=True)
df_test = test_main.reset_index(drop=True)

df_train.to_csv(os.path.join(PROCESSED_DIR, 'train.csv'), index=False)
df_val.to_csv(os.path.join(PROCESSED_DIR, 'validation.csv'), index=False)
df_test.to_csv(os.path.join(PROCESSED_DIR, 'test.csv'), index=False)

plt.figure(figsize=(15, 6))
df_train['global_misconception_index'].value_counts().plot(kind='bar', color='blue', alpha=0.6, label='Train')
df_val['global_misconception_index'].value_counts().plot(kind='bar', color='orange', alpha=0.6, label='Val')
df_test['global_misconception_index'].value_counts().plot(kind='bar', color='green', alpha=0.6, label='Test')
plt.title('Misconception Class Distribution Across Splits')
plt.xlabel('Misconception Index')
plt.ylabel('Count')
plt.legend()
plt.tight_layout()
plt.savefig(os.path.join(PROCESSED_DIR, 'class_distribution.png'))

print('DONE')
print(f'Total parsed examples: {len(df)}')
print(f'Missing code: {df["generated_code"].isnull().sum() + (df["generated_code"] == "").sum()}')
print(f'Missing labels: {df["global_misconception_index"].isnull().sum()}')
print(f'Exact duplicate records: {df.duplicated().sum()}')
print(f'Duplicate code: {df.duplicated(subset=["generated_code"]).sum()}')
print(f'Remaining examples: {len(df_clean)}')
print(f'Rare classes (<10 examples): {len(rare_classes)}')
print(f'Train: {len(df_train)}, Val: {len(df_val)}, Test: {len(df_test)}')
