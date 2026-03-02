"""
Membership Inference Attack Evaluation
Tests whether an attacker can determine if a specific text was in the training corpus.
"""

import json
import os
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, accuracy_score, precision_recall_curve, auc
from typing import List, Dict, Tuple
import argparse
from pathlib import Path


def _documents_dir(corpus_path: str) -> str:
    """If corpus_path is a corpus root with documents/ subdir, return path to documents."""
    p = Path(corpus_path)
    if p.is_dir() and (p / "documents").is_dir():
        return str(p / "documents")
    return corpus_path


def load_corpus(corpus_path: str) -> List[str]:
    """Load corpus texts from JSON or directory of text files."""
    texts = []
    corpus_path = _documents_dir(corpus_path)
    
    if os.path.isdir(corpus_path):
        # Load from directory of text files
        for file_path in Path(corpus_path).glob("*.txt"):
            with open(file_path, 'r', encoding='utf-8') as f:
                texts.append(f.read().strip())
    elif corpus_path.endswith('.json'):
        # Load from JSON file
        with open(corpus_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        texts.append(item.get('text', item.get('content', '')))
                    else:
                        texts.append(str(item))
            else:
                texts = [data.get('text', '')] if isinstance(data, dict) else []
    else:
        raise ValueError(f"Unsupported file format: {corpus_path}")
    
    return texts


def prepare_membership_inference_data(
    corpus_texts: List[str],
    external_texts: List[str] = None,
    test_size: float = 0.2
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Prepare data for membership inference attack.
    
    Args:
        corpus_texts: Texts from the training corpus
        external_texts: External texts not in corpus (if None, split corpus)
        test_size: Fraction of corpus to use as "non-members" if external_texts is None
    
    Returns:
        X: Feature vectors
        y: Labels (1 = member, 0 = non-member)
    """
    # Create member examples (label = 1) - all texts from the generated corpus
    member_texts = corpus_texts.copy()
    member_labels = [1] * len(member_texts)
    
    # Create non-member examples (label = 0)
    if external_texts is None:
        # Split corpus to simulate non-members
        # This creates a held-out subset from the same corpus to test
        # whether the attack can distinguish between different subsets
        _, non_member_texts = train_test_split(
            corpus_texts, test_size=test_size, random_state=42
        )
    else:
        # Use external texts as non-members
        non_member_texts = external_texts
    
    non_member_labels = [0] * len(non_member_texts)
    
    # Combine
    all_texts = member_texts + non_member_texts
    all_labels = member_labels + non_member_labels
    
    # Vectorize texts
    vectorizer = TfidfVectorizer(
        max_features=5000,
        ngram_range=(1, 3),
        min_df=2,
        max_df=0.95
    )
    
    X = vectorizer.fit_transform(all_texts).toarray()
    y = np.array(all_labels)
    
    return X, y, vectorizer


def train_membership_inference_attack(
    X: np.ndarray,
    y: np.ndarray,
    test_size: float = 0.2
) -> Tuple[LogisticRegression, Dict[str, float]]:
    """
    Train a membership inference attack model.
    
    Returns:
        model: Trained attack model
        metrics: Evaluation metrics
    """
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=42, stratify=y
    )
    
    # Train attack model
    attack_model = LogisticRegression(max_iter=1000, random_state=42)
    attack_model.fit(X_train, y_train)
    
    # Evaluate
    y_pred = attack_model.predict(X_test)
    y_pred_proba = attack_model.predict_proba(X_test)[:, 1]
    
    # Calculate metrics
    accuracy = accuracy_score(y_test, y_pred)
    auc_score = roc_auc_score(y_test, y_pred_proba)
    precision, recall, _ = precision_recall_curve(y_test, y_pred_proba)
    pr_auc = auc(recall, precision)
    
    metrics = {
        'accuracy': accuracy,
        'auc_roc': auc_score,
        'auc_pr': pr_auc,
        'precision': precision[-1] if len(precision) > 0 else 0.0,
        'recall': recall[-1] if len(recall) > 0 else 0.0
    }
    
    return attack_model, metrics


def evaluate_membership_inference(
    corpus_path: str,
    external_corpus_path: str = None,
    output_path: str = "membership_inference_results.json"
) -> Dict:
    """
    Complete membership inference evaluation.
    
    Args:
        corpus_path: Path to corpus (directory or JSON)
        external_corpus_path: Path to external texts (optional)
        output_path: Path to save results
    """
    print("Loading corpus...")
    corpus_texts = load_corpus(corpus_path)
    print(f"Loaded {len(corpus_texts)} texts from corpus")
    
    external_texts = None
    if external_corpus_path:
        external_texts = load_corpus(external_corpus_path)
        print(f"Loaded {len(external_texts)} external texts")
    
    print("Preparing membership inference data...")
    X, y, vectorizer = prepare_membership_inference_data(
        corpus_texts, external_texts
    )
    
    print(f"Data shape: {X.shape}, Labels: {np.sum(y==1)} members, {np.sum(y==0)} non-members")
    
    print("Training membership inference attack...")
    attack_model, metrics = train_membership_inference_attack(X, y)
    
    # Interpretation
    baseline_accuracy = max(np.mean(y), 1 - np.mean(y))  # Random baseline
    
    results = {
        'corpus_size': len(corpus_texts),
        'external_size': len(external_texts) if external_texts else 0,
        'attack_metrics': metrics,
        'baseline_accuracy': baseline_accuracy,
        'privacy_risk': {
            'low_risk': metrics['auc_roc'] < 0.6,
            'medium_risk': 0.6 <= metrics['auc_roc'] < 0.7,
            'high_risk': 0.7 <= metrics['auc_roc'] < 0.8,
            'critical_risk': metrics['auc_roc'] >= 0.8
        },
        'interpretation': {
            'auc_roc_interpretation': (
                "Low risk (<0.6)" if metrics['auc_roc'] < 0.6 else
                "Medium risk (0.6-0.7)" if metrics['auc_roc'] < 0.7 else
                "High risk (0.7-0.8)" if metrics['auc_roc'] < 0.8 else
                "Critical risk (>=0.8)"
            ),
            'recommendation': (
                "No significant membership inference risk detected. "
                "The model does not memorize training examples in a way that allows "
                "reliable membership inference." if metrics['auc_roc'] < 0.6 else
                "Moderate membership inference risk. Consider applying differential privacy "
                "or additional regularization." if metrics['auc_roc'] < 0.7 else
                "High membership inference risk. Strongly recommend applying differential "
                "privacy or other privacy-preserving techniques." if metrics['auc_roc'] < 0.8 else
                "Critical membership inference risk. Immediate action required: apply "
                "differential privacy or redesign the generation pipeline."
            )
        }
    }
    
    # Save results
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\nMembership Inference Results:")
    print(f"  AUC-ROC: {metrics['auc_roc']:.4f}")
    print(f"  AUC-PR: {metrics['auc_pr']:.4f}")
    print(f"  Accuracy: {metrics['accuracy']:.4f}")
    print(f"  Baseline: {baseline_accuracy:.4f}")
    print(f"  Risk Level: {results['privacy_risk']}")
    print(f"\nResults saved to {output_path}")
    
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Membership Inference Attack Evaluation")
    parser.add_argument(
        "--corpus_path",
        type=str,
        required=True,
        help="Path to corpus (directory of .txt files or .json file)"
    )
    parser.add_argument(
        "--external_corpus_path",
        type=str,
        default=None,
        help="Path to external texts not in corpus (optional)"
    )
    parser.add_argument(
        "--output_path",
        type=str,
        default="membership_inference_results.json",
        help="Path to save results"
    )
    
    args = parser.parse_args()
    
    evaluate_membership_inference(
        args.corpus_path,
        args.external_corpus_path,
        args.output_path
    )

