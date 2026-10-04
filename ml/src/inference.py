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
import joblib

logger = logging.getLogger(__name__)

_DEFAULT_MODEL_PATH = os.path.join(
    os.path.dirname(__file__), "../../models/best_model.pkl"
)
_MISCONCEPTION_BANK_PATH = os.path.join(
    os.path.dirname(__file__),
    "../../data/raw/mcminer/misconception_bank.json",
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
    """
    Loads a saved Re:Learn misconception model and provides predict().

    The model artefact is a dict produced by one of the train_*.py scripts:
        {
          "clf": sklearn pipeline,
          "le" : LabelEncoder,
          optionally: "tfidf": TfidfVectorizer
        }

    For embedding-based models, the pipeline includes a StandardScaler + SVM/LR.
    For TF-IDF models, tfidf is stored separately and applied before clf.
    """

    def __init__(self, model_path: str = _DEFAULT_MODEL_PATH, top_k: int = 3):
        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"Model not found at {model_path}. "
                "Run the training scripts first (train_baseline.py, train_embedding.py, etc.)."
            )
        artefact = joblib.load(model_path)
        self.clf   = artefact["clf"]
        self.le    = artefact["le"]
        self.tfidf = artefact.get("tfidf", None)
        self.top_k = top_k
        self.model_path = model_path
        self.model_name = os.path.basename(model_path).replace(".pkl", "")

        # Load misconception descriptions if available
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
        """
        Turn raw code into features appropriate for this model type.
        TF-IDF models have a .tfidf field; embedding models embed inline.
        For the canonical best_model.pkl, the embedding is assumed to be
        pre-handled by the pipeline's scaler.
        """
        if self.tfidf is not None:
            return self.tfidf.transform([code])
        # For models that need embeddings at inference time, we use MiniLM
        # (light enough to run on CPU without GPU dependency)
        try:
            from sentence_transformers import SentenceTransformer
            if not hasattr(self, "_st_model"):
                self._st_model = SentenceTransformer(
                    "sentence-transformers/all-MiniLM-L6-v2"
                )
            emb = self._st_model.encode(
                [code[:2048]], normalize_embeddings=True
            )
            # If model also expects tree-sitter features, append them
            try:
                from src.features.tree_sitter_features import (
                    extract_features_from_code, FEATURE_NAMES
                )
                ts_feat = extract_features_from_code(code)
                ts_vec = np.array(
                    [[ts_feat.get(k, 0.0) for k in FEATURE_NAMES]], dtype=float
                )
                from sklearn.preprocessing import normalize
                emb_n = normalize(emb)
                return np.hstack([emb_n, ts_vec])
            except ImportError:
                return emb
        except ImportError:
            raise RuntimeError(
                "sentence-transformers not installed. "
                "Run: pip install sentence-transformers"
            )

    def predict(self, code: str) -> PredictionResult:
        """
        Predict misconception for a single code string.

        Parameters
        ----------
        code : str   Raw Python student code.

        Returns
        -------
        PredictionResult  with predicted class, confidence, and top-k list.
        """
        X = self._get_features(code)
        class_idx = int(self.clf.predict(X)[0])
        proba = self.clf.predict_proba(X)[0]

        # Map encoded index → original misconception integer
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

    def predict_dict(self, code: str) -> dict:
        """Return prediction as a JSON-serialisable dict."""
        result = self.predict(code)
        return {
            "predicted_misconception": result.predicted_misconception,
            "misconception_description": result.misconception_description,
            "confidence": result.confidence,
            "model_name": result.model_name,
            "top_predictions": [
                {
                    "misconception": p.misconception,
                    "probability": p.probability,
                    "description": p.description,
                }
                for p in result.top_predictions
            ],
        }


# ── Module-level convenience function ────────────────────────────────────────
_PREDICTOR: Optional[MisconceptionPredictor] = None


def predict(code: str, model_path: str = _DEFAULT_MODEL_PATH, top_k: int = 3) -> dict:
    """
    Predict misconception for a single code string.

    This is the primary inference function to be called by FastAPI later.

    Parameters
    ----------
    code       : str  Raw Python student code.
    model_path : str  Path to the saved model pkl.
    top_k      : int  Number of top predictions to return.

    Returns
    -------
    dict  JSON-serialisable prediction result.
    """
    global _PREDICTOR
    if _PREDICTOR is None or _PREDICTOR.model_path != model_path:
        _PREDICTOR = MisconceptionPredictor(model_path=model_path, top_k=top_k)
    return _PREDICTOR.predict_dict(code)


# ── CLI smoke-test ────────────────────────────────────────────────────────────
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
    result = predict(sample_code, model_path=model_path)
    print(json.dumps(result, indent=2))
