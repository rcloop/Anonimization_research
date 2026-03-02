# Privacy analysis report — Corpus V1

Date: 2026-03-02  
Workspace: `Anonimization_research`  
Corpus: `corpus_repo/corpus_v1`  
Documents: **14,035**

### Executive summary

- **Overall assessment**: **CRITICAL privacy risk** for downstream release/use as-is.
- **Main drivers**:
  - **Attribute inference** signals are **critical** across all evaluated attributes (AUC-ROC ~0.97–0.999).
  - **Memorization / repetition** of PHI entities is **high** (exact repeats across many documents), indicating strong re-identification and leakage potential.
- **Membership inference** appears **low** in this run, but is **limited** because `external_size = 0` (no true holdout/external set).

### Scope and methodology

This report summarizes results produced by the privacy evaluation suite located in `src/privacy_evaluation/` on **Corpus V1**, with:

- **Canary insertion**: **skipped**
- **Memorization detection**:
  - **Exact duplicates (PHI entities)**: enabled
  - **Semantic similarity (near-duplicate texts)**: enabled (computed into a separate artifact; see “Artifacts”)

Definition used in memorization outputs:

- **occurrences** = **number of documents** that contain the entity at least once (not total mentions).

### Results

#### Membership inference

Source: `membership_inference.json`

- **AUC-ROC**: **0.4207** → **LOW**
- **Accuracy**: 0.8332 (close to baseline 0.8333)
- **External set**: **0 documents** (important limitation)

Interpretation: the implemented membership attack does **not** reliably separate in/out samples **given the current setup**, but conclusions are constrained without an external comparison set.

#### Attribute inference

Source: `attribute_inference.json`

All evaluated attributes are **critical**:

- **has_person**: AUC-ROC **0.9687**
- **has_date**: AUC-ROC **0.9988**
- **has_location**: AUC-ROC **0.9762**
- **has_id**: AUC-ROC **0.9828**
- **has_age**: AUC-ROC **0.9969**
- **has_contact**: AUC-ROC **0.9957**
- **has_medical_condition**: AUC-ROC **0.9770**

This indicates that the presence of sensitive attributes is highly predictable from the representation/features used by the attack pipeline — i.e., strong signal remains.

#### Memorization detection — exact PHI repeats

Source: `memorization_detection_exact_only.json`

- **Repeated entities (by type)**:
  - **person**: 215
  - **id**: 802
  - **date**: 17
  - **location**: 169
  - **phone**: 86
  - **email**: 66
- **Total repeated PHI entities**: **1,355**

Most repeated examples (by **document occurrences**):

- **person**:
  - `Sra. Elena Castillo Domínguez` — 328 docs
  - `Marcos Vidal Peña` — 320 docs
  - `D.ª Clara Robles Soto` — 310 docs
- **id**:
  - `HC-2024-654321` — 414 docs
  - `Placas XYZ-123` — 360 docs
  - `VIN 1HGCM82633A123456` — 358 docs
- **date**:
  - `Junio 2023` — 364 docs
  - `13 de julio de 2023` — 364 docs
  - `15-07-2023` — 341 docs
- **location**:
  - `Francia` — 399 docs
  - `Italia` — 387 docs
  - `Consultorio Local Santa Clara` — 385 docs
- **phone**:
  - `+34 91 345 09 87` — 365 docs
  - `+34 952 88 76 54` — 357 docs
  - `555-345-6789` — 357 docs
- **email**:
  - `cmartinez@hospitallapaz.es` — 228 docs
  - `carlos.martinez@hospitalcentral.org` — 222 docs
  - `c.martinez@fundacioncardiologica.es` — 217 docs

#### Memorization detection — semantic similarity (near-duplicate documents)

Source: `memorization_detection_with_semantic.json`

- **Pairs with similarity ≥ 0.85**: **56,734**  
- **Pairs with similarity ≥ 0.95**: **100**

Interpretation: a high number of near-duplicate pairs implies templated or highly repetitive clinical narratives, which increases memorization and leakage risk (especially for structured identifiers and contact fields).

### Overall interpretation (why this is CRITICAL)

Even if membership inference is low in this specific setup, the combination of:

- **attribute inference being consistently critical**, and
- **large-scale exact repetition of PHI entities across documents**, plus
- **substantial near-duplicate text structure (semantic similarity)**

supports a **CRITICAL** privacy posture for the corpus (and for any model trained on it without strong privacy controls and de-identification hardening).

### Recommendations (prioritized)

- **Block release/use as-is** for any public/shared setting until mitigations are applied and re-evaluated.
- **Deduplication**:
  - Remove exact and near-duplicate documents (or template boilerplate) before training.
- **Stronger de-identification**:
  - Ensure identifiers, contacts, and stable pseudo-identifiers are consistently removed or irreversibly transformed.
- **Training-time protections** (if training/generation is involved):
  - Apply **differential privacy** where feasible.
  - Add **PII filters** at generation and post-generation.
  - Consider **per-record clipping / noise** and **privacy auditing** as gating.
- **Re-run privacy suite** after each mitigation batch and compare:
  - repeated PHI totals,
  - top repeated entities,
  - semantic similarity pair counts,
  - attribute AUC-ROC.

### Artifacts (files)

All artifacts referenced live in:

`src/privacy_evaluation/privacy_evaluation_results_v1/`

- `membership_inference.json`
- `attribute_inference.json`
- `memorization_detection_exact_only.json`
- `memorization_detection_with_semantic.json`
- `consolidated_privacy_report.json` (note: may reflect an earlier run prior to the latest extractor fix)

