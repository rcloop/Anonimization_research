"""
Metric 1.2 - Sesgo rol-profesión vs género

Qué:
  Matriz de contingencia (género x rol/profesión) a partir de anotaciones.

Lectura de anotaciones:
  - Directorio `entidades/` con JSON por documento (formato MEDDOCAN-like):
      { "id": "...", "data": [ { "entity": "...", "text": "..." }, ... ] }
    o bien:
      { "entities": [ { "label": "...", "text": "..." }, ... ] }

Estrategia:
  - Género: inferido desde `NOMBRE_PERSONAL_SANITARIO` (o alias en inglés) usando la heurística/lexicón de 1.1.
  - Rol/profesión:
      - Preferente: entidad `PROFESION` (o aliases).
      - Fallback: tokens de rol en el texto del nombre (p.ej., "DRA", "DR", "ENFERMERA").
  - Asociación: por documento. Si un doc tiene múltiples nombres y múltiples profesiones,
    por defecto se contabiliza el producto cartesiano (cada nombre con cada rol encontrado).

Salida:
  - JSON con contingency table, razones de prevalencia por género y χ² de independencia.
  - (opcional) heatmap PNG (requiere matplotlib).
"""

from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from name_gender_distribution import (
    DEFAULT_TARGET_LABELS,
    extract_first_name,
    infer_gender,
    iter_entities_from_annotation_obj,
    load_entities,
    load_lexicon,
    normalize_name,
)


DEFAULT_PROFESSION_LABELS = [
    # MEDDOCAN
    "PROFESION",
    # potential english alias
    "PROFESSION",
]

# Canonical role categories (extendable)
ROLE_PATTERNS: List[Tuple[str, re.Pattern]] = [
    ("doctor", re.compile(r"\b(MEDIC[OA]|DOCTOR[AE]?|DRA|DR)\b", re.IGNORECASE)),
    ("nurse", re.compile(r"\b(ENFERMER[OA]|ENF\.)\b", re.IGNORECASE)),
    ("assistant", re.compile(r"\b(AUXILIAR|CELADOR[AE]?|TCAE)\b", re.IGNORECASE)),
    ("technician", re.compile(r"\b(TECNIC[OA]|T[ÉE]CNICO)\b", re.IGNORECASE)),
    ("administrative", re.compile(r"\b(ADMINISTRATIV[OA]|SECRETARI[OA])\b", re.IGNORECASE)),
    ("pharmacist", re.compile(r"\b(FARMAC[ÉE]UTIC[OA])\b", re.IGNORECASE)),
    ("psychologist", re.compile(r"\b(PSIC[ÓO]LOG[OA])\b", re.IGNORECASE)),
]


def infer_role_from_text(text: str) -> str:
    t = normalize_name(text)
    if not t:
        return "other"
    for role, pat in ROLE_PATTERNS:
        if pat.search(t):
            return role
    return "other"


def chi_square_independence(table: List[List[int]]) -> Dict[str, Optional[float]]:
    """
    Chi-square test of independence.
    Returns chi2, df and (if scipy available) p_value.
    """
    r = len(table)
    c = len(table[0]) if r else 0
    if r == 0 or c == 0:
        return {"chi2": None, "p_value": None, "df": None}

    row_sums = [sum(row) for row in table]
    col_sums = [sum(table[i][j] for i in range(r)) for j in range(c)]
    total = sum(row_sums)
    if total == 0:
        return {"chi2": None, "p_value": None, "df": None}

    chi2 = 0.0
    for i in range(r):
        for j in range(c):
            expected = (row_sums[i] * col_sums[j]) / total
            if expected > 0:
                chi2 += ((table[i][j] - expected) ** 2) / expected

    df = (r - 1) * (c - 1)
    p_value = None
    try:
        from scipy.stats import chi2 as chi2_dist  # type: ignore

        p_value = float(chi2_dist.sf(chi2, df=df))
    except Exception:
        p_value = None

    return {"chi2": float(chi2), "p_value": p_value, "df": float(df)}


def prevalence_ratios(
    counts: Dict[str, Counter],
    genders: List[str],
    roles: List[str],
    ref_gender: str = "masc",
) -> Dict[str, Any]:
    """
    For each role, compute prevalence p(role | gender) and PR = p(role|gender)/p(role|ref_gender).
    Uses determinable genders only (fem/masc by default).
    """
    out: Dict[str, Any] = {}

    totals_by_gender = {g: sum(counts[g].values()) for g in genders}
    for role in roles:
        per_gender = {}
        ref_p = None
        for g in genders:
            den = totals_by_gender.get(g, 0)
            p = (counts[g].get(role, 0) / den) if den else None
            per_gender[g] = p
            if g == ref_gender:
                ref_p = p

        pr = {}
        for g in genders:
            p = per_gender[g]
            if ref_p is None or ref_p == 0 or p is None:
                pr[g] = None
            else:
                pr[g] = p / ref_p

        out[role] = {"prevalence": per_gender, "prevalence_ratio_vs_ref": pr, "ref_gender": ref_gender}
    return out


def make_heatmap(
    table: List[List[int]],
    row_labels: List[str],
    col_labels: List[str],
    out_path: Path,
) -> Optional[str]:
    try:
        import matplotlib.pyplot as plt  # type: ignore
        import numpy as np  # type: ignore
    except Exception:
        return None

    arr = np.array(table, dtype=float)
    fig, ax = plt.subplots(figsize=(max(6, 1 + 0.7 * len(col_labels)), 3.8))
    im = ax.imshow(arr, aspect="auto")
    ax.set_xticks(list(range(len(col_labels))))
    ax.set_yticks(list(range(len(row_labels))))
    ax.set_xticklabels(col_labels, rotation=25, ha="right")
    ax.set_yticklabels(row_labels)
    ax.set_title("Contingencia: género × rol/profesión (conteos)")
    fig.colorbar(im, ax=ax, shrink=0.8)

    # annotate
    for i in range(arr.shape[0]):
        for j in range(arr.shape[1]):
            ax.text(j, i, str(int(arr[i, j])), ha="center", va="center", fontsize=9, color="white" if arr[i, j] > arr.max() * 0.5 else "black")

    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=200)
    plt.close(fig)
    return str(out_path)


def evaluate_role_profession_gender_bias(
    annotations_path: str,
    name_labels: Optional[List[str]] = None,
    profession_labels: Optional[List[str]] = None,
    lexicon_path: Optional[str] = None,
    max_files: Optional[int] = None,
    association_mode: str = "cartesian",  # cartesian | first
) -> Dict[str, Any]:
    name_labels_u = [l.upper().strip() for l in (name_labels or DEFAULT_TARGET_LABELS) if l]
    profession_labels_u = [l.upper().strip() for l in (profession_labels or DEFAULT_PROFESSION_LABELS) if l]
    lexicon = load_lexicon(lexicon_path)

    # Load raw entities as pairs (label,text) but we need doc boundaries to associate.
    p = Path(annotations_path)
    if not p.exists():
        raise FileNotFoundError(str(p))

    counts: Dict[str, Counter] = defaultdict(Counter)  # gender -> Counter(role)
    docs_seen = 0
    docs_used = 0

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
            pairs = list(iter_entities_from_annotation_obj(obj))
            names = [t for (lab, t) in pairs if lab.upper().strip() in set(name_labels_u)]
            profs = [t for (lab, t) in pairs if lab.upper().strip() in set(profession_labels_u)]

            if not names:
                continue

            genders = []
            for n in names:
                g = infer_gender(extract_first_name(n), lexicon)
                genders.append(g)

            roles = []
            for pr in profs:
                roles.append(infer_role_from_text(pr))
            if not roles:
                # fallback: infer role from name string itself
                roles = [infer_role_from_text(n) for n in names]

            if not roles:
                continue
            docs_used += 1

            if association_mode == "first":
                for g in genders[:1]:
                    counts[g][roles[0]] += 1
            else:
                for g in genders:
                    for r in roles:
                        counts[g][r] += 1
    else:
        # Single file mode: no doc boundaries => just compute role from PROFESION entities and gender from NAME entities independently.
        entities = load_entities(str(p), max_files=None)
        names = [t for (lab, t) in entities if lab.upper().strip() in set(name_labels_u)]
        profs = [t for (lab, t) in entities if lab.upper().strip() in set(profession_labels_u)]
        for n in names:
            g = infer_gender(extract_first_name(n), lexicon)
            if profs:
                for pr in profs:
                    counts[g][infer_role_from_text(pr)] += 1
            else:
                counts[g][infer_role_from_text(n)] += 1

    # Build table (rows = genders, cols = roles)
    row_labels = ["fem", "masc", "other"]
    role_set = set()
    for g in row_labels:
        role_set.update(counts[g].keys())
    col_labels = sorted(role_set)
    table = [[int(counts[g].get(r, 0)) for r in col_labels] for g in row_labels]

    chi = chi_square_independence(table)
    pr = prevalence_ratios(counts, genders=["fem", "masc"], roles=col_labels, ref_gender="masc")

    return {
        "metric": "1.2_role_profession_vs_gender",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "input_summary": {
            "annotations_path": str(annotations_path),
            "name_labels": name_labels_u,
            "profession_labels": profession_labels_u,
            "lexicon_path": lexicon_path,
            "max_files": max_files,
            "association_mode": association_mode,
            "docs_seen": docs_seen if p.is_dir() else None,
            "docs_used": docs_used if p.is_dir() else None,
        },
        "contingency": {
            "row_labels": row_labels,
            "col_labels": col_labels,
            "table": table,
            "counts_by_gender": {g: dict(counts[g]) for g in row_labels},
        },
        "chi_square_independence": chi,
        "prevalence_ratios": pr,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Metric 1.2 - Sesgo rol-profesión vs género")
    parser.add_argument("--annotations_path", required=True, help="Ruta a entidades/ (directorio) o a un JSON")
    parser.add_argument("--lexicon_path", default=None, help="CSV/JSON opcional con mapeo nombre->género")
    parser.add_argument("--max_files", type=int, default=None, help="Limita cantidad de JSON a leer (para pruebas)")
    parser.add_argument("--association_mode", choices=["cartesian", "first"], default="cartesian")
    parser.add_argument("--output_path", default="bias_evaluation_results/role_profession_gender_bias.json")
    parser.add_argument("--plot_path", default="bias_evaluation_results/role_profession_gender_heatmap.png")
    parser.add_argument("--make_plot", action="store_true", help="Genera heatmap PNG (requiere matplotlib)")
    args = parser.parse_args()

    result = evaluate_role_profession_gender_bias(
        annotations_path=args.annotations_path,
        lexicon_path=args.lexicon_path,
        max_files=args.max_files,
        association_mode=args.association_mode,
    )

    out_p = Path(args.output_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    out_p.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    plot_written = None
    if args.make_plot:
        plot_written = make_heatmap(
            table=result["contingency"]["table"],
            row_labels=result["contingency"]["row_labels"],
            col_labels=result["contingency"]["col_labels"],
            out_path=Path(args.plot_path),
        )
    if args.make_plot and plot_written is None:
        result["plot_warning"] = "Plot requested but matplotlib is not available."
        out_p.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    result["plot_path"] = plot_written

    # Console summary
    print("=" * 80)
    print("METRIC 1.2 - ROLE/PROFESSION VS GENDER")
    print("=" * 80)
    print(f"Output: {out_p}")
    if plot_written:
        print(f"Plot: {plot_written}")
    print("")
    print("Chi-square independence:", result["chi_square_independence"])
    print("Roles:", ", ".join(result["contingency"]["col_labels"]))

