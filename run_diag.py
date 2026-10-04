import os, json
import numpy as np
import pandas as pd
import joblib
from sklearn.metrics import classification_report, confusion_matrix

DATA_DIR = 'ml/data/processed'
MODELS_DIR = 'ml/models'
RESULTS_DIR = 'ml/experiments/results'
RAW_DATA_DIR = 'ml/data/raw/mcminer'

# Load bank
misc_bank = {}
with open(os.path.join(RAW_DATA_DIR, 'misconception_bank.json')) as f:
    raw = json.load(f)
    for v in raw:
        misc_bank[int(v['id'])] = v.get('description', v.get('name', ''))

# Load splits
train = pd.read_csv(os.path.join(DATA_DIR, 'train.csv'))
val = pd.read_csv(os.path.join(DATA_DIR, 'validation.csv'))
test = pd.read_csv(os.path.join(DATA_DIR, 'test.csv'))
all_df = pd.read_csv(os.path.join(DATA_DIR, 'mcminer_all.csv'))

artefact = joblib.load(os.path.join(MODELS_DIR, 'best_model.pkl'))
le = artefact['le']

print("===== 2. TRAINING DATA AVAIL =====")
stats = []
for cls in le.classes_:
    t = len(train[train['global_misconception_index'] == cls])
    v = len(val[val['global_misconception_index'] == cls])
    te = len(test[test['global_misconception_index'] == cls])
    total = t + v + te
    probs = all_df[all_df['global_misconception_index'] == cls]['problem_id'].nunique()
    stats.append((cls, total, t, v, te, probs))

stats_df = pd.DataFrame(stats, columns=['class', 'total', 'train', 'val', 'test', 'probs'])
print("<5 examples:", len(stats_df[stats_df['total'] < 5]))
print("<10 examples:", len(stats_df[stats_df['total'] < 10]))
print("<2 probs:", len(stats_df[stats_df['probs'] < 2]))

print("\n===== 1. PER CLASS METRICS =====")
with open(os.path.join(RESULTS_DIR, 'exp5_fusion_test.json')) as f:
    res = json.load(f)

# Let's get actual predictions
clf = artefact['clf']
y_raw = test['global_misconception_index'].values
mask = np.isin(y_raw, le.classes_)
emb = np.load(os.path.join(MODELS_DIR, 'exp2_minilm_svm_emb_test.npy'))[mask]
ts = np.load(os.path.join(MODELS_DIR, 'ts_feats_test.npy'))[mask]

from sklearn.preprocessing import normalize
X = np.hstack([normalize(emb), ts])
y = le.transform(y_raw[mask])

y_pred = clf.predict(X)
y_proba = clf.predict_proba(X)
top3 = np.argsort(y_proba, axis=1)[:, -3:]

report = classification_report(y, y_pred, output_dict=True, zero_division=0)
cls_mets = []
for i, cls in enumerate(le.classes_):
    if str(i) not in report: continue
    rep = report[str(i)]
    mask_c = (y == i)
    if sum(mask_c) == 0: continue
    top3_rec = sum([1 for t3 in top3[mask_c] if i in t3]) / sum(mask_c)
    cls_mets.append({'cls': cls, 'supp': rep['support'], 'prec': rep['precision'], 'rec': rep['recall'], 'f1': rep['f1-score'], 't3': top3_rec})

mets_df = pd.DataFrame(cls_mets).sort_values('f1')
print(mets_df.head(10).to_string(index=False))

print("\n===== 3. CONFUSION =====")
cm = confusion_matrix(y, y_pred, labels=np.arange(len(le.classes_)))
confused = []
for i in range(len(le.classes_)):
    for j in range(i+1, len(le.classes_)):
        c_ij = cm[i, j]
        c_ji = cm[j, i]
        if c_ij + c_ji > 0:
            cA = le.classes_[i]
            cB = le.classes_[j]
            confused.append({
                'A': cA, 'B': cB, 'A->B': c_ij, 'B->A': c_ji, 'total': c_ij+c_ji,
                'desc_A': misc_bank.get(cA, '')[:60], 'desc_B': misc_bank.get(cB, '')[:60]
            })

c_df = pd.DataFrame(confused).sort_values('total', ascending=False).head(20)
print(c_df.to_string(index=False))

print("\n===== 4. CONFIDENCE =====")
conf = np.max(y_proba, axis=1)
correct = (y == y_pred)
high_conf_wrong = sum((conf > 0.8) & (~correct))
low_conf_correct = sum((conf < 0.3) & correct)
print("High conf wrong (>0.8):", high_conf_wrong)
print("Low conf correct (<0.3):", low_conf_correct)
