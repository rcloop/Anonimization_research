"""
Bias / fairness metrics for binary classification.

Input expectations:
- y_true: 0/1
- y_pred: 0/1
- sensitive attribute: any hashable group label (e.g., "F", "M", "65+", "region_1")
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple


def _safe_div(n: float, d: float) -> Optional[float]:
    if d == 0:
        return None
    return n / d


@dataclass(frozen=True)
class Confusion:
    tp: int
    fp: int
    tn: int
    fn: int

    @property
    def n(self) -> int:
        return self.tp + self.fp + self.tn + self.fn


def confusion_from_labels(y_true: Iterable[int], y_pred: Iterable[int]) -> Confusion:
    tp = fp = tn = fn = 0
    for yt, yp in zip(y_true, y_pred):
        if yt not in (0, 1) or yp not in (0, 1):
            raise ValueError(f"y_true/y_pred must be 0/1. Got y_true={yt}, y_pred={yp}")
        if yt == 1 and yp == 1:
            tp += 1
        elif yt == 0 and yp == 1:
            fp += 1
        elif yt == 0 and yp == 0:
            tn += 1
        else:
            fn += 1
    return Confusion(tp=tp, fp=fp, tn=tn, fn=fn)


def metrics_from_confusion(c: Confusion) -> Dict[str, Optional[float]]:
    acc = _safe_div(c.tp + c.tn, c.n)
    selection_rate = _safe_div(c.tp + c.fp, c.n)
    prevalence = _safe_div(c.tp + c.fn, c.n)

    tpr = _safe_div(c.tp, c.tp + c.fn)  # recall / sensitivity
    fpr = _safe_div(c.fp, c.fp + c.tn)
    tnr = _safe_div(c.tn, c.tn + c.fp)  # specificity
    fnr = _safe_div(c.fn, c.fn + c.tp)

    precision = _safe_div(c.tp, c.tp + c.fp)  # PPV
    npv = _safe_div(c.tn, c.tn + c.fn)

    return {
        "n": float(c.n),
        "tp": float(c.tp),
        "fp": float(c.fp),
        "tn": float(c.tn),
        "fn": float(c.fn),
        "accuracy": acc,
        "prevalence": prevalence,
        "selection_rate": selection_rate,
        "tpr": tpr,
        "fpr": fpr,
        "tnr": tnr,
        "fnr": fnr,
        "precision": precision,
        "npv": npv,
    }


def _finite(vals: Iterable[Optional[float]]) -> List[float]:
    return [v for v in vals if v is not None]


def _diff_max_min(vals: Iterable[Optional[float]]) -> Optional[float]:
    f = _finite(vals)
    if not f:
        return None
    return max(f) - min(f)


def _ratio_min_max(vals: Iterable[Optional[float]]) -> Optional[float]:
    f = _finite(vals)
    if not f:
        return None
    mx = max(f)
    mn = min(f)
    if mx == 0:
        return None
    return mn / mx


def evaluate_group_fairness(
    y_true: List[int],
    y_pred: List[int],
    sensitive: List[Any],
) -> Dict[str, Any]:
    if not (len(y_true) == len(y_pred) == len(sensitive)):
        raise ValueError("y_true, y_pred and sensitive must have same length.")
    if len(y_true) == 0:
        raise ValueError("Empty input.")

    # Per-group confusion + metrics
    groups: Dict[str, Dict[str, Any]] = {}
    by_group: Dict[str, Tuple[List[int], List[int]]] = {}
    for yt, yp, s in zip(y_true, y_pred, sensitive):
        g = str(s)
        if g not in by_group:
            by_group[g] = ([], [])
        by_group[g][0].append(int(yt))
        by_group[g][1].append(int(yp))

    selection_rates = []
    tprs = []
    fprs = []

    for g, (yt_g, yp_g) in sorted(by_group.items(), key=lambda kv: kv[0]):
        c = confusion_from_labels(yt_g, yp_g)
        m = metrics_from_confusion(c)
        groups[g] = {
            "confusion": {"tp": c.tp, "fp": c.fp, "tn": c.tn, "fn": c.fn, "n": c.n},
            "metrics": m,
        }
        selection_rates.append(m.get("selection_rate"))
        tprs.append(m.get("tpr"))
        fprs.append(m.get("fpr"))

    # Overall
    c_all = confusion_from_labels(y_true, y_pred)
    overall = {
        "confusion": {"tp": c_all.tp, "fp": c_all.fp, "tn": c_all.tn, "fn": c_all.fn, "n": c_all.n},
        "metrics": metrics_from_confusion(c_all),
    }

    # Fairness summary (classic group fairness for binary classification)
    fairness = {
        "demographic_parity_difference": _diff_max_min(selection_rates),
        "demographic_parity_ratio": _ratio_min_max(selection_rates),  # also called disparate impact
        "equal_opportunity_difference": _diff_max_min(tprs),  # TPR gap
        "false_positive_rate_difference": _diff_max_min(fprs),  # FPR gap
        "equalized_odds_difference": (
            None
            if _diff_max_min(tprs) is None or _diff_max_min(fprs) is None
            else max(_diff_max_min(tprs), _diff_max_min(fprs))
        ),
    }

    return {
        "overall": overall,
        "per_group": groups,
        "fairness": fairness,
        "groups": sorted(groups.keys()),
    }

