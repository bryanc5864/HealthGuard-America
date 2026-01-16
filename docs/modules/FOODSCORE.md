# FoodScore Module Documentation

**Module:** Food Product Health Scoring
**Version:** 1.0
**Last Updated:** January 16, 2026

---

## Overview

FoodScore is HealthGuard's food safety and nutrition module that analyzes food products using machine learning to determine processing level (NOVA classification) and additive risk scores. It empowers consumers to make healthier food choices at the point of purchase.

---

## Problem Statement

### Before FoodScore

1. **Label Confusion:** "Natural flavors" and chemical names are meaningless to consumers
2. **Marketing Deception:** "Organic" and "Natural" labels don't mean healthy
3. **Hidden Processing:** 70% of products are ultra-processed but look healthy
4. **Unknown Additives:** E-numbers and chemical names are unrecognizable
5. **No Quick Assessment:** Reading labels takes too long in the store

### After FoodScore

1. **Instant Classification:** Scan barcode, get NOVA level in seconds
2. **Truth in Processing:** ML identifies ultra-processed products (96.2% accuracy)
3. **Additive Risk Scores:** Each additive rated 0-100 for health risk
4. **Plain Language:** "Red 40 - High Risk Petroleum Dye" vs "FD&C Red No. 40"
5. **Mobile Ready:** API designed for smartphone barcode scanning apps

---

## ML Models

### 1. NOVA Classifier

**Purpose:** Classify food products into NOVA processing levels

| NOVA Level | Description | Examples |
|------------|-------------|----------|
| 1 | Unprocessed/minimally processed | Fresh fruits, vegetables, eggs, meat |
| 2 | Processed culinary ingredients | Oils, butter, sugar, flour |
| 3 | Processed foods | Canned vegetables, cheese, bread |
| 4 | Ultra-processed products | Soda, chips, frozen dinners, candy |

**Architecture:**
```
Input: Ingredient text (max 200 tokens)
    ↓
Embedding Layer (vocab=10,000, dim=128)
    ↓
Conv1D (256 filters, kernel=3) + ReLU
    ↓
Global Average Pooling
    ↓
Dense(256) + BatchNorm + ReLU + Dropout(0.3)
    ↓
Dense(128) + BatchNorm + ReLU + Dropout(0.3)
    ↓
Dense(4) + Softmax
    ↓
Output: NOVA class probabilities [1, 2, 3, 4]
```

**Performance:**
| Metric | Value |
|--------|-------|
| Overall Accuracy | **96.16%** |
| Macro F1 | 0.904 |
| NOVA 1 Accuracy | 93.7% |
| NOVA 2 Accuracy | 86.3% |
| NOVA 3 Accuracy | 91.7% |
| NOVA 4 Accuracy | 98.1% |

**Ultra-Processing Indicators (learned by model):**
- "high fructose corn syrup"
- "partially hydrogenated"
- "sodium benzoate"
- "artificial flavor"
- "modified starch"
- Multiple emulsifiers together

### 2. Additive Risk Scorer

**Purpose:** Predict health risk scores (0-100) for food additives

**Two Versions:**

| Model | Dataset | Accuracy | Best For |
|-------|---------|----------|----------|
| Regular | 42 additives | 85.71% | Small curated datasets |
| FoodScore+ | 344 additives | 56.60% | Large diverse datasets |

**Risk Categories:**
| Category | Score | Color | Action |
|----------|-------|-------|--------|
| Low | 0-29 | Green | Safe to consume |
| Moderate | 30-69 | Yellow | Use in moderation |
| High | 70-100 | Red | Avoid if possible |

**Input Features (13):**
- Additive type (dye, sweetener, preservative, emulsifier, flavor, other)
- FDA status (approved, banned)
- EU status (approved, restricted, banned)
- Is artificial (boolean)
- Is petroleum-based (boolean)

**Example Scores:**
| Additive | Risk Score | Category | Reason |
|----------|------------|----------|--------|
| Red 40 | 85 | High | Petroleum dye, hyperactivity link |
| Aspartame | 65 | Moderate | Artificial sweetener, some concerns |
| Sodium Benzoate | 55 | Moderate | Preservative, benzene formation risk |
| Citric Acid | 15 | Low | Natural, widely used |
| Pectin | 10 | Low | Natural fiber |

---

## Data Pipeline

### Data Sources

| Source | Description | Records |
|--------|-------------|---------|
| OpenFoodFacts | Crowdsourced product database | 50,000 US products |
| FDA GRAS List | Generally Recognized as Safe | 4,000+ substances |
| EWG Food Scores | Environmental Working Group | 80,000+ products |
| CSPI Chemical Cuisine | Additive safety ratings | 150+ additives |
| EU E-Number Database | European additive codes | 400+ E-numbers |

### Pipeline Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  OpenFoodFacts  │────▶│  Ingredient     │────▶│  Additive       │
│  Product Data   │     │  Parser         │     │  Extractor      │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                        │
         ┌──────────────────────────────────────────────┤
         ▼                                              ▼
┌─────────────────┐                          ┌─────────────────┐
│  NOVA           │                          │  Additive       │
│  Classifier     │                          │  Scorer         │
│  (96.2%)        │                          │  (85.7%)        │
└─────────────────┘                          └─────────────────┘
         │                                              │
         └──────────────────┬───────────────────────────┘
                            ▼
                  ┌─────────────────┐
                  │  FoodScore      │
                  │  Database       │
                  └─────────────────┘
```

### Processing Steps

1. **Ingest:** Load product data from OpenFoodFacts
2. **Parse:** Extract ingredient lists, nutrition facts
3. **Tokenize:** Convert ingredients to model input format
4. **Classify:** Run NOVA classifier on ingredient text
5. **Extract:** Identify additives in ingredient list
6. **Score:** Run additive scorer on each additive
7. **Aggregate:** Calculate overall product health score
8. **Store:** Save to PostgreSQL with all scores

---

## Database Schema

### Tables

```sql
-- Food products
CREATE TABLE food_products (
    id SERIAL PRIMARY KEY,
    barcode VARCHAR(20) UNIQUE,
    name VARCHAR(500) NOT NULL,
    brand VARCHAR(255),
    categories TEXT,
    ingredients_text TEXT,
    nutrition_json JSONB,
    nova_class INTEGER CHECK (nova_class BETWEEN 1 AND 4),
    nova_confidence FLOAT,
    nutriscore_grade CHAR(1),
    health_score INTEGER CHECK (health_score BETWEEN 0 AND 100),
    image_url TEXT,
    source VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Additives master list
CREATE TABLE additives (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    e_number VARCHAR(10),
    type VARCHAR(50),  -- dye, sweetener, preservative, etc.
    risk_score INTEGER CHECK (risk_score BETWEEN 0 AND 100),
    risk_category VARCHAR(20),
    fda_status VARCHAR(20),
    eu_status VARCHAR(20),
    is_artificial BOOLEAN,
    is_petroleum_based BOOLEAN,
    description TEXT,
    health_concerns TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Product-additive junction
CREATE TABLE product_additives (
    id SERIAL PRIMARY KEY,
    product_id INTEGER REFERENCES food_products(id),
    additive_id INTEGER REFERENCES additives(id),
    position_in_list INTEGER,  -- Order in ingredient list
    UNIQUE(product_id, additive_id)
);

-- Food categories
CREATE TABLE food_categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    parent_id INTEGER REFERENCES food_categories(id),
    avg_nova_score FLOAT,
    product_count INTEGER
);
```

---

## API Reference

### Endpoints

#### Scan Product

```http
GET /api/foodscore/products/{barcode}
```

**Response:**
```json
{
  "product": {
    "barcode": "0012345678901",
    "name": "Chocolate Chip Cookies",
    "brand": "Generic Brand",
    "image_url": "https://..."
  },
  "scores": {
    "nova_class": 4,
    "nova_label": "Ultra-processed",
    "nova_confidence": 0.94,
    "health_score": 25,
    "nutriscore": "E"
  },
  "ingredients": {
    "text": "Enriched wheat flour, sugar, palm oil...",
    "count": 18,
    "additives": [
      {
        "name": "Red 40",
        "e_number": "E129",
        "risk_score": 85,
        "risk_category": "high",
        "concern": "Petroleum-based dye linked to hyperactivity"
      },
      {
        "name": "TBHQ",
        "risk_score": 60,
        "risk_category": "moderate",
        "concern": "Preservative, limited safety data"
      }
    ]
  },
  "nutrition": {
    "per_100g": {
      "calories": 480,
      "fat": 22,
      "saturated_fat": 10,
      "sugar": 28,
      "sodium": 350,
      "fiber": 2,
      "protein": 5
    }
  },
  "recommendation": "Avoid - Ultra-processed with high-risk additives"
}
```

#### Classify Ingredients

```http
POST /api/foodscore/classify
```

**Request:**
```json
{
  "ingredients": "water, sugar, high fructose corn syrup, citric acid, natural flavors, sodium benzoate, Red 40"
}
```

**Response:**
```json
{
  "nova_class": 4,
  "nova_label": "Ultra-processed",
  "confidence": 0.97,
  "indicators": [
    "high fructose corn syrup",
    "sodium benzoate",
    "Red 40"
  ],
  "additives_detected": [
    {"name": "citric acid", "risk": "low"},
    {"name": "sodium benzoate", "risk": "moderate"},
    {"name": "Red 40", "risk": "high"}
  ]
}
```

#### Score Additive

```http
GET /api/foodscore/additives/{name}
```

**Response:**
```json
{
  "additive": {
    "name": "Red 40",
    "aliases": ["Allura Red", "E129", "FD&C Red No. 40"],
    "type": "dye",
    "e_number": "E129"
  },
  "risk": {
    "score": 85,
    "category": "high",
    "confidence": 0.88
  },
  "regulatory": {
    "fda_status": "approved",
    "eu_status": "approved with warning",
    "banned_in": ["Norway", "Finland"]
  },
  "health_concerns": [
    "Linked to hyperactivity in children",
    "Petroleum-derived",
    "May contain carcinogenic contaminants"
  ],
  "found_in": 3420,
  "alternatives": [
    {"name": "Beet juice", "risk": "low"},
    {"name": "Paprika extract", "risk": "low"}
  ]
}
```

#### Search Products

```http
GET /api/foodscore/products
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| q | string | Search product name |
| brand | string | Filter by brand |
| nova_class | integer | Filter by NOVA level |
| max_risk | integer | Max additive risk score |
| category | string | Product category |
| limit | integer | Results per page |

**Response:**
```json
{
  "total": 1250,
  "products": [
    {
      "barcode": "0012345678901",
      "name": "Organic Apple Sauce",
      "brand": "Simple Foods",
      "nova_class": 1,
      "health_score": 92,
      "additive_count": 0
    }
  ]
}
```

#### Get Healthier Alternatives

```http
GET /api/foodscore/products/{barcode}/alternatives
```

**Response:**
```json
{
  "original": {
    "name": "Sugary Cereal",
    "nova_class": 4,
    "health_score": 22
  },
  "alternatives": [
    {
      "name": "Whole Grain Oats",
      "barcode": "0098765432101",
      "nova_class": 1,
      "health_score": 88,
      "improvement": "+66 health score",
      "reason": "No artificial additives, whole grain, low sugar"
    }
  ]
}
```

---

## Data Statistics

### Product Database

| Metric | Value |
|--------|-------|
| Total Products | 50,000 |
| Products with Additives | 25,105 (50.2%) |
| Avg Additives per Product | 3.63 |
| Unique Additives | 344 |

### NOVA Distribution

| NOVA Level | Count | Percentage |
|------------|-------|------------|
| 4 - Ultra-processed | 22,277 | **70.3%** |
| 3 - Processed | 4,825 | 15.2% |
| 1 - Unprocessed | 3,943 | 12.5% |
| 2 - Culinary | 625 | 2.0% |

### Top Brands

| Brand | Products | Avg NOVA |
|-------|----------|----------|
| Kroger | 4,550 | 3.2 |
| Spartan | 1,340 | 3.4 |
| Roundy's | 1,314 | 3.3 |
| Private Selection | 1,077 | 2.9 |
| Simple Truth | 762 | 1.8 |

### Most Common Additives

| Additive | Products | Risk |
|----------|----------|------|
| Citric Acid | 8,420 | Low |
| Natural Flavors | 7,891 | Low |
| Soy Lecithin | 5,234 | Low |
| Sodium Benzoate | 3,102 | Moderate |
| Red 40 | 2,456 | High |
| Yellow 5 | 2,103 | High |
| TBHQ | 1,892 | Moderate |

---

## Use Cases

### 1. Grocery Shopping

```
Scenario: Parent choosing breakfast cereal
1. Scan cereal box barcode with phone
2. FoodScore shows: NOVA 4, Health Score 25
3. See additives: Red 40 (high risk), BHT (moderate)
4. Tap "Find Alternatives"
5. Switch to NOVA 1 granola, Health Score 85
6. Healthier choice for kids
```

### 2. Dietary Restriction

```
Scenario: Person avoiding artificial dyes
1. Search "crackers" in FoodScore
2. Filter: max_risk = 30 (exclude high-risk additives)
3. Results show only natural crackers
4. Compare options by health score
5. Choose additive-free option
```

### 3. Product Development

```
Scenario: Food company reformulating product
1. Analyze competitor products
2. Identify high-risk additives to avoid
3. Find natural alternatives
4. Reformulate to achieve NOVA 3 or lower
5. Market as "clean label"
```

---

## Configuration

### Environment Variables

```bash
# Database
FOODSCORE_DB_HOST=localhost
FOODSCORE_DB_NAME=healthguard

# ML Models
NOVA_CLASSIFIER_PATH=ml/weights/nova_classifier.pt
NOVA_TOKENIZER_PATH=ml/weights/nova_tokenizer.json
ADDITIVE_SCORER_PATH=ml/weights/additive_scorer.pt

# Thresholds
NOVA_CONFIDENCE_THRESHOLD=0.60
ADDITIVE_HIGH_RISK_THRESHOLD=70
ADDITIVE_MODERATE_RISK_THRESHOLD=30

# OpenFoodFacts
OFF_API_URL=https://world.openfoodfacts.org/api/v0
OFF_USER_AGENT=HealthGuard/1.0
```

### Config File (ml/config.py)

```python
@dataclass
class NOVAClassifierConfig:
    vocab_size: int = 10000
    max_length: int = 200
    embedding_dim: int = 128
    conv_filters: int = 256
    hidden_dims: List[int] = field(default_factory=lambda: [256, 128])
    dropout: float = 0.3
    confidence_threshold: float = 0.60
    weights_path: str = "ml/weights/nova_classifier.pt"
    tokenizer_path: str = "ml/weights/nova_tokenizer.json"

@dataclass
class AdditiveRiskScorerConfig:
    input_features: int = 13
    hidden_dims: List[int] = field(default_factory=lambda: [64, 32])
    dropout: float = 0.3
    weights_path: str = "ml/weights/additive_scorer.pt"
```

---

## File Structure

```
backend/foodscore/
├── __init__.py
├── api/
│   ├── __init__.py
│   ├── products.py           # Product lookup/search
│   ├── classify.py           # NOVA classification
│   ├── additives.py          # Additive scoring
│   └── alternatives.py       # Healthier alternatives
├── models/
│   ├── __init__.py
│   ├── product.py            # FoodProduct ORM
│   ├── additive.py           # Additive ORM
│   └── category.py           # FoodCategory ORM
├── services/
│   ├── __init__.py
│   ├── ingredient_parser.py  # Parse ingredient lists
│   ├── nova_service.py       # NOVA classification
│   └── additive_service.py   # Additive risk scoring
└── data/
    ├── __init__.py
    └── openfoodfacts_loader.py

ml/nova_classifier/
├── __init__.py
├── model.py                  # NOVAClassifier class
├── dataset.py                # Training data
├── train.py                  # Training script
├── inference.py              # Prediction functions
└── tokenizer.py              # Custom tokenizer

ml/additive_scorer/
├── __init__.py
├── model.py                  # AdditiveRiskScorer class
├── dataset.py                # Additive data loading
├── train.py                  # Training script
└── inference.py              # Batch prediction

ml/additive_scorer_plus/
├── __init__.py
├── model.py                  # FoodScore+ with n-grams
├── dataset.py                # Extended dataset
└── train.py                  # Training with weighted loss

data/
├── raw/foodscore/
│   ├── openfoodfacts_us.csv.gz
│   ├── additive_risks.csv
│   └── fda_additives_scraped.csv
└── processed/foodscore/
    ├── nova_training_data.parquet
    └── additive_lookup.parquet
```

---

## Health Score Calculation

### Formula

```python
def calculate_health_score(product):
    """
    Calculate overall health score (0-100).

    Components:
    - NOVA score (40% weight)
    - Additive risk (30% weight)
    - Nutrition quality (30% weight)
    """
    # NOVA component (higher NOVA = lower score)
    nova_score = {1: 100, 2: 75, 3: 50, 4: 25}[product.nova_class]

    # Additive component (average risk of all additives)
    additive_risks = [a.risk_score for a in product.additives]
    additive_score = 100 - (sum(additive_risks) / len(additive_risks)) if additive_risks else 100

    # Nutrition component (NutriScore mapping)
    nutri_score = {'A': 100, 'B': 80, 'C': 60, 'D': 40, 'E': 20}.get(product.nutriscore, 50)

    # Weighted average
    health_score = (
        0.40 * nova_score +
        0.30 * additive_score +
        0.30 * nutri_score
    )

    return round(health_score)
```

---

## Future Enhancements

1. **Barcode Scanner App:** Native mobile app with camera integration
2. **Personalized Alerts:** Warn about allergens or dietary restrictions
3. **Recipe Analysis:** Score homemade recipes
4. **Restaurant Menus:** Analyze menu items from major chains
5. **Trend Tracking:** Monitor product reformulations over time

---

*Documentation generated for HealthGuard FoodScore Module*
