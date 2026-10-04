import os
import pandas as pd
import torch
import json
import numpy as np
from datasets import Dataset
from transformers import AutoTokenizer, AutoModelForSequenceClassification, TrainingArguments, Trainer
from sklearn.metrics import f1_score, accuracy_score, precision_recall_fscore_support

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.join(_HERE, "..")
DATA_DIR = os.path.join(_ROOT, "data", "processed")
RAW_DATA_DIR = os.path.join(_ROOT, "data", "raw", "mcminer")

def compute_metrics(eval_pred):
    logits, labels = eval_pred
    predictions = np.argmax(logits, axis=-1)
    
    # Calculate metrics
    macro_f1 = f1_score(labels, predictions, average="macro", zero_division=0)
    acc = accuracy_score(labels, predictions)
    
    return {
        "accuracy": acc,
        "macro_f1": macro_f1
    }

def main():
    print("Loading data...")
    augmented_train_path = os.path.join(DATA_DIR, 'train_augmented.csv')
    if os.path.exists(augmented_train_path):
        print(f"Using augmented training data: {augmented_train_path}")
        train_df = pd.read_csv(augmented_train_path)
    else:
        print("Augmented data not found, falling back to original train.csv")
        train_df = pd.read_csv(os.path.join(DATA_DIR, 'train.csv'))
        
    val_df = pd.read_csv(os.path.join(DATA_DIR, 'validation.csv'))
    test_df = pd.read_csv(os.path.join(DATA_DIR, 'test.csv'))
    
    # Ensure labels are integers
    for df in [train_df, val_df, test_df]:
        df['global_misconception_index'] = df['global_misconception_index'].astype(int)
        df['generated_code'] = df['generated_code'].fillna('')
        df['problem_misconception_index'] = df['problem_misconception_index'].fillna('').astype(str)

    # Initialize tokenizer
    model_name = "microsoft/codebert-base"
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    
    def format_input(row):
        # We format the input as: "[CLS] Problem Context [SEP] Code [SEP]"
        prob_context = row['problem_misconception_index']
        code = row['generated_code']
        # if problem context is just an int or short string, we prepend "Problem:"
        return f"Problem: {prob_context}\n\nCode:\n{code}"

    print("Formatting inputs...")
    train_df['text'] = train_df.apply(format_input, axis=1)
    val_df['text'] = val_df.apply(format_input, axis=1)
    test_df['text'] = test_df.apply(format_input, axis=1)
    
    # Create HuggingFace datasets
    train_dataset = Dataset.from_pandas(train_df[['text', 'global_misconception_index']])
    val_dataset = Dataset.from_pandas(val_df[['text', 'global_misconception_index']])
    test_dataset = Dataset.from_pandas(test_df[['text', 'global_misconception_index']])
    
    # Determine number of classes
    all_labels = pd.concat([train_df['global_misconception_index'], val_df['global_misconception_index'], test_df['global_misconception_index']])
    num_labels = all_labels.max() + 1
    
    def tokenize_function(examples):
        return tokenizer(examples['text'], padding='max_length', truncation=True, max_length=512)
        
    print("Tokenizing datasets...")
    train_dataset = train_dataset.map(tokenize_function, batched=True)
    val_dataset = val_dataset.map(tokenize_function, batched=True)
    test_dataset = test_dataset.map(tokenize_function, batched=True)
    
    # Rename label column
    train_dataset = train_dataset.rename_column("global_misconception_index", "labels")
    val_dataset = val_dataset.rename_column("global_misconception_index", "labels")
    test_dataset = test_dataset.rename_column("global_misconception_index", "labels")

    train_dataset.set_format('torch', columns=['input_ids', 'attention_mask', 'labels'])
    val_dataset.set_format('torch', columns=['input_ids', 'attention_mask', 'labels'])
    test_dataset.set_format('torch', columns=['input_ids', 'attention_mask', 'labels'])
    
    print("Loading model...")
    model = AutoModelForSequenceClassification.from_pretrained(model_name, num_labels=num_labels)
    
    output_dir = os.path.join(_ROOT, "models", "codebert-misconception")
    
    training_args = TrainingArguments(
        output_dir=output_dir,
        eval_strategy="epoch",
        save_strategy="epoch",
        learning_rate=2e-5,
        per_device_train_batch_size=8,
        per_device_eval_batch_size=16,
        num_train_epochs=5,
        weight_decay=0.01,
        load_best_model_at_end=True,
        metric_for_best_model="macro_f1",
        fp16=torch.cuda.is_available(), # Use mixed precision if GPU is available
        logging_dir=os.path.join(output_dir, "logs"),
        logging_steps=10,
    )
    
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        compute_metrics=compute_metrics,
    )
    
    print("Starting training...")
    trainer.train()
    
    print("Evaluating on test set...")
    test_results = trainer.evaluate(test_dataset)
    print("Test Results:", test_results)
    
    print("Saving final model...")
    trainer.save_model(os.path.join(_ROOT, "models", "best_codebert"))
    tokenizer.save_pretrained(os.path.join(_ROOT, "models", "best_codebert"))
    
    print("Done!")

if __name__ == "__main__":
    main()
