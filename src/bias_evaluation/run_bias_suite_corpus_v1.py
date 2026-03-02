"""
Run bias evaluation metrics (1.1–1.6) on corpus_v1.

Designed to mirror privacy suite style: run multiple metrics and write a consolidated report.
Supports running on the first N documents (sorted by filename) for quick checks.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from age_distribution import evaluate_age_distribution
from diagnosis_condition_bias import evaluate_diagnosis_bias
from geographic_toponymic_bias import evaluate_geographic_toponymic_bias
from institution_bias import evaluate_institution_bias
from name_gender_distribution import DEFAULT_TARGET_LABELS, evaluate_name_gender_distribution
from role_profession_gender_bias import evaluate_role_profession_gender_bias


def _write_json(path: Path, obj: Dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")
    return str(path)


def run_suite(
    corpus_root: str,
    output_dir: str = "bias_evaluation_results_suite",
    max_docs: Optional[int] = 10,
    make_plots: bool = False,
    lexicon_path: Optional[str] = None,
    diagnosis_reference_path: Optional[str] = None,
) -> Dict[str, Any]:
    root = Path(corpus_root)
    entidades_dir = root / "entidades"
    documents_dir = root / "documents"

    if not entidades_dir.is_dir():
        raise FileNotFoundError(f"No se encontró entidades/: {entidades_dir}")
    if not documents_dir.is_dir():
        raise FileNotFoundError(f"No se encontró documents/: {documents_dir}")

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    suite_meta = {
        "suite": "bias_suite_corpus_v1",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "corpus_root": str(root),
        "paths": {"entidades": str(entidades_dir), "documents": str(documents_dir)},
        "max_docs": max_docs,
        "make_plots": make_plots,
        "lexicon_path": lexicon_path,
        "diagnosis_reference_path": diagnosis_reference_path,
    }

    results: Dict[str, Any] = {"meta": suite_meta, "metrics": {}}

    # 1.1
    m11 = evaluate_name_gender_distribution(
        annotations_path=str(entidades_dir),
        target_labels=DEFAULT_TARGET_LABELS,
        lexicon_path=lexicon_path,
        max_files=max_docs,
    )
    m11_path = _write_json(out_dir / "1_1_name_gender_distribution.json", m11)
    results["metrics"]["1.1_name_gender_distribution"] = {"output_path": m11_path, "result": m11}

    # 1.2
    m12 = evaluate_role_profession_gender_bias(
        annotations_path=str(entidades_dir),
        lexicon_path=lexicon_path,
        max_files=max_docs,
        association_mode="cartesian",
    )
    m12_path = _write_json(out_dir / "1_2_role_profession_gender_bias.json", m12)
    results["metrics"]["1.2_role_profession_gender_bias"] = {"output_path": m12_path, "result": m12}

    # 1.3
    m13 = evaluate_geographic_toponymic_bias(
        annotations_path=str(entidades_dir),
        top_k=20,
        max_files=max_docs,
    )
    m13_path = _write_json(out_dir / "1_3_geographic_toponymic_bias.json", m13)
    results["metrics"]["1.3_geographic_toponymic_bias"] = {"output_path": m13_path, "result": m13}

    # 1.4
    m14 = evaluate_age_distribution(
        annotations_path=str(entidades_dir),
        max_files=max_docs,
        underrep_min_percent=5.0,
    )
    m14_path = _write_json(out_dir / "1_4_age_distribution.json", m14)
    results["metrics"]["1.4_age_distribution"] = {"output_path": m14_path, "result": m14}

    # 1.5
    m15 = evaluate_institution_bias(
        annotations_path=str(entidades_dir),
        top_k=20,
        max_files=max_docs,
    )
    m15_path = _write_json(out_dir / "1_5_institution_bias.json", m15)
    results["metrics"]["1.5_institution_bias"] = {"output_path": m15_path, "result": m15}

    # 1.6
    m16 = evaluate_diagnosis_bias(
        documents_path=str(documents_dir),
        reference_path=diagnosis_reference_path,
        top_k=20,
        max_files=max_docs,
        use_sections=True,
        use_phrases=True,
    )
    m16_path = _write_json(out_dir / "1_6_diagnosis_condition_bias.json", m16)
    results["metrics"]["1.6_diagnosis_condition_bias"] = {"output_path": m16_path, "result": m16}

    # Consolidated
    consolidated_path = _write_json(out_dir / "consolidated_bias_report.json", results)
    return {"output_dir": str(out_dir), "consolidated_path": consolidated_path, "report": results}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run bias suite (1.1–1.6) on corpus_v1")
    parser.add_argument("--corpus_root", required=True, help="Ruta a corpus_v1 (con documents/ y entidades/)")
    parser.add_argument("--output_dir", default="bias_evaluation_results_suite")
    parser.add_argument("--max_docs", type=int, default=10, help="Cantidad de archivos a procesar (ordenados por nombre)")
    parser.add_argument("--make_plots", action="store_true", help="(placeholder) plots are run per-metric scripts")
    parser.add_argument("--lexicon_path", default=None, help="CSV/JSON opcional nombre->género (para 1.1/1.2)")
    parser.add_argument("--diagnosis_reference_path", default=None, help="CSV/JSON con distribución de referencia (1.6)")
    args = parser.parse_args()

    out = run_suite(
        corpus_root=args.corpus_root,
        output_dir=args.output_dir,
        max_docs=args.max_docs,
        make_plots=args.make_plots,
        lexicon_path=args.lexicon_path,
        diagnosis_reference_path=args.diagnosis_reference_path,
    )

    print("=" * 80)
    print("BIAS SUITE (1.1–1.6) COMPLETADA")
    print("=" * 80)
    print(f"Output dir: {out['output_dir']}")
    print(f"Consolidated: {out['consolidated_path']}")
