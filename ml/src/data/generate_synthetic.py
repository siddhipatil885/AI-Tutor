import os
import json
import time
import pandas as pd
import numpy as np
import google.generativeai as genai
import re

# Set up API key
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
genai.configure(api_key=GEMINI_API_KEY)

model = genai.GenerativeModel('gemini-3.5-flash')

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.join(_HERE, "..", "..")
DATA_DIR = os.path.join(_ROOT, "data", "processed")
RAW_DATA_DIR = os.path.join(_ROOT, "data", "raw", "mcminer")

# Load bank
misc_bank = {}
with open(os.path.join(RAW_DATA_DIR, 'misconception_bank.json')) as f:
    raw = json.load(f)
    for v in raw:
        misc_bank[int(v['id'])] = v.get('description', v.get('name', ''))

# Load splits
train = pd.read_csv(os.path.join(DATA_DIR, 'train.csv'))
all_df = pd.read_csv(os.path.join(DATA_DIR, 'mcminer_all.csv'))

# Get unique problems to sample from
problems = all_df[['problem_id', 'problem_misconception_index']].drop_duplicates().to_dict('records')
# Actually, the problem context is not fully described in the csv except as a problem_id.
# But mcminer_all.csv has "generated_code" which are snippets.
# Instead of abstract problem descriptions (which we don't have easily), we can prompt the LLM to invent a simple introductory programming problem where this misconception could occur, and then write the buggy student code.

def generate_synthetic_example(misc_id, misc_desc):
    prompt = f"""
    You are an expert computer science instructor.
    We are building a dataset of introductory Python programming errors.
    
    Misconception ID: {misc_id}
    Misconception Description: {misc_desc}
    
    Your task:
    1. Invent a short, realistic introductory programming problem (1-2 sentences).
    2. Write the buggy Python code a student might write if they had THIS EXACT misconception.
    3. The code must be runnable (syntactically valid if the misconception allows, or contain the logical/syntactic error described).
    
    Output strictly in the following JSON format without markdown code blocks:
    {{
        "problem_description": "...",
        "student_code": "..."
    }}
    """
    
    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        # Clean markdown
        if text.startswith("```json"):
            text = text[7:-3]
        elif text.startswith("```"):
            text = text[3:-3]
        data = json.loads(text.strip())
        return data['student_code'], data['problem_description']
    except Exception as e:
        print(f"Error generating for {misc_id}: {e}")
        return None, None

def main():
    # Identify classes with < 10 examples in train set
    class_counts = train['global_misconception_index'].value_counts()
    target_count = 10
    
    synthetic_records = []
    
    print("Starting synthetic data generation...")
    # Iterate over all 67 classes (assume 1 to 67, or specifically the keys in misc_bank)
    for cls in misc_bank.keys():
        current_count = class_counts.get(cls, 0)
        if current_count < target_count:
            needed = target_count - current_count
            print(f"Class {cls}: Needs {needed} examples. Desc: {misc_bank[cls][:50]}...")
            
            for i in range(needed):
                code, prob_desc = generate_synthetic_example(cls, misc_bank[cls])
                if code is not None:
                    synthetic_records.append({
                        'example_id': f'synth_{cls}_{i}',
                        'generated_code': code,
                        'global_misconception_index': cls,
                        'problem_misconception_index': prob_desc, # We store problem desc here temporarily or as a feature
                        'feedback_loop': '[]', # No compiler feedback for synthetic
                        'reasoning': 'Synthetic data based on misconception description.',
                        'is_synthetic': True
                    })
                print("Sleeping for 15 seconds to respect free tier rate limit of 5 RPM...")
                time.sleep(15) # rate limit prevention (5 RPM free tier)
    
    if synthetic_records:
        synth_df = pd.DataFrame(synthetic_records)
        out_path = os.path.join(DATA_DIR, 'synthetic_train.csv')
        synth_df.to_csv(out_path, index=False)
        print(f"Saved {len(synth_df)} synthetic examples to {out_path}")
        
        # Merge with train
        train['is_synthetic'] = False
        new_train = pd.concat([train, synth_df], ignore_index=True)
        merged_path = os.path.join(DATA_DIR, 'train_augmented.csv')
        new_train.to_csv(merged_path, index=False)
        print(f"Saved augmented train set to {merged_path} (Total: {len(new_train)})")
    else:
        print("No synthetic records generated.")

if __name__ == "__main__":
    main()
