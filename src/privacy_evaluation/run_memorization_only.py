"""
Ejecuta solo la evaluación de memorización (exact duplicates) y escribe el JSON.
Útil para ver los conteos corregidos sin esperar la similitud semántica (~9 min).
"""
import argparse
import json
from pathlib import Path
from nearest_neighbor_memorization import (
    load_corpus,
    evaluate_memorization,
)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus_path", required=True, help="Ruta al corpus (ej. corpus_repo/corpus_v1)")
    parser.add_argument("--annotations_path", required=True, help="Ruta a entidades/")
    parser.add_argument("--output_path", default="memorization_detection.json")
    args = parser.parse_args()

    results = evaluate_memorization(
        corpus_path=args.corpus_path,
        annotations_path=args.annotations_path,
        output_path=args.output_path,
        skip_semantic=True,
    )
    print(f"Resultados guardados en {args.output_path}")
    print("Conteos exact_duplicates:")
    for cat, data in results.get("exact_duplicates", {}).items():
        print(f"  {cat}: total_repeated={data.get('total_repeated', 0)}")
