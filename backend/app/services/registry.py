"""Model registry for discovering, loading, and serving PyTorch waste models."""

import json
import threading
from pathlib import Path
from typing import Any

import torch
from wasteml.gradcam import GradCAM
from wasteml.models.factory import build_model, gradcam_target_layer
from wasteml.utils import get_device

from app.config import settings


class LoadedModel:
    """Wrapper holding a loaded PyTorch model, metadata, and Grad-CAM engine."""

    def __init__(
        self,
        name: str,
        model: torch.nn.Module,
        model_card: dict[str, Any],
        calibration: dict[str, Any],
        target_layer: torch.nn.Module,
        device: torch.device,
    ) -> None:
        self.name = name
        self.model = model
        self.model_card = model_card
        self.calibration = calibration
        self.target_layer = target_layer
        self.device = device
        self.class_names: list[str] = model_card.get("class_names", [])
        self.temperature: float = float(calibration.get("temperature", 1.0))
        # The backend uses ui_uncertain_threshold when present, otherwise uncertain_threshold
        ui_thresh = calibration.get("ui_uncertain_threshold") or model_card.get("ui_uncertain_threshold")
        if ui_thresh is not None:
            self.uncertain_threshold: float = float(ui_thresh)
        else:
            self.uncertain_threshold: float = float(calibration.get("uncertain_threshold", 0.50))
        self.gradcam_engine = GradCAM(model, target_layer)
        self.lock = threading.Lock()


class ModelRegistry:
    """Registry managing model cards, weights, and lazy/eager loading."""

    def __init__(self) -> None:
        self.model_dir = Path(settings.MODEL_DIR)
        self.device = get_device(settings.TORCH_DEVICE)
        self.available_models: dict[str, Path] = {}
        self._cache: dict[str, LoadedModel] = {}
        self.is_ready: bool = False
        self._classes_cache: list[dict[str, Any]] | None = None
        self._full_metrics_cache: dict[str, dict[str, Any]] = {}

    def discover(self) -> None:
        """Scan MODEL_DIR for valid model folders with model_card.json."""
        self.available_models.clear()
        if not self.model_dir.is_dir():
            print(f"Model directory not found: {self.model_dir}", flush=True)
            return

        for p in self.model_dir.iterdir():
            if p.is_dir() and (p / "model_card.json").exists():
                self.available_models[p.name] = p

        print(f"Discovered {len(self.available_models)} models in {self.model_dir}: {list(self.available_models.keys())}", flush=True)

    def startup(self) -> None:
        """Eagerly load default model and verify readiness."""
        self.discover()
        if settings.DEFAULT_MODEL in self.available_models:
            try:
                self.load_model(settings.DEFAULT_MODEL)
                self.is_ready = True
                print(f"Eagerly loaded default model: {settings.DEFAULT_MODEL}", flush=True)
            except Exception as e:
                print(f"Failed to load default model {settings.DEFAULT_MODEL}: {e}", flush=True)
                self.is_ready = False
        else:
            print(f"Default model {settings.DEFAULT_MODEL} not found in {list(self.available_models.keys())}", flush=True)
            self.is_ready = False

    def load_model(self, name: str) -> LoadedModel:
        """Load a model by name with weights_only=True and per-model lock."""
        name_key = name.lower().strip()
        if name_key in self._cache:
            return self._cache[name_key]

        if name_key not in self.available_models:
            raise KeyError(f"Unknown model '{name}'. Available: {list(self.available_models.keys())}")

        p = self.available_models[name_key]
        with open(p / "model_card.json") as f:
            card = json.load(f)

        calib_path = p / "calibration.json"
        if calib_path.exists():
            with open(calib_path) as f:
                calibration = json.load(f)
        else:
            calibration = {"temperature": 1.0, "uncertain_threshold": 0.50}

        weights_file = card.get("weights_file", "best.pt")
        weights_path = p / weights_file
        if not weights_path.exists():
            raise FileNotFoundError(f"Missing weights for {name} at {weights_path}")

        # Build architecture and load state_dict with weights_only=True (SECURITY.md T13)
        num_classes = card.get("num_classes", 12)
        model = build_model(name_key, num_classes=num_classes, pretrained=False)
        state_dict = torch.load(weights_path, map_location="cpu", weights_only=True)
        model.load_state_dict(state_dict)
        model.to(self.device)
        model.eval()

        target_layer = gradcam_target_layer(model, name_key)
        loaded = LoadedModel(
            name=name_key,
            model=model,
            model_card=card,
            calibration=calibration,
            target_layer=target_layer,
            device=self.device,
        )
        self._cache[name_key] = loaded
        return loaded

    def get_model_summary(self, name: str) -> dict[str, Any] | None:
        """Get model card and metrics summary for GET /models."""
        name_key = name.lower().strip()
        if name_key not in self.available_models:
            return None

        p = self.available_models[name_key]
        with open(p / "model_card.json") as f:
            card = json.load(f)

        metrics_summary = {}
        metrics_path = p / "metrics.json"
        if metrics_path.exists():
            with open(metrics_path) as f:
                m_data = json.load(f)
            metrics_summary = {
                "accuracy": m_data.get("accuracy"),
                "macro_f1": m_data.get("macro_f1"),
                "params": m_data.get("params"),
                "size_mb": m_data.get("size_mb"),
                "cpu_latency_ms_p50": m_data.get("cpu_latency_ms_p50"),
                "uncertain_threshold": card.get("ui_uncertain_threshold", card.get("uncertain_threshold")),
            }

        return {
            "name": name_key,
            "display_name": card.get("display_name", name_key),
            "trained_from_scratch": card.get("trained_from_scratch", False),
            "is_default": name_key == settings.DEFAULT_MODEL,
            "metrics_summary": metrics_summary,
        }

    def get_full_metrics(self, name: str) -> dict[str, Any] | None:
        """Return full metrics, confusion matrix, calibration, and history for GET /models/{name}/metrics."""
        name_key = name.lower().strip()
        if name_key in self._full_metrics_cache:
            return self._full_metrics_cache[name_key]

        if name_key not in self.available_models:
            return None

        p = self.available_models[name_key]
        res: dict[str, Any] = {"name": name_key}

        for fname, key in [
            ("model_card.json", "model_card"),
            ("metrics.json", "metrics"),
            ("confusion_matrix.json", "confusion_matrix"),
            ("calibration.json", "calibration"),
        ]:
            fpath = p / fname
            if fpath.exists():
                with open(fpath) as f:
                    res[key] = json.load(f)

        # Parse history.csv with standard csv (zero pandas dependency overhead)
        hist_path = p / "history.csv"
        if hist_path.exists():
            import csv
            with open(hist_path, newline="") as f:
                reader = csv.DictReader(f)
                records = []
                for row in reader:
                    parsed: dict[str, Any] = {}
                    for k, v in row.items():
                        try:
                            parsed[k] = float(v) if "." in v else int(v)
                        except (ValueError, TypeError):
                            parsed[k] = v
                    records.append(parsed)
                res["history"] = records

        self._full_metrics_cache[name_key] = res
        return res

    def get_classes(self) -> list[dict[str, Any]]:
        """Return [{name, stream, disposal}] derived from classes.json by class NAME."""
        if self._classes_cache is not None:
            return self._classes_cache

        classes_path = Path(settings.CLASSES_JSON_PATH)
        if not classes_path.exists():
            return []

        with open(classes_path) as f:
            cdata = json.load(f)

        # Alphabetical order matching model card class order (ARCHITECTURE §3)
        sorted_names = sorted(cdata.keys())
        out = []
        for name in sorted_names:
            out.append({
                "name": name,
                "stream": cdata[name].get("stream", "dry"),
                "disposal": cdata[name].get("disposal", ""),
            })

        self._classes_cache = out
        return out


registry = ModelRegistry()
