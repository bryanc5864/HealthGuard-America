"""
DrugWatch - Drug Pricing Models
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


class Country(str, enum.Enum):
    """Supported countries for drug pricing."""
    US = "US"
    CANADA = "Canada"
    AUSTRALIA = "Australia"
    UK = "UK"
    GERMANY = "Germany"
    FRANCE = "France"
    JAPAN = "Japan"


class DrugType(str, enum.Enum):
    """Drug classification."""
    BRAND = "brand"
    GENERIC = "generic"
    BIOSIMILAR = "biosimilar"
    OTC = "otc"


class Drug(Base):
    """Master drug record with canonical information."""

    __tablename__ = "drugs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Identifiers
    ndc: Mapped[Optional[str]] = mapped_column(String(20), index=True)  # National Drug Code (US)
    rxcui: Mapped[Optional[str]] = mapped_column(String(20), index=True)  # RxNorm Concept ID
    atc_code: Mapped[Optional[str]] = mapped_column(String(10), index=True)  # WHO ATC code

    # Names
    generic_name: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    brand_name: Mapped[Optional[str]] = mapped_column(String(500), index=True)
    manufacturer: Mapped[Optional[str]] = mapped_column(String(300))

    # Classification
    drug_type: Mapped[Optional[DrugType]] = mapped_column(SQLEnum(DrugType))
    therapeutic_class: Mapped[Optional[str]] = mapped_column(String(200))
    pharmacologic_class: Mapped[Optional[str]] = mapped_column(String(200))

    # Formulation
    dosage_form: Mapped[Optional[str]] = mapped_column(String(100))  # tablet, injection, etc.
    strength: Mapped[Optional[str]] = mapped_column(String(100))
    route: Mapped[Optional[str]] = mapped_column(String(50))  # oral, IV, etc.
    package_size: Mapped[Optional[str]] = mapped_column(String(100))

    # Regulatory
    fda_approval_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    is_controlled: Mapped[bool] = mapped_column(Boolean, default=False)
    schedule: Mapped[Optional[str]] = mapped_column(String(10))  # II, III, IV, V

    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    us_prices: Mapped[List["DrugPriceUS"]] = relationship(
        "DrugPriceUS", back_populates="drug", lazy="dynamic"
    )
    international_prices: Mapped[List["DrugPriceInternational"]] = relationship(
        "DrugPriceInternational", back_populates="drug", lazy="dynamic"
    )

    __table_args__ = (
        Index("ix_drugs_generic_brand", "generic_name", "brand_name"),
        Index("ix_drugs_manufacturer", "manufacturer"),
    )

    def __repr__(self) -> str:
        return f"<Drug(generic={self.generic_name}, brand={self.brand_name})>"


class DrugPriceUS(Base):
    """US drug pricing from Medicare Part D and other sources."""

    __tablename__ = "drug_prices_us"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    drug_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("drugs.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Price data (from Medicare Part D)
    year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    total_spending: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2))
    total_claims: Mapped[Optional[int]] = mapped_column(Integer)
    total_beneficiaries: Mapped[Optional[int]] = mapped_column(Integer)
    total_units: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2))

    # Per-unit pricing
    avg_price_per_unit: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 4))
    avg_price_per_claim: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 2))

    # Price changes
    price_change_yoy: Mapped[Optional[float]] = mapped_column(Float)  # Year-over-year % change

    # Source
    source: Mapped[str] = mapped_column(String(100), default="Medicare Part D")

    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    drug: Mapped["Drug"] = relationship("Drug", back_populates="us_prices")

    __table_args__ = (
        Index("ix_drug_prices_us_drug_year", "drug_id", "year", unique=True),
    )

    def __repr__(self) -> str:
        return f"<DrugPriceUS(drug_id={self.drug_id}, year={self.year})>"


class DrugPriceInternational(Base):
    """International drug pricing for comparison."""

    __tablename__ = "drug_prices_international"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    drug_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("drugs.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Country info
    country: Mapped[Country] = mapped_column(SQLEnum(Country), nullable=False, index=True)
    local_drug_code: Mapped[Optional[str]] = mapped_column(String(50))  # PBS code, DIN, etc.
    local_drug_name: Mapped[Optional[str]] = mapped_column(String(500))

    # Pricing
    price_local: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 4))
    currency: Mapped[str] = mapped_column(String(3), nullable=False)  # AUD, CAD, GBP, etc.
    exchange_rate: Mapped[float] = mapped_column(Float, nullable=False)  # To USD
    price_usd: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 4))
    price_per_unit_usd: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 4))

    # Pack info
    pack_size: Mapped[Optional[int]] = mapped_column(Integer)
    formulation: Mapped[Optional[str]] = mapped_column(String(200))

    # Reimbursement
    is_covered: Mapped[bool] = mapped_column(Boolean, default=True)
    reimbursement_rate: Mapped[Optional[float]] = mapped_column(Float)

    # Source
    source: Mapped[str] = mapped_column(String(100))
    source_date: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    drug: Mapped["Drug"] = relationship("Drug", back_populates="international_prices")

    __table_args__ = (
        Index("ix_drug_prices_intl_drug_country", "drug_id", "country"),
    )

    def __repr__(self) -> str:
        return f"<DrugPriceInternational(drug_id={self.drug_id}, country={self.country})>"


class DrugComparison(Base):
    """Pre-computed US vs international price comparisons."""

    __tablename__ = "drug_comparisons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    drug_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("drugs.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # US price reference
    us_price_per_unit: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    us_total_spending: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2))
    us_total_units: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2))

    # Best international price
    lowest_intl_price: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    lowest_intl_country: Mapped[Country] = mapped_column(SQLEnum(Country), nullable=False)

    # MFN (Most Favored Nation) calculations
    price_ratio: Mapped[float] = mapped_column(Float, nullable=False)  # US / lowest_intl
    potential_savings_per_unit: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    potential_savings_total: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2))

    # Comparison year
    year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    # Metadata
    calculated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_drug_comparisons_drug_year", "drug_id", "year", unique=True),
        Index("ix_drug_comparisons_ratio", "price_ratio"),
    )

    def __repr__(self) -> str:
        return f"<DrugComparison(drug_id={self.drug_id}, ratio={self.price_ratio:.2f}x)>"
