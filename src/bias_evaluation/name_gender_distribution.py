"""
Metric 1.1 - Distribución de género en nombres (sintéticos)

Qué:
  Proporción masculino/femenino/otros-no-determinable en entidades de nombre.

Entrada:
  - Directorio `entidades/` con JSON por documento (formato MEDDOCAN-like):
      { "id": "...", "data": [ { "entity": "...", "text": "..." }, ... ] }
    o bien:
      { "entities": [ { "label": "...", "text": "..." }, ... ] }
  - También acepta un único archivo JSON con lista de entidades.

Salida:
  - JSON con conteos y proporciones por tipo de entidad
  - (opcional) PNG con barras apiladas por tipo
  - (opcional) prueba χ² contra uniformidad (si `scipy` está disponible)
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


DEFAULT_TARGET_LABELS = [
    # MEDDOCAN (es)
    "NOMBRE_SUJETO_ASISTENCIA",
    "NOMBRE_PERSONAL_SANITARIO",
    # english aliases (if they appear)
    "NAME_OF_ASSISTED_SUBJECT",
    "NAME_OF_HEALTHCARE_PERSONNEL",
]


def _strip_accents(s: str) -> str:
    return "".join(ch for ch in unicodedata.normalize("NFD", s) if unicodedata.category(ch) != "Mn")


def normalize_name(s: str) -> str:
    s = _strip_accents(str(s)).upper().strip()
    s = re.sub(r"[^A-Z\s'-]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def extract_first_name(full_name: str) -> Optional[str]:
    """
    Heurística:
    - toma el primer token, pero preserva combinaciones comunes (MARIA JOSE, JOSE MARIA).
    """
    n = normalize_name(full_name)
    if not n:
        return None
    parts = n.split(" ")
    if not parts:
        return None
    if len(parts) >= 2 and parts[0] in {"MARIA", "JOSE", "JESUS"}:
        return f"{parts[0]} {parts[1]}"
    return parts[0]


def load_lexicon(path: Optional[str]) -> Dict[str, str]:
    """
    Lexicon mapping normalized first-name -> gender label: 'fem' or 'masc'.
    Accepted formats:
    - CSV with columns: name, gender (gender in {f,m,fem,masc})
    - JSON dict: { "MARIA": "fem", "JOSE": "masc", ... }
    """
    base = {
        "MARIA": "fem",
        "MARIA JOSE": "fem",
        "JOSE": "masc",
        "JOSE MARIA": "masc",
        "ANA": "fem",
        "LUIS": "masc",
        "CARMEN": "fem",
        "JUAN": "masc",
    }
    if not path:
        return base

    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(str(p))

    if p.suffix.lower() == ".json":
        data = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("Lexicon JSON must be a dict of name->gender.")
        for k, v in data.items():
            nk = normalize_name(k)
            gv = str(v).strip().lower()
            if gv in {"f", "fem", "female"}:
                base[nk] = "fem"
            elif gv in {"m", "masc", "male"}:
                base[nk] = "masc"
        return base

    if p.suffix.lower() in {".csv", ".tsv"}:
        delim = "\t" if p.suffix.lower() == ".tsv" else ","
        with p.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f, delimiter=delim)
            if not reader.fieldnames:
                raise ValueError("Lexicon CSV has no header.")
            fields = [c.strip().lower() for c in reader.fieldnames]
            if "name" not in fields or "gender" not in fields:
                raise ValueError("Lexicon CSV must have columns: name, gender")
            for row in reader:
                name = normalize_name(row.get("name", ""))
                gender = str(row.get("gender", "")).strip().lower()
                if not name:
                    continue
                if gender in {"f", "fem", "female"}:
                    base[name] = "fem"
                elif gender in {"m", "masc", "male"}:
                    base[name] = "masc"
        return base

    raise ValueError(f"Unsupported lexicon format: {p.suffix}")


def infer_gender(first_name: Optional[str], lexicon: Dict[str, str]) -> str:
    if not first_name:
        return "other"
    key = normalize_name(first_name)
    if key in lexicon:
        return lexicon[key]

    # very lightweight heuristic fallback
    if key.endswith("A"):
        return "fem"
    if key.endswith("O") or key.endswith("OS"):
        return "masc"
    return "other"


def iter_entities_from_annotation_obj(obj: Any) -> Iterable[Tuple[str, str]]:
    """
    Yields (label, text) pairs from supported annotation JSON shapes.
    """
    if isinstance(obj, dict):
        if "data" in obj and isinstance(obj["data"], list):
            for item in obj["data"]:
                if isinstance(item, dict):
                    label = str(item.get("entity", "")).strip()
                    text = str(item.get("text", item.get("value", ""))).strip()
                    if label and text:
                        yield (label, text)
        if "entities" in obj and isinstance(obj["entities"], list):
            for item in obj["entities"]:
                if isinstance(item, dict):
                    label = str(item.get("label", item.get("type", ""))).strip()
                    text = str(item.get("text", item.get("value", ""))).strip()
                    if label and text:
                        yield (label, text)
    elif isinstance(obj, list):
        # list of entities
        for item in obj:
            if isinstance(item, dict):
                label = str(item.get("entity_label", item.get("entity", item.get("label", "")))).strip()
                text = str(item.get("entity_text", item.get("text", item.get("value", "")))).strip()
                if label and text:
                    yield (label, text)


def load_entities(annotations_path: str, max_files: Optional[int] = None) -> List[Tuple[str, str]]:
    p = Path(annotations_path)
    if not p.exists():
        raise FileNotFoundError(str(p))

    pairs: List[Tuple[str, str]] = []
    if p.is_dir():
        files = sorted(p.glob("*.json"))
        if max_files is not None:
            files = files[: max_files]
        for fp in files:
            try:
                obj = json.loads(fp.read_text(encoding="utf-8"))
            except Exception:
                # ignore broken files, but keep going
                continue
            pairs.extend(list(iter_entities_from_annotation_obj(obj)))
        return pairs

    # single file
    obj = json.loads(p.read_text(encoding="utf-8"))
    pairs.extend(list(iter_entities_from_annotation_obj(obj)))
    return pairs


def chi_square_uniformity(counts: Dict[str, int]) -> Dict[str, Optional[float]]:
    """
    χ² against uniform distribution across present categories.
    Returns statistic and (if scipy available) p_value.
    """
    observed = [counts.get(k, 0) for k in ("fem", "masc", "other")]
    total = sum(observed)
    if total == 0:
        return {"chi2": None, "p_value": None, "df": None}
    k = 3
    expected = total / k
    chi2 = 0.0
    for o in observed:
        chi2 += ((o - expected) ** 2) / expected

    p_value = None
    try:
        from scipy.stats import chi2 as chi2_dist  # type: ignore

        p_value = float(chi2_dist.sf(chi2, df=k - 1))
    except Exception:
        p_value = None

    return {"chi2": float(chi2), "p_value": p_value, "df": float(k - 1)}


def make_stacked_bar_plot(result: Dict[str, Any], out_path: Path) -> Optional[str]:
    try:
        import matplotlib.pyplot as plt  # type: ignore
    except Exception:
        return None

    per_label = result["per_label"]
    labels = list(per_label.keys())
    fem = [per_label[l]["proportions"]["p_fem"] for l in labels]
    masc = [per_label[l]["proportions"]["p_masc"] for l in labels]
    oth = [per_label[l]["proportions"]["p_other"] for l in labels]

    x = range(len(labels))
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.bar(x, fem, label="fem")
    ax.bar(x, masc, bottom=fem, label="masc")
    ax.bar(x, oth, bottom=[fem[i] + masc[i] for i in range(len(labels))], label="other/ND")
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, rotation=15, ha="right")
    ax.set_ylim(0, 1.0)
    ax.set_ylabel("Proporción")
    ax.set_title("Distribución de género inferido por tipo de entidad (nombres)")
    ax.legend(loc="upper right")
    fig.tight_layout()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=200)
    plt.close(fig)
    return str(out_path)


def evaluate_name_gender_distribution(
    annotations_path: str,
    target_labels: List[str],
    lexicon_path: Optional[str] = None,
    max_files: Optional[int] = None,
) -> Dict[str, Any]:
    lexicon = load_lexicon(lexicon_path)
    entities = load_entities(annotations_path=annotations_path, max_files=max_files)

    target_set = {t.upper().strip() for t in target_labels}

    counts_by_label: Dict[str, Counter] = defaultdict(Counter)
    total_seen = 0
    total_matched = 0

    for label, text in entities:
        total_seen += 1
        lu = label.upper().strip()
        if lu not in target_set:
            continue
        total_matched += 1
        first = extract_first_name(text)
        g = infer_gender(first, lexicon)
        counts_by_label[lu][g] += 1

    def props(c: Counter) -> Dict[str, float]:
        n = sum(c.values())
        if n == 0:
            return {"p_fem": 0.0, "p_masc": 0.0, "p_other": 0.0}
        return {
            "p_fem": c.get("fem", 0) / n,
            "p_masc": c.get("masc", 0) / n,
            "p_other": c.get("other", 0) / n,
        }

    per_label: Dict[str, Any] = {}
    overall_counter: Counter = Counter()
    for lu in sorted(target_set):
        c = counts_by_label.get(lu, Counter())
        overall_counter.update(c)
        p = props(c)
        chi = chi_square_uniformity({"fem": c.get("fem", 0), "masc": c.get("masc", 0), "other": c.get("other", 0)})

        # imbalance check (>70/30) only on determinable fem/masc
        det = c.get("fem", 0) + c.get("masc", 0)
        p_max_det = None
        if det > 0:
            p_max_det = max(c.get("fem", 0), c.get("masc", 0)) / det

        per_label[lu] = {
            "counts": {"fem": c.get("fem", 0), "masc": c.get("masc", 0), "other": c.get("other", 0), "n": sum(c.values())},
            "proportions": p,
            "chi_square_uniformity": chi,
            "determinable": {
                "n_fem_masc": det,
                "p_max_over_fem_masc": p_max_det,
                "flag_extreme_imbalance_70_30": (p_max_det is not None and p_max_det > 0.7),
            },
        }

    overall = {
        "counts": {"fem": overall_counter.get("fem", 0), "masc": overall_counter.get("masc", 0), "other": overall_counter.get("other", 0), "n": sum(overall_counter.values())},
        "proportions": props(overall_counter),
        "chi_square_uniformity": chi_square_uniformity(
            {"fem": overall_counter.get("fem", 0), "masc": overall_counter.get("masc", 0), "other": overall_counter.get("other", 0)}
        ),
    }

    return {
        "metric": "1.1_name_gender_distribution",
        "input_summary": {
            "annotations_path": str(annotations_path),
            "target_labels": sorted(list(target_set)),
            "max_files": max_files,
            "entities_seen_total": total_seen,
            "entities_matched_total": total_matched,
            "lexicon_path": lexicon_path,
            "lexicon_entries": len(lexicon),
        },
        "overall": overall,
        "per_label": per_label,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Metric 1.1 - Distribución de género en nombres (sintéticos)")
    parser.add_argument("--annotations_path", required=True, help="Ruta a entidades/ (directorio) o a un JSON")
    parser.add_argument(
        "--labels",
        nargs="+",
        default=DEFAULT_TARGET_LABELS,
        help="Entity labels a incluir (default: nombres sujeto/personal sanitario + aliases en inglés)",
    )
    parser.add_argument("--lexicon_path", default=None, help="CSV/JSON opcional con mapeo nombre->género")
    parser.add_argument("--max_files", type=int, default=None, help="Limita cantidad de JSON a leer (para pruebas)")
    parser.add_argument("--output_path", default="bias_evaluation_results/name_gender_distribution.json")
    parser.add_argument("--plot_path", default="bias_evaluation_results/name_gender_distribution_stacked.png")
    parser.add_argument("--make_plot", action="store_true", help="Genera PNG con barras apiladas (requiere matplotlib)")

    args = parser.parse_args()

    result = evaluate_name_gender_distribution(
        annotations_path=args.annotations_path,
        target_labels=args.labels,
        lexicon_path=args.lexicon_path,
        max_files=args.max_files,
    )
    result["timestamp_utc"] = datetime.now(timezone.utc).isoformat()

    out_p = Path(args.output_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    out_p.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    plot_written = None
    if args.make_plot:
        plot_written = make_stacked_bar_plot(result, Path(args.plot_path))
    result["plot_path"] = plot_written
    if args.make_plot and plot_written is None:
        result["plot_warning"] = "Plot requested but matplotlib is not available."
        out_p.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    print("=" * 80)
    print("METRIC 1.1 - NAME GENDER DISTRIBUTION")
    print("=" * 80)
    print(f"Output: {out_p}")
    if plot_written:
        print(f"Plot: {plot_written}")
    print("")
    for label, info in result["per_label"].items():
        p = info["proportions"]
        print(f"{label}: p_fem={p['p_fem']:.3f} p_masc={p['p_masc']:.3f} p_other={p['p_other']:.3f} (n={info['counts']['n']})")

