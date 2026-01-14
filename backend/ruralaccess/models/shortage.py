"""
RuralAccess - Healthcare Shortage and Access Models
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from sqlalchemy import (
    String, Integer, Float, DateTime, Text, Boolean,
    ForeignKey, Index, Numeric, Enum as SQLEnum
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from core.database import Base


class DisciplineType(str, enum.Enum):
    """Healthcare discipline types for shortage areas."""
    PRIMARY_CARE = "Primary Care"
    DENTAL = "Dental Health"
    MENTAL_HEALTH = "Mental Health"


class DesignationType(str, enum.Enum):
    """HPSA designation types."""
    GEOGRAPHIC = "Geographic HPSA"
    POPULATION = "Population HPSA"
    FACILITY = "Facility HPSA"
    AUTO = "Auto HPSA"


class RuralStatus(str, enum.Enum):
    """Rural classification status."""
    RURAL = "Rural"
    NON_RURAL = "Non-Rural"
    PARTIALLY_RURAL = "Partially Rural"
    UNKNOWN = "Unknown"


class ProviderType(str, enum.Enum):
    """Healthcare provider types."""
    PHYSICIAN = "physician"
    NURSE_PRACTITIONER = "nurse_practitioner"
    PHYSICIAN_ASSISTANT = "physician_assistant"
    DENTIST = "dentist"
    PSYCHOLOGIST = "psychologist"
    PSYCHIATRIST = "psychiatrist"
    HOSPITAL = "hospital"
    CLINIC = "clinic"
    FQHC = "fqhc"  # Federally Qualified Health Center
    RHC = "rhc"    # Rural Health Clinic
    OTHER = "other"


class HPSA(Base):
    """Health Professional Shortage Area designations."""

    __tablename__ = "hpsa_designations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # HRSA identifiers
    hpsa_id: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    source_id: Mapped[Optional[str]] = mapped_column(String(50))

    # Basic info
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    designation_type: Mapped[DesignationType] = mapped_column(
        SQLEnum(DesignationType), nullable=False, index=True
    )
    discipline: Mapped[DisciplineType] = mapped_column(
        SQLEnum(DisciplineType), nullable=False, index=True
    )

    # Shortage severity
    hpsa_score: Mapped[Optional[int]] = mapped_column(Integer, index=True)  # 0-25, higher = more severe
    shortage_level: Mapped[Optional[str]] = mapped_column(String(50))  # Low, Moderate, High, Critical

    # Status
    status: Mapped[str] = mapped_column(String(50), default="Designated")
    designation_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    last_update_date: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Location
    state: Mapped[str] = mapped_column(String(2), nullable=False, index=True)
    county: Mapped[Optional[str]] = mapped_column(String(100), index=True)
    county_fips: Mapped[Optional[str]] = mapped_column(String(5), index=True)
    address: Mapped[Optional[str]] = mapped_column(Text)
    city: Mapped[Optional[str]] = mapped_column(String(100))
    zip_code: Mapped[Optional[str]] = mapped_column(String(10))

    # Coordinates
    latitude: Mapped[Optional[float]] = mapped_column(Float)
    longitude: Mapped[Optional[float]] = mapped_column(Float)
    # Note: For PostGIS, we'd add a geometry column here

    # Rural status
    rural_status: Mapped[RuralStatus] = mapped_column(
        SQLEnum(RuralStatus), default=RuralStatus.UNKNOWN
    )

    # Population data
    designation_population: Mapped[Optional[int]] = mapped_column(Integer)
    poverty_rate: Mapped[Optional[float]] = mapped_column(Float)  # Percentage
    uninsured_rate: Mapped[Optional[float]] = mapped_column(Float)

    # Provider ratios
    population_to_provider_ratio: Mapped[Optional[float]] = mapped_column(Float)
    providers_needed: Mapped[Optional[int]] = mapped_column(Integer)  # FTE needed to remove shortage

    # Component details (for facility HPSAs)
    facility_name: Mapped[Optional[str]] = mapped_column(String(300))
    facility_type: Mapped[Optional[str]] = mapped_column(String(100))

    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        Index("ix_hpsa_state_discipline", "state", "discipline"),
        Index("ix_hpsa_score_discipline", "hpsa_score", "discipline"),
        Index("ix_hpsa_county_fips", "county_fips"),
        Index("ix_hpsa_location", "latitude", "longitude"),
    )

    def __repr__(self) -> str:
        return f"<HPSA(id={self.hpsa_id}, name={self.name[:50]})>"

    @property
    def severity_category(self) -> str:
        """Categorize shortage severity based on HPSA score."""
        if self.hpsa_score is None:
            return "unknown"
        if self.hpsa_score >= 20:
            return "critical"
        if self.hpsa_score >= 15:
            return "high"
        if self.hpsa_score >= 10:
            return "moderate"
        return "low"


class County(Base):
    """County-level geographic and demographic data."""

    __tablename__ = "counties"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Identifiers
    fips: Mapped[str] = mapped_column(String(5), unique=True, nullable=False, index=True)
    state_fips: Mapped[str] = mapped_column(String(2), nullable=False, index=True)

    # Names
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    state: Mapped[str] = mapped_column(String(2), nullable=False, index=True)
    state_name: Mapped[Optional[str]] = mapped_column(String(50))

    # Geography
    land_area_sq_miles: Mapped[Optional[float]] = mapped_column(Float)
    latitude: Mapped[Optional[float]] = mapped_column(Float)  # Centroid
    longitude: Mapped[Optional[float]] = mapped_column(Float)  # Centroid
    # For PostGIS: geometry column would store actual boundary

    # Demographics
    population: Mapped[Optional[int]] = mapped_column(Integer)
    population_density: Mapped[Optional[float]] = mapped_column(Float)  # per sq mile
    median_age: Mapped[Optional[float]] = mapped_column(Float)
    median_income: Mapped[Optional[int]] = mapped_column(Integer)
    poverty_rate: Mapped[Optional[float]] = mapped_column(Float)
    uninsured_rate: Mapped[Optional[float]] = mapped_column(Float)

    # Rural classification
    rural_status: Mapped[RuralStatus] = mapped_column(
        SQLEnum(RuralStatus), default=RuralStatus.UNKNOWN
    )
    urban_influence_code: Mapped[Optional[int]] = mapped_column(Integer)
    rural_urban_code: Mapped[Optional[int]] = mapped_column(Integer)

    # Healthcare access metrics (cached)
    primary_care_shortage: Mapped[bool] = mapped_column(Boolean, default=False)
    dental_shortage: Mapped[bool] = mapped_column(Boolean, default=False)
    mental_health_shortage: Mapped[bool] = mapped_column(Boolean, default=False)

    primary_care_providers: Mapped[int] = mapped_column(Integer, default=0)
    dentists: Mapped[int] = mapped_column(Integer, default=0)
    mental_health_providers: Mapped[int] = mapped_column(Integer, default=0)
    hospitals: Mapped[int] = mapped_column(Integer, default=0)

    # Provider ratios (per 10,000 population)
    primary_care_ratio: Mapped[Optional[float]] = mapped_column(Float)
    dentist_ratio: Mapped[Optional[float]] = mapped_column(Float)
    mental_health_ratio: Mapped[Optional[float]] = mapped_column(Float)

    # Access scores (our computed metrics, 0-100)
    access_score: Mapped[Optional[float]] = mapped_column(Float, index=True)
    access_score_components: Mapped[Optional[str]] = mapped_column(Text)  # JSON breakdown

    # Nearest facility distances (miles)
    nearest_hospital_miles: Mapped[Optional[float]] = mapped_column(Float)
    nearest_fqhc_miles: Mapped[Optional[float]] = mapped_column(Float)

    # Telehealth infrastructure
    broadband_coverage: Mapped[Optional[float]] = mapped_column(Float)  # Percentage with broadband

    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    providers: Mapped[List["Provider"]] = relationship(
        "Provider", back_populates="county", lazy="dynamic"
    )

    __table_args__ = (
        Index("ix_counties_state_name", "state", "name"),
        Index("ix_counties_access", "access_score"),
    )

    def __repr__(self) -> str:
        return f"<County(fips={self.fips}, name={self.name}, state={self.state})>"

    @property
    def is_healthcare_desert(self) -> bool:
        """Check if county qualifies as a healthcare desert."""
        return (
            self.primary_care_shortage and
            (self.nearest_hospital_miles is None or self.nearest_hospital_miles > 30)
        )


class Provider(Base):
    """Individual healthcare providers and facilities."""

    __tablename__ = "providers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Identifiers
    npi: Mapped[Optional[str]] = mapped_column(String(10), unique=True, index=True)
    cms_id: Mapped[Optional[str]] = mapped_column(String(20), index=True)

    # Provider info
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    provider_type: Mapped[ProviderType] = mapped_column(
        SQLEnum(ProviderType), nullable=False, index=True
    )
    specialty: Mapped[Optional[str]] = mapped_column(String(200))
    sub_specialty: Mapped[Optional[str]] = mapped_column(String(200))

    # For facilities
    is_facility: Mapped[bool] = mapped_column(Boolean, default=False)
    facility_type: Mapped[Optional[str]] = mapped_column(String(100))
    bed_count: Mapped[Optional[int]] = mapped_column(Integer)

    # Location
    county_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("counties.id"), index=True
    )
    address: Mapped[Optional[str]] = mapped_column(Text)
    city: Mapped[Optional[str]] = mapped_column(String(100))
    state: Mapped[str] = mapped_column(String(2), nullable=False, index=True)
    zip_code: Mapped[Optional[str]] = mapped_column(String(10), index=True)
    latitude: Mapped[Optional[float]] = mapped_column(Float)
    longitude: Mapped[Optional[float]] = mapped_column(Float)

    # Practice info
    accepting_new_patients: Mapped[Optional[bool]] = mapped_column(Boolean)
    accepts_medicare: Mapped[Optional[bool]] = mapped_column(Boolean)
    accepts_medicaid: Mapped[Optional[bool]] = mapped_column(Boolean)
    telehealth_available: Mapped[bool] = mapped_column(Boolean, default=False)

    # Contact
    phone: Mapped[Optional[str]] = mapped_column(String(20))
    website: Mapped[Optional[str]] = mapped_column(Text)

    # Metadata
    source: Mapped[str] = mapped_column(String(50), default="CMS")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    county: Mapped[Optional["County"]] = relationship("County", back_populates="providers")

    __table_args__ = (
        Index("ix_providers_type_state", "provider_type", "state"),
        Index("ix_providers_location", "latitude", "longitude"),
        Index("ix_providers_zip", "zip_code"),
    )

    def __repr__(self) -> str:
        return f"<Provider(npi={self.npi}, name={self.name})>"


class AccessMetric(Base):
    """Time-series access metrics for tracking MAHA progress."""

    __tablename__ = "access_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Time period
    year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    month: Mapped[Optional[int]] = mapped_column(Integer)
    quarter: Mapped[Optional[int]] = mapped_column(Integer)

    # Geographic scope
    scope_type: Mapped[str] = mapped_column(String(20), nullable=False)  # national, state, county
    scope_value: Mapped[Optional[str]] = mapped_column(String(100), index=True)  # state code or FIPS

    # Shortage metrics
    hpsa_count: Mapped[int] = mapped_column(Integer, default=0)
    population_in_hpsa: Mapped[int] = mapped_column(Integer, default=0)
    pct_population_in_hpsa: Mapped[Optional[float]] = mapped_column(Float)

    # Provider metrics
    provider_count: Mapped[int] = mapped_column(Integer, default=0)
    provider_ratio: Mapped[Optional[float]] = mapped_column(Float)  # per 10k population

    # Access metrics
    avg_distance_to_care: Mapped[Optional[float]] = mapped_column(Float)  # miles
    pct_within_30min: Mapped[Optional[float]] = mapped_column(Float)
    pct_with_broadband: Mapped[Optional[float]] = mapped_column(Float)

    # Composite score
    access_equity_score: Mapped[Optional[float]] = mapped_column(Float)  # 0-100

    # Metadata
    calculated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_access_metrics_time", "year", "month"),
        Index("ix_access_metrics_scope", "scope_type", "scope_value"),
    )

    def __repr__(self) -> str:
        return f"<AccessMetric(year={self.year}, scope={self.scope_type}:{self.scope_value})>"
