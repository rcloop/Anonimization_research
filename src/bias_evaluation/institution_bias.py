"""
Metric 1.5 - Sesgo en instituciones (HOSPITAL/INSTITUCION/CENTRO_SALUD/HEALTH_CENTER)

Qué:
  Top-k instituciones sintéticas y métricas de concentración:
  - HHI (Herfindahl-Hirschman Index): sum(p_i^2)
  - Gini: desigualdad en frecuencias
  - Curva de Lorenz (opcional plot)

Entrada:
  - Directorio `entidades/` con JSON por documento (formato MEDDOCAN-like).

Salida:
  - JSON con top-k, HHI, Gini y datos de Lorenz
  - (opcional) PNG con curva de Lorenz (requiere matplotlib)
"""

from __future__ import annotations

import argparse
import json
import math
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from name_gender_distribution import iter_entities_from_annotation_obj


DEFAULT_INSTITUTION_LABELS = [
    # MEDDOCAN-ish
    "HOSPITAL",
    "INSTITUCION",
    "CENTRO_SALUD",
    # common variants / english aliases
    "INSTITUTION",
    "HEALTH_CENTER",
    "HEALTHCARE_CENTER",
]


def _strip_accents(s: str) -> str:
    return "".join(ch for ch in unicodedata.normalize("NFD", s) if unicodedata.category(ch) != "Mn")


def normalize_institution(s: str) -> str:
    s = _strip_accents(str(s)).upper().strip()
    s = re.sub(r"\s+", " ", s)
    return s


def hhi(counter: Counter) -> Optional[float]:
    total = sum(counter.values())
    if total == 0:
        return None
    return float(sum((v / total) ** 2 for v in counter.values()))


def gini(counter: Counter) -> Optional[float]:
    """
    Gini coefficient over frequency distribution.
    Computed on counts sorted ascending.
    """
    xs = sorted([v for v in counter.values() if v > 0])
    n = len(xs)
    if n == 0:
        return None
    s = sum(xs)
    if s == 0:
        return None
    cum = 0.0
    for i, x in enumerate(xs, start=1):
        cum += i * x
    g = (2 * cum) / (n * s) - (n + 1) / n
    return float(g)


def lorenz_points(counter: Counter) -> Dict[str, Any]:
    """
    Returns Lorenz curve points for institutions:
    x = cumulative share of institutions (sorted by frequency ascending)
    y = cumulative share of mentions
    """
    xs = sorted([v for v in counter.values() if v > 0])
    n = len(xs)
    total = sum(xs)
    if n == 0 or total == 0:
        return {"x": [], "y": [], "n_items": n, "total": total}

    x = [0.0]
    y = [0.0]
    cum = 0.0
    for i, v in enumerate(xs, start=1):
        cum += v
        x.append(i / n)
        y.append(cum / total)
    return {"x": x, "y": y, "n_items": n, "total": total}


def make_lorenz_plot(points: Dict[str, Any], out_path: Path) -> Optional[str]:
    try:
        import matplotlib.pyplot as plt  # type: ignore
    except Exception:
        return None

    x = points.get("x", [])
    y = points.get("y", [])
    fig, ax = plt.subplots(figsize=(5.5, 5.5))
    ax.plot(x, y, label="Lorenz")
    ax.plot([0, 1], [0, 1], linestyle="--", label="Igualdad")
    ax.set_xlabel("Proporción acumulada de instituciones")
    ax.set_ylabel("Proporción acumulada de menciones")
    ax.set_title("Curva de concentración (Lorenz) - instituciones")
    ax.legend()
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=200)
    plt.close(fig)
    return str(out_path)


def evaluate_institution_bias(
    annotations_path: str,
    institution_labels: Optional[List[str]] = None,
    top_k: int = 20,
    max_files: Optional[int] = None,
) -> Dict[str, Any]:
    p = Path(annotations_path)
    if not p.exists():
        raise FileNotFoundError(str(p))

    label_set = {l.upper().strip() for l in (institution_labels or DEFAULT_INSTITUTION_LABELS)}

    counts_by_label: Dict[str, Counter] = defaultdict(Counter)
    overall = Counter()
    docs_seen = 0
    ents_seen = 0
    ents_matched = 0

    def handle_obj(obj: Any):
        nonlocal ents_seen, ents_matched
        for lab, txt in iter_entities_from_annotation_obj(obj):
            ents_seen += 1
            lu = lab.upper().strip()
            if lu not in label_set:
                continue
            ents_matched += 1
            val = normalize_institution(txt)
            if not val:
                continue
            counts_by_label[lu][val] += 1
            overall[val] += 1

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

    points = lorenz_points(overall)

    per_label_out = {}
    for lab in sorted(label_set):
        c = counts_by_label.get(lab, Counter())
        per_label_out[lab] = {
            "top_k": c.most_common(top_k),
            "n": int(sum(c.values())),
            "hhi": hhi(c),
            "gini": gini(c),
        }

    return {
        "metric": "1.5_institution_bias",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "input_summary": {
            "annotations_path": str(annotations_path),
            "institution_labels": sorted(label_set),
            "top_k": top_k,
            "max_files": max_files,
            "docs_seen": docs_seen if p.is_dir() else None,
            "entities_seen_total": ents_seen,
            "entities_matched_total": ents_matched,
        },
        "overall": {
            "top_k": overall.most_common(top_k),
            "n": int(sum(overall.values())),
            "hhi": hhi(overall),
            "gini": gini(overall),
            "lorenz": points,
        },
        "per_label": per_label_out,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Metric 1.5 - Sesgo en instituciones (concentración)")
    parser.add_argument("--annotations_path", required=True, help="Ruta a entidades/ (directorio) o a un JSON")
    parser.add_argument("--top_k", type=int, default=20)
    parser.add_argument("--max_files", type=int, default=None, help="Limita cantidad de JSON a leer (para pruebas)")
    parser.add_argument("--output_path", default="bias_evaluation_results/institution_bias.json")
    parser.add_argument("--make_plot", action="store_true", help="Genera curva de Lorenz PNG (requiere matplotlib)")
    parser.add_argument("--plot_path", default="bias_evaluation_results/institution_lorenz.png")
    args = parser.parse_args()

    result = evaluate_institution_bias(
        annotations_path=args.annotations_path,
        top_k=args.top_k,
        max_files=args.max_files,
    )

    out_p = Path(args.output_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    out_p.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    plot_written = None
    if args.make_plot:
        plot_written = make_lorenz_plot(result["overall"]["lorenz"], out_path=Path(args.plot_path))
    result["plot_path"] = plot_written
    if args.make_plot and plot_written is None:
        result["plot_warning"] = "Plot requested but matplotlib is not available."
        out_p.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    print("=" * 80)
    print("METRIC 1.5 - INSTITUTION BIAS")
    print("=" * 80)
    print(f"Output: {out_p}")
    if plot_written:
        print(f"Plot: {plot_written}")
    print("Overall HHI:", result["overall"]["hhi"])
    print("Overall Gini:", result["overall"]["gini"])

