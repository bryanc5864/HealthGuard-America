# HealthGuard America - Technical Documentation

**Version:** 1.0.0
**Last Updated:** January 2026
**Platform:** Healthcare Transparency & Analytics

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [System Architecture](#2-system-architecture)
3. [Project Structure](#3-project-structure)
4. [Data Layer](#4-data-layer)
5. [Machine Learning Models](#5-machine-learning-models)
6. [Frontend Application](#6-frontend-application)
7. [Service Layer](#7-service-layer)
8. [API Reference](#8-api-reference)
9. [Configuration](#9-configuration)
10. [Security & Authentication](#10-security--authentication)
11. [Deployment Guide](#11-deployment-guide)
12. [Development Guide](#12-development-guide)
13. [Testing](#13-testing)
14. [Performance Optimization](#14-performance-optimization)
15. [Troubleshooting](#15-troubleshooting)
16. [Appendices](#16-appendices)

---

## 1. Executive Summary

### 1.1 Project Overview

HealthGuard America is a comprehensive healthcare transparency and analytics platform designed to empower consumers and government officials with actionable healthcare data. The platform integrates hospital pricing, drug costs, food safety analysis, rural healthcare access mapping, and chronic disease risk prediction through a dual-portal web application backed by machine learning.

### 1.2 Key Features

| Module | Purpose | Primary Users | ML Integration |
|--------|---------|---------------|----------------|
| **PriceVision** | Hospital price transparency | Consumers, Regulators | Procedure semantic matching, Price fairness analysis |
| **DrugWatch** | Drug pricing comparison | Consumers, Policy analysts | Price trend analysis |
| **FoodScore** | Food product health scoring | Consumers, SNAP administrators | NOVA classification, Additive risk scoring |
| **RuralAccess** | Healthcare access mapping | Policy makers, Researchers | Geographic analytics |
| **ChronicCare** | Chronic disease analytics | Public health officials | Disease prediction, Intervention prioritization |

### 1.3 Platform Statistics

| Metric | Value |
|--------|-------|
| Hospital Price Records | 30.2M |
| US Drugs Tracked | 75,854 |
| Food Products Analyzed | 50,000+ |
| HPSA Designations | 14,631 |
| Counties Covered | 2,956 |
| ML Models | 6 |

### 1.4 Technology Stack

**Backend:**
- Python 3.10+
- Flask (Primary web framework)
- FastAPI (Optional enterprise backend)
- Pandas, NumPy (Data processing)
- PyArrow (Parquet I/O)

**Machine Learning:**
- PyTorch (Deep learning)
- Transformers (BioClinicalBERT, DistilBERT)
- scikit-learn (Preprocessing, metrics)

**Frontend:**
- Jinja2 Templates
- Bootstrap 5
- Chart.js (Visualizations)
- Leaflet.js (Maps)

**Data Storage:**
- Apache Parquet (Columnar storage)
- CSV (Raw data)
- JSON (Configuration, ML artifacts)
- SQLite/PostgreSQL (Optional backend)

---

## 2. System Architecture

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              HealthGuard America                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────┐    ┌─────────────────────┐                        │
│  │   Public Portal     │    │  Government Portal  │                        │
│  │   (No Auth)         │    │  (Auth Required)    │                        │
│  │                     │    │                     │                        │
│  │  • PriceVision      │    │  • PriceVision      │                        │
│  │  • DrugWatch        │    │  • DrugWatch        │                        │
│  │  • FoodScore        │    │  • FoodScore        │                        │
│  │                     │    │  • RuralAccess      │                        │
│  │                     │    │  • ChronicCare      │                        │
│  └──────────┬──────────┘    └──────────┬──────────┘                        │
│             │                          │                                    │
│             └──────────┬───────────────┘                                    │
│                        ▼                                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        Flask Application                             │   │
│  │                                                                      │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐               │   │
│  │  │   Blueprints │  │   Services   │  │  ML Services │               │   │
│  │  │              │  │              │  │              │               │   │
│  │  │  • public/   │  │  • PriceV.   │  │  • NOVA      │               │   │
│  │  │  • gov/      │  │  • DrugW.    │  │  • Additive  │               │   │
│  │  │              │  │  • FoodS.    │  │  • Chronic   │               │   │
│  │  │              │  │  • RuralA.   │  │  • Procedure │               │   │
│  │  │              │  │  • ChronC.   │  │              │               │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘               │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                        │                          │                         │
│                        ▼                          ▼                         │
│  ┌─────────────────────────────────┐  ┌─────────────────────────────────┐  │
│  │         Data Layer              │  │      ML Model Weights           │  │
│  │                                 │  │                                 │  │
│  │  data/processed/                │  │  ml/weights/                    │  │
│  │  ├── pricevision/              │  │  ├── nova_classifier.pt         │  │
│  │  ├── drugwatch/                │  │  ├── additive_scorer.pt         │  │
│  │  ├── foodscore/                │  │  ├── chronic_risk_predictor.pt  │  │
│  │  ├── ruralaccess/              │  │  ├── procedure_encoder.pt       │  │
│  │  └── chroniccare/              │  │  └── ...                        │  │
│  └─────────────────────────────────┘  └─────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Request Flow

```
User Request
     │
     ▼
┌─────────────┐
│   Flask     │
│   Router    │
└──────┬──────┘
       │
       ▼
┌─────────────┐     ┌─────────────┐
│  Blueprint  │────▶│   Service   │
│   Handler   │     │    Layer    │
└──────┬──────┘     └──────┬──────┘
       │                   │
       │            ┌──────┴──────┐
       │            ▼             ▼
       │     ┌──────────┐  ┌──────────┐
       │     │   Data   │  │    ML    │
       │     │  Files   │  │ Inference│
       │     └──────────┘  └──────────┘
       │            │             │
       │            └──────┬──────┘
       │                   │
       ▼                   ▼
┌─────────────────────────────────┐
│         Template Render         │
└─────────────────────────────────┘
       │
       ▼
   HTML Response
```

### 2.3 Data Flow Architecture

```
Raw Data Sources                    Processing Pipeline                  Serving Layer
─────────────────                  ────────────────────                 ──────────────

┌───────────────┐
│  CMS Hospital │
│  MRF Files    │──┐
└───────────────┘  │
                   │    ┌──────────────────┐    ┌────────────────────┐
┌───────────────┐  │    │                  │    │                    │
│  Medicare     │──┼───▶│  ETL Pipeline    │───▶│  Parquet Files     │
│  Part D Data  │  │    │  (process_data)  │    │  (Columnar Store)  │
└───────────────┘  │    │                  │    │                    │
                   │    └──────────────────┘    └─────────┬──────────┘
┌───────────────┐  │                                      │
│  Open Food    │──┤                                      │
│  Facts        │  │                                      ▼
└───────────────┘  │                           ┌────────────────────┐
                   │                           │                    │
┌───────────────┐  │                           │  Service Layer     │
│  CDC PLACES   │──┤                           │  (Cached DataFrames)│
│  County Data  │  │                           │                    │
└───────────────┘  │                           └─────────┬──────────┘
                   │                                     │
┌───────────────┐  │                                     ▼
│  HRSA HPSA    │──┘                           ┌────────────────────┐
│  Designations │                              │                    │
└───────────────┘                              │  Flask Routes      │
                                               │  (JSON/HTML)       │
                                               │                    │
                                               └────────────────────┘
```

### 2.4 ML Pipeline Architecture

```
Training Pipeline                               Inference Pipeline
─────────────────                              ──────────────────

┌───────────────────┐                          ┌───────────────────┐
│  Training Data    │                          │   User Request    │
│  (Parquet/CSV)    │                          │                   │
└────────┬──────────┘                          └────────┬──────────┘
         │                                              │
         ▼                                              ▼
┌───────────────────┐                          ┌───────────────────┐
│  Dataset Class    │                          │  Service Layer    │
│  (PyTorch)        │                          │  Lazy Loading     │
└────────┬──────────┘                          └────────┬──────────┘
         │                                              │
         ▼                                              ▼
┌───────────────────┐                          ┌───────────────────┐
│  DataLoader       │                          │  Model Instance   │
│  (Batching)       │                          │  (Cached)         │
└────────┬──────────┘                          └────────┬──────────┘
         │                                              │
         ▼                                              ▼
┌───────────────────┐                          ┌───────────────────┐
│  Model Training   │                          │  Feature Encoding │
│  (GPU/CPU)        │                          │  (Preprocessing)  │
└────────┬──────────┘                          └────────┬──────────┘
         │                                              │
         ▼                                              ▼
┌───────────────────┐                          ┌───────────────────┐
│  Checkpointing    │                          │  Forward Pass     │
│  (Best Model)     │                          │  (Inference)      │
└────────┬──────────┘                          └────────┬──────────┘
         │                                              │
         ▼                                              ▼
┌───────────────────┐                          ┌───────────────────┐
│  ml/weights/      │                          │  Post-processing  │
│  model.pt         │                          │  (Confidence, etc)│
└───────────────────┘                          └───────────────────┘
```

---

## 3. Project Structure

### 3.1 Complete Directory Tree

```
HealthGuard/
│
├── frontend/                          # Flask Web Application
│   ├── app.py                         # Main Flask app entry point
│   ├── config.py                      # Frontend configuration
│   ├── requirements.txt               # Python dependencies
│   │
│   ├── blueprints/                    # Flask route handlers
│   │   ├── public/                    # Public portal routes
│   │   │   ├── __init__.py            # Blueprint registration
│   │   │   ├── pricevision.py         # Hospital pricing routes
│   │   │   ├── drugwatch.py           # Drug pricing routes
│   │   │   └── foodscore.py           # Food scoring routes
│   │   │
│   │   └── gov/                       # Government portal routes
│   │       ├── __init__.py            # Auth middleware
│   │       ├── pricevision.py         # + Compliance analytics
│   │       ├── drugwatch.py           # + MFN analysis
│   │       ├── foodscore.py           # + SNAP analysis
│   │       ├── ruralaccess.py         # Healthcare mapping
│   │       └── chroniccare.py         # Disease analytics
│   │
│   ├── services/                      # Data service layer
│   │   ├── __init__.py                # VALID_US_STATES constant
│   │   ├── pricevision.py             # PriceVisionService
│   │   ├── drugwatch.py               # DrugWatchService
│   │   ├── foodscore.py               # FoodScoreService
│   │   ├── ruralaccess.py             # RuralAccessService
│   │   └── chroniccare.py             # ChronicCareService
│   │
│   ├── templates/                     # Jinja2 templates
│   │   ├── base.html                  # Base layout
│   │   ├── landing.html               # Portal selector
│   │   │
│   │   ├── public/                    # Public portal templates
│   │   │   ├── base_public.html
│   │   │   ├── home.html
│   │   │   ├── pricevision/           # 5 templates
│   │   │   ├── drugwatch/             # 4 templates
│   │   │   └── foodscore/             # 5 templates
│   │   │
│   │   └── gov/                       # Government templates
│   │       ├── base_gov.html
│   │       ├── login.html
│   │       ├── home.html
│   │       ├── pricevision/           # 6 templates
│   │       ├── drugwatch/             # 5 templates
│   │       ├── foodscore/             # 5 templates
│   │       ├── ruralaccess/           # 5 templates
│   │       └── chroniccare/           # 7 templates
│   │
│   └── static/                        # Static assets
│       ├── css/
│       └── js/
│
├── backend/                           # FastAPI Backend (Optional)
│   ├── core/
│   │   ├── config.py                  # Backend settings
│   │   ├── database.py                # SQLAlchemy setup
│   │   └── models.py                  # ORM models
│   │
│   └── [module]/                      # Per-module structure
│       ├── models/
│       ├── api/
│       ├── services/
│       └── data/
│
├── ml/                                # Machine Learning
│   ├── config.py                      # ML configuration dataclasses
│   ├── training_utils.py              # Shared training utilities
│   ├── services.py                    # Unified ML API
│   │
│   ├── weights/                       # Trained model weights (~104 MB)
│   │   ├── nova_classifier.pt         # NOVA model (5.7 MB)
│   │   ├── nova_tokenizer.json        # Tokenizer vocab (171 KB)
│   │   ├── additive_scorer.pt         # Risk scorer (15 KB)
│   │   ├── additive_scorer_plus.pt    # Enhanced (438 KB)
│   │   ├── chronic_risk_predictor.pt  # Disease predictor (256 KB)
│   │   ├── intervention_prioritizer.pt # Priority model (62 KB)
│   │   ├── procedure_encoder.pt       # BioClinicalBERT (87 MB)
│   │   └── canonical_procedure_embeddings.pt  # Cached (10 MB)
│   │
│   ├── nova_classifier/               # NOVA 1-4 classification
│   │   ├── model.py                   # CNN architecture
│   │   ├── tokenizer.py               # Ingredient tokenizer
│   │   ├── dataset.py                 # Data loader
│   │   ├── train.py                   # Training script
│   │   └── inference.py               # NovaClassificationService
│   │
│   ├── additive_scorer/               # Additive risk scoring
│   │   ├── model.py                   # MLP architecture
│   │   ├── dataset.py                 # Additive dataset
│   │   ├── train.py                   # Training script
│   │   └── inference.py               # AdditiveRiskService
│   │
│   ├── additive_scorer_plus/          # Enhanced with uncertainty
│   │   ├── model.py                   # Transformer fusion
│   │   ├── dataset.py
│   │   └── train.py
│   │
│   ├── chroniccare/                   # Chronic disease models
│   │   ├── model.py                   # Multi-task MLP
│   │   ├── dataset.py                 # County data loader
│   │   ├── train.py                   # Training scripts
│   │   └── inference.py               # ChronicCareMLService
│   │
│   └── procedure_encoder/             # Semantic procedure matching
│       ├── model.py                   # BioClinicalBERT
│       ├── dataset.py                 # Procedure pairs
│       ├── train.py                   # Contrastive learning
│       └── inference.py               # ProcedureMatchingService
│
├── data/                              # Data storage
│   ├── raw/                           # Unprocessed source data
│   │   ├── pricevision/
│   │   │   ├── mrfs/                  # Hospital MRF files
│   │   │   ├── hospital_general_info.csv
│   │   │   └── provider_util/         # Medicare utilization
│   │   │
│   │   ├── drugwatch/
│   │   │   ├── us/                    # US drug data
│   │   │   │   ├── part_d/            # Medicare Part D
│   │   │   │   └── ndc/               # NDC directory
│   │   │   ├── australia/             # PBS data
│   │   │   └── canada/                # DPD data
│   │   │
│   │   ├── foodscore/
│   │   │   ├── openfoodfacts_us.csv.gz
│   │   │   └── additive_risks.csv
│   │   │
│   │   ├── ruralaccess/
│   │   │   ├── hrsa_hpsa.csv
│   │   │   └── county_boundaries/
│   │   │
│   │   └── chroniccare/
│   │
│   └── processed/                     # Cleaned, normalized data
│       ├── pricevision/
│       │   ├── medicare_procedures.csv
│       │   └── all_prices_normalized.parquet
│       │
│       ├── drugwatch/
│       │   ├── us_drugs.parquet
│       │   ├── australia_drugs.parquet
│       │   └── canada_drugs.parquet
│       │
│       ├── foodscore/
│       │   └── us_products_scored.parquet
│       │
│       ├── ruralaccess/
│       │   ├── hpsa_designations.parquet
│       │   └── county_shortage_summary.parquet
│       │
│       └── chroniccare/
│           ├── chroniccare_merged.parquet
│           ├── cdc_places_county.csv
│           └── usda_food_environment.csv
│
├── scripts/                           # Data processing & training
│   ├── process_data.py                # Main ETL pipeline
│   ├── chroniccare_pipeline.py        # ChronicCare data pipeline
│   ├── train_models.py                # Model training orchestrator
│   ├── download_new_data.py           # Data download utilities
│   └── analyze_data.py                # Data analysis
│
├── docs/                              # Documentation
│   ├── DATA_BRIEF.md                  # Data summary
│   ├── DATA_SOURCES.md                # Source documentation
│   ├── VISUAL_ENHANCEMENTS.md         # UI/UX guide
│   └── TECHNICAL_DOCUMENTATION.md     # This file
│
├── results/                           # Analysis results
│   ├── guides/
│   ├── data_insights/
│   ├── model_performance/
│   └── training_curves/
│
└── datadownload/                      # Download utilities
    ├── download_data.py
    └── README.md
```

### 3.2 File Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Python modules | lowercase_underscore | `price_vision.py` |
| Classes | PascalCase | `PriceVisionService` |
| Functions | lowercase_underscore | `get_hospital_info()` |
| Constants | UPPERCASE_UNDERSCORE | `VALID_US_STATES` |
| Templates | lowercase with hyphens | `my-price.html` |
| Data files | lowercase_underscore | `us_drugs.parquet` |
| Model weights | lowercase_underscore | `nova_classifier.pt` |

### 3.3 Import Structure

```python
# Standard library
import sys
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional

# Third-party
import pandas as pd
import numpy as np
import torch
from flask import Flask, render_template, request, jsonify

# Local imports - relative
from . import module_bp
from .services import ServiceClass

# Local imports - absolute (from project root)
from ml.nova_classifier.inference import NovaClassificationService
from frontend.services.pricevision import PriceVisionService
```

---

## 4. Data Layer

### 4.1 Data Sources Overview

| Module | Source | Format | Records | Update Frequency |
|--------|--------|--------|---------|------------------|
| **PriceVision** | CMS Hospital MRFs | JSON/CSV | 30.2M | Quarterly |
| **PriceVision** | Hospital General Info | CSV | 1,002 | Annual |
| **DrugWatch** | Medicare Part D | CSV | 3,598 | Annual |
| **DrugWatch** | Australia PBS | CSV | 15,000+ | Monthly |
| **DrugWatch** | Canada DPD | JSON | 50,000+ | Monthly |
| **FoodScore** | Open Food Facts | CSV.GZ | 50,000+ | Weekly |
| **FoodScore** | FDA Additives | CSV | 344 | As needed |
| **RuralAccess** | HRSA HPSA | CSV | 14,631 | Quarterly |
| **ChronicCare** | CDC PLACES | CSV | 3,000+ | Annual |
| **ChronicCare** | USDA Food Atlas | CSV | 3,000+ | Annual |

### 4.2 Data Processing Pipeline

#### 4.2.1 PriceVision Data Processing

```python
# scripts/process_data.py - PriceVision section

class PriceVisionProcessor:
    """Process hospital MRF files into normalized pricing data."""

    def process_all(self):
        """
        1. Load hospital metadata from hospital_general_info.csv
        2. Iterate through MRF files in data/raw/pricevision/mrfs/
        3. Parse each MRF (JSON or CSV format)
        4. Normalize procedure codes to HCPCS
        5. Extract pricing: gross_charge, cash_price, negotiated_rates
        6. Output: data/processed/pricevision/all_prices_normalized.parquet
        """
        pass

# Schema: all_prices_normalized.parquet
schema = {
    'hospital_npi': 'string',
    'hospital_name': 'string',
    'hospital_state': 'string',
    'hospital_city': 'string',
    'hcpcs_code': 'string',
    'procedure_description': 'string',
    'canonical_description': 'string',
    'gross_charge': 'float64',
    'cash_price': 'float64',
    'min_negotiated': 'float64',
    'max_negotiated': 'float64',
    'payer_specific_rates': 'object'  # JSON
}
```

#### 4.2.2 DrugWatch Data Processing

```python
# Schema: us_drugs.parquet
schema = {
    'ndc': 'string',
    'brand_name': 'string',
    'generic_name': 'string',
    'manufacturer': 'string',
    'total_spending_2023': 'float64',
    'total_claims_2023': 'int64',
    'avg_cost_per_claim': 'float64',
    'price_per_unit': 'float64'
}

# Schema: australia_drugs.parquet
schema = {
    'pbs_code': 'string',
    'drug_name': 'string',
    'generic_name': 'string',
    'price_usd': 'float64',
    'price_aud': 'float64',
    'country': 'string'  # Always 'Australia'
}
```

#### 4.2.3 FoodScore Data Processing

```python
# Schema: us_products_scored.parquet
schema = {
    'code': 'string',                  # Barcode
    'product_name': 'string',
    'brands': 'string',
    'categories_en': 'string',         # Comma-separated
    'ingredients_text': 'string',
    'nova_group': 'int64',             # 1-4
    'nutriscore_grade': 'string',      # A-E
    'energy_kcal_100g': 'float64',
    'fat_100g': 'float64',
    'saturated_fat_100g': 'float64',
    'sugars_100g': 'float64',
    'sodium_100g': 'float64',
    'fiber_100g': 'float64',
    'proteins_100g': 'float64',
    'additives_tags': 'string',        # Comma-separated
    'maha_score': 'float64'            # 0-100 health score
}
```

#### 4.2.4 ChronicCare Data Processing

```python
# scripts/chroniccare_pipeline.py

class ChronicCarePipeline:
    """Merge county-level health datasets."""

    def run(self):
        """
        1. Download CDC PLACES county data
        2. Download CMS geographic variation data
        3. Download USDA food environment atlas
        4. Merge on county FIPS code
        5. Calculate derived metrics (risk scores)
        6. Output: data/processed/chroniccare/chroniccare_merged.parquet
        """
        pass

# Schema: chroniccare_merged.parquet
schema = {
    'fips': 'string',
    'county_name': 'string',
    'state_abbr': 'string',

    # Disease prevalence (%)
    'diabetes_prevalence': 'float64',
    'obesity_prevalence': 'float64',
    'heart_disease_prevalence': 'float64',
    'high_bp_prevalence': 'float64',

    # Food environment
    'grocery_stores_per_1000': 'float64',
    'fast_food_restaurants_per_1000': 'float64',
    'food_environment_index': 'float64',
    'food_insecurity_rate': 'float64',

    # Healthcare access
    'pcp_rate': 'float64',
    'pct_uninsured': 'float64',

    # Socioeconomic
    'median_household_income': 'float64',
    'child_poverty_rate': 'float64',

    # Behavioral
    'physical_inactivity_prevalence': 'float64',
    'smoking_prevalence': 'float64',

    # Demographics
    'pct_rural': 'float64',
    'population': 'int64'
}
```

### 4.3 Parquet Optimization

**Why Parquet:**
- Columnar storage: Only read needed columns
- Compression: 4-10x smaller than CSV
- Predicate pushdown: Filter at storage level
- Schema enforcement: Type safety

**Usage Pattern:**
```python
import pyarrow.parquet as pq

# Predicate pushdown - only loads matching rows
filters = [
    ('hospital_npi', '=', '1234567890'),
    ('cash_price', '>', 0)
]
table = pq.read_table(
    'all_prices_normalized.parquet',
    filters=filters,
    columns=['hospital_npi', 'cash_price', 'procedure_description']
)
df = table.to_pandas()
```

### 4.4 Data Validation

```python
# Common validation patterns used in services

def validate_state(state: str) -> bool:
    """Validate US state/territory abbreviation."""
    return state.upper() in VALID_US_STATES

def validate_fips(fips: str) -> bool:
    """Validate county FIPS code (5 digits)."""
    return len(str(fips)) == 5 and str(fips).isdigit()

def validate_npi(npi: str) -> bool:
    """Validate NPI (10 digits)."""
    return len(str(npi)) == 10 and str(npi).isdigit()

def clean_nan_records(records: List[Dict]) -> List[Dict]:
    """Replace NaN values with None for JSON serialization."""
    cleaned = []
    for record in records:
        clean_record = {}
        for key, value in record.items():
            if pd.isna(value):
                clean_record[key] = None
            else:
                clean_record[key] = value
        cleaned.append(clean_record)
    return cleaned
```

---

## 5. Machine Learning Models

### 5.1 Model Overview

| Model | Type | Input | Output | Parameters | Performance |
|-------|------|-------|--------|------------|-------------|
| **NOVA Classifier** | CNN | Ingredient text | NOVA 1-4 | 2.5M | 96.16% accuracy |
| **Additive Scorer** | MLP | Categorical features | Risk 0-100 | 2.5K | 85.71% accuracy |
| **Chronic Risk Predictor** | Multi-task MLP | 19 county features | 6 disease prevalences | 500K | MAE 1.76% |
| **Intervention Prioritizer** | MLP Classifier | 16 features | 4 priority classes | 150K | 93.9% accuracy |
| **Procedure Encoder** | BioClinicalBERT | Procedure text | 768-dim embedding | 110M | MRR 0.85 |

### 5.2 NOVA Classifier

**Purpose:** Classify food products into NOVA 1-4 processing levels based on ingredient lists.

**Architecture:**
```
Input: Token IDs [batch, 200]
         │
         ▼
┌─────────────────────────┐
│ Embedding(10000, 128)   │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│ Conv1d(128→256, k=3)    │
│ ReLU                    │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│ GlobalAvgPool(dim=2)    │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│ Dense(256) → ReLU       │
│ BatchNorm → Dropout(0.3)│
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│ Dense(128) → ReLU       │
│ BatchNorm → Dropout(0.3)│
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│ Dense(4) → Softmax      │
└─────────────────────────┘
            │
            ▼
Output: Probabilities [batch, 4]
```

**Training Configuration:**
```python
NovaClassifierConfig = {
    'vocab_size': 10000,
    'embedding_dim': 128,
    'conv_filters': 256,
    'kernel_size': 3,
    'hidden_dims': [256, 128],
    'dropout': 0.3,
    'max_length': 200,
    'batch_size': 64,
    'learning_rate': 1e-3,
    'epochs': 20,
    'early_stopping_patience': 5,
    'class_weights': 'inverse_frequency'
}
```

**Inference API:**
```python
from ml.nova_classifier.inference import NovaClassificationService

# Load service
service = NovaClassificationService.load()

# Single classification
result = service.classify("water, sugar, corn syrup, artificial flavors")
print(result.nova_group)      # 4
print(result.confidence)       # 0.92
print(result.description)      # "Ultra-processed food and drink products"
print(result.probabilities)    # [0.02, 0.01, 0.05, 0.92]

# Batch classification
results = service.classify_batch([
    "fresh apples",
    "sugar, water",
    "wheat flour, water, salt",
    "water, high fructose corn syrup, red 40"
])

# Get NOVA indicators (rule-based analysis)
indicators = service.get_nova_indicators("sugar, modified starch, maltodextrin")
# Returns: {
#   'nova4_indicators': ['modified starch', 'maltodextrin'],
#   'nova3_indicators': [],
#   'ingredient_count': 3,
#   'likely_ultra_processed': True
# }
```

### 5.3 Additive Risk Scorer

**Purpose:** Score food additives (0-100) based on regulatory status and chemical properties.

**Architecture:**
```
Input: 13 encoded features
         │
         ▼
┌─────────────────────────┐
│ Linear(13→64) → ReLU    │
│ Dropout(0.2)            │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│ Linear(64→32) → ReLU    │
│ Dropout(0.2)            │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│ Linear(32→1) → Sigmoid  │
│ Scale by 100            │
└─────────────────────────┘
            │
            ▼
Output: Risk Score [0-100]
```

**Input Features (13 total):**
```python
# One-hot encoded categorical features
additive_type = ['dye', 'sweetener', 'preservative', 'emulsifier', 'flavor', 'other']  # 6
fda_status = ['approved', 'banned']  # 2
eu_status = ['approved', 'restricted', 'banned']  # 3

# Binary features
is_artificial = [0, 1]  # 1
is_petroleum_based = [0, 1]  # 1

# Total: 6 + 2 + 3 + 1 + 1 = 13 features
```

**Inference API:**
```python
from ml.additive_scorer.inference import AdditiveRiskService

service = AdditiveRiskService.load()

# Single scoring
result = service.score_additive("Red 40")
print(result.risk_score)       # 72.5
print(result.risk_category)    # 'high'
print(result.fda_status)       # 'approved'
print(result.eu_status)        # 'approved'
print(result.is_artificial)    # True

# Batch scoring
results = service.score_batch(["Red 40", "Yellow 5", "Citric Acid"])

# Product analysis
analysis = service.score_product_ingredients(
    "water, sugar, red 40, yellow 5, citric acid"
)
print(analysis['additive_count'])       # 3
print(analysis['max_risk_score'])       # 72.5
print(analysis['high_risk_additives'])  # ['Red 40']
```

### 5.4 Chronic Risk Predictor

**Purpose:** Predict county-level chronic disease prevalence from environmental factors.

**Architecture (Multi-task):**
```
Input: 19 features
         │
         ▼
┌─────────────────────────────┐
│      Shared Encoder         │
│                             │
│ Linear(19→256) → BN → ReLU  │
│ Dropout(0.3)                │
│                             │
│ Linear(256→128) → BN → ReLU │
│ Dropout(0.3)                │
│                             │
│ Linear(128→64) → BN → ReLU  │
│ Dropout(0.3)                │
└───────────┬─────────────────┘
            │
    ┌───────┴───────┬───────────┬───────────┬───────────┬───────────┐
    ▼               ▼           ▼           ▼           ▼           ▼
┌─────────┐   ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐
│Diabetes │   │ Obesity │ │ Heart   │ │ High BP │ │  COPD   │ │Depress. │
│ Head    │   │  Head   │ │ Disease │ │  Head   │ │  Head   │ │  Head   │
│ 64→32→1 │   │ 64→32→1 │ │ 64→32→1 │ │ 64→32→1 │ │ 64→32→1 │ │ 64→32→1 │
└────┬────┘   └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘
     │             │           │           │           │           │
     ▼             ▼           ▼           ▼           ▼           ▼
  diabetes      obesity    heart_dis   high_bp       copd      depression
  prevalence    prevalence prevalence  prevalence  prevalence  prevalence
```

**Input Features (19 total):**
```python
FEATURE_NAMES = [
    # Food Environment (5)
    'grocery_stores_per_1000',
    'fast_food_restaurants_per_1000',
    'food_environment_index',
    'food_insecurity_rate',
    'pct_limited_food_access',

    # Healthcare Access (4)
    'pcp_rate',
    'mental_health_provider_rate',
    'pct_uninsured',
    'preventable_hospitalizations',

    # Socioeconomic (5)
    'median_household_income',
    'child_poverty_rate',
    'income_inequality_ratio',
    'high_school_graduation_rate',
    'pct_some_college',

    # Behavioral (4)
    'physical_inactivity_prevalence',
    'excessive_drinking_prevalence',
    'smoking_prevalence',
    'pct_insufficient_sleep',

    # Demographics (1)
    'pct_rural'
]
```

**Inference API:**
```python
from ml.chroniccare.inference import get_chroniccare_service

service = get_chroniccare_service()
service.load()

# Single county prediction
features = {
    'grocery_stores_per_1000': 2.5,
    'fast_food_restaurants_per_1000': 0.8,
    'food_insecurity_rate': 15.0,
    'pcp_rate': 45.0,
    'pct_uninsured': 12.0,
    'physical_inactivity_prevalence': 30.0,
    'smoking_prevalence': 20.0,
    # ... remaining features
}

predictions = service.risk_service.predict(features)
# Returns: {
#   'diabetes_prevalence': 12.3,
#   'obesity_prevalence': 35.2,
#   'heart_disease_prevalence': 6.8,
#   ...
# }
```

### 5.5 Intervention Prioritizer

**Purpose:** Classify counties into intervention priority tiers for MAHA initiative.

**Architecture:**
```
Input: 16 features
         │
         ▼
┌─────────────────────────────┐
│ Linear(16→128) → BN → ReLU  │
│ Dropout(0.3)                │
└───────────┬─────────────────┘
            │
            ▼
┌─────────────────────────────┐
│ Linear(128→64) → BN → ReLU  │
│ Dropout(0.3)                │
└───────────┬─────────────────┘
            │
            ▼
┌─────────────────────────────┐
│ Linear(64→32) → BN → ReLU   │
│ Dropout(0.3)                │
└───────────┬─────────────────┘
            │
            ▼
┌─────────────────────────────┐
│ Linear(32→4) → Softmax      │
└─────────────────────────────┘
            │
            ▼
Output: [Critical, High, Medium, Low]
```

**MAHA Index Calculation:**
```python
class MAHAIndexCalculator:
    """
    MAHA Index = Make America Healthy Again intervention priority score.

    Components (weighted):
    - Disease Burden: 30% (higher = more urgent)
    - Food Environment: 25% (lower = more urgent, inverted)
    - Healthcare Access: 20% (lower = more urgent, inverted)
    - Economic Vulnerability: 25% (higher = more urgent)
    """

    WEIGHT_PRESETS = {
        "balanced": {
            "disease_burden": 0.30,
            "food_environment": 0.25,
            "healthcare_access": 0.20,
            "economic_vulnerability": 0.25,
        }
    }

    # Percentile-based thresholds
    THRESHOLDS = {
        "critical": 46.0,  # Top 5%
        "high": 43.0,      # Top 20%
        "medium": 39.0,    # Top 50%
    }
```

**Inference API:**
```python
# Get priority classification
priority = service.prioritization_service.prioritize(features)
# Returns: {
#   'priority': 'High',
#   'priority_index': 1,
#   'confidence': 0.87,
#   'all_probabilities': {'critical': 0.05, 'high': 0.87, 'medium': 0.06, 'low': 0.02},
#   'maha_index': 44.2,
#   'maha_components': {
#     'disease_burden': 15.3,
#     'food_environment': 12.5,
#     'healthcare_access': 8.2,
#     'economic_vulnerability': 8.2
#   }
# }
```

### 5.6 Procedure Encoder

**Purpose:** Match hospital procedure descriptions to canonical CPT codes using semantic similarity.

**Architecture:**
```
Input: Procedure text
         │
         ▼
┌─────────────────────────────┐
│  BioClinicalBERT Tokenizer  │
│  Max Length: 128            │
└───────────┬─────────────────┘
            │
            ▼
┌─────────────────────────────┐
│  BioClinicalBERT Encoder    │
│  (12 transformer layers)    │
│  Hidden: 768                │
└───────────┬─────────────────┘
            │
            ▼
┌─────────────────────────────┐
│  Mean Pooling               │
│  (with attention mask)      │
└───────────┬─────────────────┘
            │
            ▼
┌─────────────────────────────┐
│  L2 Normalization           │
└─────────────────────────────┘
            │
            ▼
Output: 768-dim embedding
```

**Training (Contrastive Learning):**
```python
class MultipleNegativesRankingLoss:
    """
    Contrastive loss for semantic similarity learning.

    - Anchor: procedure description variant
    - Positive: same CPT code alternative description
    - Negatives: all other samples in batch (in-batch negatives)

    Maximizes: cos(anchor, positive)
    Minimizes: cos(anchor, negative)
    """
    scale = 20.0  # Temperature
```

**Inference API:**
```python
from ml.procedure_encoder.inference import ProcedureMatchingService

service = ProcedureMatchingService.load()

# Single matching
result = service.match("MRI BRAIN W/O CONTRAST")
print(result.matched_code)         # '70551'
print(result.matched_description)  # 'MRI brain w/o dye'
print(result.confidence)           # 0.92
print(result.status)               # 'matched' (>0.80), 'review' (0.65-0.80), 'unmatched' (<0.65)

# Find similar procedures
similar = service.find_similar("CT ABDOMEN", top_k=5)
# Returns: [(code, description, similarity), ...]

# Get embedding for custom storage
embedding = service.get_embedding("COLONOSCOPY WITH BIOPSY")  # 768-dim vector
```

### 5.7 Model Training

**Common Training Pattern:**
```python
# ml/training_utils.py

def train_model(model, train_loader, val_loader, config):
    """Standard training loop with early stopping."""

    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=config.learning_rate,
        weight_decay=config.weight_decay
    )

    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode='min', factor=0.5, patience=config.scheduler_patience
    )

    early_stopping = EarlyStopping(patience=config.early_stopping_patience)

    for epoch in range(config.epochs):
        # Training phase
        model.train()
        train_loss = 0
        for batch in train_loader:
            optimizer.zero_grad()
            loss = compute_loss(model, batch)
            loss.backward()
            optimizer.step()
            train_loss += loss.item()

        # Validation phase
        model.eval()
        val_loss = evaluate(model, val_loader)

        # Learning rate scheduling
        scheduler.step(val_loss)

        # Early stopping check
        if early_stopping(val_loss, model):
            print(f"Early stopping at epoch {epoch}")
            break

    return model
```

**Training Commands:**
```bash
# Train all models
python scripts/train_models.py --all

# Train specific model
python -m ml.nova_classifier.train
python -m ml.additive_scorer.train
python -m ml.chroniccare.train --model risk
python -m ml.chroniccare.train --model prioritizer
python -m ml.procedure_encoder.train
```

---

## 6. Frontend Application

### 6.1 Flask Application Structure

**Main Application (`frontend/app.py`):**
```python
from flask import Flask, render_template, request, jsonify
from config import Config

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = Config.SECRET_KEY

# Register blueprints
from blueprints.public import public_bp
from blueprints.gov import gov_bp

app.register_blueprint(public_bp, url_prefix='/public')
app.register_blueprint(gov_bp, url_prefix='/gov')

@app.route('/')
def landing():
    """Portal selector landing page."""
    return render_template('landing.html', modules=Config.MODULES)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
```

### 6.2 Blueprint Architecture

**Public Blueprint (`frontend/blueprints/public/__init__.py`):**
```python
from flask import Blueprint

public_bp = Blueprint('public', __name__)

# Import routes after blueprint creation to avoid circular imports
from . import pricevision
from . import drugwatch
from . import foodscore

@public_bp.route('/')
def home():
    """Public portal home page."""
    return render_template('public/home.html')
```

**Government Blueprint (`frontend/blueprints/gov/__init__.py`):**
```python
from flask import Blueprint, session, redirect, url_for, request
from functools import wraps

gov_bp = Blueprint('gov', __name__)

def gov_required(f):
    """Decorator for routes requiring government authentication."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_gov_user'):
            return redirect(url_for('gov.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# Import routes
from . import pricevision
from . import drugwatch
from . import foodscore
from . import ruralaccess
from . import chroniccare
```

### 6.3 Template Hierarchy

```
templates/
├── base.html                    # Root base template
│   └── {% block content %}
│
├── public/
│   ├── base_public.html         # Extends base.html
│   │   └── Public navigation
│   │   └── {% block content %}
│   │
│   └── [module]/
│       └── [page].html          # Extends base_public.html
│
└── gov/
    ├── base_gov.html            # Extends base.html
    │   └── Gov navigation
    │   └── Authentication check
    │   └── {% block content %}
    │
    └── [module]/
        └── [page].html          # Extends base_gov.html
```

**Base Template Pattern:**
```html
<!-- templates/base.html -->
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}HealthGuard America{% endblock %}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css" rel="stylesheet">
    {% block head %}{% endblock %}
</head>
<body>
    {% block navbar %}{% endblock %}

    <main>
        {% block content %}{% endblock %}
    </main>

    {% block footer %}{% endblock %}

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    {% block scripts %}{% endblock %}
</body>
</html>
```

### 6.4 Static Assets

```
frontend/static/
├── css/
│   └── healthguard.css          # Custom styles
│       ├── Portal-specific themes
│       ├── Module color schemes
│       ├── Card and stat styles
│       └── Responsive breakpoints
│
└── js/
    ├── charts.js                # Chart.js integrations
    │   ├── initPriceChart()
    │   ├── initNovaChart()
    │   └── initTrendChart()
    │
    └── maps.js                  # Leaflet.js integrations
        ├── initHPSAMap()
        └── initCountyMap()
```

---

## 7. Service Layer

### 7.1 Service Architecture

All services follow a consistent pattern:
- Class methods for stateless access
- In-memory caching via class variables
- DataFrame caching for efficient filtering
- NaN → None conversion for JSON serialization

**Base Pattern:**
```python
class BaseService:
    _cache = {}       # General results cache
    _df_cache = {}    # DataFrame cache

    @classmethod
    def _get_dataframe(cls, cache_key: str, file_path: Path) -> pd.DataFrame:
        """Load DataFrame with caching."""
        if cache_key not in cls._df_cache:
            if file_path.suffix == '.parquet':
                cls._df_cache[cache_key] = pd.read_parquet(file_path)
            else:
                cls._df_cache[cache_key] = pd.read_csv(file_path)
        return cls._df_cache[cache_key]

    @classmethod
    def get_items(cls, limit=100, search=None, **filters) -> List[Dict]:
        """Standard get with filtering."""
        df = cls._get_dataframe('items', DATA_FILE)

        if df.empty:
            return []

        # Apply filters
        if search:
            mask = df['name'].str.lower().str.contains(search.lower(), regex=False)
            df = df[mask]

        for field, value in filters.items():
            if value and field in df.columns:
                df = df[df[field] == value]

        return clean_nan_records(df.head(limit).to_dict('records'))
```

### 7.2 PriceVisionService

**File:** `frontend/services/pricevision.py`

**Key Methods:**

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `get_procedures()` | `limit`, `search` | `List[Dict]` | Medicare procedures |
| `get_hospitals()` | `state`, `limit` | `List[Dict]` | Hospital list |
| `get_hospital()` | `facility_id` | `Dict` | Single hospital (O(1) lookup) |
| `get_prices()` | `hospital_npi`, `procedure_code`, `state`, `limit` | `List[Dict]` | Price records with predicate pushdown |
| `get_states()` | - | `List[str]` | US states with hospitals |
| `get_stats()` | - | `Dict` | Summary statistics |

**Caching Strategy:**
- Hospital index: `_hospital_by_id` for O(1) lookups
- Hospital info cache: Simplified dict for enrichment
- Prices: Parquet predicate pushdown (no persistent cache)

### 7.3 DrugWatchService

**File:** `frontend/services/drugwatch.py`

**Key Methods:**

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `get_us_drugs()` | `limit`, `search` | `List[Dict]` | US drug list |
| `get_drug()` | `drug_id` | `Dict` | Single drug (exact + partial match) |
| `get_international_prices()` | `country` | `List[Dict]` | Australia/Canada prices |
| `get_nadac_prices()` | `limit`, `search` | `List[Dict]` | NADAC pricing |
| `compare_prices()` | `drug_name` | `Dict` | US vs international |
| `get_top_expensive()` | `limit` | `List[Dict]` | By total spending |

### 7.4 FoodScoreService

**File:** `frontend/services/foodscore.py`

**Key Methods:**

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `get_products()` | `limit`, `search`, `category` | `List[Dict]` | Food products |
| `get_product()` | `barcode` | `Dict` | Single product |
| `get_additives()` | `limit`, `search` | `List[Dict]` | Additive database |
| `get_categories()` | - | `List[str]` | Product categories |
| `get_nova_distribution()` | - | `Dict[int, int]` | NOVA class counts |
| `get_high_risk_products()` | `limit` | `List[Dict]` | Lowest MAHA scores |

### 7.5 ChronicCareService

**File:** `frontend/services/chroniccare.py`

**Key Methods:**

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `get_county_health()` | `state`, `limit` | `List[Dict]` | County health data |
| `get_county()` | `fips` | `Dict` | Single county |
| `get_correlations()` | - | `List[Dict]` | Food-disease correlations |
| `get_intervention_priorities()` | `limit` | `List[Dict]` | ML priority scores (21+ features) |
| `get_state_statistics()` | - | `Dict[str, Dict]` | State-level aggregates |
| `get_national_trends()` | - | `Dict` | National averages |

### 7.6 RuralAccessService

**File:** `frontend/services/ruralaccess.py`

**Key Methods:**

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `get_hpsa_designations()` | `state`, `discipline`, `shortage_level`, etc. | `List[Dict]` | HPSA areas |
| `get_counties()` | `state`, `limit` | `List[Dict]` | County shortage data |
| `get_fqhc_locations()` | `state`, `limit` | `List[Dict]` | Health centers |
| `get_shortage_map_data()` | - | `List[Dict]` | Map visualization data |
| `get_analytics()` | - | `Dict` | Comprehensive analytics |

---

## 8. API Reference

### 8.1 Public API Endpoints

#### PriceVision

| Method | Endpoint | Parameters | Response |
|--------|----------|------------|----------|
| GET | `/public/api/pricevision/procedures` | `q`, `limit` | `[{hcpcs_code, description, ...}]` |
| GET | `/public/api/pricevision/hospitals` | `state`, `limit` | `[{npi, name, state, ...}]` |

#### DrugWatch

| Method | Endpoint | Parameters | Response |
|--------|----------|------------|----------|
| GET | `/public/api/drugwatch/drugs` | `q`, `limit` | `[{brand_name, generic_name, ...}]` |
| GET | `/public/api/drugwatch/compare/<drug_name>` | - | `{us: {...}, international: [...]}` |

#### FoodScore

| Method | Endpoint | Parameters | Response |
|--------|----------|------------|----------|
| GET | `/public/api/foodscore/products` | `q`, `category`, `limit` | `[{barcode, product_name, ...}]` |
| GET | `/public/api/foodscore/product/<barcode>` | - | `{...product, ml_nova_group, ml_additive_risks}` |
| GET | `/public/api/foodscore/additives` | `q`, `limit` | `[{name, risk_score, ...}]` |
| GET | `/public/api/foodscore/stats` | - | `{total_products, ...}` |

### 8.2 Government API Endpoints

#### RuralAccess (Gov Only)

| Method | Endpoint | Parameters | Response |
|--------|----------|------------|----------|
| GET | `/gov/api/ruralaccess/hpsas` | `state`, `discipline`, `shortage_level`, `limit` | `{data: [...], total, returned}` |
| GET | `/gov/api/ruralaccess/counties` | `state`, `limit` | `{data: [...], total, returned}` |
| GET | `/gov/api/ruralaccess/analytics` | - | `{by_shortage_level, by_state, ...}` |
| GET | `/gov/api/ruralaccess/map-data` | - | `[{hpsa_id, lat, lng, ...}]` |

#### ChronicCare (Gov Only)

| Method | Endpoint | Parameters | Response |
|--------|----------|------------|----------|
| GET | `/gov/api/chroniccare/counties` | `state`, `limit` | `[{fips, county_name, ...}]` |
| GET | `/gov/api/chroniccare/correlations` | - | `[{fips, diabetes, obesity, fast_food, ...}]` |
| GET | `/gov/api/chroniccare/interventions` | `limit` | `[{fips, risk_score, priority, ...}]` |
| GET | `/gov/api/chroniccare/stats` | - | `{total_counties, avg_diabetes, ...}` |
| GET | `/gov/api/chroniccare/state-stats` | - | `{state: {total_counties, ...}}` |

### 8.3 Response Formats

**Success Response:**
```json
{
  "data": [...],
  "total": 1000,
  "returned": 100,
  "limit": 100
}
```

**Error Response:**
```json
{
  "error": "Not found",
  "message": "Hospital with NPI 1234567890 not found"
}
```

---

## 9. Configuration

### 9.1 Frontend Configuration

**File:** `frontend/config.py`

```python
class Config:
    """Flask application configuration."""

    # Security
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')

    # Session
    SESSION_TYPE = 'filesystem'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)

    # Data paths
    DATA_DIR = Path(__file__).parent.parent / 'data'
    RAW_DATA_DIR = DATA_DIR / 'raw'
    PROCESSED_DATA_DIR = DATA_DIR / 'processed'

    # ML paths
    ML_WEIGHTS_DIR = Path(__file__).parent.parent / 'ml' / 'weights'

    # Module definitions
    MODULES = {
        'pricevision': {
            'name': 'PriceVision',
            'description': 'Hospital price transparency',
            'icon': 'bi-currency-dollar',
            'color': '#fd7e14',
            'public': True,
            'gov': True
        },
        'drugwatch': {
            'name': 'DrugWatch',
            'description': 'Drug pricing comparison',
            'icon': 'bi-capsule',
            'color': '#dc3545',
            'public': True,
            'gov': True
        },
        'foodscore': {
            'name': 'FoodScore',
            'description': 'Food health scoring',
            'icon': 'bi-basket',
            'color': '#28a745',
            'public': True,
            'gov': True
        },
        'ruralaccess': {
            'name': 'RuralAccess',
            'description': 'Healthcare access mapping',
            'icon': 'bi-geo-alt',
            'color': '#6f42c1',
            'public': False,
            'gov': True
        },
        'chroniccare': {
            'name': 'ChronicCare',
            'description': 'Chronic disease analytics',
            'icon': 'bi-activity',
            'color': '#0dcaf0',
            'public': False,
            'gov': True
        }
    }

    # Government users (production: use database)
    GOV_USERS = {
        'admin': 'healthguard2024',
        'analyst': 'data2024'
    }
```

### 9.2 ML Configuration

**File:** `ml/config.py`

```python
from dataclasses import dataclass
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / 'data'
WEIGHTS_DIR = Path(__file__).parent / 'weights'

@dataclass
class NovaClassifierConfig:
    """NOVA food classification model configuration."""

    # Model architecture
    vocab_size: int = 10000
    embedding_dim: int = 128
    conv_filters: int = 256
    kernel_size: int = 3
    hidden_dims: tuple = (256, 128)
    num_classes: int = 4
    dropout: float = 0.3
    max_length: int = 200

    # Training
    batch_size: int = 64
    learning_rate: float = 1e-3
    epochs: int = 20
    early_stopping_patience: int = 5

    # Inference
    confidence_threshold: float = 0.60

    # Paths
    training_data: Path = DATA_DIR / 'processed/foodscore/us_products_scored.parquet'
    output_model: Path = WEIGHTS_DIR / 'nova_classifier.pt'
    tokenizer_path: Path = WEIGHTS_DIR / 'nova_tokenizer.json'

    # Device
    device: str = 'cuda'  # Falls back to CPU automatically

@dataclass
class ChronicRiskPredictorConfig:
    """Chronic disease risk prediction model configuration."""

    # Model architecture
    input_dim: int = 19
    num_targets: int = 6
    hidden_dims: tuple = (256, 128, 64)
    dropout: float = 0.3

    # Training
    batch_size: int = 64
    learning_rate: float = 1e-3
    weight_decay: float = 1e-4
    epochs: int = 200
    early_stopping_patience: int = 20

    # Target names
    target_names: tuple = (
        'diabetes_prevalence',
        'obesity_prevalence',
        'heart_disease_prevalence',
        'high_bp_prevalence',
        'copd_prevalence',
        'depression_prevalence'
    )

    # Paths
    training_data: Path = DATA_DIR / 'processed/chroniccare/chroniccare_merged.parquet'
    output_model: Path = WEIGHTS_DIR / 'chronic_risk_predictor.pt'
    scaler_path: Path = WEIGHTS_DIR / 'chronic_feature_scaler.pkl'
```

### 9.3 Environment Variables

```bash
# .env file (not committed to git)

# Flask
FLASK_ENV=development
FLASK_DEBUG=1
SECRET_KEY=your-secret-key-here

# Database (optional backend)
DATABASE_URL=postgresql://user:pass@localhost:5432/healthguard

# Redis (optional caching)
REDIS_URL=redis://localhost:6379/0

# ML
CUDA_VISIBLE_DEVICES=0
ML_DEVICE=cuda  # or 'cpu'

# API Keys (if needed)
OPENAI_API_KEY=your-key-here
```

---

## 10. Security & Authentication

### 10.1 Authentication Flow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   User      │────▶│  /gov/login │────▶│  Validate   │
│             │     │   (GET)     │     │  Session    │
└─────────────┘     └─────────────┘     └──────┬──────┘
                                               │
                           ┌───────────────────┼───────────────────┐
                           │ No session        │                   │ Valid session
                           ▼                   │                   ▼
                    ┌─────────────┐            │            ┌─────────────┐
                    │  Show Login │            │            │  Redirect   │
                    │    Form     │            │            │  to /gov/   │
                    └──────┬──────┘            │            └─────────────┘
                           │                   │
                           ▼                   │
                    ┌─────────────┐            │
                    │  /gov/login │            │
                    │   (POST)    │            │
                    └──────┬──────┘            │
                           │                   │
                    ┌──────┴──────┐            │
                    │  Validate   │            │
                    │ Credentials │            │
                    └──────┬──────┘            │
                           │                   │
              ┌────────────┼────────────┐      │
              │ Invalid    │            │ Valid│
              ▼            │            ▼      │
       ┌─────────────┐     │     ┌─────────────┐
       │  Error Msg  │     │     │ Set Session │
       │  Re-render  │     │     │ Redirect    │
       └─────────────┘     │     └─────────────┘
                           │            │
                           └────────────┘
```

### 10.2 Session Management

```python
# Authentication in blueprints/gov/__init__.py

from functools import wraps
from flask import session, redirect, url_for, request, flash

def gov_required(f):
    """Decorator requiring government authentication."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_gov_user'):
            flash('Please log in to access the government portal.', 'warning')
            return redirect(url_for('gov.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

@gov_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Government portal login."""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if username in Config.GOV_USERS and Config.GOV_USERS[username] == password:
            session['is_gov_user'] = True
            session['gov_username'] = username
            session.permanent = True

            next_url = request.args.get('next', url_for('gov.home'))
            return redirect(next_url)

        flash('Invalid credentials.', 'danger')

    return render_template('gov/login.html')

@gov_bp.route('/logout')
def logout():
    """Clear session and logout."""
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('landing'))
```

### 10.3 Security Best Practices

**Input Validation:**
```python
def validate_input(value: str, max_length: int = 1000) -> str:
    """Sanitize user input."""
    if not value:
        return ''
    # Limit length
    value = str(value)[:max_length]
    # Remove dangerous characters (basic XSS prevention)
    value = value.replace('<', '&lt;').replace('>', '&gt;')
    return value.strip()
```

**SQL Injection Prevention:**
```python
# Always use parameterized queries (if using SQL)
# Services use pandas which handles this automatically

# BAD - Never do this
# df = pd.read_sql(f"SELECT * FROM drugs WHERE name = '{user_input}'", conn)

# GOOD - Use parameterized queries
# df = pd.read_sql("SELECT * FROM drugs WHERE name = ?", conn, params=[user_input])
```

**CSRF Protection:**
```python
# Add to app.py for production
from flask_wtf.csrf import CSRFProtect

csrf = CSRFProtect(app)
```

---

## 11. Deployment Guide

### 11.1 Local Development

```bash
# Clone repository
git clone https://github.com/org/healthguard.git
cd healthguard

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r frontend/requirements.txt
pip install -r ml/requirements.txt

# Process data (if needed)
python scripts/process_data.py --all
python scripts/chroniccare_pipeline.py --all

# Train models (if needed)
python scripts/train_models.py --all

# Run development server
python frontend/app.py
```

### 11.2 Production Deployment

**Using Gunicorn (Linux):**
```bash
# Install Gunicorn
pip install gunicorn

# Run with 4 workers
gunicorn -w 4 -b 0.0.0.0:5000 frontend.app:app

# With logging
gunicorn -w 4 -b 0.0.0.0:5000 \
    --access-logfile /var/log/healthguard/access.log \
    --error-logfile /var/log/healthguard/error.log \
    frontend.app:app
```

**Nginx Configuration:**
```nginx
server {
    listen 80;
    server_name healthguard.example.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location /static {
        alias /var/www/healthguard/frontend/static;
        expires 30d;
    }
}
```

**Docker Deployment:**
```dockerfile
# Dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Run
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "frontend.app:app"]
```

```yaml
# docker-compose.yml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "5000:5000"
    volumes:
      - ./data:/app/data
      - ./ml/weights:/app/ml/weights
    environment:
      - FLASK_ENV=production
      - SECRET_KEY=${SECRET_KEY}
    restart: unless-stopped
```

### 11.3 Cloud Deployment

**AWS (EC2 + S3):**
```bash
# Store large data files in S3
aws s3 sync data/processed/ s3://healthguard-data/processed/

# Download to EC2 on startup
aws s3 sync s3://healthguard-data/processed/ data/processed/
```

**Azure (App Service):**
```bash
# Deploy using Azure CLI
az webapp up --name healthguard --resource-group rg-healthguard --runtime PYTHON:3.10
```

---

## 12. Development Guide

### 12.1 Adding a New Module

1. **Create service class:**
```python
# frontend/services/newmodule.py
class NewModuleService:
    _cache = {}
    _df_cache = {}

    @classmethod
    def get_items(cls, limit=100, search=None):
        # Implementation
        pass
```

2. **Create blueprint routes:**
```python
# frontend/blueprints/public/newmodule.py
from flask import render_template
from . import public_bp
from services.newmodule import NewModuleService

@public_bp.route('/newmodule/')
def newmodule_home():
    items = NewModuleService.get_items(limit=10)
    return render_template('public/newmodule/home.html', items=items)
```

3. **Create templates:**
```html
<!-- frontend/templates/public/newmodule/home.html -->
{% extends "public/base_public.html" %}

{% block content %}
<div class="container py-4">
    <h1>New Module</h1>
    <!-- Content -->
</div>
{% endblock %}
```

4. **Update configuration:**
```python
# frontend/config.py
MODULES = {
    # ... existing modules
    'newmodule': {
        'name': 'NewModule',
        'description': 'Description',
        'icon': 'bi-icon-name',
        'color': '#hexcolor',
        'public': True,
        'gov': True
    }
}
```

### 12.2 Adding a New ML Model

1. **Create model architecture:**
```python
# ml/newmodel/model.py
import torch.nn as nn

class NewModel(nn.Module):
    def __init__(self, config):
        super().__init__()
        # Define layers

    def forward(self, x):
        # Forward pass
        pass

    def save(self, path):
        torch.save(self.state_dict(), path)

    @classmethod
    def load(cls, path, config):
        model = cls(config)
        model.load_state_dict(torch.load(path))
        return model
```

2. **Create inference service:**
```python
# ml/newmodel/inference.py
class NewModelService:
    def __init__(self, model, config):
        self.model = model
        self.config = config

    @classmethod
    def load(cls):
        model = NewModel.load(WEIGHTS_PATH, CONFIG)
        return cls(model, CONFIG)

    def predict(self, input_data):
        # Inference logic
        pass
```

3. **Create training script:**
```python
# ml/newmodel/train.py
def train():
    # Load data
    # Create model
    # Training loop
    # Save best model
    pass

if __name__ == '__main__':
    train()
```

4. **Add configuration:**
```python
# ml/config.py
@dataclass
class NewModelConfig:
    # Architecture
    input_dim: int = 100
    hidden_dim: int = 64
    output_dim: int = 1

    # Training
    batch_size: int = 32
    learning_rate: float = 1e-3
    epochs: int = 100

    # Paths
    training_data: Path = DATA_DIR / 'processed/newmodel/data.parquet'
    output_model: Path = WEIGHTS_DIR / 'newmodel.pt'
```

### 12.3 Code Style Guidelines

**Python Style:**
- Follow PEP 8
- Use type hints for function signatures
- Docstrings for all public methods
- Maximum line length: 100 characters

```python
def get_hospital(self, facility_id: str) -> Optional[Dict]:
    """
    Get single hospital by facility ID.

    Args:
        facility_id: The CMS facility identifier

    Returns:
        Hospital dict or None if not found
    """
    pass
```

**Template Style:**
- Use Jinja2 best practices
- Consistent indentation (4 spaces)
- Comments for complex logic

```html
{% for item in items %}
    {# Display item card #}
    <div class="card">
        {{ item.name }}
    </div>
{% else %}
    <p>No items found.</p>
{% endfor %}
```

---

## 13. Testing

### 13.1 Service Testing

```python
# tests/test_services.py
import pytest
from frontend.services.pricevision import PriceVisionService
from frontend.services.drugwatch import DrugWatchService

class TestPriceVisionService:
    def test_get_procedures_returns_list(self):
        procedures = PriceVisionService.get_procedures(limit=10)
        assert isinstance(procedures, list)
        assert len(procedures) <= 10

    def test_get_procedures_search(self):
        procedures = PriceVisionService.get_procedures(search='MRI')
        for p in procedures:
            assert 'mri' in p['description'].lower()

    def test_get_hospital_returns_none_for_invalid(self):
        hospital = PriceVisionService.get_hospital('invalid')
        assert hospital is None

    def test_get_states_returns_valid_states(self):
        states = PriceVisionService.get_states()
        assert all(len(s) == 2 for s in states)

class TestDrugWatchService:
    def test_get_drug_with_none_returns_none(self):
        drug = DrugWatchService.get_drug(None)
        assert drug is None

    def test_get_drug_with_empty_returns_none(self):
        drug = DrugWatchService.get_drug('')
        assert drug is None

    def test_compare_prices_returns_dict(self):
        result = DrugWatchService.compare_prices('aspirin')
        assert 'us' in result
        assert 'international' in result
```

### 13.2 Route Testing

```python
# tests/test_routes.py
import pytest
from frontend.app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

class TestPublicRoutes:
    def test_landing_page(self, client):
        response = client.get('/')
        assert response.status_code == 200
        assert b'HealthGuard' in response.data

    def test_public_home(self, client):
        response = client.get('/public/')
        assert response.status_code == 200

    def test_pricevision_home(self, client):
        response = client.get('/public/pricevision/')
        assert response.status_code == 200

    def test_api_returns_json(self, client):
        response = client.get('/public/api/foodscore/stats')
        assert response.status_code == 200
        assert response.content_type == 'application/json'

class TestGovRoutes:
    def test_gov_requires_auth(self, client):
        response = client.get('/gov/')
        assert response.status_code == 302  # Redirect to login

    def test_login_page(self, client):
        response = client.get('/gov/login')
        assert response.status_code == 200
        assert b'Login' in response.data
```

### 13.3 ML Model Testing

```python
# tests/test_ml.py
import pytest
import torch
from ml.nova_classifier.inference import NovaClassificationService
from ml.additive_scorer.inference import AdditiveRiskService

class TestNovaClassifier:
    @pytest.fixture(scope='class')
    def service(self):
        return NovaClassificationService.load()

    def test_classify_fresh_food(self, service):
        result = service.classify('fresh apples')
        assert result.nova_group in [1, 2]

    def test_classify_ultra_processed(self, service):
        result = service.classify('water, high fructose corn syrup, red 40, artificial flavors')
        assert result.nova_group == 4

    def test_confidence_in_range(self, service):
        result = service.classify('sugar')
        assert 0 <= result.confidence <= 1

    def test_batch_classification(self, service):
        results = service.classify_batch(['apple', 'sugar', 'soda'])
        assert len(results) == 3

class TestAdditiveScorer:
    @pytest.fixture(scope='class')
    def service(self):
        return AdditiveRiskService.load()

    def test_score_known_additive(self, service):
        result = service.score_additive('Red 40')
        assert 0 <= result.risk_score <= 100
        assert result.risk_category in ['low', 'moderate', 'high']

    def test_batch_scoring(self, service):
        results = service.score_batch(['Red 40', 'Citric Acid'])
        assert len(results) == 2
```

---

## 14. Performance Optimization

### 14.1 Data Layer Optimization

**Parquet Predicate Pushdown:**
```python
# Efficient - only loads matching rows
import pyarrow.parquet as pq

filters = [('state', '=', 'CA'), ('price', '>', 0)]
table = pq.read_table('prices.parquet', filters=filters, columns=['price', 'hospital'])
```

**DataFrame Caching:**
```python
class OptimizedService:
    _df_cache = {}

    @classmethod
    def _get_cached_df(cls, key, loader_func):
        if key not in cls._df_cache:
            cls._df_cache[key] = loader_func()
        return cls._df_cache[key]
```

**Index-based Lookups:**
```python
class HospitalService:
    _hospital_by_id = {}

    @classmethod
    def _build_index(cls, hospitals):
        cls._hospital_by_id = {h['facility_id']: h for h in hospitals}

    @classmethod
    def get_hospital(cls, facility_id):
        # O(1) lookup instead of O(n)
        return cls._hospital_by_id.get(facility_id)
```

### 14.2 ML Inference Optimization

**Model Caching:**
```python
# Lazy loading with singleton pattern
_service_instance = None

def get_service():
    global _service_instance
    if _service_instance is None:
        _service_instance = MLService.load()
    return _service_instance
```

**Batch Inference:**
```python
# Inefficient - one at a time
for item in items:
    result = model.predict(item)

# Efficient - batch processing
results = model.predict_batch(items)
```

**GPU Acceleration:**
```python
device = 'cuda' if torch.cuda.is_available() else 'cpu'
model = model.to(device)
inputs = inputs.to(device)
```

### 14.3 Response Optimization

**Pagination:**
```python
@app.route('/api/items')
def get_items():
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 50))

    total = len(all_items)
    start = (page - 1) * per_page
    items = all_items[start:start + per_page]

    return jsonify({
        'data': items,
        'page': page,
        'per_page': per_page,
        'total': total,
        'pages': (total + per_page - 1) // per_page
    })
```

**Response Compression:**
```python
from flask_compress import Compress

compress = Compress()
compress.init_app(app)
```

---

## 15. Troubleshooting

### 15.1 Common Issues

**Issue: Model not loading**
```
FileNotFoundError: Model not found at ml/weights/nova_classifier.pt
```
**Solution:** Train the model first:
```bash
python -m ml.nova_classifier.train
```

**Issue: Memory error with large data**
```
MemoryError: Unable to allocate array
```
**Solution:** Use Parquet with predicate pushdown, or increase system memory.

**Issue: CUDA out of memory**
```
RuntimeError: CUDA out of memory
```
**Solution:** Reduce batch size or use CPU:
```python
config.device = 'cpu'
```

**Issue: Template not found**
```
jinja2.exceptions.TemplateNotFound: public/module/page.html
```
**Solution:** Check template path and ensure file exists.

### 15.2 Debugging

**Enable Flask debug mode:**
```python
app.run(debug=True)
```

**Add logging:**
```python
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

logger.debug(f"Processing {len(items)} items")
logger.error(f"Failed to load data: {e}")
```

**Profile slow code:**
```python
import cProfile
import pstats

profiler = cProfile.Profile()
profiler.enable()

# Code to profile
result = slow_function()

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats(10)
```

---

## 16. Appendices

### 16.1 Glossary

| Term | Definition |
|------|------------|
| **HCPCS** | Healthcare Common Procedure Coding System |
| **CPT** | Current Procedural Terminology |
| **NPI** | National Provider Identifier |
| **FIPS** | Federal Information Processing Standards (county codes) |
| **HPSA** | Health Professional Shortage Area |
| **NOVA** | Food classification system (1-4 processing levels) |
| **MAHA** | Make America Healthy Again index |
| **MRF** | Machine Readable File (hospital pricing) |
| **PBS** | Pharmaceutical Benefits Scheme (Australia) |
| **NADAC** | National Average Drug Acquisition Cost |

### 16.2 Data Source URLs

| Source | URL |
|--------|-----|
| CMS Hospital Data | https://data.cms.gov/ |
| Medicare Part D | https://data.cms.gov/provider-summary-by-type-of-service/medicare-part-d-prescribers |
| Open Food Facts | https://world.openfoodfacts.org/data |
| CDC PLACES | https://www.cdc.gov/places/ |
| HRSA HPSA | https://data.hrsa.gov/ |
| USDA Food Atlas | https://www.ers.usda.gov/data-products/food-environment-atlas/ |

### 16.3 Model Performance Summary

| Model | Metric | Value | Date Trained |
|-------|--------|-------|--------------|
| NOVA Classifier | Accuracy | 96.16% | Jan 2026 |
| NOVA Classifier | Macro F1 | 0.94 | Jan 2026 |
| Additive Scorer | Accuracy | 85.71% | Jan 2026 |
| Additive Scorer | R² | 0.82 | Jan 2026 |
| Chronic Risk | MAE | 1.76% | Jan 2026 |
| Intervention Prioritizer | Accuracy | 93.9% | Jan 2026 |
| Procedure Encoder | MRR | 0.85 | Jan 2026 |
| Procedure Encoder | Hits@5 | 0.92 | Jan 2026 |

### 16.4 File Size Reference

| Category | Files | Total Size |
|----------|-------|------------|
| Raw Data (PriceVision) | 1,084 MRFs | ~5 GB |
| Raw Data (FoodScore) | 1 file | ~6 GB (compressed) |
| Processed Data | ~20 files | ~500 MB |
| ML Weights | 10 files | ~104 MB |
| Templates | 40+ files | ~200 KB |

### 16.5 Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | Jan 2026 | Initial release |
| 0.9.0 | Dec 2025 | Beta release with all 5 modules |
| 0.8.0 | Nov 2025 | Added ChronicCare module |
| 0.7.0 | Oct 2025 | Added RuralAccess module |
| 0.6.0 | Sep 2025 | Added FoodScore ML models |
| 0.5.0 | Aug 2025 | Added DrugWatch module |
| 0.4.0 | Jul 2025 | Added PriceVision module |
| 0.1.0 | Jun 2025 | Project initialization |

---

## Document Metadata

**Document:** TECHNICAL_DOCUMENTATION.md
**Version:** 1.0.0
**Last Updated:** January 2026
**Authors:** HealthGuard Development Team
**License:** Proprietary

---

*End of Technical Documentation*
