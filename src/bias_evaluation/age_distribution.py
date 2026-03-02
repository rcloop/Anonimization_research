"""
Metric 1.4 - Distribución de edades (AGE_OF_SUBJECT / EDAD_SUJETO_ASISTENCIA)

Qué:
  Histograma por décadas (0–9, 10–19, ...), porcentajes por bin, entropía (Shannon),
  y detección simple de infrarrepresentación (configurable).

Entrada:
  - Directorio `entidades/` con JSON por documento (formato MEDDOCAN-like):
      { "id": "...", "data": [ { "entity": "...", "text": "..." }, ... ] }
    o bien:
      { "entities": [ { "label": "...", "text": "..." }, ... ] }

Salida:
  - JSON con bins + métricas
  - (opcional) PNG con histograma (requiere matplotlib)
"""

from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from name_gender_distribution import iter_entities_from_annotation_obj


DEFAULT_AGE_LABELS = [
    # MEDDOCAN (es)
    "EDAD_SUJETO_ASISTENCIA",
    # english alias
    "AGE_OF_SUBJECT",
]


def parse_age(text: str) -> Optional[int]:
    """
    Extract age as integer from a string.
    Accepts patterns like: "85", "85 años", "Edad: 32", "32-year-old" (best-effort).
    """
    s = str(text).strip()
    if not s:
        return None

    # Prefer explicit 0-120 like numbers; avoid IDs by restricting magnitude.
    m = re.search(r"(?<!\d)(\d{1,3})(?!\d)", s)
    if not m:
        return None
    try:
        age = int(m.group(1))
    except Exception:
        return None
    if age < 0 or age > 120:
        return None
    return age


def decade_bin(age: int, max_decade: int = 120) -> str:
    """
    Returns a label like '0-9', '10-19', ..., '80-89', '90-99', '100-109', '110-119', '120+'.
    """
    if age >= max_decade:
        return f"{max_decade}+"
    start = (age // 10) * 10
    end = start + 9
    return f"{start}-{end}"


def shannon_entropy(counter: Counter) -> Dict[str, Optional[float]]:
    total = sum(counter.values())
    if total == 0:
        return {"entropy_bits": None, "normalized_entropy": None, "support": 0}
    h = 0.0
    for _, v in counter.items():
        p = v / total
        if p > 0:
            h -= p * math.log(p, 2)
    support = len(counter)
    h_norm = None
    if support > 1:
        h_norm = h / math.log(support, 2)
    return {
        "entropy_bits": float(h),
        "normalized_entropy": (float(h_norm) if h_norm is not None else None),
        "support": int(support),
    }


def make_histogram_plot(bins: List[str], percentages: List[float], out_path: Path) -> Optional[str]:
    try:
        import matplotlib.pyplot as plt  # type: ignore
    except Exception:
        return None

    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.bar(range(len(bins)), percentages)
    ax.set_xticks(range(len(bins)))
    ax.set_xticklabels(bins, rotation=30, ha="right")
    ax.set_ylabel("%")
    ax.set_title("Distribución de edades por décadas")
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=200)
    plt.close(fig)
    return str(out_path)


def evaluate_age_distribution(
    annotations_path: str,
    age_labels: Optional[List[str]] = None,
    max_files: Optional[int] = None,
    max_decade: int = 120,
    underrep_min_percent: float = 5.0,
    underrep_bins: Optional[List[str]] = None,
) -> Dict[str, Any]:
    p = Path(annotations_path)
    if not p.exists():
        raise FileNotFoundError(str(p))

    label_set = {l.upper().strip() for l in (age_labels or DEFAULT_AGE_LABELS)}

    ages_seen = 0
    ages_parsed = 0
    docs_seen = 0

    bin_counts: Counter = Counter()

    def handle_obj(obj: Any):
        nonlocal ages_seen, ages_parsed
        for lab, txt in iter_entities_from_annotation_obj(obj):
            lu = lab.upper().strip()
            if lu not in label_set:
                continue
            ages_seen += 1
            age = parse_age(txt)
            if age is None:
                continue
            ages_parsed += 1
            bin_counts[decade_bin(age, max_decade=max_decade)] += 1

    if p.is_dir():
        files = sorted(p.glob("*.json"))
        if max_files is not None:
            files = files[: max_files]
        for fp in files:
            docs_seen += 1
            try:
                obj = json.loads(fp.read_text(encoding="utf-8"))
            except Exception:
                continue
            handle_obj(obj)
    else:
        obj = json.loads(p.read_text(encoding="utf-8"))
        handle_obj(obj)

    # build ordered bins (0-9.., plus max_decade+)
    decade_starts = list(range(0, max_decade, 10))
    bins = [f"{s}-{s+9}" for s in decade_starts] + [f"{max_decade}+"]

    n = sum(bin_counts.values())
    percentages = [(bin_counts.get(b, 0) * 100.0 / n) if n else 0.0 for b in bins]

    underrep_bins = underrep_bins or [b for b in bins if b.startswith("80-") or b.startswith("90-") or b.endswith("+")]
    underrep = []
    for b in underrep_bins:
        pct = (bin_counts.get(b, 0) * 100.0 / n) if n else 0.0
        underrep.append(
            {
                "bin": b,
                "percent": pct,
                "flag_underrepresented": (pct < underrep_min_percent) if n else None,
                "threshold_percent": underrep_min_percent,
            }
        )

    return {
        "metric": "1.4_age_distribution",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "input_summary": {
            "annotations_path": str(annotations_path),
            "age_labels": sorted(label_set),
            "max_files": max_files,
            "docs_seen": docs_seen if p.is_dir() else None,
            "ages_entities_seen": ages_seen,
            "ages_parsed": ages_parsed,
            "max_decade": max_decade,
        },
        "histogram": {
            "bins": bins,
            "counts": [int(bin_counts.get(b, 0)) for b in bins],
            "percentages": percentages,
            "n": int(n),
        },
        "entropy": shannon_entropy(bin_counts),
        "underrepresentation_checks": underrep,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Metric 1.4 - Distribución de edades por décadas")
    parser.add_argument("--annotations_path", required=True, help="Ruta a entidades/ (directorio) o a un JSON")
    parser.add_argument("--max_files", type=int, default=None, help="Limita cantidad de JSON a leer (para pruebas)")
    parser.add_argument("--output_path", default="bias_evaluation_results/age_distribution.json")
    parser.add_argument("--make_plot", action="store_true", help="Genera histograma PNG (requiere matplotlib)")
    parser.add_argument("--plot_path", default="bias_evaluation_results/age_distribution_hist.png")
    parser.add_argument("--underrep_min_percent", type=float, default=5.0)
    args = parser.parse_args()

    result = evaluate_age_distribution(
        annotations_path=args.annotations_path,
        max_files=args.max_files,
        underrep_min_percent=args.underrep_min_percent,
    )

    out_p = Path(args.output_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    out_p.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    plot_written = None
    if args.make_plot:
        plot_written = make_histogram_plot(
            bins=result["histogram"]["bins"],
            percentages=result["histogram"]["percentages"],
            out_path=Path(args.plot_path),
        )
    result["plot_path"] = plot_written
    if args.make_plot and plot_written is None:
        result["plot_warning"] = "Plot requested but matplotlib is not available."
        out_p.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    print("=" * 80)
    print("METRIC 1.4 - AGE DISTRIBUTION")
    print("=" * 80)
    print(f"Output: {out_p}")
    if plot_written:
        print(f"Plot: {plot_written}")
    print("Entropy:", result["entropy"])

