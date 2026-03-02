"""
Single-file runner for the privacy evaluation suite (no canary).

This script executes the evaluations directly (without calling the other runner):
  1) Membership inference
  2) Attribute inference
  3) Memorization detection (exact + optional semantic similarity)

Always skips:
  - Canary insertion
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Optional

from attribute_inference import evaluate_attribute_inference
from membership_inference import evaluate_membership_inference
from nearest_neighbor_memorization import evaluate_memorization


def _repo_root() -> Path:
    # repo_root/src/privacy_evaluation/run_suite_no_canary.py -> repo_root
    return Path(__file__).resolve().parents[2]


def _default_corpus_path() -> Optional[Path]:
    root = _repo_root()
    candidates = [
        root / "corpus_repo" / "corpus_v1",
        root / "corpus_repo" / "corpus",
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


def _default_output_dir(corpus_path: Path) -> Path:
    # Keep outputs next to the suite for easy discovery.
    suite_dir = Path(__file__).resolve().parent
    name = corpus_path.name or "corpus"
    return suite_dir / f"privacy_evaluation_results_{name}_no_canary"


def _risk_level_from_score(score: float) -> str:
    if score >= 0.8:
        return "critical"
    if score >= 0.7:
        return "high"
    if score >= 0.6:
        return "medium"
    return "low"


def _generate_overall_risk_assessment(results: dict) -> dict:
    risk_scores: list[float] = []
    risk_details: list[dict] = []

    mi = results.get("membership_inference", {})
    if isinstance(mi, dict) and "attack_metrics" in mi:
        mi_auc = float(mi.get("attack_metrics", {}).get("auc_roc", 0.5) or 0.5)
        risk_scores.append(mi_auc)
        risk_details.append(
            {
                "test": "membership_inference",
                "score": mi_auc,
                "risk": "high" if mi_auc >= 0.7 else "medium" if mi_auc >= 0.6 else "low",
            }
        )

    ai = results.get("attribute_inference", {})
    if isinstance(ai, dict) and "overall_risk" in ai:
        ai_max = float(ai.get("overall_risk", {}).get("max_auc_roc", 0.5) or 0.5)
        risk_scores.append(ai_max)
        risk_details.append(
            {
                "test": "attribute_inference",
                "score": ai_max,
                "risk": "high" if ai_max >= 0.7 else "medium" if ai_max >= 0.6 else "low",
            }
        )

    mem = results.get("memorization_detection", {})
    if isinstance(mem, dict) and "memorization_risk" in mem:
        mem_risk = mem.get("memorization_risk", {}) or {}
        total_repeated = float(mem_risk.get("total_repeated_phi_entities", 0) or 0)
        high_sim = float(mem_risk.get("high_similarity_pairs", 0) or 0)
        mem_score = min(1.0, (total_repeated / 200.0 + high_sim / 100.0) / 2.0)
        risk_scores.append(mem_score)
        risk_details.append(
            {
                "test": "memorization",
                "score": mem_score,
                "risk": str(mem_risk.get("risk_level", _risk_level_from_score(mem_score))),
            }
        )

    if risk_scores:
        max_risk = max(risk_scores)
        mean_risk = sum(risk_scores) / len(risk_scores)
        overall = _risk_level_from_score(max_risk)
    else:
        overall = "unknown"
        max_risk = 0.0
        mean_risk = 0.0

    return {
        "overall_risk_level": overall,
        "max_risk_score": max_risk,
        "mean_risk_score": mean_risk,
        "individual_risks": risk_details,
        "recommendation": (
            "Critical privacy risk detected. Immediate action required: implement differential "
            "privacy, review and redesign generation pipeline, and conduct thorough privacy audit."
            if overall == "critical"
            else "High privacy risk detected. Strongly recommend implementing differential privacy "
            "or other privacy-preserving mechanisms. Review generation pipeline for potential memorization issues."
            if overall == "high"
            else "Moderate privacy risk detected. Consider implementing additional privacy-preserving techniques."
            if overall == "medium"
            else "Low overall privacy risk detected. Continue monitoring."
            if overall == "low"
            else "Insufficient data to generate recommendation."
        ),
    }


def _print_summary(consolidated: dict) -> None:
    overall = consolidated.get("overall_risk_assessment", {}) or {}
    print("\n" + "-" * 80)
    print("SUMMARY")
    print("-" * 80)
    print(f"Overall Risk Level: {str(overall.get('overall_risk_level', 'unknown')).upper()}")
    print(f"Max Risk Score: {float(overall.get('max_risk_score', 0.0) or 0.0):.4f}")
    print(f"Mean Risk Score: {float(overall.get('mean_risk_score', 0.0) or 0.0):.4f}")
    print()
    print("Individual Test Results:")
    for risk in overall.get("individual_risks", []) or []:
        test = risk.get("test", "unknown")
        rlevel = str(risk.get("risk", "unknown")).upper()
        score = float(risk.get("score", 0.0) or 0.0)
        print(f"  - {test}: {rlevel} (score: {score:.4f})")
    print()
    print("Recommendation:")
    print(f"  {overall.get('recommendation', 'N/A')}")
    print()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run privacy evaluation suite (no canary insertion)."
    )
    parser.add_argument(
        "--corpus_path",
        type=str,
        default=None,
        help=(
            "Path to corpus (directory or .json file). "
            "If omitted, tries repo-local defaults (e.g. corpus_repo/corpus_v1)."
        ),
    )
    parser.add_argument(
        "--annotations_path",
        type=str,
        default=None,
        help=(
            "Path to annotations (optional). "
            "If omitted and corpus_path is a directory, tries <corpus_path>/entidades."
        ),
    )
    parser.add_argument(
        "--external_corpus_path",
        type=str,
        default=None,
        help="Path to external corpus for membership inference (optional).",
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default=None,
        help="Output directory for results (optional).",
    )
    parser.add_argument(
        "--semantic_model",
        type=str,
        default="paraphrase-multilingual-MiniLM-L12-v2",
        help="Sentence transformer model for semantic similarity.",
    )
    parser.add_argument(
        "--skip_semantic",
        action="store_true",
        help="Skip semantic similarity search (memorization exact-only).",
    )

    args = parser.parse_args()

    corpus_path = Path(args.corpus_path) if args.corpus_path else _default_corpus_path()
    if corpus_path is None:
        parser.error(
            "--corpus_path is required when no default corpus exists in the repo."
        )
    corpus_path = corpus_path.resolve()

    annotations_path: Optional[Path]
    if args.annotations_path:
        annotations_path = Path(args.annotations_path).resolve()
    else:
        annotations_path = (corpus_path / "entidades") if corpus_path.is_dir() else None

    output_dir = (
        Path(args.output_dir).resolve()
        if args.output_dir
        else _default_output_dir(corpus_path)
    )

    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("PRIVACY EVALUATION SUITE (NO CANARY)")
    print("=" * 80)
    print(f"Corpus: {corpus_path}")
    print(f"Annotations: {annotations_path if annotations_path else '[none]'}")
    print(f"Output directory: {output_dir}")
    print(f"Semantic similarity: {'SKIPPED' if args.skip_semantic else 'ENABLED'}")
    print()

    all_results: dict = {}

    print("\n" + "=" * 80)
    print("1. MEMBERSHIP INFERENCE EVALUATION")
    print("=" * 80)
    try:
        mi_results = evaluate_membership_inference(
            corpus_path=str(corpus_path),
            external_corpus_path=args.external_corpus_path,
            output_path=str(output_dir / "membership_inference.json"),
        )
        all_results["membership_inference"] = mi_results
    except Exception as e:
        print(f"Error in membership inference: {e}")
        all_results["membership_inference"] = {"error": str(e)}

    print("\n" + "=" * 80)
    print("2. ATTRIBUTE INFERENCE EVALUATION")
    print("=" * 80)
    try:
        ai_results = evaluate_attribute_inference(
            corpus_path=str(corpus_path),
            annotations_path=str(annotations_path) if annotations_path else None,
            output_path=str(output_dir / "attribute_inference.json"),
        )
        all_results["attribute_inference"] = ai_results
    except Exception as e:
        print(f"Error in attribute inference: {e}")
        all_results["attribute_inference"] = {"error": str(e)}

    print("\n" + "=" * 80)
    print("3. MEMORIZATION DETECTION (NEAREST NEIGHBOR)")
    print("=" * 80)
    if args.skip_semantic:
        print("[WARNING] Similitud semantica deshabilitada (solo busqueda exacta)")
    try:
        mem_results = evaluate_memorization(
            corpus_path=str(corpus_path),
            annotations_path=str(annotations_path) if annotations_path else None,
            output_path=str(output_dir / "memorization_detection.json"),
            semantic_model=args.semantic_model,
            skip_semantic=args.skip_semantic,
        )
        all_results["memorization_detection"] = mem_results
    except Exception as e:
        print(f"Error in memorization detection: {e}")
        all_results["memorization_detection"] = {"error": str(e)}

    print("\n" + "=" * 80)
    print("4. CANARY INSERTION TEST")
    print("=" * 80)
    print("[SKIPPED] Canary insertion test skipped (this runner is no-canary).")
    all_results["canary_insertion"] = {
        "skipped": True,
        "reason": "No-canary runner",
    }

    consolidated = {
        "corpus_info": {
            "corpus_path": str(corpus_path),
            "corpus_size": all_results.get("membership_inference", {}).get(
                "corpus_size", "unknown"
            ),
        },
        "evaluations": all_results,
        "overall_risk_assessment": _generate_overall_risk_assessment(all_results),
    }

    consolidated_path = output_dir / "consolidated_privacy_report.json"
    with open(consolidated_path, "w", encoding="utf-8") as f:
        json.dump(consolidated, f, indent=2, ensure_ascii=False)

    print(f"\nConsolidated report saved to: {consolidated_path}")
    _print_summary(consolidated)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

