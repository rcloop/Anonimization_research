"""
Run a simple bias/fairness evaluation suite over a labeled dataset.

Input formats:
- CSV with columns:
  - y_true (required): 0/1
  - y_pred (optional): 0/1
  - y_score (optional): float in [0,1] (used to derive y_pred with threshold)
  - sensitive column (required): specified via --sensitive_col
"""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from bias_metrics import evaluate_group_fairness


def _parse_int01(v: Any, field: str) -> int:
    s = str(v).strip()
    if s in ("0", "0.0", "false", "False", "FALSE"):
        return 0
    if s in ("1", "1.0", "true", "True", "TRUE"):
        return 1
    raise ValueError(f"Field '{field}' must be 0/1 (or true/false). Got: {v!r}")


def _parse_float(v: Any, field: str) -> float:
    try:
        return float(str(v).strip())
    except Exception as e:
        raise ValueError(f"Field '{field}' must be float. Got: {v!r}") from e


def load_csv(
    data_path: Path,
    sensitive_col: str,
    y_true_col: str = "y_true",
    y_pred_col: str = "y_pred",
    y_score_col: str = "y_score",
    threshold: float = 0.5,
) -> Tuple[List[int], List[int], List[str], Dict[str, Any]]:
    if not data_path.exists():
        raise FileNotFoundError(str(data_path))

    y_true: List[int] = []
    y_pred: List[int] = []
    sensitive: List[str] = []

    with data_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError("CSV has no header.")

        fieldnames = [c.strip() for c in reader.fieldnames]
        if y_true_col not in fieldnames:
            raise ValueError(f"Missing required column '{y_true_col}'. Found: {fieldnames}")
        if sensitive_col not in fieldnames:
            raise ValueError(f"Missing required column '{sensitive_col}'. Found: {fieldnames}")

        has_y_pred = y_pred_col in fieldnames
        has_y_score = y_score_col in fieldnames
        if not has_y_pred and not has_y_score:
            raise ValueError(
                f"CSV must include '{y_pred_col}' or '{y_score_col}'. Found: {fieldnames}"
            )

        rows = 0
        derived_from_score = 0
        for row in reader:
            rows += 1
            yt = _parse_int01(row.get(y_true_col), y_true_col)
            s = str(row.get(sensitive_col)).strip()
            if has_y_pred and row.get(y_pred_col) not in (None, ""):
                yp = _parse_int01(row.get(y_pred_col), y_pred_col)
            else:
                score = _parse_float(row.get(y_score_col), y_score_col)
                yp = 1 if score >= threshold else 0
                derived_from_score += 1

            y_true.append(yt)
            y_pred.append(yp)
            sensitive.append(s)

    meta = {
        "rows": rows,
        "fieldnames": fieldnames,
        "used_columns": {
            "y_true": y_true_col,
            "y_pred": y_pred_col if has_y_pred else None,
            "y_score": y_score_col if has_y_score else None,
            "sensitive": sensitive_col,
        },
        "threshold": threshold,
        "y_pred_derived_from_score_rows": derived_from_score,
    }
    return y_true, y_pred, sensitive, meta


def run_bias_suite(
    data_path: str,
    sensitive_col: str,
    output_path: str,
    y_true_col: str = "y_true",
    y_pred_col: str = "y_pred",
    y_score_col: str = "y_score",
    threshold: float = 0.5,
) -> Dict[str, Any]:
    data_p = Path(data_path)
    y_true, y_pred, sensitive, meta = load_csv(
        data_path=data_p,
        sensitive_col=sensitive_col,
        y_true_col=y_true_col,
        y_pred_col=y_pred_col,
        y_score_col=y_score_col,
        threshold=threshold,
    )

    results = evaluate_group_fairness(y_true=y_true, y_pred=y_pred, sensitive=sensitive)
    report = {
        "suite": "bias_evaluation",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "input": {
            "data_path": str(data_p),
            "format": "csv",
            **meta,
        },
        "results": results,
    }

    out_p = Path(output_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    with out_p.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Bias/Fairness Evaluation Suite (binary classification)")
    parser.add_argument("--data_path", required=True, help="CSV path with y_true, y_pred/y_score and sensitive column")
    parser.add_argument("--sensitive_col", required=True, help="Column name for sensitive attribute / group")
    parser.add_argument("--output_path", default="bias_evaluation_results/bias_report.json", help="Where to write JSON")

    parser.add_argument("--y_true_col", default="y_true")
    parser.add_argument("--y_pred_col", default="y_pred")
    parser.add_argument("--y_score_col", default="y_score")
    parser.add_argument("--threshold", type=float, default=0.5, help="Threshold for y_score -> y_pred")

    args = parser.parse_args()

    report = run_bias_suite(
        data_path=args.data_path,
        sensitive_col=args.sensitive_col,
        output_path=args.output_path,
        y_true_col=args.y_true_col,
        y_pred_col=args.y_pred_col,
        y_score_col=args.y_score_col,
        threshold=args.threshold,
    )

    fairness = report.get("results", {}).get("fairness", {})
    print("=" * 80)
    print("BIAS EVALUATION SUITE")
    print("=" * 80)
    print(f"Output: {args.output_path}")
    print(f"Groups: {', '.join(report.get('results', {}).get('groups', []))}")
    print("")
    print("Fairness summary:")
    for k in (
        "demographic_parity_difference",
        "demographic_parity_ratio",
        "equal_opportunity_difference",
        "false_positive_rate_difference",
        "equalized_odds_difference",
    ):
        print(f"  - {k}: {fairness.get(k)}")

