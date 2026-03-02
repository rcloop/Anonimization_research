"""
Nearest Neighbor Search for Memorization Detection
Detects potential memorization of names/identifiers through semantic and exact similarity search.
"""

import json
import os
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple, Set
import argparse
from collections import Counter
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
import hashlib
from meddocan_label_mapping import map_meddocan_to_phi


def _documents_dir(corpus_path: str) -> str:
    """If corpus_path is a corpus root with documents/ subdir, return path to documents."""
    p = Path(corpus_path)
    if p.is_dir() and (p / "documents").is_dir():
        return str(p / "documents")
    return corpus_path


def load_corpus(corpus_path: str) -> List[Tuple[str, str, str]]:
    """
    Load corpus texts.
    
    Returns:
        List of (text, filename, doc_id) tuples
    """
    texts = []
    corpus_path = _documents_dir(corpus_path)
    
    if os.path.isdir(corpus_path):
        for file_path in Path(corpus_path).glob("*.txt"):
            with open(file_path, 'r', encoding='utf-8') as f:
                texts.append((f.read().strip(), file_path.name, file_path.stem))
    elif corpus_path.endswith('.json'):
        with open(corpus_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, list):
                for i, item in enumerate(data):
                    if isinstance(item, dict):
                        text = item.get('text', item.get('content', ''))
                        doc_id = item.get('id', f"doc_{i}")
                        texts.append((text, f"doc_{i}.json", doc_id))
                    else:
                        texts.append((str(item), f"doc_{i}.json", f"doc_{i}"))
    
    return texts


def extract_phi_entities(text: str, annotations: Dict = None) -> Dict[str, List[str]]:
    """
    Extract PHI entities (names, IDs, dates, etc.) from text.
    When annotations are present, only annotation-based extraction is used for PHI
    to avoid double-counting and misclassification (e.g. locations captured as "person" by regex).
    
    Returns:
        Dictionary mapping entity types to lists of entity values (unique per document).
    """
    entities = {
        'person': [],
        'date': [],
        'location': [],
        'id': [],
        'age': [],
        'phone': [],
        'email': []
    }
    has_annotation_entities = False
    
    # Extract from annotations if available
    if annotations:
        if isinstance(annotations, dict):
            # Handle format with "data" array (from entidades JSON files)
            if 'data' in annotations and isinstance(annotations['data'], list):
                for entity_item in annotations['data']:
                    if isinstance(entity_item, dict):
                        entity_type = entity_item.get('entity', '').strip()
                        value = entity_item.get('text', entity_item.get('value', ''))
                        
                        if not value:
                            continue
                        has_annotation_entities = True
                        
                        # Map MEDDOCAN label to generic PHI category
                        phi_category = map_meddocan_to_phi(entity_type)
                        
                        if phi_category in entities:
                            entities[phi_category].append(value)
            
            # Handle format with "entities" array
            ann_entities = annotations.get('entities', [])
            for entity in ann_entities:
                if isinstance(entity, dict):
                    label = entity.get('label', entity.get('type', '')).strip()
                    value = entity.get('text', entity.get('value', ''))
                    
                    if not value:
                        continue
                    has_annotation_entities = True
                    
                    # Map MEDDOCAN label to generic PHI category
                    phi_category = map_meddocan_to_phi(label)
                    
                    if phi_category in entities:
                        entities[phi_category].append(value)
    
    # Pattern-based extraction (fallback only when no annotations, to avoid double count and noise)
    if has_annotation_entities:
        for key in entities:
            entities[key] = list(set(entities[key]))
        return entities
    
    # Regex fallback when document has no annotations
    # Person names (capitalized words, 2-4 words)
    person_pattern = r'\b([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+){1,3})\b'
    persons = re.findall(person_pattern, text)
    entities['person'].extend([p.strip() for p in persons if len(p.split()) >= 2])
    
    # Dates
    date_patterns = [
        r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',
        r'\b\d{1,2}\s+de\s+\w+\s+de\s+\d{4}\b',
        r'\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b'
    ]
    for pattern in date_patterns:
        dates = re.findall(pattern, text)
        entities['date'].extend(dates)
    
    # IDs (numbers with 6+ digits)
    id_pattern = r'\b\d{6,}\b'
    ids = re.findall(id_pattern, text)
    entities['id'].extend(ids)
    
    # Phone numbers
    phone_pattern = r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b|\b\+\d{1,3}[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9}\b'
    phones = re.findall(phone_pattern, text)
    entities['phone'].extend(phones)
    
    # Emails
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    emails = re.findall(email_pattern, text)
    entities['email'].extend(emails)
    
    # Remove duplicates
    for key in entities:
        entities[key] = list(set(entities[key]))
    
    return entities


def exact_similarity_search(
    texts: List[Tuple[str, str, str]],
    annotations: Dict = None,
    entity_type: str = 'person',
    min_occurrences: int = 2
) -> Dict[str, List[Dict]]:
    """
    Find exact duplicates of entities across texts.
    
    Args:
        texts: List of (text, filename, doc_id) tuples
        annotations: Dictionary mapping document IDs to annotation dicts
        entity_type: Type of entity to search for
        min_occurrences: Minimum number of occurrences to report
    
    Returns:
        Dictionary mapping entity values to lists of documents containing them
    """
    entity_to_docs = {}
    
    for text, filename, doc_id in texts:
        # Try to get annotations for this document
        doc_annotations = None
        if annotations:
            if doc_id in annotations:
                doc_annotations = annotations[doc_id]
            elif filename in annotations:
                doc_annotations = annotations[filename]
        
        entities = extract_phi_entities(text, doc_annotations)
        entity_values = entities.get(entity_type, [])
        
        for entity_value in entity_values:
            if entity_value not in entity_to_docs:
                entity_to_docs[entity_value] = []
            entity_to_docs[entity_value].append({
                'filename': filename,
                'doc_id': doc_id,
                'text_preview': text[:200] if len(text) > 200 else text
            })
    
    # Filter by minimum occurrences
    repeated_entities = {
        entity: docs for entity, docs in entity_to_docs.items()
        if len(docs) >= min_occurrences
    }
    
    return repeated_entities


def semantic_similarity_search(
    texts: List[Tuple[str, str, str]],
    model_name: str = 'paraphrase-multilingual-MiniLM-L12-v2',
    top_k: int = 5,
    similarity_threshold: float = 0.85
) -> List[Dict]:
    """
    Find semantically similar texts using sentence transformers.
    
    Returns:
        List of similar text pairs with similarity scores
    """
    if not SENTENCE_TRANSFORMERS_AVAILABLE:
        raise ImportError("sentence-transformers is not installed. Install it with: pip install sentence-transformers")
    
    print(f"Loading semantic model: {model_name}...")
    model = SentenceTransformer(model_name)
    
    print("Encoding texts...")
    text_strings = [text for text, _, _ in texts]
    embeddings = model.encode(text_strings, show_progress_bar=True)
    
    print("Computing similarity matrix...")
    similarity_matrix = cosine_similarity(embeddings)
    
    # Find similar pairs
    similar_pairs = []
    seen_pairs = set()
    
    for i in range(len(texts)):
        # Get top-k most similar (excluding self)
        similarities = similarity_matrix[i]
        similarities[i] = -1  # Exclude self
        top_indices = np.argsort(similarities)[::-1][:top_k]
        
        for j in top_indices:
            if similarities[j] >= similarity_threshold:
                pair_key = tuple(sorted([i, j]))
                if pair_key not in seen_pairs:
                    seen_pairs.add(pair_key)
                    similar_pairs.append({
                        'doc1': {
                            'filename': texts[i][1],
                            'doc_id': texts[i][2],
                            'text_preview': texts[i][0][:200]
                        },
                        'doc2': {
                            'filename': texts[j][1],
                            'doc_id': texts[j][2],
                            'text_preview': texts[j][0][:200]
                        },
                        'similarity': float(similarities[j])
                    })
    
    # Sort by similarity
    similar_pairs.sort(key=lambda x: x['similarity'], reverse=True)
    
    return similar_pairs


def evaluate_memorization(
    corpus_path: str,
    annotations_path: str = None,
    output_path: str = "memorization_detection_results.json",
    semantic_model: str = 'paraphrase-multilingual-MiniLM-L12-v2',
    similarity_threshold: float = 0.85,
    skip_semantic: bool = False
) -> Dict:
    """
    Complete memorization detection evaluation.
    """
    print("Loading corpus...")
    texts = load_corpus(corpus_path)
    print(f"Loaded {len(texts)} texts")
    
    # Load annotations if available
    annotations = {}
    if annotations_path and os.path.exists(annotations_path):
        if os.path.isdir(annotations_path):
            print(f"Loading annotations from {annotations_path}...")
            for json_file in Path(annotations_path).glob("*.json"):
                with open(json_file, 'r', encoding='utf-8') as f:
                    ann_data = json.load(f)
                    # Use the ID from the annotation file or filename
                    ann_id = ann_data.get('id', json_file.stem)
                    annotations[ann_id] = ann_data
            print(f"Loaded {len(annotations)} annotation files")
        elif annotations_path.endswith('.json'):
            with open(annotations_path, 'r', encoding='utf-8') as f:
                annotations = json.load(f)
    
    # Map document IDs to annotations (doc_id = .txt stem; annotation keys = id from JSON or filename stem)
    corpus_annotations = {}
    if annotations_path and os.path.exists(annotations_path) and os.path.isdir(annotations_path):
        if corpus_path.endswith('.json'):
            with open(corpus_path, 'r', encoding='utf-8') as f:
                corpus_data = json.load(f)
                if isinstance(corpus_data, list):
                    for item in corpus_data:
                        if isinstance(item, dict):
                            doc_id = item.get('id', '')
                            if doc_id and doc_id in annotations:
                                corpus_annotations[doc_id] = annotations[doc_id]
        else:
            # Corpus is a directory (e.g. documents/*.txt); use all annotations, lookup by doc_id in exact_similarity_search
            corpus_annotations = annotations
    else:
        corpus_annotations = annotations
    
    results = {
        'corpus_size': len(texts),
        '_occurrences_meaning': 'occurrences = number of documents that contain the entity at least once (not total mentions)',
        'exact_duplicates': {},
        'semantic_similarities': [],
        'memorization_risk': {}
    }
    
    # 1. Exact similarity search for PHI entities
    print("\n=== Exact Similarity Search ===")
    entity_types = ['person', 'id', 'date', 'location', 'phone', 'email']
    
    for entity_type in entity_types:
        print(f"Searching for repeated {entity_type} entities...")
        repeated = exact_similarity_search(texts, corpus_annotations, entity_type, min_occurrences=2)
        
        if repeated:
            print(f"  Found {len(repeated)} repeated {entity_type} entities")
            # Show top 5 most repeated
            sorted_repeated = sorted(
                repeated.items(),
                key=lambda x: len(x[1]),
                reverse=True
            )[:5]
            
            results['exact_duplicates'][entity_type] = {
                'total_repeated': len(repeated),
                'top_repeated': [
                    {
                        'entity': entity,
                        'occurrences': len(docs),  # number of documents containing this entity (not total mentions)
                        'documents': docs[:3]  # Limit to first 3 docs
                    }
                    for entity, docs in sorted_repeated
                ]
            }
        else:
            results['exact_duplicates'][entity_type] = {
                'total_repeated': 0,
                'top_repeated': []
            }
    
    # 2. Semantic similarity search
    if skip_semantic:
        print("\n=== Semantic Similarity Search ===")
        print("[WARNING] Similitud semantica deshabilitada (skip_semantic=True)")
        results['semantic_similarities'] = []
        results['semantic_skipped'] = True
    else:
        print("\n=== Semantic Similarity Search ===")
        try:
            similar_pairs = semantic_similarity_search(
                texts,
                model_name=semantic_model,
                similarity_threshold=similarity_threshold
            )
            results['semantic_similarities'] = similar_pairs[:100]  # Top 100
            print(f"Found {len(similar_pairs)} highly similar text pairs (similarity >= {similarity_threshold})")
        except Exception as e:
            print(f"Error in semantic search: {e}")
            results['semantic_similarities'] = []
            results['semantic_error'] = str(e)
    
    # 3. Risk assessment
    total_repeated_entities = sum(
        r.get('total_repeated', 0)
        for r in results['exact_duplicates'].values()
    )
    
    if skip_semantic:
        high_similarity_pairs = 0
        semantic_note = " (semantic similarity skipped)"
    else:
        high_similarity_pairs = len([
            p for p in results['semantic_similarities']
            if p.get('similarity', 0) >= 0.95
        ])
        semantic_note = ""
    
    # Risk assessment based on exact duplicates only if semantic is skipped
    if skip_semantic:
        risk_level = (
            'low' if total_repeated_entities < 10 else
            'medium' if total_repeated_entities < 50 else
            'high' if total_repeated_entities < 200 else
            'critical'
        )
        interpretation = (
            f"Low memorization risk. Minimal repetition of PHI entities.{semantic_note}"
            if total_repeated_entities < 10 else
            f"Moderate memorization risk. Some repetition detected.{semantic_note}"
            if total_repeated_entities < 50 else
            f"High memorization risk. Significant repetition of PHI entities.{semantic_note}"
            if total_repeated_entities < 200 else
            f"Critical memorization risk. Extensive repetition detected.{semantic_note}"
        )
    else:
        risk_level = (
            'low' if total_repeated_entities < 10 and high_similarity_pairs < 5 else
            'medium' if total_repeated_entities < 50 and high_similarity_pairs < 20 else
            'high' if total_repeated_entities < 200 and high_similarity_pairs < 100 else
            'critical'
        )
        interpretation = (
            "Low memorization risk. Minimal repetition of PHI entities and low semantic similarity."
            if total_repeated_entities < 10 and high_similarity_pairs < 5 else
            "Moderate memorization risk. Some repetition detected. Consider increasing diversity in generation."
            if total_repeated_entities < 50 and high_similarity_pairs < 20 else
            "High memorization risk. Significant repetition of PHI entities. Review generation pipeline."
            if total_repeated_entities < 200 and high_similarity_pairs < 100 else
            "Critical memorization risk. Extensive repetition detected. Immediate review required."
        )
    
    results['memorization_risk'] = {
        'total_repeated_phi_entities': total_repeated_entities,
        'high_similarity_pairs': high_similarity_pairs,
        'semantic_skipped': skip_semantic,
        'risk_level': risk_level,
        'interpretation': interpretation
    }
    
    # Save results
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n=== Memorization Detection Results ===")
    print(f"Total repeated PHI entities: {total_repeated_entities}")
    print(f"High similarity pairs (>=0.95): {high_similarity_pairs}")
    print(f"Risk level: {results['memorization_risk']['risk_level']}")
    print(f"\nResults saved to {output_path}")
    
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Memorization Detection via Nearest Neighbor Search")
    parser.add_argument(
        "--corpus_path",
        type=str,
        required=True,
        help="Path to corpus (directory or .json file)"
    )
    parser.add_argument(
        "--annotations_path",
        type=str,
        default=None,
        help="Path to annotations (optional)"
    )
    parser.add_argument(
        "--output_path",
        type=str,
        default="memorization_detection_results.json",
        help="Path to save results"
    )
    parser.add_argument(
        "--semantic_model",
        type=str,
        default="paraphrase-multilingual-MiniLM-L12-v2",
        help="Sentence transformer model for semantic similarity"
    )
    parser.add_argument(
        "--similarity_threshold",
        type=float,
        default=0.85,
        help="Minimum similarity threshold for semantic search"
    )
    parser.add_argument(
        "--skip_semantic",
        action="store_true",
        help="Skip semantic similarity search (only exact similarity)"
    )
    
    args = parser.parse_args()
    
    evaluate_memorization(
        args.corpus_path,
        args.annotations_path,
        args.output_path,
        args.semantic_model,
        args.similarity_threshold,
        args.skip_semantic
    )

