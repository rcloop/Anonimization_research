"""
Metric 1.3 - Sesgo geográfico / toponímico

Qué:
  Distribución de topónimos por labels geográficos (p.ej., TERRITORIO/PAIS/CALLE/CIUDAD...).

Salida:
  - top-k territorios por label + overall
  - entropía de Shannon (bits) para diversidad geográfica
  - (opcional) gráfico de barras (requiere matplotlib)
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
from typing import Any, Dict, Iterable, List, Optional, Tuple

from name_gender_distribution import iter_entities_from_annotation_obj


DEFAULT_GEO_LABELS = [
    # MEDDOCAN-ish (es)
    "TERRITORIO",
    "PAIS",
    "CALLE",
    "HOSPITAL",
    "CENTRO_SALUD",
    "INSTITUCION",
    # potential extras if appear
    "CIUDAD",
    "POBLACION",
    "PROVINCIA",
    "COMUNIDAD_AUTONOMA",
    # english aliases (if appear)
    "TERRITORY",
    "COUNTRY",
    "STREET",
    "CITY",
    "PROVINCE",
    "REGION",
]


def _strip_accents(s: str) -> str:
    return "".join(ch for ch in unicodedata.normalize("NFD", s) if unicodedata.category(ch) != "Mn")


def normalize_toponym(s: str) -> str:
    s = _strip_accents(str(s)).upper().strip()
    s = re.sub(r"\s+", " ", s)
    return s


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
    return {"entropy_bits": float(h), "normalized_entropy": (float(h_norm) if h_norm is not None else None), "support": int(support)}


def load_geo_counts(annotations_path: str, labels: List[str], max_files: Optional[int] = None) -> Tuple[Dict[str, Counter], Counter, Dict[str, Any]]:
    p = Path(annotations_path)
    if not p.exists():
        raise FileNotFoundError(str(p))

    label_set = {l.upper().strip() for l in labels}
    per_label: Dict[str, Counter] = defaultdict(Counter)
    overall = Counter()

    docs_seen = 0
    ents_seen = 0
    ents_matched = 0

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
            for lab, txt in iter_entities_from_annotation_obj(obj):
                ents_seen += 1
                lu = lab.upper().strip()
                if lu not in label_set:
                    continue
                ents_matched += 1
                val = normalize_toponym(txt)
                if not val:
                    continue
                per_label[lu][val] += 1
                overall[val] += 1
    else:
        obj = json.loads(p.read_text(encoding="utf-8"))
        for lab, txt in iter_entities_from_annotation_obj(obj):
            ents_seen += 1
            lu = lab.upper().strip()
            if lu not in label_set:
                continue
            ents_matched += 1
            val = normalize_toponym(txt)
            if not val:
                continue
            per_label[lu][val] += 1
            overall[val] += 1

    meta = {
        "docs_seen": docs_seen if p.is_dir() else None,
        "entities_seen_total": ents_seen,
        "entities_matched_total": ents_matched,
    }
    return per_label, overall, meta


def make_bar_plot(counter: Counter, title: str, out_path: Path, top_k: int = 20) -> Optional[str]:
    try:
        import matplotlib.pyplot as plt  # type: ignore
    except Exception:
        return None

    most = counter.most_common(top_k)
    labels = [k for k, _ in most]
    values = [v for _, v in most]

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(range(len(labels)), values)
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=30, ha="right")
    ax.set_ylabel("Conteo")
    ax.set_title(title)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=200)
    plt.close(fig)
    return str(out_path)


def evaluate_geographic_toponymic_bias(
    annotations_path: str,
    geo_labels: Optional[List[str]] = None,
    top_k: int = 20,
    max_files: Optional[int] = None,
) -> Dict[str, Any]:
    labels = geo_labels or DEFAULT_GEO_LABELS
    per_label, overall, meta = load_geo_counts(annotations_path=annotations_path, labels=labels, max_files=max_files)

    per_label_out = {}
    for lab in sorted({l.upper().strip() for l in labels}):
        c = per_label.get(lab, Counter())
        per_label_out[lab] = {
            "top_k": c.most_common(top_k),
            "entropy": shannon_entropy(c),
            "n": int(sum(c.values())),
        }

    return {
        "metric": "1.3_geographic_toponymic_bias",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "input_summary": {
            "annotations_path": str(annotations_path),
            "geo_labels": sorted({l.upper().strip() for l in labels}),
            "top_k": top_k,
            "max_files": max_files,
            **meta,
        },
        "overall": {"top_k": overall.most_common(top_k), "entropy": shannon_entropy(overall), "n": int(sum(overall.values()))},
        "per_label": per_label_out,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Metric 1.3 - Sesgo geográfico/toponímico (top-k + entropía)")
    parser.add_argument("--annotations_path", required=True, help="Ruta a entidades/ (directorio) o a un JSON")
    parser.add_argument("--top_k", type=int, default=20)
    parser.add_argument("--max_files", type=int, default=None, help="Limita cantidad de JSON a leer (para pruebas)")
    parser.add_argument("--output_path", default="bias_evaluation_results/geographic_toponymic_bias.json")
    parser.add_argument("--make_plot", action="store_true", help="Genera barra top-k (requiere matplotlib)")
    parser.add_argument("--plot_path", default="bias_evaluation_results/geographic_toponymic_topk.png")
    args = parser.parse_args()

    result = evaluate_geographic_toponymic_bias(
        annotations_path=args.annotations_path,
        top_k=args.top_k,
        max_files=args.max_files,
    )

    out_p = Path(args.output_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    out_p.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    plot_written = None
    if args.make_plot:
        plot_written = make_bar_plot(
            counter=Counter(dict(result["overall"]["top_k"])),
            title="Top-K topónimos (overall)",
            out_path=Path(args.plot_path),
            top_k=args.top_k,
        )
    result["plot_path"] = plot_written
    if args.make_plot and plot_written is None:
        result["plot_warning"] = "Plot requested but matplotlib is not available."
        out_p.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    print("=" * 80)
    print("METRIC 1.3 - GEOGRAPHIC/TOPONYMIC BIAS")
    print("=" * 80)
    print(f"Output: {out_p}")
    if plot_written:
        print(f"Plot: {plot_written}")
    print("Overall entropy:", result["overall"]["entropy"])

