from __future__ import annotations

import base64
import io
from typing import Iterable, Optional

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd


def _figure_to_data_url() -> str:
    buffer = io.BytesIO()
    plt.tight_layout()
    plt.savefig(buffer, format="png", dpi=140, bbox_inches="tight")
    plt.close()
    encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{encoded}"


def generate_equity_curve_plot(dates: Iterable, equity: pd.Series) -> Optional[str]:
    if equity.empty:
        return None

    plt.figure(figsize=(10, 4.5))
    plt.plot(list(dates), equity.values, color="#22c55e", linewidth=2.0)
    plt.fill_between(list(dates), equity.values, 1.0, color="#22c55e", alpha=0.12)
    plt.title("Equity Curve")
    plt.xlabel("Date")
    plt.ylabel("Equity")
    plt.grid(alpha=0.2, linestyle="--")
    return _figure_to_data_url()


def generate_roc_curve_plot(fpr, tpr, auc: float) -> Optional[str]:
    if fpr is None or tpr is None:
        return None

    plt.figure(figsize=(5.5, 5.0))
    plt.plot(fpr, tpr, label=f"Strategy (AUC = {auc:.2f})", color="#38bdf8", linewidth=2.0)
    plt.plot([0, 1], [0, 1], linestyle="--", color="#94a3b8", label="Random (0.50)")
    plt.xlabel("False Positive Rate")
    plt.ylabel("True Positive Rate")
    plt.title("ROC Curve vs Next-Day Direction")
    plt.legend()
    plt.grid(alpha=0.2, linestyle="--")
    return _figure_to_data_url()
