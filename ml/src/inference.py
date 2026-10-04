"""
inference.py — Clean inference interface for Re:Learn misconception detection.

This module is designed to be imported by a future FastAPI integration.
It loads the best-performing model and exposes a single `predict()` function.

Usage:
    from ml.src.inference import predict, MisconceptionPredictor

    result = predict(code)
    # {
    #   "predicted_misconception": 17,
    #   "misconception_description": "...",
    #   "confidence": 0.84,
    #   "top_predictions": [
    #       {"misconception": 17, "probability": 0.84},
    #       {"misconception": 32, "probability": 0.09},
    #       {"misconception": 11, "probability": 0.05},
    #   ]
    # }
"""
import os, json, logging
from dataclasses import dataclass, field
from typing import Optional
import numpy as np
import torch
import joblib

logger = logging.getLogger(__name__)

_DEFAULT_MODEL_PATH = os.path.join(
    os.path.dirname(__file__), "../models/best_codebert"
)
_MISCONCEPTION_BANK_PATH = os.path.join(
    os.path.dirname(__file__),
    "../data/raw/mcminer/misconception_bank.json",
)

@dataclass
class TopPrediction:
    misconception: int
    probability: float
    description: str = ""

@dataclass
class PredictionResult:
    predicted_misconception: int
    confidence: float
    top_predictions: list = field(default_factory=list)
    misconception_description: str = ""
    model_name: str = ""

class MisconceptionPredictor:
    def __init__(self, model_path: str = _DEFAULT_MODEL_PATH, top_k: int = 3):
        self.top_k = top_k
        self.model_path = model_path
        self.model_name = os.path.basename(model_path).replace(".pkl", "")
        self.is_transformers = os.path.isdir(model_path)
        
        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"Model not found at {model_path}. "
            )
            
        if self.is_transformers:
            from transformers import AutoTokenizer, AutoModelForSequenceClassification
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            self.tokenizer = AutoTokenizer.from_pretrained(model_path)
            self.model = AutoModelForSequenceClassification.from_pretrained(model_path).to(self.device)
            self.model.eval()
        else:
            artefact = joblib.load(model_path)
            self.clf   = artefact["clf"]
            self.le    = artefact["le"]
            self.tfidf = artefact.get("tfidf", None)

        self.misc_bank: dict = {}
        if os.path.exists(_MISCONCEPTION_BANK_PATH):
            try:
                with open(_MISCONCEPTION_BANK_PATH) as f:
                    raw = json.load(f)
                for item in raw.values() if isinstance(raw, dict) else raw:
                    mid = item.get("id") or item.get("misconception_id")
                    desc = item.get("description") or item.get("name", "")
                    if mid is not None:
                        self.misc_bank[int(mid)] = desc
            except Exception as e:
                logger.warning("Could not load misconception bank: %s", e)

        logger.info("MisconceptionPredictor loaded: %s", self.model_name)

    def _get_features(self, code: str) -> np.ndarray:
        if self.tfidf is not None:
            return self.tfidf.transform([code])
        try:
            from sentence_transformers import SentenceTransformer
            if not hasattr(self, "_st_model"):
                self._st_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
            emb = self._st_model.encode([code[:2048]], normalize_embeddings=True)
            
            if "fusion" in self.model_name:
                import sys
                import os
                root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
                if root_dir not in sys.path:
                    sys.path.insert(0, root_dir)
                from ml.src.features.tree_sitter_features import extract_features_from_code, features_to_matrix
                ts_dict = extract_features_from_code(code)
                ts_mat, _ = features_to_matrix([ts_dict])
                return np.hstack([emb, ts_mat])
            return emb
        except ImportError:
            raise RuntimeError("sentence-transformers not installed.")

    def predict(self, code: str, problem_context: str = "") -> PredictionResult:
        if self.is_transformers:
            # CodeBERT inference
            text = f"Problem: {problem_context}\n\nCode:\n{code}"
            inputs = self.tokenizer(text, return_tensors="pt", padding='max_length', truncation=True, max_length=512)
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            with torch.no_grad():
                outputs = self.model(**inputs)
            logits = outputs.logits
            probs = torch.nn.functional.softmax(logits, dim=-1)[0].cpu().numpy()
            predicted_class = int(np.argmax(probs))
            confidence = float(probs[predicted_class])
            
            top_k_idx = np.argsort(probs)[::-1][: self.top_k]
            top_preds = []
            for idx in top_k_idx:
                mc_int = int(idx)
                top_preds.append(TopPrediction(
                    misconception=mc_int,
                    probability=float(probs[idx]),
                    description=self.misc_bank.get(mc_int, ""),
                ))
        else:
            # Sklearn inference
            X = self._get_features(code)
            class_idx = int(self.clf.predict(X)[0])
            proba = self.clf.predict_proba(X)[0]
            predicted_class = int(self.le.inverse_transform([class_idx])[0])
            confidence = float(proba[class_idx])
            
            top_k_idx = np.argsort(proba)[::-1][: self.top_k]
            top_preds = []
            for idx in top_k_idx:
                mc_int = int(self.le.inverse_transform([idx])[0])
                top_preds.append(TopPrediction(
                    misconception=mc_int,
                    probability=float(proba[idx]),
                    description=self.misc_bank.get(mc_int, ""),
                ))

        return PredictionResult(
            predicted_misconception=predicted_class,
            confidence=confidence,
            top_predictions=top_preds,
            misconception_description=self.misc_bank.get(predicted_class, ""),
            model_name=self.model_name,
        )

    def predict_dict(self, code: str, problem_context: str = "") -> dict:
        result = self.predict(code, problem_context)
        return {
            "predicted_misconception": {
                "id": str(result.predicted_misconception),
                "name": result.misconception_description,
                "description": result.misconception_description
            },
            "confidence": result.confidence,
            "top_predictions": [
                {
                    "misconception": str(p.misconception),
                    "confidence": p.probability
                }
                for p in result.top_predictions
            ],
        }

_PREDICTOR: Optional[MisconceptionPredictor] = None

def predict(code: str, problem_context: str = "", model_path: str = _DEFAULT_MODEL_PATH, top_k: int = 3) -> dict:
    global _PREDICTOR
    if _PREDICTOR is None or _PREDICTOR.model_path != model_path:
        _PREDICTOR = MisconceptionPredictor(model_path=model_path, top_k=top_k)
    return _PREDICTOR.predict_dict(code, problem_context)

if __name__ == "__main__":
    import sys
    sample_code = """
def add_list(lst):
    total = 0
    for i in range(len(lst)):
        total = total + lst[i]
    return total
"""
    model_path = sys.argv[1] if len(sys.argv) > 1 else _DEFAULT_MODEL_PATH
    result = predict(sample_code, problem_context="Sum elements in list", model_path=model_path)
    print(json.dumps(result, indent=2))

