# HealthGuard AI - Model Usage Guide

A comprehensive guide to using HealthGuard's machine learning models for healthcare intelligence.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [NOVA Classifier](#1-nova-classifier)
3. [Additive Risk Scorer](#2-additive-risk-scorer)
4. [Procedure Encoder](#3-procedure-encoder)
5. [Chronic Risk Predictor](#4-chronic-risk-predictor)
6. [Intervention Prioritizer](#5-intervention-prioritizer)
7. [Batch Processing](#batch-processing)
8. [API Integration](#api-integration)

---

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/your-org/HealthGuard.git
cd HealthGuard

# Create conda environment
conda create -n healthguard python=3.10
conda activate healthguard

# Install dependencies
pip install torch transformers pandas numpy scikit-learn
```

### Basic Usage

```python
from ml.services import (
    classify_nova,
    score_additive,
    match_procedure,
    predict_county_risk,
    prioritize_intervention
)

# Classify a food product
result = classify_nova("sugar, high fructose corn syrup, red 40")
print(f"NOVA Class: {result['nova_class']}")  # Output: 4 (ultra-processed)

# Score an additive
risk = score_additive("Red 40", additive_type="dye")
print(f"Risk Score: {risk['score']}/100")  # Output: 85/100 (high risk)
```

---

## 1. NOVA Classifier

**Purpose:** Classify food products into NOVA processing levels (1-4)

### What is NOVA?

| Level | Name | Description | Examples |
|-------|------|-------------|----------|
| 1 | Unprocessed | Natural foods | Fresh fruits, vegetables, eggs |
| 2 | Culinary | Cooking ingredients | Oil, butter, salt, sugar |
| 3 | Processed | Modified foods | Canned vegetables, cheese |
| 4 | Ultra-processed | Industrial formulations | Soda, chips, instant noodles |

### Usage

```python
from ml.nova_classifier import NOVAClassifier

# Load model
classifier = NOVAClassifier.load('ml/weights/nova_classifier.pt')

# Single prediction
ingredients = "enriched wheat flour, high fructose corn syrup, partially hydrogenated soybean oil, sodium benzoate, red 40"
result = classifier.predict(ingredients)

print(f"NOVA Class: {result['class']}")           # 4
print(f"Confidence: {result['confidence']:.1%}")  # 94.2%
print(f"Label: {result['label']}")                # "Ultra-processed"
```

### Batch Processing

```python
# Multiple products
products = [
    "fresh apples",
    "olive oil, salt",
    "tomatoes, salt, citric acid",
    "sugar, corn syrup, artificial flavors, red 40"
]

results = classifier.predict_batch(products)
for product, result in zip(products, results):
    print(f"{product[:30]:30} → NOVA {result['class']} ({result['confidence']:.0%})")
```

**Output:**
```
fresh apples                   → NOVA 1 (97%)
olive oil, salt                → NOVA 2 (89%)
tomatoes, salt, citric acid    → NOVA 3 (85%)
sugar, corn syrup, artificial  → NOVA 4 (96%)
```

### Key Indicators by Class

| NOVA 4 Indicators | NOVA 1 Indicators |
|-------------------|-------------------|
| High fructose corn syrup | Fresh, raw, natural |
| Partially hydrogenated | Unprocessed |
| Artificial flavors/colors | Whole foods |
| Sodium benzoate | No additives |
| Modified starch | Single ingredient |

---

## 2. Additive Risk Scorer

**Purpose:** Assess health risk of food additives (0-100 scale)

### Risk Categories

| Score | Category | Meaning | Action |
|-------|----------|---------|--------|
| 0-29 | Low | Generally safe | No concern |
| 30-69 | Moderate | Some concerns | Limit intake |
| 70-100 | High | Health risks | Avoid |

### Usage

```python
from ml.additive_scorer import AdditiveRiskScorer

# Load model
scorer = AdditiveRiskScorer.load('ml/weights/additive_scorer.pt')

# Score an additive
result = scorer.predict(
    name="Red 40",
    additive_type="dye",
    fda_status="approved",
    eu_status="restricted",
    is_artificial=True,
    is_petroleum_based=True
)

print(f"Risk Score: {result['score']}/100")    # 85
print(f"Category: {result['category']}")       # "high"
print(f"Recommendation: {result['action']}")   # "Avoid if possible"
```

### Common Additives Reference

| Additive | Type | Risk Score | Notes |
|----------|------|------------|-------|
| Red 40 | Dye | 85 | Petroleum-based, hyperactivity link |
| Yellow 5 | Dye | 75 | EU restricted |
| Aspartame | Sweetener | 55 | Controversial studies |
| Sodium Benzoate | Preservative | 45 | Benzene formation concern |
| Citric Acid | Preservative | 10 | Natural, safe |
| Pectin | Thickener | 5 | Natural fiber |

### Batch Analysis

```python
additives = ["Red 40", "Citric Acid", "Sodium Benzoate", "Aspartame"]
results = scorer.predict_batch(additives)

for additive, result in zip(additives, results):
    emoji = "🔴" if result['score'] >= 70 else "🟡" if result['score'] >= 30 else "🟢"
    print(f"{emoji} {additive}: {result['score']}/100 ({result['category']})")
```

**Output:**
```
🔴 Red 40: 85/100 (high)
🟢 Citric Acid: 10/100 (low)
🟡 Sodium Benzoate: 45/100 (moderate)
🟡 Aspartame: 55/100 (moderate)
```

---

## 3. Procedure Encoder

**Purpose:** Match hospital procedure descriptions to standard CPT codes

### How It Works

The model converts procedure text into 384-dimensional embeddings, then uses cosine similarity to match against a database of canonical procedures.

### Usage

```python
from ml.procedure_encoder import ProcedureEncoder

# Load model
encoder = ProcedureEncoder.load('ml/weights/procedure_encoder.pt')

# Match a procedure
query = "MRI BRAIN WITHOUT CONTRAST"
matches = encoder.find_matches(query, top_k=3)

for match in matches:
    print(f"CPT: {match['code']} | Similarity: {match['similarity']:.2f} | {match['description']}")
```

**Output:**
```
CPT: 70551 | Similarity: 0.88 | MRI brain w/o contrast
CPT: 70553 | Similarity: 0.72 | MRI brain w/ and w/o contrast
CPT: 70552 | Similarity: 0.68 | MRI brain with contrast
```

### Similarity Thresholds

| Similarity | Confidence | Action |
|------------|------------|--------|
| ≥ 0.80 | High | Auto-match |
| 0.65 - 0.80 | Medium | Review recommended |
| < 0.65 | Low | Manual coding required |

### Compare Two Procedures

```python
# Check if two descriptions refer to the same procedure
similarity = encoder.compare(
    "MRI BRAIN WITHOUT CONTRAST",
    "70551 - MRI HEAD W/O"
)
print(f"Similarity: {similarity:.2f}")  # 0.88 - Same procedure!

similarity = encoder.compare(
    "MRI BRAIN",
    "COMPLETE BLOOD COUNT"
)
print(f"Similarity: {similarity:.2f}")  # 0.14 - Different procedures
```

---

## 4. Chronic Risk Predictor

**Purpose:** Predict chronic disease prevalence from county-level factors

### Diseases Predicted

1. Diabetes
2. Obesity
3. Heart Disease
4. High Blood Pressure
5. COPD
6. Depression

### Input Features

| Category | Features |
|----------|----------|
| Food Environment | Grocery stores per capita, fast food density, food insecurity |
| Healthcare | Primary care providers, hospital beds, uninsured rate |
| Socioeconomic | Median income, poverty rate, unemployment |
| Demographics | Population density, % elderly, % rural |
| Behavioral | Smoking rate, physical inactivity, excessive drinking |

### Usage

```python
from ml.chroniccare import ChronicRiskPredictor

# Load model
predictor = ChronicRiskPredictor.load('ml/weights/chronic_risk_predictor.pt')

# Predict for a county
county_data = {
    'grocery_stores_per_capita': 0.15,
    'fast_food_per_capita': 0.8,
    'poverty_rate': 18.5,
    'uninsured_rate': 12.0,
    'smoking_rate': 22.0,
    'physical_inactivity': 28.0,
    # ... other features
}

predictions = predictor.predict(county_data)

print("Predicted Disease Prevalence:")
for disease, prevalence in predictions.items():
    print(f"  {disease}: {prevalence:.1f}%")
```

**Output:**
```
Predicted Disease Prevalence:
  diabetes: 12.4%
  obesity: 35.2%
  heart_disease: 7.8%
  high_bp: 32.1%
  copd: 8.2%
  depression: 19.5%
```

### Accuracy

| Disease | MAE | Interpretation |
|---------|-----|----------------|
| Diabetes | 1.36% | Prediction within ±1.36% |
| Obesity | 2.30% | Prediction within ±2.30% |
| Heart Disease | 0.99% | Prediction within ±0.99% |
| High BP | 3.02% | Prediction within ±3.02% |
| COPD | 0.88% | Prediction within ±0.88% |
| Depression | 2.10% | Prediction within ±2.10% |

---

## 5. Intervention Prioritizer

**Purpose:** Classify counties into MAHA intervention priority tiers

### Priority Tiers

| Tier | Percentile | Action |
|------|------------|--------|
| Critical | Top 5% | Immediate intervention |
| High | Top 20% | Priority funding |
| Medium | Top 50% | Enhanced monitoring |
| Low | Bottom 50% | Standard programs |

### Usage

```python
from ml.chroniccare import InterventionPrioritizer

# Load model
prioritizer = InterventionPrioritizer.load('ml/weights/intervention_prioritizer.pt')

# Classify a county
county_data = {
    'diabetes_prevalence': 14.2,
    'obesity_prevalence': 38.0,
    'poverty_rate': 24.0,
    'uninsured_rate': 15.0,
    'pcp_per_capita': 0.3,
    # ... other features
}

result = prioritizer.predict(county_data)

print(f"Priority Tier: {result['tier']}")           # "critical"
print(f"Confidence: {result['confidence']:.1%}")    # 91.2%
print(f"MAHA Index: {result['maha_index']:.1f}")    # 47.3
```

### MAHA Index Components

```python
# The MAHA index is calculated from weighted factors:
maha_index = (
    0.25 * disease_burden +       # 25% weight
    0.20 * food_environment +     # 20% weight
    0.20 * healthcare_access +    # 20% weight
    0.15 * economic_vulnerability + # 15% weight
    0.10 * behavioral_factors +   # 10% weight
    0.10 * demographic_risk       # 10% weight
)
```

---

## Batch Processing

### Process Multiple Items

```python
import pandas as pd
from ml.services import classify_nova, score_additive

# Load product data
products_df = pd.read_csv('products.csv')

# Classify all products
products_df['nova_class'] = products_df['ingredients'].apply(
    lambda x: classify_nova(x)['class']
)

# Score all additives
additives_df = pd.read_csv('additives.csv')
additives_df['risk_score'] = additives_df.apply(
    lambda row: score_additive(row['name'], row['type'])['score'],
    axis=1
)
```

### GPU Acceleration

```python
import torch

# Check GPU availability
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f"Using device: {device}")

# Models automatically use GPU if available
# For explicit control:
classifier = NOVAClassifier.load('model.pt', device='cuda')
```

---

## API Integration

### FastAPI Endpoints

```python
from fastapi import FastAPI
from ml.services import classify_nova, score_additive

app = FastAPI()

@app.post("/api/nova/classify")
async def classify_food(ingredients: str):
    result = classify_nova(ingredients)
    return {
        "nova_class": result['class'],
        "confidence": result['confidence'],
        "label": result['label']
    }

@app.post("/api/additive/score")
async def score_food_additive(name: str, type: str):
    result = score_additive(name, additive_type=type)
    return {
        "risk_score": result['score'],
        "category": result['category']
    }
```

### REST API Examples

```bash
# Classify a food product
curl -X POST "http://localhost:8000/api/nova/classify" \
  -H "Content-Type: application/json" \
  -d '{"ingredients": "sugar, corn syrup, red 40"}'

# Score an additive
curl -X POST "http://localhost:8000/api/additive/score" \
  -H "Content-Type: application/json" \
  -d '{"name": "Red 40", "type": "dye"}'
```

---

## Performance Tips

### 1. Batch Processing

```python
# Bad: One at a time (slow)
for item in items:
    result = model.predict(item)

# Good: Batch processing (fast)
results = model.predict_batch(items)
```

### 2. Model Caching

```python
# Load once, reuse many times
classifier = NOVAClassifier.load('model.pt')  # Load once

for product in products:
    result = classifier.predict(product)  # Reuse
```

### 3. GPU Memory

```python
# For large batches, process in chunks
batch_size = 64
for i in range(0, len(items), batch_size):
    batch = items[i:i+batch_size]
    results = model.predict_batch(batch)
```

---

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| `CUDA out of memory` | Reduce batch size |
| `Model not found` | Check path to weights |
| `Tokenizer error` | Ensure tokenizer JSON exists |
| `Low accuracy` | Check input format matches training |

### Getting Help

- GitHub Issues: [github.com/your-org/HealthGuard/issues](https://github.com/your-org/HealthGuard/issues)
- Documentation: [docs/ANALYSIS_REPORT.md](../docs/ANALYSIS_REPORT.md)

---

*HealthGuard AI Platform - Making Healthcare Data Actionable*
