"""
ChronicCare - County-Level Chronic Disease and Food Environment Models

Links chronic disease burden to food supply, healthcare costs, and access.
Supports the MAHA (Make America Healthy Again) thesis that:
food supply -> chronic disease -> healthcare costs
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    String, Integer, Float, DateTime, Text, Boolean,
    ForeignKey, Index, Numeric, Enum as SQLEnum
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from core.database import Base


class RuralUrbanCode(int, enum.Enum):
    """USDA Rural-Urban Continuum Code."""
    METRO_1M_PLUS = 1      # Metro - population 1 million+
    METRO_250K_1M = 2      # Metro - population 250K to 1 million
    METRO_LT_250K = 3      # Metro - population < 250K
    NONMETRO_20K_PLUS = 4  # Nonmetro - urban pop 20K+, adjacent to metro
    NONMETRO_20K_ADJ = 5   # Nonmetro - urban pop 20K+, not adjacent
    NONMETRO_2500_20K_ADJ = 6   # Nonmetro - urban pop 2.5K-20K, adjacent
    NONMETRO_2500_20K = 7       # Nonmetro - urban pop 2.5K-20K, not adjacent
    NONMETRO_LT_2500_ADJ = 8    # Nonmetro - urban pop < 2.5K, adjacent
    NONMETRO_LT_2500 = 9        # Nonmetro - urban pop < 2.5K, not adjacent


class FoodAccessLevel(str, enum.Enum):
    """Food access classification."""
    HIGH_ACCESS = "high_access"
    MODERATE_ACCESS = "moderate_access"
    LOW_ACCESS = "low_access"
    FOOD_DESERT = "food_desert"


class CountyHealth(Base):
    """
    County-level chronic disease prevalence from CDC PLACES.

    Contains age-adjusted prevalence rates for major chronic diseases
    that are linked to diet and lifestyle factors.
    """

    __tablename__ = "county_health"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Geographic identifiers
    fips: Mapped[str] = mapped_column(String(5), unique=True, nullable=False, index=True)
    state_fips: Mapped[str] = mapped_column(String(2), nullable=False, index=True)
    county_name: Mapped[str] = mapped_column(String(100), nullable=False)
    state_abbr: Mapped[str] = mapped_column(String(2), nullable=False, index=True)
    state_name: Mapped[str] = mapped_column(String(50), nullable=False)

    # Population
    total_population: Mapped[Optional[int]] = mapped_column(Integer)
    population_65_plus: Mapped[Optional[int]] = mapped_column(Integer)

    # Key chronic disease prevalence (age-adjusted %)
    # Diabetes
    diabetes_prevalence: Mapped[Optional[float]] = mapped_column(Float, index=True)
    diabetes_confidence_low: Mapped[Optional[float]] = mapped_column(Float)
    diabetes_confidence_high: Mapped[Optional[float]] = mapped_column(Float)

    # Obesity
    obesity_prevalence: Mapped[Optional[float]] = mapped_column(Float, index=True)
    obesity_confidence_low: Mapped[Optional[float]] = mapped_column(Float)
    obesity_confidence_high: Mapped[Optional[float]] = mapped_column(Float)

    # Heart Disease (Coronary Heart Disease)
    heart_disease_prevalence: Mapped[Optional[float]] = mapped_column(Float, index=True)
    heart_disease_confidence_low: Mapped[Optional[float]] = mapped_column(Float)
    heart_disease_confidence_high: Mapped[Optional[float]] = mapped_column(Float)

    # Stroke
    stroke_prevalence: Mapped[Optional[float]] = mapped_column(Float)
    stroke_confidence_low: Mapped[Optional[float]] = mapped_column(Float)
    stroke_confidence_high: Mapped[Optional[float]] = mapped_column(Float)

    # High Blood Pressure
    high_bp_prevalence: Mapped[Optional[float]] = mapped_column(Float)
    high_bp_confidence_low: Mapped[Optional[float]] = mapped_column(Float)
    high_bp_confidence_high: Mapped[Optional[float]] = mapped_column(Float)

    # High Cholesterol
    high_cholesterol_prevalence: Mapped[Optional[float]] = mapped_column(Float)
    high_cholesterol_confidence_low: Mapped[Optional[float]] = mapped_column(Float)
    high_cholesterol_confidence_high: Mapped[Optional[float]] = mapped_column(Float)

    # Chronic Kidney Disease
    kidney_disease_prevalence: Mapped[Optional[float]] = mapped_column(Float)
    kidney_disease_confidence_low: Mapped[Optional[float]] = mapped_column(Float)
    kidney_disease_confidence_high: Mapped[Optional[float]] = mapped_column(Float)

    # Cancer (all types)
    cancer_prevalence: Mapped[Optional[float]] = mapped_column(Float)
    cancer_confidence_low: Mapped[Optional[float]] = mapped_column(Float)
    cancer_confidence_high: Mapped[Optional[float]] = mapped_column(Float)

    # COPD
    copd_prevalence: Mapped[Optional[float]] = mapped_column(Float)
    copd_confidence_low: Mapped[Optional[float]] = mapped_column(Float)
    copd_confidence_high: Mapped[Optional[float]] = mapped_column(Float)

    # Depression
    depression_prevalence: Mapped[Optional[float]] = mapped_column(Float)
    depression_confidence_low: Mapped[Optional[float]] = mapped_column(Float)
    depression_confidence_high: Mapped[Optional[float]] = mapped_column(Float)

    # Behavioral risk factors
    physical_inactivity_prevalence: Mapped[Optional[float]] = mapped_column(Float)
    smoking_prevalence: Mapped[Optional[float]] = mapped_column(Float)
    binge_drinking_prevalence: Mapped[Optional[float]] = mapped_column(Float)

    # Composite scores (calculated)
    chronic_disease_burden_score: Mapped[Optional[float]] = mapped_column(Float, index=True)  # 0-100
    preventable_disease_score: Mapped[Optional[float]] = mapped_column(Float)  # Focus on diet-related

    # Data year and source
    data_year: Mapped[int] = mapped_column(Integer, default=2023, index=True)
    source: Mapped[str] = mapped_column(String(50), default="cdc_places")

    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    food_environment: Mapped[Optional["CountyFoodEnvironment"]] = relationship(
        "CountyFoodEnvironment", back_populates="county_health", uselist=False
    )
    medicare_spending: Mapped[Optional["CountyMedicareSpending"]] = relationship(
        "CountyMedicareSpending", back_populates="county_health", uselist=False
    )

    __table_args__ = (
        Index("ix_county_health_state_diabetes", "state_abbr", "diabetes_prevalence"),
        Index("ix_county_health_state_obesity", "state_abbr", "obesity_prevalence"),
        Index("ix_county_health_burden", "chronic_disease_burden_score"),
    )

    def __repr__(self) -> str:
        return f"<CountyHealth(fips={self.fips}, county={self.county_name}, state={self.state_abbr})>"

    @property
    def diet_related_disease_avg(self) -> Optional[float]:
        """Average of diet-related chronic disease rates."""
        diseases = [
            self.diabetes_prevalence,
            self.obesity_prevalence,
            self.heart_disease_prevalence,
            self.high_bp_prevalence,
        ]
        valid = [d for d in diseases if d is not None]
        return sum(valid) / len(valid) if valid else None


class CountyFoodEnvironment(Base):
    """
    County-level food environment data from USDA Food Environment Atlas.

    Captures food access, availability, and quality metrics that
    correlate with chronic disease outcomes.
    """

    __tablename__ = "county_food_environment"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Link to county health
    fips: Mapped[str] = mapped_column(
        String(5), ForeignKey("county_health.fips"), unique=True, nullable=False, index=True
    )

    # Food store access
    grocery_stores_per_1000: Mapped[Optional[float]] = mapped_column(Float)
    supercenters_per_1000: Mapped[Optional[float]] = mapped_column(Float)
    convenience_stores_per_1000: Mapped[Optional[float]] = mapped_column(Float)
    specialty_food_stores_per_1000: Mapped[Optional[float]] = mapped_column(Float)

    # Fast food / Restaurant density
    fast_food_restaurants_per_1000: Mapped[Optional[float]] = mapped_column(Float, index=True)
    full_service_restaurants_per_1000: Mapped[Optional[float]] = mapped_column(Float)
    fast_food_to_full_service_ratio: Mapped[Optional[float]] = mapped_column(Float)

    # Food access metrics (% of population)
    pct_low_access_pop: Mapped[Optional[float]] = mapped_column(Float, index=True)  # Low access to grocery
    pct_low_access_seniors: Mapped[Optional[float]] = mapped_column(Float)
    pct_low_access_children: Mapped[Optional[float]] = mapped_column(Float)
    pct_low_access_low_income: Mapped[Optional[float]] = mapped_column(Float)

    # Food desert metrics
    pct_food_desert_pop: Mapped[Optional[float]] = mapped_column(Float, index=True)
    food_desert_tracts: Mapped[Optional[int]] = mapped_column(Integer)
    total_tracts: Mapped[Optional[int]] = mapped_column(Integer)

    # Food assistance
    snap_participants: Mapped[Optional[int]] = mapped_column(Integer)
    snap_participation_rate: Mapped[Optional[float]] = mapped_column(Float)
    snap_redemptions_per_store: Mapped[Optional[float]] = mapped_column(Float)
    wic_participants: Mapped[Optional[int]] = mapped_column(Integer)
    school_lunch_participation_rate: Mapped[Optional[float]] = mapped_column(Float)

    # Food insecurity
    food_insecurity_rate: Mapped[Optional[float]] = mapped_column(Float, index=True)
    child_food_insecurity_rate: Mapped[Optional[float]] = mapped_column(Float)
    very_low_food_security_rate: Mapped[Optional[float]] = mapped_column(Float)

    # Economic factors
    median_household_income: Mapped[Optional[int]] = mapped_column(Integer)
    poverty_rate: Mapped[Optional[float]] = mapped_column(Float, index=True)
    unemployment_rate: Mapped[Optional[float]] = mapped_column(Float)

    # Rural/Urban classification
    rural_urban_code: Mapped[Optional[RuralUrbanCode]] = mapped_column(
        SQLEnum(RuralUrbanCode), index=True
    )
    metro_nonmetro: Mapped[Optional[str]] = mapped_column(String(20))  # "metro" or "nonmetro"
    pct_rural_population: Mapped[Optional[float]] = mapped_column(Float)

    # Food access classification (calculated)
    food_access_level: Mapped[Optional[FoodAccessLevel]] = mapped_column(
        SQLEnum(FoodAccessLevel), index=True
    )
    food_environment_score: Mapped[Optional[float]] = mapped_column(Float, index=True)  # 0-100, higher=better

    # Data year and source
    data_year: Mapped[int] = mapped_column(Integer, default=2023)
    source: Mapped[str] = mapped_column(String(50), default="usda_food_atlas")

    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationship
    county_health: Mapped["CountyHealth"] = relationship(
        "CountyHealth", back_populates="food_environment"
    )

    __table_args__ = (
        Index("ix_food_env_desert_poverty", "pct_food_desert_pop", "poverty_rate"),
        Index("ix_food_env_fast_food", "fast_food_restaurants_per_1000"),
    )

    def __repr__(self) -> str:
        return f"<CountyFoodEnvironment(fips={self.fips})>"


class CountyMedicareSpending(Base):
    """
    County-level Medicare spending data from CMS Geographic Variation.

    Links healthcare costs to chronic disease burden for
    calculating potential MAHA intervention savings.
    """

    __tablename__ = "county_medicare_spending"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Link to county health
    fips: Mapped[str] = mapped_column(
        String(5), ForeignKey("county_health.fips"), unique=True, nullable=False, index=True
    )

    # Beneficiary counts
    total_beneficiaries: Mapped[Optional[int]] = mapped_column(Integer)
    ffs_beneficiaries: Mapped[Optional[int]] = mapped_column(Integer)  # Fee-for-service
    ma_beneficiaries: Mapped[Optional[int]] = mapped_column(Integer)   # Medicare Advantage

    # Total spending
    total_spending: Mapped[Optional[float]] = mapped_column(Float)
    per_capita_spending: Mapped[Optional[float]] = mapped_column(Float, index=True)
    standardized_per_capita: Mapped[Optional[float]] = mapped_column(Float)  # Adjusted for regional price

    # Spending by service type
    inpatient_spending: Mapped[Optional[float]] = mapped_column(Float)
    outpatient_spending: Mapped[Optional[float]] = mapped_column(Float)
    physician_spending: Mapped[Optional[float]] = mapped_column(Float)
    post_acute_spending: Mapped[Optional[float]] = mapped_column(Float)  # SNF, home health, hospice
    prescription_drug_spending: Mapped[Optional[float]] = mapped_column(Float)
    dme_spending: Mapped[Optional[float]] = mapped_column(Float)  # Durable medical equipment

    # Spending on chronic conditions (if available)
    diabetes_spending: Mapped[Optional[float]] = mapped_column(Float, index=True)
    diabetes_spending_per_beneficiary: Mapped[Optional[float]] = mapped_column(Float)
    heart_disease_spending: Mapped[Optional[float]] = mapped_column(Float)
    heart_disease_spending_per_beneficiary: Mapped[Optional[float]] = mapped_column(Float)
    obesity_related_spending: Mapped[Optional[float]] = mapped_column(Float)
    hypertension_spending: Mapped[Optional[float]] = mapped_column(Float)

    # Hospitalizations (per 1000 beneficiaries)
    all_cause_hospitalizations: Mapped[Optional[float]] = mapped_column(Float)
    preventable_hospitalizations: Mapped[Optional[float]] = mapped_column(Float, index=True)  # AHRQ PQIs
    diabetes_hospitalizations: Mapped[Optional[float]] = mapped_column(Float)
    heart_failure_hospitalizations: Mapped[Optional[float]] = mapped_column(Float)

    # Emergency department visits (per 1000 beneficiaries)
    ed_visits: Mapped[Optional[float]] = mapped_column(Float)
    ed_visits_avoidable: Mapped[Optional[float]] = mapped_column(Float)

    # Readmissions
    readmission_rate: Mapped[Optional[float]] = mapped_column(Float)

    # Quality indicators
    beneficiaries_with_diabetes: Mapped[Optional[int]] = mapped_column(Integer)
    pct_beneficiaries_diabetes: Mapped[Optional[float]] = mapped_column(Float)
    beneficiaries_with_heart_disease: Mapped[Optional[int]] = mapped_column(Integer)
    pct_beneficiaries_heart_disease: Mapped[Optional[float]] = mapped_column(Float)
    beneficiaries_with_multiple_chronic: Mapped[Optional[int]] = mapped_column(Integer)
    pct_multiple_chronic: Mapped[Optional[float]] = mapped_column(Float)

    # Calculated fields
    diet_related_spending_estimate: Mapped[Optional[float]] = mapped_column(Float, index=True)
    potential_savings_10pct_reduction: Mapped[Optional[float]] = mapped_column(Float)  # If disease reduced 10%
    preventable_cost_score: Mapped[Optional[float]] = mapped_column(Float)  # 0-100

    # Comparison to national/state
    spending_vs_national: Mapped[Optional[float]] = mapped_column(Float)  # Ratio
    spending_vs_state: Mapped[Optional[float]] = mapped_column(Float)

    # Data year and source
    data_year: Mapped[int] = mapped_column(Integer, default=2023, index=True)
    source: Mapped[str] = mapped_column(String(50), default="cms_geographic_variation")

    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationship
    county_health: Mapped["CountyHealth"] = relationship(
        "CountyHealth", back_populates="medicare_spending"
    )

    __table_args__ = (
        Index("ix_medicare_spending_per_capita", "per_capita_spending"),
        Index("ix_medicare_preventable", "preventable_hospitalizations"),
    )

    def __repr__(self) -> str:
        return f"<CountyMedicareSpending(fips={self.fips}, per_capita=${self.per_capita_spending})>"


class ChronicDiseaseMetric(Base):
    """
    Aggregated chronic disease metrics for dashboard and analysis.

    Stores computed correlations, rankings, and MAHA intervention targets.
    """

    __tablename__ = "chronic_disease_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Scope (national, state, or county)
    scope_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)  # national/state/county
    scope_value: Mapped[Optional[str]] = mapped_column(String(10), index=True)  # State abbr or FIPS

    # Disease burden statistics
    avg_diabetes_rate: Mapped[Optional[float]] = mapped_column(Float)
    avg_obesity_rate: Mapped[Optional[float]] = mapped_column(Float)
    avg_heart_disease_rate: Mapped[Optional[float]] = mapped_column(Float)
    avg_chronic_burden_score: Mapped[Optional[float]] = mapped_column(Float)

    # Food environment statistics
    avg_food_environment_score: Mapped[Optional[float]] = mapped_column(Float)
    pct_in_food_desert: Mapped[Optional[float]] = mapped_column(Float)
    avg_fast_food_density: Mapped[Optional[float]] = mapped_column(Float)

    # Cost statistics
    total_medicare_spending: Mapped[Optional[float]] = mapped_column(Float)
    avg_per_capita_spending: Mapped[Optional[float]] = mapped_column(Float)
    total_diet_related_spending: Mapped[Optional[float]] = mapped_column(Float)
    total_preventable_spending: Mapped[Optional[float]] = mapped_column(Float)

    # Correlations (food environment -> disease)
    corr_fast_food_diabetes: Mapped[Optional[float]] = mapped_column(Float)
    corr_fast_food_obesity: Mapped[Optional[float]] = mapped_column(Float)
    corr_food_desert_diabetes: Mapped[Optional[float]] = mapped_column(Float)
    corr_food_desert_heart: Mapped[Optional[float]] = mapped_column(Float)
    corr_poverty_chronic_disease: Mapped[Optional[float]] = mapped_column(Float)

    # Rankings (for county-level records)
    chronic_burden_rank_state: Mapped[Optional[int]] = mapped_column(Integer)
    chronic_burden_rank_national: Mapped[Optional[int]] = mapped_column(Integer)
    food_environment_rank_state: Mapped[Optional[int]] = mapped_column(Integer)
    spending_rank_state: Mapped[Optional[int]] = mapped_column(Integer)

    # MAHA intervention targeting
    maha_priority_score: Mapped[Optional[float]] = mapped_column(Float, index=True)  # 0-100
    maha_intervention_tier: Mapped[Optional[str]] = mapped_column(String(20))  # critical/high/medium/low
    potential_lives_improved: Mapped[Optional[int]] = mapped_column(Integer)
    potential_annual_savings: Mapped[Optional[float]] = mapped_column(Float)

    # Time series tracking
    data_year: Mapped[int] = mapped_column(Integer, default=2023, index=True)
    trend_direction: Mapped[Optional[str]] = mapped_column(String(20))  # improving/worsening/stable
    yoy_change_diabetes: Mapped[Optional[float]] = mapped_column(Float)
    yoy_change_obesity: Mapped[Optional[float]] = mapped_column(Float)

    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        Index("ix_chronic_metrics_scope", "scope_type", "scope_value"),
        Index("ix_chronic_metrics_maha_priority", "maha_priority_score"),
    )

    def __repr__(self) -> str:
        return f"<ChronicDiseaseMetric(scope={self.scope_type}:{self.scope_value}, year={self.data_year})>"
