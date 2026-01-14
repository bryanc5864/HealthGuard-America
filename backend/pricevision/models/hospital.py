"""
PriceVision - Hospital and Price Models
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


class CodeType(str, enum.Enum):
    """Billing code types."""
    CPT = "CPT"
    HCPCS = "HCPCS"
    DRG = "DRG"
    APR_DRG = "APR-DRG"
    MS_DRG = "MS-DRG"
    REVENUE = "REVENUE"
    CDM = "CDM"
    NDC = "NDC"
    ICD10 = "ICD10"
    OTHER = "OTHER"


class CareSetting(str, enum.Enum):
    """Care setting for price."""
    INPATIENT = "inpatient"
    OUTPATIENT = "outpatient"
    BOTH = "both"
    UNSPECIFIED = "unspecified"


class Hospital(Base):
    """Hospital information from CMS and MRF data."""

    __tablename__ = "hospitals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    npi: Mapped[str] = mapped_column(String(10), unique=True, nullable=False, index=True)

    # Basic info
    name: Mapped[Optional[str]] = mapped_column(String(500))
    facility_type: Mapped[Optional[str]] = mapped_column(String(100))
    ownership_type: Mapped[Optional[str]] = mapped_column(String(100))

    # Location
    address: Mapped[Optional[str]] = mapped_column(String(500))
    city: Mapped[Optional[str]] = mapped_column(String(100))
    state: Mapped[Optional[str]] = mapped_column(String(2), index=True)
    zip_code: Mapped[Optional[str]] = mapped_column(String(10))
    county: Mapped[Optional[str]] = mapped_column(String(100))
    latitude: Mapped[Optional[float]] = mapped_column(Float)
    longitude: Mapped[Optional[float]] = mapped_column(Float)

    # Contact
    phone: Mapped[Optional[str]] = mapped_column(String(20))
    website: Mapped[Optional[str]] = mapped_column(String(500))

    # Transparency compliance
    has_mrf: Mapped[bool] = mapped_column(Boolean, default=False)
    mrf_url: Mapped[Optional[str]] = mapped_column(Text)
    mrf_format: Mapped[Optional[str]] = mapped_column(String(20))
    mrf_last_updated: Mapped[Optional[datetime]] = mapped_column(DateTime)
    is_compliant: Mapped[bool] = mapped_column(Boolean, default=False)

    # Statistics (cached for performance)
    total_procedures: Mapped[int] = mapped_column(Integer, default=0)
    avg_gross_charge: Mapped[Optional[float]] = mapped_column(Float)
    avg_cash_price: Mapped[Optional[float]] = mapped_column(Float)

    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    prices: Mapped[List["HospitalPrice"]] = relationship(
        "HospitalPrice", back_populates="hospital", lazy="dynamic"
    )

    __table_args__ = (
        Index("ix_hospitals_state_city", "state", "city"),
        Index("ix_hospitals_location", "latitude", "longitude"),
    )

    def __repr__(self) -> str:
        return f"<Hospital(npi={self.npi}, name={self.name})>"


class Procedure(Base):
    """Canonical procedure codes (CPT/HCPCS)."""

    __tablename__ = "procedures"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    code_type: Mapped[CodeType] = mapped_column(SQLEnum(CodeType), nullable=False)

    # Description
    description: Mapped[str] = mapped_column(Text, nullable=False)
    short_description: Mapped[Optional[str]] = mapped_column(String(200))
    category: Mapped[Optional[str]] = mapped_column(String(100), index=True)
    subcategory: Mapped[Optional[str]] = mapped_column(String(100))

    # For ML matching
    embedding_vector: Mapped[Optional[bytes]] = mapped_column(Text)  # Stored as base64

    # Statistics across all hospitals
    national_median_price: Mapped[Optional[float]] = mapped_column(Float)
    national_min_price: Mapped[Optional[float]] = mapped_column(Float)
    national_max_price: Mapped[Optional[float]] = mapped_column(Float)
    hospital_count: Mapped[int] = mapped_column(Integer, default=0)

    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    prices: Mapped[List["HospitalPrice"]] = relationship(
        "HospitalPrice", back_populates="procedure", lazy="dynamic"
    )

    __table_args__ = (
        Index("ix_procedures_code_type", "code", "code_type", unique=True),
    )

    def __repr__(self) -> str:
        return f"<Procedure(code={self.code}, type={self.code_type})>"


class HospitalPrice(Base):
    """Price data for procedures at specific hospitals."""

    __tablename__ = "hospital_prices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Foreign keys
    hospital_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("hospitals.id", ondelete="CASCADE"), nullable=False, index=True
    )
    procedure_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("procedures.id", ondelete="SET NULL"), index=True
    )

    # Raw description (before matching to canonical procedure)
    raw_description: Mapped[str] = mapped_column(Text, nullable=False)
    raw_code: Mapped[Optional[str]] = mapped_column(String(50))
    raw_code_type: Mapped[Optional[str]] = mapped_column(String(50))
    revenue_code: Mapped[Optional[str]] = mapped_column(String(10))

    # Price fields (using Numeric for precision)
    gross_charge: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 2))
    cash_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 2))
    min_negotiated: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 2))
    max_negotiated: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 2))

    # Insurance-specific pricing
    payer_name: Mapped[Optional[str]] = mapped_column(String(200), index=True)
    plan_name: Mapped[Optional[str]] = mapped_column(String(200))
    negotiated_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 2))

    # Setting
    setting: Mapped[CareSetting] = mapped_column(
        SQLEnum(CareSetting), default=CareSetting.UNSPECIFIED
    )

    # ML matching confidence
    match_confidence: Mapped[Optional[float]] = mapped_column(Float)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)

    # Source tracking
    source_file: Mapped[Optional[str]] = mapped_column(String(255))
    source_row: Mapped[Optional[int]] = mapped_column(Integer)

    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    hospital: Mapped["Hospital"] = relationship("Hospital", back_populates="prices")
    procedure: Mapped[Optional["Procedure"]] = relationship("Procedure", back_populates="prices")

    __table_args__ = (
        Index("ix_hospital_prices_hospital_procedure", "hospital_id", "procedure_id"),
        Index("ix_hospital_prices_payer", "payer_name"),
        Index("ix_hospital_prices_setting", "setting"),
    )

    def __repr__(self) -> str:
        return f"<HospitalPrice(hospital_id={self.hospital_id}, desc={self.raw_description[:50]})>"

    @property
    def best_price(self) -> Optional[Decimal]:
        """Return the best available price (prefer cash, then min negotiated)."""
        if self.cash_price:
            return self.cash_price
        if self.min_negotiated:
            return self.min_negotiated
        return self.gross_charge

    @property
    def price_ratio(self) -> Optional[float]:
        """Calculate ratio of gross charge to cash price."""
        if self.gross_charge and self.cash_price and self.cash_price > 0:
            return float(self.gross_charge / self.cash_price)
        return None
