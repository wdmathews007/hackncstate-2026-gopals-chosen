"""
Lazy-loaded ResNet50 classifier for image authenticity detection.

Classes:  0 = real,  1 = ai,  2 = spliced
Outward label contract:  "real" | "fake"  (ai and spliced both map to fake)
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

import torch
import torch.nn as nn
from PIL import Image
from torchvision import models, transforms

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_MODEL_PATH = str(
    Path(__file__).resolve().parent.parent / "models" / "best_resnet50_model.pth"
)

CLASS_NAMES: list[str] = ["real", "ai", "spliced"]

OUTWARD_LABEL_MAP: dict[str, str] = {
    "real": "real",
    "ai": "fake",
    "spliced": "fake",
}

# ImageNet normalization (same transform the model was trained with)
_PREPROCESS = transforms.Compose(
    [
        transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ]
)

# ---------------------------------------------------------------------------
# Singleton loader
# ---------------------------------------------------------------------------

_model: nn.Module | None = None
_model_load_error: str | None = None


def _build_resnet50(num_classes: int = 3) -> nn.Module:
    """Construct a ResNet50 whose fc head matches the checkpoint layout."""
    model = models.resnet50(weights=None)
    model.fc = nn.Sequential(
        nn.Dropout(p=0.5),
        nn.Linear(model.fc.in_features, num_classes),
    )
    return model


def _load_model() -> nn.Module | None:
    """Load model weights once; return None on failure."""
    global _model, _model_load_error

    if _model is not None:
        return _model
    if _model_load_error is not None:
        # Already failed once this process; don't retry every request.
        return None

    model_path = os.environ.get("MODEL_CHECKPOINT_PATH", _DEFAULT_MODEL_PATH)

    if not Path(model_path).is_file():
        _model_load_error = f"Model file not found: {model_path}"
        logger.error(_model_load_error)
        return None

    try:
        logger.info("Loading model from %s ...", model_path)
        state_dict = torch.load(model_path, map_location="cpu", weights_only=False)

        # Handle wrapped checkpoints (e.g. {"model_state_dict": ...})
        if isinstance(state_dict, dict) and "model_state_dict" in state_dict:
            state_dict = state_dict["model_state_dict"]
        elif isinstance(state_dict, dict) and "state_dict" in state_dict:
            state_dict = state_dict["state_dict"]

        # Strip 'module.' prefix from DataParallel checkpoints
        cleaned: dict[str, torch.Tensor] = {}
        for key, value in state_dict.items():
            clean_key = key.removeprefix("module.")
            cleaned[clean_key] = value

        model = _build_resnet50(num_classes=3)
        model.load_state_dict(cleaned, strict=True)
        model.eval()

        _model = model
        logger.info("Model loaded successfully (%d parameters)", sum(p.numel() for p in model.parameters()))
        return _model

    except Exception as exc:
        _model_load_error = f"Failed to load model: {exc}"
        logger.error(_model_load_error, exc_info=True)
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

_FALLBACK: dict = {
    "label": "unknown",
    "confidence": 0.0,
    "classifier_subtype": None,
    "class_probs": None,
}


def predict(image: Image.Image) -> dict:
    """Run inference on a PIL Image.

    Returns dict with keys:
        label            – "real" | "fake" | "unknown"
        confidence       – float in [0, 1]
        classifier_subtype – "real" | "ai" | "spliced" | None
        class_probs      – dict[str, float] | None
    """
    model = _load_model()
    if model is None:
        return dict(_FALLBACK)

    try:
        rgb = image.convert("RGB")
        tensor = _PREPROCESS(rgb).unsqueeze(0)  # (1, 3, 224, 224)

        with torch.no_grad():
            logits = model(tensor)  # (1, 3)
            probs = torch.softmax(logits, dim=1).squeeze(0)  # (3,)

        top_idx = int(probs.argmax())
        subtype = CLASS_NAMES[top_idx]
        confidence = float(probs[top_idx])

        return {
            "label": OUTWARD_LABEL_MAP[subtype],
            "confidence": round(confidence, 4),
            "classifier_subtype": subtype,
            "class_probs": {name: round(float(probs[i]), 4) for i, name in enumerate(CLASS_NAMES)},
        }

    except Exception as exc:
        logger.error("Inference failed: %s", exc, exc_info=True)
        return dict(_FALLBACK)
