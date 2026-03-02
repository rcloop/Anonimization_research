"""
Canary Insertion Test for Privacy Leakage Detection
Inserts unique canary strings into training data and checks if they appear in generated outputs.
"""

import json
import os
import random
import string
import hashlib
from pathlib import Path
from typing import List, Dict, Tuple, Set
import argparse
import re


def generate_canary_string(length: int = 20, prefix: str = "CANARY") -> str:
    """
    Generate a unique canary string.
    
    Format: CANARY-<random_string>
    """
    random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))
    return f"{prefix}-{random_part}"


def generate_canary_entities(num_canaries: int = 10) -> Dict[str, List[str]]:
    """
    Generate canary entities of different types.
    
    Returns:
        Dictionary mapping entity types to lists of canary values
    """
    canaries = {
        'person': [],
        'date': [],
        'location': [],
        'id': [],
        'phone': [],
        'email': []
    }
    
    for i in range(num_canaries):
        # Person name canary
        canaries['person'].append(f"CANARY-PERSON-{i:04d}-{''.join(random.choices(string.ascii_uppercase, k=8))}")
        
        # Date canary
        day = random.randint(1, 28)
        month = random.randint(1, 12)
        year = random.randint(2000, 2020)
        canaries['date'].append(f"{day:02d}/{month:02d}/{year}-CANARY-{i:04d}")
        
        # Location canary
        canaries['location'].append(f"CALLE CANARY {i:04d} {''.join(random.choices(string.ascii_uppercase, k=6))}")
        
        # ID canary
        canaries['id'].append(f"CANARY-ID-{i:04d}-{''.join(random.choices(string.digits, k=10))}")
        
        # Phone canary
        canaries['phone'].append(f"+34-CANARY-{i:04d}-{''.join(random.choices(string.digits, k=9))}")
        
        # Email canary
        canaries['email'].append(f"canary.{i:04d}.{''.join(random.choices(string.ascii_lowercase, k=8))}@canary-test.com")
    
    return canaries


def insert_canaries_into_text(
    text: str,
    canaries: Dict[str, List[str]],
    insertion_rate: float = 0.1
) -> Tuple[str, Set[str]]:
    """
    Insert canary strings into text at random positions.
    
    Returns:
        Modified text and set of inserted canaries
    """
    inserted = set()
    modified_text = text
    
    # Decide which canary types to insert
    for entity_type, canary_list in canaries.items():
        if random.random() < insertion_rate and canary_list:
            canary = random.choice(canary_list)
            
            # Insert canary in a natural position
            # For person names: insert after "paciente" or "Dr."
            if entity_type == 'person':
                patterns = [r'\b(paciente|Dr\.|doctor|señor|señora)\s+', r'\.\s+']
                for pattern in patterns:
                    matches = list(re.finditer(pattern, modified_text, re.IGNORECASE))
                    if matches:
                        pos = random.choice(matches).end()
                        modified_text = modified_text[:pos] + canary + " " + modified_text[pos:]
                        inserted.add(canary)
                        break
            
            # For dates: insert after date-related words
            elif entity_type == 'date':
                patterns = [r'\b(fecha|nacimiento|admitido|fecha de)\s+', r'\.\s+']
                for pattern in patterns:
                    matches = list(re.finditer(pattern, modified_text, re.IGNORECASE))
                    if matches:
                        pos = random.choice(matches).end()
                        modified_text = modified_text[:pos] + canary + " " + modified_text[pos:]
                        inserted.add(canary)
                        break
            
            # For other types: insert at sentence boundaries
            else:
                sentences = re.split(r'([.!?]\s+)', modified_text)
                if len(sentences) > 1:
                    insert_pos = random.randint(0, len(sentences) - 1)
                    sentences[insert_pos] = sentences[insert_pos] + " " + canary + " "
                    modified_text = ''.join(sentences)
                    inserted.add(canary)
    
    return modified_text, inserted


def search_canaries_in_text(text: str, canaries: Dict[str, List[str]]) -> Set[str]:
    """
    Search for canary strings in text.
    
    Returns:
        Set of found canaries
    """
    found = set()
    text_lower = text.lower()
    
    for entity_type, canary_list in canaries.items():
        for canary in canary_list:
            # Exact match
            if canary.lower() in text_lower:
                found.add(canary)
            # Partial match (for dates/IDs that might be formatted differently)
            canary_base = canary.split('-CANARY-')[0] if '-CANARY-' in canary else canary
            if canary_base.lower() in text_lower and 'canary' in text_lower:
                found.add(canary)
    
    return found


def evaluate_canary_insertion(
    original_corpus_path: str,
    generated_corpus_path: str,
    num_canaries: int = 50,
    insertion_rate: float = 0.1,
    output_path: str = "canary_insertion_results.json"
) -> Dict:
    """
    Canary insertion evaluation.
    
    ⚠️ LIMITACIÓN IMPORTANTE:
    Este test requiere insertar canaries en los PROMPTS durante la generación,
    no en textos ya generados. Como el corpus ya está generado, este test
    solo puede hacer una simulación limitada que NO refleja memorización real.
    
    Para un test válido de canary insertion:
    1. Insertar canaries en los prompts/datos de entrada al modelo generativo
    2. Generar nuevos textos con esos canaries en los prompts
    3. Buscar si esos canaries aparecen en los textos generados
    
    Este test actual solo simula insertando canaries en textos ya generados,
    lo cual NO es un test válido de memorización.
    
    Args:
        original_corpus_path: Path to corpus (used as both original and generated for simulation)
        generated_corpus_path: Path to generated corpus (if None, uses original_corpus_path)
        num_canaries: Number of canaries per entity type
        insertion_rate: Probability of inserting a canary (not used in valid test)
        output_path: Path to save results
    """
    print("Generating canary strings...")
    canaries = generate_canary_entities(num_canaries)
    
    total_canaries = sum(len(v) for v in canaries.values())
    print(f"Generated {total_canaries} canary strings across {len(canaries)} entity types")
    
    def _documents_dir(path: str) -> str:
        p = Path(path)
        if p.is_dir() and (p / "documents").is_dir():
            return str(p / "documents")
        return path

    # Load original corpus
    print("Loading original corpus...")
    original_texts = []
    orig_dir = _documents_dir(original_corpus_path)
    if os.path.isdir(orig_dir):
        for txt_file in Path(orig_dir).glob("*.txt"):
            with open(txt_file, 'r', encoding='utf-8') as f:
                original_texts.append(f.read().strip())
    elif original_corpus_path.endswith('.json'):
        with open(original_corpus_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        original_texts.append(item.get('text', item.get('content', '')))
                    else:
                        original_texts.append(str(item))
    
    print(f"Loaded {len(original_texts)} original texts")
    
    # Insert canaries into original corpus
    # ⚠️ NOTE: This is a SIMULATION. Real canary insertion requires inserting canaries
    # in the generation prompts, not in already-generated texts.
    print(f"[SIMULATION] Inserting canaries into already-generated texts (rate: {insertion_rate})...")
    print("[WARNING] This is NOT a valid canary insertion test - canaries should be in generation prompts")
    texts_with_canaries = []
    all_inserted = set()
    
    for text in original_texts:
        modified_text, inserted = insert_canaries_into_text(text, canaries, insertion_rate)
        texts_with_canaries.append(modified_text)
        all_inserted.update(inserted)
    
    print(f"[SIMULATION] Inserted {len(all_inserted)} unique canaries into {len(texts_with_canaries)} texts")
    print("[WARNING] These canaries were NOT part of the generation process, so finding 0% is expected")
    
    # Load generated corpus
    print("Loading generated corpus...")
    generated_texts = []
    gen_dir = _documents_dir(generated_corpus_path) if generated_corpus_path else None
    if gen_dir and os.path.exists(gen_dir):
        if os.path.isdir(gen_dir):
            for txt_file in Path(gen_dir).glob("*.txt"):
                with open(txt_file, 'r', encoding='utf-8') as f:
                    generated_texts.append(f.read().strip())
        elif generated_corpus_path.endswith('.json'):
            with open(generated_corpus_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict):
                            generated_texts.append(item.get('text', item.get('content', '')))
                        else:
                            generated_texts.append(str(item))
    else:
        # If no generated corpus, use original (simulated test)
        print("[WARNING] No generated corpus provided, using original corpus")
        print("[WARNING] This is a SIMULATION only - not a valid canary insertion test")
        print("[WARNING] Valid canary insertion requires inserting canaries in generation prompts")
        generated_texts = original_texts
    
    print(f"Loaded {len(generated_texts)} generated texts")
    
    # Search for canaries in generated corpus
    print("Searching for canaries in generated corpus...")
    found_canaries = set()
    canary_occurrences = {}
    
    for text in generated_texts:
        found = search_canaries_in_text(text, canaries)
        found_canaries.update(found)
        for canary in found:
            if canary not in canary_occurrences:
                canary_occurrences[canary] = 0
            canary_occurrences[canary] += 1
    
    # Calculate leakage metrics
    leakage_rate = len(found_canaries) / len(all_inserted) if all_inserted else 0.0
    total_occurrences = sum(canary_occurrences.values())
    
    # Risk assessment
    risk_level = (
        'low' if leakage_rate < 0.01 else
        'medium' if leakage_rate < 0.05 else
        'high' if leakage_rate < 0.20 else
        'critical'
    )
    
    results = {
        'test_validity': {
            'is_valid_test': False,
            'limitation': 'Canaries were inserted into already-generated texts, not in generation prompts',
            'note': 'A valid canary insertion test requires inserting canaries in the generation pipeline and regenerating the corpus'
        },
        'canary_config': {
            'num_canaries_per_type': num_canaries,
            'total_canaries': total_canaries,
            'insertion_rate': insertion_rate
        },
        'insertion_stats': {
            'original_texts': len(original_texts),
            'texts_with_canaries': len(texts_with_canaries),
            'canaries_inserted': len(all_inserted),
            'note': 'Canaries inserted post-generation (simulation only)'
        },
        'leakage_detection': {
            'generated_texts_searched': len(generated_texts),
            'canaries_found': len(found_canaries),
            'total_occurrences': total_occurrences,
            'leakage_rate': leakage_rate,
            'found_canaries': list(found_canaries)[:20],  # Limit to first 20
            'canary_occurrences': dict(list(canary_occurrences.items())[:20]),
            'note': 'Finding 0% leakage is expected since canaries were not in generation prompts'
        },
        'risk_assessment': {
            'risk_level': risk_level,
            'interpretation': (
                "Low leakage risk. Minimal canary detection indicates good privacy protection."
                if leakage_rate < 0.01 else
                "Moderate leakage risk. Some canaries detected. Review generation process."
                if leakage_rate < 0.05 else
                "High leakage risk. Significant canary detection. Strongly recommend privacy-preserving techniques."
                if leakage_rate < 0.20 else
                "Critical leakage risk. Extensive canary detection. Immediate action required."
            ),
            'note': 'This assessment is based on a simulation and may not reflect actual memorization risk'
        }
    }
    
    # Save results
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n=== Canary Insertion Test Results ===")
    print(f"Canaries inserted: {len(all_inserted)}")
    print(f"Canaries found: {len(found_canaries)}")
    print(f"Leakage rate: {leakage_rate:.4f} ({leakage_rate*100:.2f}%)")
    print(f"Risk level: {risk_level}")
    print(f"\nResults saved to {output_path}")
    
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Canary Insertion Test for Privacy Leakage")
    parser.add_argument(
        "--original_corpus_path",
        type=str,
        required=True,
        help="Path to original corpus (where canaries will be inserted)"
    )
    parser.add_argument(
        "--generated_corpus_path",
        type=str,
        default=None,
        help="Path to generated corpus (to check for canary leakage)"
    )
    parser.add_argument(
        "--num_canaries",
        type=int,
        default=50,
        help="Number of canaries per entity type"
    )
    parser.add_argument(
        "--insertion_rate",
        type=float,
        default=0.1,
        help="Probability of inserting a canary into each text"
    )
    parser.add_argument(
        "--output_path",
        type=str,
        default="canary_insertion_results.json",
        help="Path to save results"
    )
    
    args = parser.parse_args()
    
    evaluate_canary_insertion(
        args.original_corpus_path,
        args.generated_corpus_path,
        args.num_canaries,
        args.insertion_rate,
        args.output_path
    )

