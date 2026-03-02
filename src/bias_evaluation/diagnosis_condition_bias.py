"""
Metric 1.6 - Sesgo en diagnósticos/condiciones (si hay secciones clínicas)

Qué:
  - top-k diagnósticos/condiciones extraídos de `documents/*.txt`
  - (opcional) compara contra una distribución de referencia y calcula divergencia Jensen-Shannon

Nota:
  En este corpus las etiquetas PHI (MEDDOCAN/CARMEN-I) no incluyen diagnósticos como entidad,
  así que este métrico funciona por extracción textual (heurística) en secciones/frases.

Salida:
  - JSON con top-k + entropía + JSD (si reference)
  - (opcional) PNG bar chart (requiere matplotlib)
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


DEFAULT_SECTION_PATTERNS: List[re.Pattern] = [
    re.compile(r"(?im)^\s*(diagn[oó]stico(?:s)?|impresi[oó]n diagn[oó]stica|dx)\s*[:\-]\s*(.+?)\s*$"),
]

DEFAULT_PHRASE_PATTERNS: List[re.Pattern] = [
    re.compile(r"(?i)diagn[oó]stic[oa]?\s+de\s+([^\.\n;]{3,140})"),
    re.compile(r"(?i)compatible\s+con\s+([^\.\n;]{3,140})"),
    re.compile(r"(?i)sugestiv[oa]\s+de\s+([^\.\n;]{3,140})"),
]


def _strip_accents(s: str) -> str:
    return "".join(ch for ch in unicodedata.normalize("NFD", s) if unicodedata.category(ch) != "Mn")


def normalize_dx(s: str) -> str:
    s = _strip_accents(str(s)).upper().strip()
    s = re.sub(r"[\t\r]+", " ", s)
    s = re.sub(r"[\"'“”‘’]+", "", s)
    s = re.sub(r"[\(\)\[\]\{\}]", " ", s)
    s = re.sub(r"[^A-Z0-9ÁÉÍÓÚÑ\s\-/]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    # remove common leading fillers
    s = re.sub(r"^(DE|DEL|LA|EL|LOS|LAS)\s+", "", s).strip()
    return s


def split_candidates(text: str) -> List[str]:
    """
    Split a diagnosis candidate string into multiple items.
    """
    raw = str(text).strip()
    if not raw:
        return []
    parts = re.split(r"\s*(?:;|,|\bY\b|\bE\b|/|\|)\s*", raw, flags=re.IGNORECASE)
    out = []
    for p in parts:
        n = normalize_dx(p)
        if len(n) < 3:
            continue
        out.append(n)
    return out


def extract_diagnoses_from_text(
    text: str,
    use_sections: bool = True,
    use_phrases: bool = True,
) -> List[str]:
    candidates: List[str] = []
    lines = text.splitlines()

    if use_sections:
        for line in lines:
            for pat in DEFAULT_SECTION_PATTERNS:
                m = pat.match(line)
                if m:
                    candidates.append(m.group(2).strip())

    if use_phrases:
        for pat in DEFAULT_PHRASE_PATTERNS:
            for m in pat.finditer(text):
                candidates.append(m.group(1).strip())

    dx: List[str] = []
    for cand in candidates:
        dx.extend(split_candidates(cand))
    return dx


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


def load_reference_distribution(path: Optional[str]) -> Optional[Dict[str, float]]:
    if not path:
        return None
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(str(p))

    if p.suffix.lower() == ".json":
        obj = json.loads(p.read_text(encoding="utf-8"))
        ref: Dict[str, float] = {}
        if isinstance(obj, dict):
            for k, v in obj.items():
                try:
                    ref[normalize_dx(k)] = float(v)
                except Exception:
                    continue
        elif isinstance(obj, list):
            for item in obj:
                if isinstance(item, dict):
                    k = item.get("diagnosis", item.get("dx", item.get("name")))
                    v = item.get("p", item.get("prob", item.get("probability", item.get("weight"))))
                    if k is None or v is None:
                        continue
                    try:
                        ref[normalize_dx(str(k))] = float(v)
                    except Exception:
                        continue
        else:
            raise ValueError("Reference JSON must be dict or list of objects.")
        return _normalize_prob(ref)

    if p.suffix.lower() in {".csv", ".tsv"}:
        delim = "\t" if p.suffix.lower() == ".tsv" else ","
        with p.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f, delimiter=delim)
            if not reader.fieldnames:
                raise ValueError("Reference CSV has no header.")
            fields = [c.strip().lower() for c in reader.fieldnames]
            if "diagnosis" not in fields and "dx" not in fields and "name" not in fields:
                raise ValueError("Reference CSV needs a diagnosis-like column: diagnosis/dx/name")
            if "p" not in fields and "prob" not in fields and "probability" not in fields and "weight" not in fields:
                raise ValueError("Reference CSV needs a probability-like column: p/prob/probability/weight")

            def get_col(row: Dict[str, Any], candidates: List[str]) -> Any:
                for c in candidates:
                    if c in row and row[c] not in (None, ""):
                        return row[c]
                return None

            ref: Dict[str, float] = {}
            for row in reader:
                d = get_col(row, ["diagnosis", "dx", "name"])
                w = get_col(row, ["p", "prob", "probability", "weight"])
                if d is None or w is None:
                    continue
                try:
                    ref[normalize_dx(str(d))] = float(w)
                except Exception:
                    continue
        return _normalize_prob(ref)

    raise ValueError(f"Unsupported reference format: {p.suffix}")


def _normalize_prob(d: Dict[str, float]) -> Dict[str, float]:
    s = sum(v for v in d.values() if v is not None and v >= 0)
    if s <= 0:
        return {}
    return {k: float(v) / s for k, v in d.items() if v is not None and v >= 0}


def js_divergence(p: Dict[str, float], q: Dict[str, float]) -> Optional[float]:
    """
    Jensen-Shannon divergence in bits, over union support.
    """
    if not p or not q:
        return None
    keys = sorted(set(p.keys()) | set(q.keys()))
    P = [p.get(k, 0.0) for k in keys]
    Q = [q.get(k, 0.0) for k in keys]
    M = [(P[i] + Q[i]) / 2.0 for i in range(len(keys))]

    def kl(A: List[float], B: List[float]) -> float:
        s = 0.0
        for a, b in zip(A, B):
            if a <= 0 or b <= 0:
                continue
            s += a * math.log(a / b, 2)
        return s

    return 0.5 * (kl(P, M) + kl(Q, M))


def make_topk_plot(
    obs: Dict[str, float],
    top_k: int,
    out_path: Path,
    reference: Optional[Dict[str, float]] = None,
) -> Optional[str]:
    try:
        import matplotlib.pyplot as plt  # type: ignore
    except Exception:
        return None

    items = sorted(obs.items(), key=lambda kv: kv[1], reverse=True)[:top_k]
    labels = [k for k, _ in items]
    values = [v for _, v in items]

    fig, ax = plt.subplots(figsize=(11, 5))
    ax.bar(range(len(labels)), values, label="observado")

    if reference:
        ref_vals = [reference.get(k, 0.0) for k in labels]
        ax.plot(range(len(labels)), ref_vals, marker="o", linestyle="--", label="referencia")

    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=30, ha="right")
    ax.set_ylabel("Proporción")
    ax.set_title(f"Top-{top_k} diagnósticos/condiciones (proporción)")
    ax.legend()
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=200)
    plt.close(fig)
    return str(out_path)


def evaluate_diagnosis_bias(
    documents_path: str,
    reference_path: Optional[str] = None,
    top_k: int = 20,
    max_files: Optional[int] = None,
    use_sections: bool = True,
    use_phrases: bool = True,
) -> Dict[str, Any]:
    p = Path(documents_path)
    if not p.exists():
        raise FileNotFoundError(str(p))

    counts = Counter()
    docs_seen = 0
    docs_with_dx = 0
    extracted_total = 0

    if p.is_dir():
        files = sorted(p.glob("*.txt"))
        if max_files is not None:
            files = files[: max_files]
        for fp in files:
            docs_seen += 1
            try:
                text = fp.read_text(encoding="utf-8")
            except Exception:
                continue
            dx = extract_diagnoses_from_text(text, use_sections=use_sections, use_phrases=use_phrases)
            if dx:
                docs_with_dx += 1
                extracted_total += len(dx)
                counts.update(dx)
    else:
        text = p.read_text(encoding="utf-8")
        dx = extract_diagnoses_from_text(text, use_sections=use_sections, use_phrases=use_phrases)
        extracted_total += len(dx)
        counts.update(dx)

    total = sum(counts.values())
    obs_prob = {k: v / total for k, v in counts.items()} if total else {}

    ref = load_reference_distribution(reference_path)
    jsd = js_divergence(obs_prob, ref) if ref else None

    return {
        "metric": "1.6_diagnosis_condition_bias",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "input_summary": {
            "documents_path": str(documents_path),
            "reference_path": reference_path,
            "top_k": top_k,
            "max_files": max_files,
            "use_sections": use_sections,
            "use_phrases": use_phrases,
            "docs_seen": docs_seen if p.is_dir() else None,
            "docs_with_diagnosis_extracted": docs_with_dx if p.is_dir() else None,
            "diagnosis_mentions_extracted": extracted_total,
        },
        "overall": {
            "n_unique": int(len(counts)),
            "n_total_mentions": int(total),
            "entropy": shannon_entropy(counts),
        },
        "top_k": counts.most_common(top_k),
        "js_divergence_bits": jsd,
        "reference_summary": {
            "provided": bool(ref),
            "reference_support": (len(ref) if ref else 0),
        },
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Metric 1.6 - Sesgo en diagnósticos/condiciones (top-k + JSD opcional)")
    parser.add_argument("--documents_path", required=True, help="Ruta a documents/ (directorio) o a un .txt")
    parser.add_argument("--reference_path", default=None, help="CSV/JSON con distribución de referencia (diagnosis->p)")
    parser.add_argument("--top_k", type=int, default=20)
    parser.add_argument("--max_files", type=int, default=None, help="Limita cantidad de .txt a leer (para pruebas)")
    parser.add_argument("--no_sections", action="store_true", help="Desactiva extracción por headers tipo 'Diagnóstico:'")
    parser.add_argument("--no_phrases", action="store_true", help="Desactiva extracción por frases tipo 'diagnóstico de ...'")
    parser.add_argument("--output_path", default="bias_evaluation_results/diagnosis_condition_bias.json")
    parser.add_argument("--make_plot", action="store_true", help="Genera barra top-k (requiere matplotlib)")
    parser.add_argument("--plot_path", default="bias_evaluation_results/diagnosis_topk.png")
    args = parser.parse_args()

    result = evaluate_diagnosis_bias(
        documents_path=args.documents_path,
        reference_path=args.reference_path,
        top_k=args.top_k,
        max_files=args.max_files,
        use_sections=not args.no_sections,
        use_phrases=not args.no_phrases,
    )

    out_p = Path(args.output_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    out_p.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    plot_written = None
    if args.make_plot:
        # reconstruct obs prob for plotting from top_k + totals
        total = result["overall"]["n_total_mentions"]
        obs_prob = {k: (v / total) for k, v in (Counter(dict(result["top_k"])) if total else Counter()).items()}  # type: ignore
        ref = load_reference_distribution(args.reference_path)
        plot_written = make_topk_plot(obs=obs_prob, top_k=args.top_k, out_path=Path(args.plot_path), reference=ref)

    result["plot_path"] = plot_written
    if args.make_plot and plot_written is None:
        result["plot_warning"] = "Plot requested but matplotlib is not available."
        out_p.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    print("=" * 80)
    print("METRIC 1.6 - DIAGNOSIS/CONDITION BIAS")
    print("=" * 80)
    print(f"Output: {out_p}")
    print("Total mentions extracted:", result["overall"]["n_total_mentions"])
    print("JSD (bits):", result["js_divergence_bits"])

