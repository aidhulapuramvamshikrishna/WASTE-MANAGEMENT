"""Utilities for seeding, hardware acceleration selection, and tracking."""

import os
import random
import time
from typing import Self

import numpy as np
import torch


def seed_everything(seed: int = 42) -> None:
    """Set seeds for reproducibility across python, numpy, and torch."""
    random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        torch.mps.manual_seed(seed)


def get_device(preference: str | None = "auto") -> torch.device:
    """Select the best available compute device: cuda > mps > cpu.

    Prints the selected device to stdout per project specifications.
    """
    pref = (preference or "auto").lower().strip()

    if pref == "cuda" and torch.cuda.is_available():
        device = torch.device("cuda")
    elif pref == "mps" and hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        device = torch.device("mps")
    elif pref == "cpu":
        device = torch.device("cpu")
    else:  # auto
        if torch.cuda.is_available():
            device = torch.device("cuda")
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            device = torch.device("mps")
        else:
            device = torch.device("cpu")

    print(f"Using device: {device.type.upper()}")
    return device


class AverageMeter:
    """Computes and stores the average, current, and sum values."""

    def __init__(self, name: str = "Metric", fmt: str = ":.4f"):
        self.name = name
        self.fmt = fmt
        self.val: float = 0.0
        self.avg: float = 0.0
        self.sum: float = 0.0
        self.count: int = 0

    def reset(self) -> None:
        self.val = 0.0
        self.avg = 0.0
        self.sum = 0.0
        self.count = 0

    def update(self, val: float, n: int = 1) -> None:
        self.val = val
        self.sum += val * n
        self.count += n
        self.avg = self.sum / self.count if self.count > 0 else 0.0

    def __str__(self) -> str:
        fmtstr = "{name} {val" + self.fmt + "} ({avg" + self.fmt + "})"
        return fmtstr.format(**self.__dict__)


class Timer:
    """Context manager and utility to measure elapsed wall-clock seconds."""

    def __init__(self):
        self.start_time: float | None = None
        self.elapsed: float = 0.0

    def __enter__(self) -> Self:
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self.start_time is not None:
            self.elapsed = time.perf_counter() - self.start_time

    @property
    def seconds(self) -> float:
        return self.elapsed
