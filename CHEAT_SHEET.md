# HealthGuard America - Comprehensive Cheat Sheet

## Table of Contents
1. [Platform Overview](#1-platform-overview)
2. [System Architecture](#2-system-architecture)
3. [Data Pipeline & Sources](#3-data-pipeline--sources)
4. [ML Model Architectures & Results](#4-ml-model-architectures--results)
5. [Module Deep Dives](#5-module-deep-dives)
6. [Frontend & UI Features](#6-frontend--ui-features)
7. [Site Navigation Guide](#7-site-navigation-guide)
8. [Key Results & Statistics](#8-key-results--statistics)
9. [Quick Reference](#9-quick-reference)

---

## 1. Platform Overview

HealthGuard America is a dual-portal healthcare transparency platform built for the **Presidential AI Challenge**. It integrates **5 federal data modules** with **6 trained ML models** under a unified **MAHA (Make America Healthy Again) Index** that scores and prioritizes public health interventions at the county level across the United States.

**Core thesis:** By linking hospital pricing opacity, drug cost disparities, food supply quality, healthcare access gaps, and chronic disease burden into a single analytical framework, policymakers can allocate resources where they will have the greatest impact on population health.

**Stack:** Python 3.12 / Flask + Jinja2 / PyTorch / BioClinicalBERT / Pandas + Parquet / Chart.js 4.4.1 / Leaflet.js 1.9.4 / Custom CSS design system (no Bootstrap framework)

**Scale:**
| Dimension | Value |
|-----------|-------|
| Total data records | **30.3 million+** |
| Hospitals tracked | 5,421 (1,002 with MRF pricing) |
| Drug records (US + intl) | 75,854 across 3 countries |
| Food products scored | 50,000 |
| Healthcare shortage areas | 14,631 HPSAs |
| Counties with health data | 2,956 |
| ML models trained & deployed | 6 |
| Total model parameters | ~22.8 million |
| HTML templates | 53 |
| API endpoints | 20+ |

### Two Portals

| Portal | URL | Auth | Modules | Audience |
|--------|-----|------|---------|----------|
| **Public** | `/public/` | None | PriceVision, DrugWatch, FoodScore | Consumers, patients, journalists |
| **Government** | `/gov/` | Session login | All 5 (+ RuralAccess, ChronicCare) | Policymakers, analysts, HHS officials |

**Gov Credentials (MVP hardcoded):**
- `admin` / `healthguard2026`
- `analyst` / `maha2026`

### MAHA Index Composition
The MAHA Index (0-100) is a county-level composite score combining all five modules:
```
MAHA Index = weighted combination of:
  Price Transparency  (20%) ← PriceVision: hospital MRF compliance & pricing clarity
  Drug Affordability  (25%) ← DrugWatch: US vs international price gap
  Food Supply Quality (30%) ← FoodScore: NOVA ultra-processing & additive risks
  Access Equity       (25%) ← RuralAccess: HPSA shortage severity & provider density

Priority Thresholds (from Intervention Prioritizer training):
  Critical : risk score > 22  →  top 5th percentile    → immediate intervention
  High     : risk score > 19  →  80th-95th percentile  → high priority
  Medium   : risk score > 16  →  50th-80th percentile  → moderate priority
  Low      : risk score <= 16 →  below 50th percentile → monitoring
```

---

## 2. System Architecture

### System Diagram
```
                          +--------------------+
                          |    Landing Page    |
                          |  (Portal Selector) |
                          +---------+----------+
                                    |
                     +--------------+--------------+
                     |                             |
             +-------v--------+           +--------v---------+
             |  Public Portal |           |   Gov Portal     |
             |  (3 modules)   |           |   (5 modules)    |
             |  No auth       |           |   @gov_required  |
             +-------+--------+           +--------+---------+
                     |                             |
          +----------+----------+    +-------------+-------------+
          |          |          |    |       |       |      |     |
      PriceVis  DrugWatch  FoodScore  PV    DW    FS   Rural  Chronic
          |          |          |    |       |       |      |     |
          +----------+----------+---+-------+-------+------+-----+
                                |
                     +----------v-----------+
                     |    Service Layer     |
                     | (Cached + Indexed)   |
                     +----------+-----------+
                                |
               +----------------+----------------+
               |                |                |
       +-------v------+  +-----v-------+  +-----v--------+
       |  Data Layer  |  |  ML Layer   |  | Cache Layer  |
       | Parquet/CSV  |  |  6 Models   |  | Dict + TTL   |
       +-------+------+  +-----+-------+  +--------------+
                               |
            +------------------+--------------------+
            |          |           |         |       |
         Chronic    Procedure    NOVA    Additive  Additive+
         Risk+Pri   Encoder    Classif   Scorer   Scorer Plus
```

### File Structure
```
HealthGuard/
├── frontend/
│   ├── app.py                         # Flask app entry, startup preload, legacy routes
│   ├── config.py                      # Config classes, gov credentials, module definitions
│   ├── services/                      # Data access layer (all cached)
│   │   ├── __init__.py                # VALID_US_STATES set (50 + DC + territories)
│   │   ├── pricevision.py             # Hospital/procedure/price + transparency scoring
│   │   ├── drugwatch.py               # US/intl drug pricing + NADAC
│   │   ├── foodscore.py               # Food products/additives + NOVA distribution
│   │   ├── ruralaccess.py             # HPSA designations/counties/FQHCs
│   │   └── chroniccare.py             # County health/disease + correlations + priorities
│   ├── blueprints/
│   │   ├── public/                    # Public portal routes (no auth)
│   │   │   ├── __init__.py            # PUBLIC_MODULES constant
│   │   │   ├── pricevision.py         # + ML semantic search, price fairness, hospital analysis
│   │   │   ├── drugwatch.py           # + cached comparisons
│   │   │   └── foodscore.py           # + NOVA/additive ML enrichment, OCR, nutrition analyzer
│   │   └── gov/                       # Gov portal routes (@gov_required)
│   │       ├── __init__.py            # gov_required decorator, login/logout routes
│   │       ├── pricevision.py         # + analytics dashboard, transparency scores
│   │       ├── drugwatch.py           # + MFN analysis, spending trends with pagination
│   │       ├── foodscore.py           # + SNAP batch analysis, additive pattern detection
│   │       ├── ruralaccess.py         # Interactive map, HPSA analytics, county profiles
│   │       └── chroniccare.py         # ML dashboard, interventions, simulator, risk breakdown
│   ├── templates/                     # 53 Jinja2 HTML templates
│   │   ├── base.html                  # Public base (Chart.js, Leaflet, fonts)
│   │   ├── landing.html               # Hero + portal selector + module cards
│   │   ├── gov/base_gov.html          # Gov base (gradient navbar, red border)
│   │   ├── gov/{module}/*.html        # Gov module templates (25 total)
│   │   └── public/{module}/*.html     # Public module templates (22 total)
│   └── static/
│       ├── css/main.css               # Custom design system (~2100 lines)
│       └── js/animations.js           # IntersectionObserver, counters, debounce
├── ml/
│   ├── chroniccare/                   # Risk predictor + intervention prioritizer
│   │   ├── model.py                   # ChronicRiskPredictor, InterventionPrioritizer, FeatureEncoder
│   │   ├── train.py                   # Training loop with early stopping
│   │   ├── inference.py               # ChronicRiskService, InterventionPrioritizationService
│   │   └── dataset.py                 # ChronicCareDataset (PyTorch Dataset)
│   ├── nova_classifier/               # NOVA food group classifier
│   │   ├── model.py                   # NovaClassifier (Conv1D CNN)
│   │   ├── train.py                   # Training with class weights + temperature calibration
│   │   ├── inference.py               # NovaClassificationService
│   │   ├── dataset.py                 # NovaDataset
│   │   └── tokenizer.py              # Custom ingredient tokenizer (10K vocab)
│   ├── additive_scorer/               # Additive risk scoring (small dataset)
│   │   ├── model.py                   # AdditiveRiskScorer MLP
│   │   ├── train.py                   # Training with per-category metrics
│   │   ├── inference.py               # AdditiveRiskService
│   │   └── dataset.py                 # AdditiveDataset
│   ├── additive_scorer_plus/          # Enhanced multi-modal scorer (large dataset)
│   │   ├── model.py                   # AdditiveRiskScorerPlus (DistilBERT fusion)
│   │   └── train.py                   # Multi-modal training
│   ├── procedure_encoder/             # BioClinicalBERT procedure matching
│   │   ├── model.py                   # ProcedureEncoder (transformer + mean pooling)
│   │   ├── train.py                   # Contrastive learning with negative ranking loss
│   │   ├── inference.py               # ProcedureMatchingService
│   │   └── dataset.py                 # ProcedureDataset (contrastive pairs)
│   ├── weights/                       # All saved model artifacts
│   │   ├── chronic_risk_predictor.pt
│   │   ├── intervention_prioritizer.pt
│   │   ├── nova_classifier.pt + nova_classifier_temperature.pt
│   │   ├── additive_scorer.pt + additive_scorer_encoder.json
│   │   ├── additive_scorer_plus.pt
│   │   ├── procedure_encoder.pt (86.7MB)
│   │   ├── canonical_procedure_embeddings.pt
│   │   ├── chronic_feature_scaler.pkl + intervention_feature_scaler.pkl
│   │   ├── nova_tokenizer.json
│   │   └── *_history.json (5 training history files)
│   ├── config.py                      # All hyperparameters for all models
│   └── services.py                    # Unified lazy-loading ML service manager
├── scripts/
│   ├── process_data.py                # Main ETL (PriceVision, DrugWatch, FoodScore, RuralAccess)
│   ├── chroniccare_pipeline.py        # ChronicCare ETL (CDC + CMS + USDA merge)
│   ├── generate_results.py            # Analysis charts & reports
│   ├── download_new_data.py           # Data download from APIs
│   ├── crawl_hospital_mrfs.py         # Hospital MRF URL discovery
│   └── expand_additive_dataset.py     # Additive risk data expansion
├── data/
│   ├── raw/                           # Original government data (~1.4GB)
│   └── processed/                     # Cleaned parquet files (~790MB)
├── results/                           # Training charts & analysis visualizations
│   └── *.png                          # 10+ generated charts
└── docs/
    ├── DATA_SOURCES.md
    ├── ANALYSIS_REPORT.md
    ├── TECHNICAL_DOCUMENTATION.md
    └── modules/                       # Per-module documentation
```

### Caching Architecture
```
Request → Route-Level Cache (TTL or permanent)
            → Service-Level Cache (class dict, permanent until restart)
                → DataFrame Cache (_df_cache, loaded once from disk)
                    → Parquet/CSV files on disk

Cache Types:
┌─────────────────────────────────────────────────────────────────────────┐
│ O(1) Index Lookups (hash map → DataFrame row index):                   │
│   hospital_by_id    : Facility ID → hospital record                    │
│   barcode_index     : product barcode → product record                 │
│   fips_index        : FIPS code → county record (ChronicCare)          │
│   hpsa_by_id        : HPSA ID → HPSA record                           │
│   county_by_fips    : county FIPS → county record (RuralAccess)        │
│   drug_index        : brand/generic name → drug record                 │
│   additive_index    : e_number or name → additive record               │
├─────────────────────────────────────────────────────────────────────────┤
│ Computed Result Caches (calculated once, stored permanently):           │
│   stats, correlations, priorities, transparency_data, state_stats,     │
│   nova_distribution, categories, states_list, map_data, analytics,     │
│   high_risk products, category_stats, nadac_stats, top_hospitals       │
├─────────────────────────────────────────────────────────────────────────┤
│ Route-Level TTL Caches (expire after N seconds):                       │
│   api_stats (300s), snap_analysis (300s)                               │
├─────────────────────────────────────────────────────────────────────────┤
│ Bounded LRU Caches (evict oldest half at capacity):                    │
│   drug_detail_cache (300), ml_search_cache (200),                      │
│   hospital_detail_cache (100), price_fairness_cache (200),             │
│   ml_enrichment_cache (200), mfn_cache (50), trends_cache (100),       │
│   analytics_cache (50), hospital_list_cache (60),                      │
│   comparison_cache (200)                                               │
└─────────────────────────────────────────────────────────────────────────┘
```

### Startup Preload Sequence
```
python frontend/app.py
  → preload_all() launches 2 background threads:
    Thread 1 - Data Loading:
      1. PriceVision: procedures, hospital index, states, hospitals_with_mrf
      2. DrugWatch: US drugs DF, international prices
      3. FoodScore: products DF, additives, NOVA distribution, categories
      4. RuralAccess: HPSA DF, counties DF, states
      5. ChronicCare: county health DF, states, FIPS index
    Thread 2 - ML Model Loading:
      1. ProcedureMatchingService (86.7MB weights + embeddings)
      2. NovaClassificationService (vocab + CNN + temperature)
      3. AdditiveRiskService (encoder + MLP)
      4. ChronicCareMLService (risk predictor + prioritizer + scalers)
  → Flask server starts on http://0.0.0.0:5000
```

---

## 3. Data Pipeline & Sources

### Source Agencies & Datasets

| Module | Agency | Dataset | Format | Raw Size | Records |
|--------|--------|---------|--------|----------|---------|
| **PriceVision** | CMS | Hospital Machine-Readable Files | CSV/JSON/XLSX | 18 MRF files | **30,200,589** prices |
| | CMS | Hospital General Information | CSV | 1.6MB | 5,421 hospitals |
| | CMS | Medicare Physician & Practitioners | CSV | ~460KB | ~10K procedures |
| **DrugWatch** | CMS | Medicare Part D Spending 2023 | CSV | varies | **3,598** US drugs |
| | PBS Australia | Pharmaceutical Benefits Scheme | 36 CSV files | varies | **14,598** AU drugs |
| | PMPRB Canada | Patented Medicine Prices Review | JSON | varies | **57,658** CA records |
| | CMS | NADAC Pharmacy Acquisition Costs | Parquet | 6.7MB | ~100K prices |
| | VA | Veterans Affairs Formulary/Pricing | CSV | varies | ~100 records |
| **FoodScore** | OpenFoodFacts | US Food Product Database | CSV.GZ | 1.2GB | **50,000** products |
| | USDA | Branded Food Database (FoodData Central) | 12 CSV files | 207MB | ~300K items |
| | FDA | Additive Risk Database (curated) | CSV | 16KB | 125 additives |
| | FDA | Food Recalls & Enforcement | JSON | 3.7MB | ~5K recalls |
| **RuralAccess** | HRSA | HPSA Designations Database | CSV | 43MB | **14,631** HPSAs |
| | Census | County Boundaries & Population | Shapefile+JSON | 80MB+156KB | 3,200+ counties |
| | CMS | Hospital Closures & Quality | CSV | 422KB | ~1K records |
| | HRSA | FQHC Locations | Parquet | 1.4MB | ~12K centers |
| | NPI | National Provider Index | ZIP | 988MB | millions |
| **ChronicCare** | CDC | PLACES County Health Estimates 2023 | CSV | 51MB | 29K+ locations |
| | CMS | County Health Rankings 2024 | CSV | 13MB | 3,200+ counties |
| | USDA | Food Environment Atlas | XLSX | 8.7MB | ~3K counties |

### ETL Pipeline
```
1. DOWNLOAD   scripts/download_new_data.py
              scripts/chroniccare_pipeline.py (download_cdc_places, download_usda_food_atlas)
              scripts/crawl_hospital_mrfs.py (discover MRF URLs from CMS)
                    ↓
2. EXTRACT    scripts/process_data.py
              - PriceVisionProcessor: Detect format (CMS v2/v3, XPath, simple, metadata)
              - DrugWatchProcessor: Parse Part D, merge AU/CA/VA
              - FoodScoreProcessor: Parse OpenFoodFacts, USDA branded, additive risks
              - RuralAccessProcessor: Filter HPSA to "Designated" status only
              scripts/chroniccare_pipeline.py
              - process_cdc_places(), process_cms_geographic(), process_usda_food_atlas()
                    ↓
3. NORMALIZE  Column standardization (100+ variant mappings for PriceVision)
              NaN cleaning, type casting, currency conversion (AUD→USD: 0.65x)
              Encoding support: UTF-8, UTF-8-sig, Latin-1, CP1252, ISO-8859-1
                    ↓
4. MERGE      ChronicCare: merge 3 datasets on county FIPS code → chroniccare_merged.parquet
              PriceVision: normalize 18 MRF files → all_prices_normalized.parquet
                    ↓
5. STORE      data/processed/{module}/*.parquet (total ~790MB)
                    ↓
6. TRAIN      ml/{module}/train.py → ml/weights/*.pt
                    ↓
7. SERVE      frontend/services/*.py (cached DataFrame access with O(1) indexes)
```

### Processed Data Sizes
```
data/processed/
├── pricevision/     389MB  (375MB all_prices_normalized.parquet + 14MB training data)
├── foodscore/       362MB  (207MB USDA branded + 147MB NOVA training + 4.8MB products)
├── chroniccare/      27MB  (3.6MB merged + supporting datasets)
├── drugwatch/       9.5MB  (6.7MB NADAC + US/AU/CA drugs)
└── ruralaccess/     2.4MB  (414KB HPSA + 1.4MB FQHC + supporting)
```

---

## 4. ML Model Architectures & Results

### Model 1: Chronic Risk Predictor

| Property | Value |
|----------|-------|
| **Type** | Multi-Task Regression Neural Network (PyTorch) |
| **Purpose** | Predict 6 chronic disease prevalences from 19 county-level features |
| **Weights** | `ml/weights/chronic_risk_predictor.pt` |
| **Parameters** | ~500K |
| **Training data** | 2,956 counties from `chroniccare_merged.parquet` |

**Architecture:**
```
Input(19) → Dense(256)→BatchNorm→ReLU→Dropout(0.3)
          → Dense(128)→BatchNorm→ReLU→Dropout(0.3)
          → Dense(64)→BatchNorm→ReLU→Dropout(0.3)
          → 6 Task-Specific Heads:
              each: Dense(64)→ReLU→Dense(1) → inverse sqrt scaling
```

**19 Input Features:**
| Category | Features |
|----------|----------|
| Food Environment (5) | `grocery_stores_per_1000`, `fast_food_restaurants_per_1000`, `food_environment_index`, `food_insecurity_rate`, `pct_limited_food_access` |
| Healthcare Access (4) | `pcp_rate`, `mental_health_provider_rate`, `pct_uninsured`, `preventable_hospitalizations` |
| Socioeconomic (5) | `median_household_income`, `child_poverty_rate`, `income_inequality_ratio`, `high_school_graduation_rate`, `pct_some_college` |
| Behavioral (4) | `physical_inactivity_prevalence`, `excessive_drinking_prevalence`, `smoking_prevalence`, `pct_insufficient_sleep` |
| Demographics (1) | `pct_rural` |

**6 Output Targets:**
| Disease | Validation MAE | Interpretation |
|---------|---------------|----------------|
| Diabetes prevalence | **1.36%** | Within 1.36 percentage points |
| Obesity prevalence | **2.30%** | Within 2.30 percentage points |
| Heart disease prevalence | **0.99%** | Within 0.99 percentage points |
| High blood pressure prevalence | **3.02%** | Within 3.02 percentage points |
| COPD prevalence | **0.88%** | Best accuracy - within 0.88 pp |
| Depression prevalence | **2.10%** | Within 2.10 percentage points |
| **Overall MAE** | **1.76%** | |

**Training:** AdamW (lr=1e-3, wd=1e-4), MSE loss, batch 64, 200 max epochs, ReduceLROnPlateau, early stop patience 20. Best epoch: **54 of 77** (val loss: 5.5326).

---

### Model 2: Intervention Prioritizer

| Property | Value |
|----------|-------|
| **Type** | 4-Class Classification MLP (PyTorch) |
| **Purpose** | Assign MAHA intervention priority tier to counties |
| **Weights** | `ml/weights/intervention_prioritizer.pt` |
| **Parameters** | 13,092 |
| **Training time** | ~10 seconds |

**Architecture:**
```
Input(16) → Dense(128)→BatchNorm→ReLU→Dropout(0.3)
          → Dense(64)→BatchNorm→ReLU→Dropout(0.3)
          → Dense(32)→BatchNorm→ReLU→Dropout(0.3)
          → Dense(4) → Softmax → {Critical, High, Medium, Low}
```

**16 Input Features:** Disease burden (5), food environment (5), healthcare access (3), demographics (3)

**Training Results:**
| Metric | Value |
|--------|-------|
| **Overall Accuracy** | **93.9%** |
| **Best Val Loss** | 0.2313 |
| **Best Epoch** | 38 of 55 |

**Per-Class Accuracy:**
| Priority Tier | Accuracy | Training Support | % of Data |
|--------------|----------|-----------------|-----------|
| Critical | **82.8%** | 148 samples | 5.0% |
| High | **93.3%** | 444 samples | 15.1% |
| Medium | **85.7%** | 886 samples | 30.0% |
| Low | **95.7%** | 1,469 samples | 49.9% |

**Training:** AdamW, CrossEntropy with class weights [10.0, 3.0, 1.0, 1.0] (heavy upweighting of Critical), batch 32, 100 max epochs, early stop 15. Labels generated via MAHAIndexCalculator using percentile-based thresholds.

**Accuracy progression:** Started at 61.46% → reached 93.88% by epoch 38.

---

### Model 3: NOVA Food Classifier

| Property | Value |
|----------|-------|
| **Type** | 1D Convolutional Neural Network (PyTorch) |
| **Purpose** | Classify food products into NOVA processing groups from ingredient text |
| **Weights** | `ml/weights/nova_classifier.pt` + `nova_classifier_temperature.pt` |
| **Parameters** | ~500K |
| **Train/Val samples** | 808,062 / 101,007 |

**Architecture:**
```
Ingredient text → Tokenize (vocab=10,000, max_len=200)
  → Embedding(10000, 128, padding_idx=0)
  → Conv1D(128→256, kernel=3, same padding) → ReLU → GlobalAvgPool
  → Dense(256)→BatchNorm→ReLU→Dropout(0.3)
  → Dense(128)→BatchNorm→ReLU→Dropout(0.3)
  → Dense(4) → TemperatureScaling → Softmax
```

**Training Results (Best: Epoch 4 of 9):**
| Metric | Value |
|--------|-------|
| **Overall Accuracy** | **96.29%** |
| **Macro F1** | 0.9110 |
| **Weighted F1** | 0.9632 |
| **Val Loss** | 0.2234 |
| **Mean Confidence** | 0.9600 |
| **ECE (calibration error)** | 0.369% |

**Per-Class Performance:**
| NOVA Group | Description | Precision | Recall | F1 | Support |
|-----------|-------------|-----------|--------|-----|---------|
| 1 | Unprocessed/minimally processed | 90.87% | 94.17% | 0.9249 | 10,054 |
| 2 | Processed culinary ingredients | 75.72% | 87.62% | 0.8124 | 1,591 |
| 3 | Processed foods | 92.65% | 91.90% | 0.9228 | 20,108 |
| 4 | Ultra-processed products | 98.72% | 98.08% | 0.9840 | 69,254 |

**Training:** Adam (lr=1e-3), CrossEntropy with class weights [6.67, 20.0, 5.0, 1.67] (inverse frequency), batch 64, 20 max epochs, early stop 5. Temperature calibration via LBFGS on validation set.

**Indicators Analysis:** The model also detects NOVA 4 indicator ingredients (e.g., "high fructose corn syrup", "artificial flavors") for interpretability.

---

### Model 4: Additive Risk Scorer

| Property | Value |
|----------|-------|
| **Type** | Regression MLP (PyTorch) |
| **Purpose** | Score food additive risk (0-100) from categorical features |
| **Weights** | `ml/weights/additive_scorer.pt` + `additive_scorer_encoder.json` |
| **Parameters** | ~2K |
| **Dataset** | 42 curated additives (small expert-labeled set) |

**Architecture:**
```
13 one-hot features → Dense(64)→ReLU→Dropout(0.2)
                    → Dense(32)→ReLU→Dropout(0.2)
                    → Dense(1) → Sigmoid → ×100
```

**13 Input Features (one-hot encoded):**
- Type (6): dye, sweetener, preservative, emulsifier, flavor, other
- FDA status (2): approved, banned
- EU status (3): approved, restricted, banned
- Binary (2): is_artificial, is_petroleum_based

**Training Results (Best: Epoch 56 of 86):**
| Metric | Value |
|--------|-------|
| **Category Accuracy** | **85.71%** |
| **R-squared** | 0.5109 |
| **Pearson r** | 0.7371 |
| **Spearman r** | 0.7143 |
| **MAE** | 17.32 |
| **RMSE** | 21.26 |

**Per-Category Breakdown:**
| Risk Category | Range | Accuracy | Mean Error |
|--------------|-------|----------|------------|
| Low | 0-29 | 50% | 33.21 |
| Moderate | 30-69 | **100%** | 12.82 |
| High | 70-100 | **100%** | 8.17 |

---

### Model 5: Additive Risk Scorer Plus

| Property | Value |
|----------|-------|
| **Type** | Multi-Modal Fusion Network (DistilBERT + Categorical) |
| **Purpose** | Enhanced additive scoring using text + structured features |
| **Weights** | `ml/weights/additive_scorer_plus.pt` (~200MB) |
| **Dataset** | 344 additives (expanded dataset with n-gram features) |

**Architecture:**
```
Additive name → DistilBERT (max 32 tokens) → Linear(768→128) ─┐
Categorical features → Embeddings ─────────────────────────────┤
                                                               → Concat
                                                               → FusionNet(256, 3 residual blocks)
                                                               → Dense(1) → Sigmoid → ×100
```

**Training Results (Best: Epoch 52):**
| Metric | Value |
|--------|-------|
| **Category Accuracy** | **56.60%** |
| **R-squared** | 0.3906 |
| **Pearson r** | 0.6310 |
| **Spearman r** | 0.7016 |
| **MAE** | 18.32 |

*Note: Lower accuracy than the small-dataset scorer due to noisier expanded dataset. The small scorer (Model 4) is used in production; this model is experimental.*

---

### Model 6: Procedure Encoder

| Property | Value |
|----------|-------|
| **Type** | Fine-tuned BioClinicalBERT with Mean Pooling |
| **Purpose** | Semantic matching of free-text procedure descriptions to CPT codes |
| **Base model** | `emilyalsentzer/Bio_ClinicalBERT` (12 layers, 768 hidden) |
| **Weights** | `ml/weights/procedure_encoder.pt` (86.7MB) + `canonical_procedure_embeddings.pt` |
| **Parameters** | **22,713,216** (largest model) |
| **Training data** | 360K+ procedure description variations |
| **Training time** | ~6 hours |

**Architecture:**
```
Procedure text (max 128 tokens)
  → BioClinicalBERT tokenizer
  → BioClinicalBERT forward → token_embeddings [batch, seq, 768]
  → Mean pooling (attention-mask weighted) → [batch, 768]
  → L2 normalize → unit-norm embedding
```

**Matching Pipeline:**
```
1. Encode query → 768-dim embedding
2. Cosine similarity vs pre-computed canonical CPT embeddings
3. Threshold:
   ≥ 0.80  → Confident match
   0.65-0.80 → Needs human review
   < 0.65  → No match
```

**Training Results:**
| Metric | Value |
|--------|-------|
| **Final Training Loss** | 0.4492 |
| **Mean Positive Similarity** | 0.6864 |
| **Final Val Loss** | 5.7464 |

**Validation Examples:**
| Query | Candidate | Similarity | Result |
|-------|-----------|-----------|--------|
| "MRI BRAIN WITHOUT CONTRAST" | "MRI HEAD W/O CONTRAST" | **0.816** | Match |
| "MRI BRAIN WITHOUT CONTRAST" | "70551 MRI BRAIN WO" | **0.880** | Match |
| "TOTAL KNEE REPLACEMENT" | "KNEE ARTHROPLASTY" | 0.685 | Similar |
| "MRI BRAIN" | "COMPLETE BLOOD COUNT" | 0.135 | Different |
| "CT CHEST" | "KNEE XRAY" | 0.295 | Different |

**Training:** AdamW (lr=2e-5, wd=0.01), MultipleNegativesRankingLoss (contrastive), 3 epochs, batch 32, linear warmup (0.1 ratio). Pairs: procedures sharing the same CPT code = positive.

---

### ML Integration Map
```
Module          Model(s) Used                       Where in App
─────────────  ──────────────────────────────────   ─────────────────────────
PriceVision  → Procedure Encoder                    Search (semantic match),
                                                    Compare (related procedures)
DrugWatch    → (none - statistical analysis only)   —
FoodScore    → NOVA Classifier                      Product detail, Analyze, SNAP batch
             → Additive Scorer                      Product detail, Search enrichment,
                                                    SNAP additive patterns
RuralAccess  → (none - geospatial analysis only)    —
ChronicCare  → Chronic Risk Predictor               Dashboard hotspots, County profile,
                                                    Interventions page, Simulator
             → Intervention Prioritizer             Same routes + MAHA index scoring
```

---

## 5. Module Deep Dives

### 5A. PriceVision - Hospital Price Transparency

**What it solves:** The CMS Hospital Price Transparency Rule (effective Jan 2021) requires hospitals to publish machine-readable files of their prices. PriceVision normalizes 18 different hospital MRF formats into a single queryable database of 30.2M price records, enabling consumers to compare procedure costs across hospitals.

**Workflow:**
```
Hospital MRF (CSV/JSON/XLSX, 6+ format variants)
  → Format detection (CMS v2/v3, XPath, simple, metadata, banner)
  → Parse & normalize to 14 standard columns
  → all_prices_normalized.parquet (30.2M rows, 375MB)
                    ↓
    ┌───────────────┼───────────────────┐
    ↓               ↓                   ↓
Procedure Search  Price Compare       Hospital Profile
(ML semantic)     (z-score fairness)  (markup analysis)
    ↓               ↓                   ↓
BioClinicalBERT   Statistical          Transparency
768-dim matching   clustering          score (0-100)
```

**Price Statistics (from 30.2M records):**
| Price Column | Mean | Median | Min | Max | Coverage |
|-------------|------|--------|-----|-----|----------|
| Gross Charge | $29,442 | $518 | $0 | $9,960,013 | 73.7% (22.3M) |
| Cash Price | $3,519 | $357 | $0 | $9,965,976 | 67.2% (20.3M) |
| Min Price | $1,121 | $63 | $0 | $4,887,658 | 55.9% (16.9M) |
| Max Price | $6,465 | $436 | $0 | $8,835,750 | 56.3% (17.0M) |
| Negotiated Rate | $1,288 | $171 | $0.0016 | $8,207,066 | 35.5% (10.7M) |

**Top Payers in Data:** CIGNA-ALL (175K records), UHC MCR ADV (159K), MULTIPLAN (125K), AETNA (124K)

**Key Features by Route:**
| Route | Feature | ML Used |
|-------|---------|---------|
| `/pricevision/search` | Text search finds procedures by meaning, not just keywords | Procedure Encoder (BioClinicalBERT) |
| `/pricevision/compare` | Z-score analysis labels each hospital's price as Fair/Overpriced/Discount | Statistical (z > 1.5 = Overpriced, z < -1.5 = Discount) |
| `/pricevision/my-price` | Enter your quoted price → get verdict, percentile rank, potential savings | Statistical + percentile |
| `/pricevision/hospital/<npi>` | Hospital markup analysis, pricing consistency, specialty breakdown | CPT range lookup |
| `/pricevision/analytics` (gov) | State compliance rates, 10K hospital coverage, suspicious gaps | Aggregate analysis |

---

### 5B. DrugWatch - Drug Price Comparison

**What it solves:** Americans pay significantly more for prescription drugs than other developed nations. DrugWatch links Medicare Part D spending data with Australian PBS and Canadian PMPRB prices to quantify the gap and estimate savings under Most Favored Nation (MFN) pricing.

**Key Data Points:**
| Metric | Value |
|--------|-------|
| Total Medicare Part D spending (2023) | **$275.9 billion** |
| Total beneficiaries | **478.6 million** |
| Mean price per unit | $563.02 |
| Median price per unit | $8.86 |

**Top 10 Drugs by Medicare Spending:**
| Rank | Drug (Generic) | 2023 Spending |
|------|---------------|---------------|
| 1 | Eliquis (Apixaban) | **$18.27B** |
| 2 | Ozempic (Semaglutide) | $9.19B |
| 3 | Jardiance (Empagliflozin) | $8.84B |
| 4 | Trulicity (Dulaglutide) | $7.36B |
| 5 | Xarelto (Rivaroxaban) | $6.31B |
| 6 | Trelegy Ellipta | $4.46B |
| 7 | Humira Pen (Adalimumab) | $4.42B |
| 8 | Farxiga (Dapagliflozin) | $4.34B |
| 9 | Januvia (Sitagliptin) | $4.09B |
| 10 | Revlimid (Lenalidomide) | $3.86B |

**Most Expensive Drugs Per Unit:**
| Drug | Price/Unit |
|------|-----------|
| Amvuttra (Vutrisiran Sodium) | **$239,746** |
| Vabysmo (Faricimab-Svoa) | $46,702 |
| Givlaari (Givosiran Sodium) | $41,427 |

**Gov-Only Features:**
- **MFN Analysis:** Estimates 30% savings if US adopted lowest international price
- **Spending Trends:** Paginated drug spending with 5-year trend charts, YoY growth

---

### 5C. FoodScore - Food Product Health Scoring

**What it solves:** Ultra-processed foods make up ~60% of American calorie intake and are linked to obesity, diabetes, and heart disease. FoodScore scores 50,000 US products using ML-powered NOVA classification and additive risk analysis, giving consumers instant health insights from a barcode scan.

**Product Distribution:**
| NOVA Group | Count | % of Scored | Description |
|-----------|-------|-------------|-------------|
| 4 - Ultra-processed | 22,277 | **70.3%** | Soft drinks, chips, instant noodles |
| 3 - Processed | 4,825 | 15.2% | Canned vegetables, cheese, bread |
| 1 - Unprocessed | 3,943 | 12.5% | Fresh fruits, vegetables, meat |
| 2 - Culinary ingredients | 625 | 2.0% | Oils, butter, sugar, salt |

**MAHA Health Score Distribution (50,000 products):**
| Score Range | Count | % | Rating |
|------------|-------|---|--------|
| 90-100 | 22,221 | 44.4% | Excellent |
| 75-90 | 5,526 | 11.1% | Good |
| 50-75 | 15,007 | 30.0% | Moderate |
| 25-50 | 6,106 | 12.2% | Poor |
| 0-25 | 1,140 | 2.3% | Very Poor |
| **Mean: 76.56** | **Median: 83.0** | **Std: 23.30** | |

**Nutrition Averages (per 100g):**
| Nutrient | Mean | Median |
|----------|------|--------|
| Energy | 429 kcal | 265 kcal |
| Sugars | 20.68g | 6.13g |
| Fat | 17.26g | 4.32g |
| Sodium | 0.92g | 0.17g |

**Top Brands:** Kroger (4,550 products), Spartan (1,340), Roundy's (1,314), Private Selection (1,077), Simple Truth (762)

**Additive Analysis:** 25,105 products (50.2%) contain additives, averaging 3.63 additives per product.

**Special Features:**
- **OCR nutrition label reading** - 3 engine fallback chain: pytesseract → Windows OCR → easyocr
- **Barcode scanner** - instant product lookup via camera
- **SNAP analysis (gov)** - batch ML classification of SNAP-eligible products, identifies most common high-risk additives with example products

---

### 5D. RuralAccess - Healthcare Shortage Mapping (Gov Only)

**What it solves:** 80+ million Americans live in healthcare professional shortage areas. RuralAccess maps all 14,631 HPSAs, tracks rural hospital closures, and correlates shortages with poverty to guide resource allocation.

**HPSA Statistics:**
| Metric | Value |
|--------|-------|
| Total HPSA designations | **14,631** |
| Unique counties affected | 2,833 |
| States/territories with HPSAs | 59 |
| Total population in HPSAs | **957 million** (cumulative across designations) |
| Mean population per HPSA | 65,451 |
| Average poverty rate in HPSAs | **23.57%** |

**HPSA Score Distribution (0-25 scale):**
| Level | Score Range | Significance |
|-------|------------|--------------|
| Critical | 20-25 | Severe shortage, immediate action needed |
| High | 15-19 | Significant shortage |
| Moderate | 10-14 | Moderate shortage |
| Low | 0-9 | Minor shortage |
| **Mean: 15.12** | **Median: 16.0** | |

**Rural Status Distribution:**
| Status | Count | % |
|--------|-------|---|
| Non-Rural | 7,953 | 54.4% |
| Rural | 5,322 | 36.4% |
| Partially Rural | 1,232 | 8.4% |
| Unknown | 124 | 0.8% |

**Top 10 States by HPSA Count:**
NY (1,820), CA (1,246), OH (1,071), AZ (700), TX (692), IL (530), WI (506), MN (483), TN (480), KY (368)

**Key Features:**
- Interactive Leaflet.js map with 5,000 geocoded markers (color-coded by severity)
- 7-filter sidebar: state, discipline, shortage level, rural status, designation type, limit
- County profiles with local HPSA list + FQHC locations
- Analytics: shortage distribution histograms, state rankings, poverty correlation analysis

---

### 5E. ChronicCare - Chronic Disease Risk Prediction (Gov Only)

**What it solves:** Chronic diseases (diabetes, obesity, heart disease) account for 90% of US healthcare spending ($4.1T/year). ChronicCare uses ML to predict disease prevalence from modifiable factors and prioritize which counties need intervention most urgently.

**National Averages (2,956 counties):**
| Disease | Mean | Median | Max |
|---------|------|--------|-----|
| Diabetes prevalence | **12.36%** | 12.1% | 25.1% |
| Obesity prevalence | **37.52%** | 38.1% | 54.0% |
| Heart disease prevalence | **6.89%** | 6.6% | 13.1% |
| Food environment score | 49.88 | - | 100 |
| Population with low food access | 18.16% | - | - |

**Intervention Priority Distribution:**
| Tier | Counties | % |
|------|---------|---|
| Medium | 1,673 | 56.6% |
| Low | 1,063 | 36.0% |
| High | 211 | 7.1% |
| Critical | ~9 | 0.3% |

**Workflow:**
```
County data (2,956 counties, 3 merged datasets)
  → Extract 19 features (food env + healthcare + socioeconomic + behavioral)
  → Chronic Risk Predictor → 6 disease prevalence predictions
  → Intervention Prioritizer → MAHA index + priority tier
  → Risk Breakdown → Top 8 contributing factors with contribution scores
  → Intervention Recommendations → Targeted actions with:
      - Estimated risk reduction (e.g., "8-12%")
      - Impact level (High/Medium/Low)
      - Cost tier (Low/Medium/High)
```

**12 Risk Factors Analyzed:**
| Factor | Threshold | Category | Weight |
|--------|-----------|----------|--------|
| Physical Inactivity | >28% | Behavioral | 0.15 |
| Food Insecurity | >15% | Food Environment | 0.12 |
| Smoking | >18% | Behavioral | 0.10 |
| Lack of Insurance | >12% | Healthcare | 0.10 |
| Low PCP Access | <50/100K | Healthcare | 0.08 |
| Limited Food Access | >10% | Food Environment | 0.08 |
| Child Poverty | >20% | Socioeconomic | 0.08 |
| High Fast Food Density | >0.8/1K | Food Environment | 0.07 |
| Low Grocery Access | <0.2/1K | Food Environment | 0.06 |
| Insufficient Sleep | >35% | Behavioral | 0.06 |
| Excessive Drinking | >20% | Behavioral | 0.05 |
| Low Education | <85% grad rate | Socioeconomic | 0.05 |

**Key Features:**
- **MAHA Dashboard** - ML-identified emerging hotspots (counties where predicted risk > actual), top risk factors across analyzed counties, model confidence badge (93.9%)
- **ML Simulator** - Adjust all 19 features with sliders, see real-time disease predictions and priority tier changes
- **County profiles** - Full risk breakdown (top 8 factors), ML predictions vs actual prevalence, 5 targeted intervention recommendations

---

## 6. Frontend & UI Features

### Design System

**Typography:**
- Display: Plus Jakarta Sans (600-800 weight)
- Body: Inter (300-700 weight)
- Mono: JetBrains Mono
- Sizes: xs (12px) through 6xl (60px) with `clamp()` fluid scaling

**Color Palette:**
| Purpose | Color | Hex |
|---------|-------|-----|
| Primary brand | Blue | `#2563eb` (50-900 scale) |
| Government accent | Red | `#b91c1c` |
| PriceVision | Amber | `#f59e0b` |
| DrugWatch | Red | `#ef4444` |
| FoodScore | Green | `#22c55e` |
| RuralAccess | Purple | `#8b5cf6` |
| ChronicCare | Cyan | `#06b6d4` |

**Spacing:** 1-24 units (0.25rem-6rem) | **Radius:** sm(4px)-full(9999px) | **Shadows:** sm-xl layered | **Transitions:** fast(150ms), base(200ms), slow(300ms)

### Libraries Loaded
- **Chart.js 4.4.1** (deferred) - all data visualizations
- **Leaflet.js 1.9.4** (deferred) - interactive maps
- **Bootstrap Icons 1.11.3** - icon system
- **Google Fonts** - Inter + Plus Jakarta Sans

### Chart Types Used (Chart.js)
| Type | Where Used | What It Shows |
|------|-----------|---------------|
| Horizontal Bar | DrugWatch trends, RuralAccess analytics | Top drugs by spending, states by HPSA count |
| Vertical Bar | ChronicCare dashboard, analytics | Disease prevalence comparisons, state breakdowns |
| Line | DrugWatch trends | 5-year spending trends |
| Doughnut | ChronicCare dashboard, DrugWatch | Risk distribution, spending concentration |
| Pie | Various | Category distributions |

### Map Implementations (Leaflet.js)
| Map | Template | Markers | Features |
|-----|----------|---------|----------|
| HPSA Shortage Map | `gov/ruralaccess/map.html` | Up to 14,631 HPSAs | 7 filters, color by severity, popups, legend |
| ChronicCare County Map | `gov/chroniccare/dashboard.html` | 2,956 counties | Circle markers, color by risk, toggle diseases |

### CSS Animations & Interactions
| Animation | Trigger | Effect |
|-----------|---------|--------|
| `fadeIn` | Page load | opacity 0→1 (0.4s) |
| `slideUp` | Scroll into view / page load | translateY(20px)→0 + fade (0.4s) |
| `slideInLeft` | Scroll | translateX(-20px)→0 + fade |
| `pulse` | Loading states | opacity blink 1→0.5 (2s infinite) |
| `bounce` | Attention elements | Y-translate oscillation (1s infinite) |
| `shimmer` | Skeleton loading | gradient sweep left→right |
| `pageEnter` | Page load | opacity + slight rise |
| Staggered card reveal | Scroll (IntersectionObserver) | Cards fade in sequentially (0.08s delay each) |
| Progress bar fill | Scroll into view | Width 0%→target (0.8s ease-out) |
| Number counter | Scroll into view | Count from 0 to target with easeOut |
| Navbar shadow | Scroll > 10px | Box-shadow appears |
| Card hover | Mouse enter | translateY(-2px) + shadow elevation |
| Module card hover | Mouse enter | translateY(-8px) + image scale(1.05) |

### Special UI Components
- **Skeleton loading screens** - `.skeleton-text`, `.skeleton-circle` pulse animations
- **Stat cards** - Module-colored 5px left border, animated counting, responsive grid
- **Badge system** - Primary/Success/Warning/Danger + pill/outline variants
- **Progress bars** - Animated fill + shimmer effect
- **Frosted glass cards** - Landing page portal selector with `backdrop-filter: blur`
- **Breadcrumb navigation** - Chevron-separated path from landing → module → page
- **Debounced search** - Auto-submit after 500ms pause (min 2 chars)
- **Pagination** - Smart ellipsis (1-3 ... N-3 to N)
- **Filter sidebars** - Sticky scroll, collapsible, multi-dropdown

### Gov vs Public Portal Differences
| Aspect | Public | Government |
|--------|--------|-----------|
| Navbar | White background, dark text | Blue gradient + **3px red bottom border** |
| Brand | Standard logo | Logo + "GOV" badge (white, semi-transparent) |
| Nav text | Dark links | White text (0.85 opacity → 1 on hover) |
| Modules | 3 (Price, Drug, Food) | 5 (+ Rural, Chronic) |
| ML features | Basic (per-product) | Advanced (batch, patterns, simulator) |
| Analytics | None | Compliance, trends, SNAP, shortage maps |

### Template Inventory (53 total)
```
Layout:     3 (base.html, gov/base_gov.html, public/base_public.html)
Landing:    1 (landing.html)
Legacy:     3 (index.html, module.html, hospitals.html, urls.html)
Gov Auth:   2 (gov/login.html, gov/home.html)
Public:     1 (public/home.html)
PriceVision: 12 (6 public + 6 gov)
DrugWatch:  10 (4 public + 6 gov)
FoodScore:  11 (5 public + 6 gov)
RuralAccess: 5 (gov only)
ChronicCare: 7 (gov only)
```

---

## 7. Site Navigation Guide

### Getting Started
```
http://localhost:5000/            ← Landing page (choose portal)
http://localhost:5000/public/     ← Public portal (no login needed)
http://localhost:5000/gov/login   ← Gov portal (admin / healthguard2026)
```

### Complete Route Map

**Public Portal - PriceVision:**
| URL | Purpose |
|-----|---------|
| `/public/pricevision/` | Home - summary stats, sample hospitals & procedures |
| `/public/pricevision/search?q=knee+replacement&type=procedure&state=CA` | ML semantic search |
| `/public/pricevision/compare?procedure=27447&state=NY` | Price comparison with fairness clustering |
| `/public/pricevision/hospital/050454` | Hospital pricing profile + markup analysis |
| `/public/pricevision/my-price?procedure=27447&price=25000&state=NY` | "Is my price fair?" |

**Public Portal - DrugWatch:**
| URL | Purpose |
|-----|---------|
| `/public/drugwatch/` | Home - top expensive drugs, stats |
| `/public/drugwatch/search?q=humira` | Drug search |
| `/public/drugwatch/compare/humira` | US vs international comparison |
| `/public/drugwatch/drug/eliquis` | Drug detail + spending data |

**Public Portal - FoodScore:**
| URL | Purpose |
|-----|---------|
| `/public/foodscore/` | Home - high-risk products, categories, stats |
| `/public/foodscore/search?q=chips&category=snacks` | Product search with category filter |
| `/public/foodscore/product/0049000042566` | Product detail + ML NOVA + additive risks |
| `/public/foodscore/scan` | Barcode scanner |
| `/public/foodscore/analyze` | Nutrition label analyzer (manual input + OCR) |
| `/public/foodscore/additives?q=red` | Additive database |

**Gov Portal - Enhanced Modules:**
| URL | Purpose |
|-----|---------|
| `/gov/pricevision/analytics?state=CA&limit=100` | State compliance dashboard |
| `/gov/drugwatch/mfn?q=&limit=50` | Most Favored Nation savings analysis |
| `/gov/drugwatch/trends?q=&limit=50&page=1` | Spending trends + pagination |
| `/gov/foodscore/snap` | SNAP batch ML analysis |
| `/gov/foodscore/additives?q=red` | Additive risk tiers (high/medium/low) |

**Gov Portal - RuralAccess (exclusive):**
| URL | Purpose |
|-----|---------|
| `/gov/ruralaccess/` | Home - stats, closures |
| `/gov/ruralaccess/map?state=TX&shortage_level=critical` | Interactive HPSA map |
| `/gov/ruralaccess/analytics` | Shortage analytics dashboard |
| `/gov/ruralaccess/county/48201` | County HPSA + FQHC detail |
| `/gov/ruralaccess/hpsa/1234` | Individual HPSA designation |

**Gov Portal - ChronicCare (exclusive):**
| URL | Purpose |
|-----|---------|
| `/gov/chroniccare/` | Home - national stats, trends, top priorities |
| `/gov/chroniccare/dashboard?state=MS&limit=100` | MAHA dashboard + ML hotspots |
| `/gov/chroniccare/interventions?state=&priority=Critical&limit=50` | ML-prioritized targets |
| `/gov/chroniccare/correlations?state=MS&limit=100` | Food-disease correlations |
| `/gov/chroniccare/analytics?state=&limit=100` | State-by-state comparison |
| `/gov/chroniccare/county/28049` | County ML profile + recommendations |
| `/gov/chroniccare/simulator` | Interactive ML feature simulator |

### API Endpoints
```
# System-wide
GET /api/stats                                → Module stats, coverage %
GET /api/inventory                            → Data file inventory by module
GET /api/hospitals?state=CA                   → Hospital list
GET /api/urls?state=CA                        → MRF URL list

# PriceVision
GET /public/api/pricevision/procedures?q=mri&limit=50
GET /public/api/pricevision/hospitals?state=NY&limit=50

# DrugWatch
GET /public/api/drugwatch/drugs?q=aspirin&limit=50
GET /public/api/drugwatch/compare/aspirin

# FoodScore
GET  /public/api/foodscore/products?q=chips&category=snacks&limit=50
GET  /public/api/foodscore/product/0049000042566     (includes ML enrichment)
GET  /public/api/foodscore/additives?q=red&limit=100
GET  /public/api/foodscore/stats
POST /public/api/foodscore/ocr                        (multipart image upload)

# RuralAccess (gov auth required)
GET /gov/api/ruralaccess/hpsas?state=TX&shortage_level=critical&limit=100
GET /gov/api/ruralaccess/counties?state=TX&limit=all
GET /gov/api/ruralaccess/map-data
GET /gov/api/ruralaccess/analytics
GET /gov/api/ruralaccess/stats

# ChronicCare (gov auth required)
GET /gov/api/chroniccare/counties?state=MS&limit=100
GET /gov/api/chroniccare/correlations
GET /gov/api/chroniccare/interventions?limit=50
GET /gov/api/chroniccare/stats
GET /gov/api/chroniccare/state-stats
```

---

## 8. Key Results & Statistics

### Platform-Wide Numbers
| Metric | Value |
|--------|-------|
| Total price records ingested | **30,200,589** |
| Hospitals in database | 5,421 (1,002 with pricing data = 18.5% compliance) |
| US drugs with spending data | 3,598 |
| International drug records | 72,256 (14,598 AU + 57,658 CA) |
| Total Medicare Part D spending tracked | **$275.9 billion** |
| Food products health-scored | 50,000 |
| Food additives risk-scored | 125 (curated) / 344 (expanded) |
| Products containing additives | 25,105 (50.2%) |
| HPSA designations mapped | 14,631 |
| Counties with chronic disease data | 2,956 |
| ML models deployed | 6 |
| Total model parameters | ~22.8 million |
| Largest model file | 86.7MB (Procedure Encoder) |

### ML Model Performance Summary
| Model | Primary Metric | Value | Training Epochs | Dataset Size |
|-------|---------------|-------|-----------------|-------------|
| NOVA Classifier | Accuracy | **96.29%** | 4 of 9 | 909K samples |
| Intervention Prioritizer | Accuracy | **93.9%** | 38 of 55 | 2,947 counties |
| Additive Risk Scorer | Category Accuracy | **85.71%** | 56 of 86 | 42 additives |
| Chronic Risk Predictor | MAE | **1.76%** | 54 of 77 | ~3K counties |
| Procedure Encoder | Cosine Similarity | **0.88** (best pair) | 5 epochs | 360K+ pairs |
| Additive Scorer Plus | Category Accuracy | 56.60% | 52 (experimental) | 344 additives |

### Disease Risk Per-Target Accuracy
| Disease | MAE | Best/Worst |
|---------|-----|-----------|
| COPD | **0.88%** | Best |
| Heart disease | **0.99%** | |
| Diabetes | **1.36%** | |
| Depression | **2.10%** | |
| Obesity | **2.30%** | |
| High BP | **3.02%** | Worst |

### NOVA Classifier Per-Class Performance
| NOVA Group | Precision | Recall | F1 | Support |
|-----------|-----------|--------|-----|---------|
| 1 (Unprocessed) | 90.87% | 94.17% | 0.925 | 10,054 |
| 2 (Culinary) | 75.72% | 87.62% | 0.812 | 1,591 |
| 3 (Processed) | 92.65% | 91.90% | 0.923 | 20,108 |
| 4 (Ultra-processed) | **98.72%** | **98.08%** | **0.984** | 69,254 |

### Key Policy-Relevant Findings
1. **Hospital price opacity:** Only 18.5% of hospitals have parseable pricing data despite the CMS mandate
2. **Drug cost gap:** Most expensive drug (Amvuttra) costs **$239,746 per unit**; top 10 drugs account for >$70B Medicare spending
3. **Ultra-processed food dominance:** 70.3% of scored products are NOVA 4 (ultra-processed); 50.2% contain food additives
4. **Healthcare deserts:** 14,631 shortage areas, 36.4% in rural areas, avg poverty rate 23.57% in HPSAs
5. **Chronic disease burden:** Obesity at 37.52% mean prevalence; 211 counties at High priority for intervention
6. **ML can predict disease risk:** 1.76% mean absolute error across 6 diseases from modifiable community factors

### Generated Visualizations (in `/results/`)
| File | Description |
|------|-------------|
| `nova_classifier_training.png` | NOVA loss curves (9 epochs) |
| `chronic_risk_training.png` | Regression loss curves |
| `model_comparison.png` | All 6 models side-by-side |
| `nova_confusion_matrix.png` | 4x4 NOVA confusion matrix |
| `intervention_confusion_matrix.png` | Priority tier confusion matrix |
| `additive_scorer_comparison.png` | 4 scorer configurations compared |
| `procedure_encoder_analysis.png` | Similarity matching analysis |
| `food_product_analysis.png` | Product distribution charts |
| `drug_spending_analysis.png` | Spending analysis charts |
| `healthcare_shortage_analysis.png` | HPSA analysis charts |
| `executive_dashboard.png` | Executive summary dashboard |

---

## 9. Quick Reference

### Run the Application
```bash
python frontend/app.py              # Start at http://localhost:5000

# ETL (if needed)
python scripts/process_data.py      # Process PriceVision, DrugWatch, FoodScore, RuralAccess
python scripts/chroniccare_pipeline.py  # Process ChronicCare (CDC + CMS + USDA merge)

# Train ML models
python -m ml.chroniccare.train      # Risk predictor + Intervention prioritizer
python -m ml.nova_classifier.train  # NOVA food classifier
python -m ml.additive_scorer.train  # Additive risk scorer
python -m ml.procedure_encoder.train # Procedure semantic encoder

# Generate analysis charts
python scripts/generate_results.py
```

### Gov Login
| Username | Password |
|----------|----------|
| `admin` | `healthguard2026` |
| `analyst` | `maha2026` |

### Key Files
| What | Where |
|------|-------|
| Flask app entry | `frontend/app.py` |
| App config + credentials | `frontend/config.py` |
| ML hyperparameters | `ml/config.py` |
| All model weights | `ml/weights/*.pt` |
| Training histories | `ml/weights/*_history.json` |
| Raw data | `data/raw/{module}/` |
| Processed data | `data/processed/{module}/` |
| Processing stats | `data/processed/{module}/processing_summary.json` |
| ETL scripts | `scripts/process_data.py`, `scripts/chroniccare_pipeline.py` |
| HTML templates | `frontend/templates/{public,gov}/{module}/` |
| CSS design system | `frontend/static/css/main.css` (~2100 lines) |
| JS animations | `frontend/static/js/animations.js` |
| Module docs | `docs/modules/{MODULE}.md` |
| Analysis report | `docs/ANALYSIS_REPORT.md` |
| Training visualizations | `results/*.png` |

### Module Quick Summary
| Module | Color | Key Metric | ML Model | Data Source |
|--------|-------|------------|----------|-------------|
| PriceVision | Amber `#f59e0b` | 30.2M prices, 1,002 hospitals | BioClinicalBERT encoder | CMS hospital MRFs |
| DrugWatch | Red `#ef4444` | $275.9B spending, 3 countries | None (statistical) | Medicare Part D, PBS, PMPRB |
| FoodScore | Green `#22c55e` | 50K products, 96.3% NOVA acc | NOVA CNN + Additive MLP | OpenFoodFacts, FDA |
| RuralAccess | Purple `#8b5cf6` | 14,631 HPSAs, 59 states | None (geospatial) | HRSA HPSA database |
| ChronicCare | Cyan `#06b6d4` | 2,956 counties, 93.9% acc | Risk Predictor + Prioritizer | CDC, CMS, USDA |
