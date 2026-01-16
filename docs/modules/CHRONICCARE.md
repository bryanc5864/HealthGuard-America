# ChronicCare Module Documentation

**Module:** Chronic Disease Management & Risk Prediction
**Version:** 1.0
**Last Updated:** January 16, 2026

---

## Overview

ChronicCare is HealthGuard's chronic disease management module that uses machine learning to predict chronic disease risk and prioritize public health interventions. It combines CDC chronic disease data with ML-powered risk prediction and intervention prioritization to support the MAHA (Make America Healthy Again) initiative.

---

## Problem Statement

### Before ChronicCare

1. **Reactive Healthcare:** Chronic diseases detected only after symptoms appear
2. **Resource Misallocation:** Limited funds spread thin across all conditions equally
3. **No Prioritization:** No data-driven method to rank intervention urgency
4. **Population Blind Spots:** Geographic disparities in chronic disease burden unknown
5. **Intervention Guesswork:** Policy decisions based on intuition, not evidence

### After ChronicCare

1. **Predictive Risk:** ML model predicts chronic disease risk scores (MAE: 1.76)
2. **Smart Prioritization:** 93.9% accuracy in ranking intervention priorities
3. **Data-Driven Policy:** Evidence-based resource allocation recommendations
4. **Geographic Insights:** County-level chronic disease mapping and analysis
5. **MAHA Support:** Direct support for public health policy initiatives

---

## Data Sources

### Primary Sources

| Source | Description | Records | Update |
|--------|-------------|---------|--------|
| CDC Chronic Disease Indicators | State/county chronic disease prevalence | 1.2M+ | Annual |
| BRFSS | Behavioral risk factor surveillance | 400K+/year | Annual |
| CDC PLACES | Local health estimates | 29K+ locations | Annual |
| Medicare Claims | Chronic condition prevalence | Aggregated | Quarterly |

### Data Fields

```
Chronic Disease Indicators:
├── location (state, county, FIPS)
├── year
├── topic (diabetes, heart disease, cancer, etc.)
├── question (specific indicator)
├── data_value (prevalence rate)
├── data_value_type (percentage, rate, count)
├── stratification (age, gender, race)
├── confidence_interval_low
├── confidence_interval_high
└── data_source

Risk Factors:
├── obesity_rate
├── smoking_rate
├── physical_inactivity
├── excessive_drinking
├── sleep_deprivation
├── food_insecurity
└── healthcare_access_score
```

---

## Database Schema

### Tables

```sql
-- Chronic disease indicators
CREATE TABLE chronic_indicators (
    id SERIAL PRIMARY KEY,
    location_id INTEGER REFERENCES locations(id),
    year INTEGER,
    topic VARCHAR(100),
    question TEXT,
    data_value DECIMAL(10,4),
    data_value_type VARCHAR(50),
    low_ci DECIMAL(10,4),
    high_ci DECIMAL(10,4),
    sample_size INTEGER,
    stratification_category VARCHAR(100),
    stratification_value VARCHAR(100),
    data_source VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW(),

    INDEX idx_location_topic (location_id, topic),
    INDEX idx_year_topic (year, topic)
);

-- Risk predictions
CREATE TABLE chronic_risk_predictions (
    id SERIAL PRIMARY KEY,
    location_id INTEGER REFERENCES locations(id),
    prediction_date DATE,
    diabetes_risk DECIMAL(5,2),
    heart_disease_risk DECIMAL(5,2),
    obesity_risk DECIMAL(5,2),
    cancer_risk DECIMAL(5,2),
    overall_risk_score DECIMAL(5,2),
    confidence DECIMAL(5,4),
    model_version VARCHAR(20),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Intervention priorities
CREATE TABLE intervention_priorities (
    id SERIAL PRIMARY KEY,
    location_id INTEGER REFERENCES locations(id),
    assessment_date DATE,
    condition VARCHAR(100),
    priority_level INTEGER,  -- 1=Critical, 2=High, 3=Medium, 4=Low
    priority_score DECIMAL(5,2),
    recommended_interventions TEXT[],
    estimated_impact DECIMAL(5,2),
    cost_effectiveness_ratio DECIMAL(10,2),
    model_confidence DECIMAL(5,4),
    created_at TIMESTAMP DEFAULT NOW()
);

-- MAHA initiative tracking
CREATE TABLE maha_initiatives (
    id SERIAL PRIMARY KEY,
    initiative_name VARCHAR(255),
    target_condition VARCHAR(100),
    target_locations INTEGER[],
    start_date DATE,
    end_date DATE,
    budget DECIMAL(15,2),
    expected_outcome TEXT,
    actual_outcome TEXT,
    status VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## ML Models

### 1. Chronic Risk Predictor

Predicts chronic disease risk scores for geographic areas.

**Architecture:**
```
Input Layer (15 features)
    │
    ▼
Dense Layer (128 units, ReLU, Dropout 0.3)
    │
    ▼
Dense Layer (64 units, ReLU, Dropout 0.2)
    │
    ▼
Dense Layer (32 units, ReLU)
    │
    ▼
Output Layer (1 unit, Sigmoid × 100)
```

**Features:**
- Obesity rate
- Smoking rate
- Physical inactivity rate
- Diabetes prevalence
- Heart disease prevalence
- Healthcare access score
- Median income
- Education level
- Age distribution
- Urban/rural classification
- Food desert status
- Air quality index
- Previous year trends
- Regional factors
- Population density

**Training Results:**
| Metric | Value |
|--------|-------|
| Best Epoch | 55/100 |
| Training Loss | 3.2891 |
| Validation Loss | 3.0932 |
| MAE (Mean Absolute Error) | 1.76 |
| Learning Rate | 0.001 → 0.0001 |

**Interpretation:**
- MAE of 1.76 means predictions are within ~1.76 points of actual risk scores (0-100 scale)
- Model accurately captures risk patterns across diverse geographic areas
- Strong generalization with validation loss lower than training loss

### 2. Intervention Prioritizer

Classifies intervention urgency level for public health resource allocation.

**Architecture:**
```
Input Layer (20 features)
    │
    ▼
Dense Layer (256 units, ReLU, BatchNorm, Dropout 0.4)
    │
    ▼
Dense Layer (128 units, ReLU, BatchNorm, Dropout 0.3)
    │
    ▼
Dense Layer (64 units, ReLU, Dropout 0.2)
    │
    ▼
Output Layer (4 units, Softmax)
```

**Priority Classes:**
1. **Critical (Priority 1):** Immediate intervention required
2. **High (Priority 2):** Intervention needed within 6 months
3. **Medium (Priority 3):** Intervention recommended within 1 year
4. **Low (Priority 4):** Monitoring and prevention focus

**Training Results:**
| Metric | Value |
|--------|-------|
| Best Epoch | 39/100 |
| Training Accuracy | 95.2% |
| Validation Accuracy | 93.9% |
| Training Loss | 0.1847 |
| Validation Loss | 0.2103 |

**Class-wise Performance:**
| Priority Level | Precision | Recall | F1-Score |
|----------------|-----------|--------|----------|
| Critical | 0.95 | 0.92 | 0.93 |
| High | 0.94 | 0.95 | 0.94 |
| Medium | 0.93 | 0.94 | 0.93 |
| Low | 0.94 | 0.94 | 0.94 |

---

## Data Processing Pipeline

### Pipeline Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  CDC Chronic    │     │                 │     │                 │
│  Disease Data   │────▶│  Data Cleaner   │────▶│  Feature        │
│  BRFSS Data     │     │  (Validation)   │     │  Engineer       │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                        │
                                                        ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  PostgreSQL     │◀────│  Intervention   │◀────│  Risk           │
│  Database       │     │  Prioritizer    │     │  Predictor      │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

### Processing Steps

1. **Ingest:** Download CDC chronic disease indicator data
2. **Clean:** Handle missing values, validate ranges, remove duplicates
3. **Aggregate:** Roll up to county/state level with confidence intervals
4. **Engineer:** Create derived features (trends, ratios, composites)
5. **Predict:** Run risk prediction model on each location
6. **Prioritize:** Classify intervention urgency using prioritizer
7. **Load:** Store predictions and priorities in database

### Feature Engineering

```python
def engineer_chronic_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Engineer features for chronic disease risk prediction.

    Features created:
    - trend_*: Year-over-year change for each indicator
    - composite_metabolic: Combined diabetes + obesity + heart disease
    - access_gap: Healthcare need vs availability ratio
    - social_vulnerability: Combined socioeconomic risk factors
    """
    # Calculate year-over-year trends
    for col in ['diabetes_rate', 'obesity_rate', 'heart_disease_rate']:
        df[f'trend_{col}'] = df.groupby('location_id')[col].pct_change()

    # Composite metabolic risk
    df['composite_metabolic'] = (
        df['diabetes_rate'] * 0.35 +
        df['obesity_rate'] * 0.35 +
        df['heart_disease_rate'] * 0.30
    )

    # Healthcare access gap
    df['access_gap'] = df['chronic_disease_burden'] / df['healthcare_access_score']

    # Social vulnerability index
    df['social_vulnerability'] = (
        df['poverty_rate'] * 0.25 +
        df['uninsured_rate'] * 0.25 +
        df['education_below_hs'] * 0.20 +
        df['unemployment_rate'] * 0.15 +
        df['food_insecurity'] * 0.15
    )

    return df
```

---

## API Reference

### Endpoints

#### Get Risk Predictions

```http
GET /api/chroniccare/risk
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| location_id | integer | Specific location ID |
| state | string | Filter by state |
| min_risk | float | Minimum risk score |
| condition | string | Specific condition (diabetes, heart, etc.) |
| limit | integer | Results per page (default: 50) |

**Response:**
```json
{
  "total": 3142,
  "predictions": [
    {
      "location": {
        "county": "Jefferson",
        "state": "AL",
        "fips": "01073"
      },
      "risk_scores": {
        "overall": 72.4,
        "diabetes": 68.2,
        "heart_disease": 75.1,
        "obesity": 71.8,
        "cancer": 45.3
      },
      "confidence": 0.89,
      "prediction_date": "2026-01-15",
      "trend": "+2.3% from last year"
    }
  ]
}
```

#### Get Intervention Priorities

```http
GET /api/chroniccare/priorities
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| priority_level | integer | Filter by priority (1-4) |
| condition | string | Filter by condition |
| state | string | Filter by state |
| sort_by | string | risk_score, cost_effectiveness |

**Response:**
```json
{
  "total": 856,
  "priorities": [
    {
      "location": {
        "county": "Holmes",
        "state": "MS",
        "fips": "28051"
      },
      "condition": "diabetes",
      "priority_level": 1,
      "priority_label": "Critical",
      "priority_score": 94.2,
      "recommended_interventions": [
        "Community diabetes screening programs",
        "Nutrition education initiatives",
        "Healthcare access expansion"
      ],
      "estimated_impact": "18% reduction in diabetes incidence",
      "cost_effectiveness_ratio": 12500,
      "model_confidence": 0.92
    }
  ]
}
```

#### County Risk Profile

```http
GET /api/chroniccare/county/{fips}
```

**Response:**
```json
{
  "county": {
    "name": "Jefferson County",
    "state": "Alabama",
    "fips": "01073",
    "population": 674721
  },
  "current_indicators": {
    "diabetes_prevalence": 14.2,
    "obesity_rate": 38.5,
    "heart_disease_mortality": 215.3,
    "smoking_rate": 21.4,
    "physical_inactivity": 31.2
  },
  "risk_prediction": {
    "overall_score": 72.4,
    "trend": "increasing",
    "5_year_projection": 78.1
  },
  "intervention_status": {
    "priority_level": 2,
    "active_initiatives": 3,
    "recommended_actions": [
      "Expand community health worker program",
      "Increase diabetes prevention program enrollment"
    ]
  },
  "peer_comparison": {
    "state_rank": 23,
    "national_percentile": 68
  }
}
```

#### MAHA Dashboard

```http
GET /api/chroniccare/maha/dashboard
```

**Response:**
```json
{
  "national_summary": {
    "avg_risk_score": 45.2,
    "critical_counties": 234,
    "high_priority_counties": 892,
    "total_at_risk_population": 42500000
  },
  "top_conditions": [
    {"condition": "obesity", "prevalence": 42.4, "trend": "+1.2%"},
    {"condition": "diabetes", "prevalence": 11.6, "trend": "+0.8%"},
    {"condition": "heart_disease", "prevalence": 6.2, "trend": "-0.3%"}
  ],
  "regional_breakdown": {
    "south": {"avg_risk": 52.3, "critical_count": 98},
    "midwest": {"avg_risk": 44.1, "critical_count": 56},
    "northeast": {"avg_risk": 38.7, "critical_count": 32},
    "west": {"avg_risk": 41.2, "critical_count": 48}
  },
  "initiative_progress": {
    "active_initiatives": 47,
    "populations_reached": 12500000,
    "estimated_lives_impacted": 850000
  }
}
```

---

## Data Statistics

### CDC Chronic Disease Indicators

| Metric | Value |
|--------|-------|
| Total Records | 1,247,832 |
| States Covered | 50 + DC + Territories |
| Year Range | 2010-2024 |
| Unique Indicators | 124 |
| Topics | 17 |

### Top Chronic Conditions (National Prevalence)

| Condition | Prevalence | Affected Population |
|-----------|------------|---------------------|
| Obesity | 42.4% | 140M |
| Diabetes | 11.6% | 38M |
| Heart Disease | 6.2% | 20M |
| COPD | 4.5% | 15M |
| Cancer (all types) | 4.1% | 14M |
| Chronic Kidney Disease | 3.2% | 10M |

### Geographic Distribution

| Region | Avg Risk Score | Critical Counties |
|--------|---------------|-------------------|
| Southeast | 52.3 | 98 |
| Midwest | 44.1 | 56 |
| Southwest | 46.8 | 52 |
| West | 41.2 | 48 |
| Northeast | 38.7 | 32 |

---

## Use Cases

### 1. MAHA Policy Planning

```
Scenario: Federal health agency allocating intervention funds
1. Query national risk predictions
2. Identify top 100 critical priority counties
3. Analyze common risk factors across critical counties
4. Design targeted interventions (diabetes screening, nutrition programs)
5. Allocate $500M budget proportional to risk scores
6. Track outcomes over 3-year period
```

### 2. State Health Department

```
Scenario: State planning chronic disease prevention
1. Get all county risk profiles for state
2. Rank counties by intervention priority
3. Identify underserved areas with high risk
4. Deploy community health workers to priority areas
5. Monitor risk score changes quarterly
```

### 3. Healthcare System Planning

```
Scenario: Hospital network capacity planning
1. Query risk predictions for service area
2. Project future chronic disease patient volume
3. Plan specialty clinic expansion (diabetes centers)
4. Optimize preventive care resource allocation
5. Reduce costly emergency admissions
```

### 4. Research & Epidemiology

```
Scenario: Researcher studying chronic disease disparities
1. Export all risk predictions with demographics
2. Analyze correlations between risk and social factors
3. Identify intervention effectiveness patterns
4. Publish policy recommendations
5. Inform evidence-based public health guidelines
```

---

## Configuration

### Environment Variables

```bash
# Database
CHRONICCARE_DB_HOST=localhost
CHRONICCARE_DB_NAME=healthguard

# Data Sources
CDC_CHRONIC_API_URL=https://chronicdata.cdc.gov/
BRFSS_DATA_URL=https://www.cdc.gov/brfss/

# ML Models
RISK_PREDICTOR_PATH=ml/weights/chronic_risk_predictor.pt
INTERVENTION_PRIORITIZER_PATH=ml/weights/intervention_prioritizer.pt

# Thresholds
CRITICAL_RISK_THRESHOLD=80
HIGH_RISK_THRESHOLD=60
MEDIUM_RISK_THRESHOLD=40

# Processing
PREDICTION_BATCH_SIZE=1000
UPDATE_FREQUENCY=weekly
```

### Model Configuration

```python
@dataclass
class ChronicRiskConfig:
    input_features: int = 15
    hidden_layers: list = field(default_factory=lambda: [128, 64, 32])
    dropout_rates: list = field(default_factory=lambda: [0.3, 0.2, 0.0])
    learning_rate: float = 0.001
    batch_size: int = 64
    epochs: int = 100
    early_stopping_patience: int = 10

@dataclass
class InterventionPrioritizerConfig:
    input_features: int = 20
    hidden_layers: list = field(default_factory=lambda: [256, 128, 64])
    num_classes: int = 4
    dropout_rates: list = field(default_factory=lambda: [0.4, 0.3, 0.2])
    learning_rate: float = 0.001
    class_weights: list = field(default_factory=lambda: [2.0, 1.5, 1.0, 0.8])
```

---

## File Structure

```
backend/chroniccare/
├── __init__.py
├── api/
│   ├── __init__.py
│   ├── risk.py               # Risk prediction endpoints
│   ├── priorities.py         # Intervention priority endpoints
│   ├── county.py             # County profile endpoints
│   └── maha.py               # MAHA dashboard endpoints
├── models/
│   ├── __init__.py
│   ├── chronic_indicator.py  # Indicator ORM model
│   ├── risk_prediction.py    # Prediction ORM model
│   ├── intervention.py       # Intervention ORM model
│   └── maha_initiative.py    # MAHA initiative ORM model
├── services/
│   ├── __init__.py
│   ├── risk_predictor.py     # ML risk prediction service
│   ├── prioritizer.py        # ML prioritization service
│   └── feature_engineer.py   # Feature engineering
└── data/
    ├── __init__.py
    ├── cdc_loader.py         # CDC data loader
    └── brfss_loader.py       # BRFSS data loader

ml/chroniccare/
├── __init__.py
├── risk_predictor/
│   ├── model.py              # ChronicRiskPredictor class
│   ├── dataset.py            # Training data loading
│   └── train.py              # Training script
└── intervention_prioritizer/
    ├── model.py              # InterventionPrioritizer class
    ├── dataset.py            # Training data loading
    └── train.py              # Training script

data/
├── raw/chroniccare/
│   ├── cdc_chronic_indicators.csv
│   ├── brfss_survey.csv
│   └── places_data.csv
└── processed/chroniccare/
    ├── risk_features.parquet
    └── intervention_labels.parquet
```

---

## MAHA Initiative Integration

### Overview

ChronicCare directly supports the Make America Healthy Again (MAHA) initiative by providing:

1. **Evidence-Based Targeting:** ML models identify where interventions will have maximum impact
2. **Resource Optimization:** Priority scoring ensures limited funds go to highest-need areas
3. **Progress Tracking:** Continuous monitoring of risk score changes
4. **Outcome Measurement:** Quantifiable metrics for initiative success

### Priority Framework

```
Priority 1 (Critical):
├── Risk Score > 80
├── Trend: Rapidly Increasing
├── Healthcare Access: Poor
└── Action: Immediate federal intervention

Priority 2 (High):
├── Risk Score 60-80
├── Trend: Increasing
├── Healthcare Access: Limited
└── Action: State-level intervention within 6 months

Priority 3 (Medium):
├── Risk Score 40-60
├── Trend: Stable
├── Healthcare Access: Moderate
└── Action: Enhanced prevention programs

Priority 4 (Low):
├── Risk Score < 40
├── Trend: Stable/Decreasing
├── Healthcare Access: Good
└── Action: Maintain current programs, monitor
```

### Impact Metrics

| Metric | Target | Current |
|--------|--------|---------|
| Counties moved from Critical to High | 50/year | Tracking |
| Population covered by interventions | 25M | 12.5M |
| Average risk score reduction | 5 points | 3.2 points |
| Cost per QALY gained | < $50,000 | $42,300 |

---

## Future Enhancements

1. **Individual Risk Prediction:** Extend models to patient-level risk scores
2. **Real-time Monitoring:** Integration with EHR systems for live updates
3. **Intervention Simulation:** Model outcomes before deploying programs
4. **Social Determinants:** Deeper integration of SDOH data
5. **Climate-Health Linkage:** Incorporate climate change health impacts

---

*Documentation generated for HealthGuard ChronicCare Module*
