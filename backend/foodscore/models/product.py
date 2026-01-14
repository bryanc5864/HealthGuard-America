"""
FoodScore - Food Product and Additive Models
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


class NovaGroup(int, enum.Enum):
    """NOVA food processing classification."""
    UNPROCESSED = 1  # Unprocessed or minimally processed foods
    CULINARY = 2     # Processed culinary ingredients
    PROCESSED = 3    # Processed foods
    ULTRA_PROCESSED = 4  # Ultra-processed foods


class NutriScore(str, enum.Enum):
    """Nutri-Score grades."""
    A = "a"
    B = "b"
    C = "c"
    D = "d"
    E = "e"


class AdditiveType(str, enum.Enum):
    """Classification of food additives."""
    PRESERVATIVE = "preservative"
    COLORANT = "colorant"
    SWEETENER = "sweetener"
    EMULSIFIER = "emulsifier"
    FLAVOR = "flavor"
    STABILIZER = "stabilizer"
    THICKENER = "thickener"
    ANTIOXIDANT = "antioxidant"
    ACIDITY_REGULATOR = "acidity_regulator"
    OTHER = "other"


class RegulatoryStatus(str, enum.Enum):
    """Regulatory approval status."""
    APPROVED = "approved"
    RESTRICTED = "restricted"
    BANNED = "banned"
    PENDING = "pending"


class FoodProduct(Base):
    """Food product information from OpenFoodFacts and other sources."""

    __tablename__ = "food_products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Identifiers
    barcode: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    off_id: Mapped[Optional[str]] = mapped_column(String(50))  # OpenFoodFacts ID

    # Product info
    product_name: Mapped[Optional[str]] = mapped_column(String(500), index=True)
    brand: Mapped[Optional[str]] = mapped_column(String(200), index=True)
    manufacturer: Mapped[Optional[str]] = mapped_column(String(300))
    categories: Mapped[Optional[str]] = mapped_column(Text)  # Comma-separated
    primary_category: Mapped[Optional[str]] = mapped_column(String(200), index=True)

    # Ingredients
    ingredients_text: Mapped[Optional[str]] = mapped_column(Text)
    ingredients_count: Mapped[Optional[int]] = mapped_column(Integer)
    allergens: Mapped[Optional[str]] = mapped_column(Text)

    # NOVA Classification
    nova_group: Mapped[Optional[NovaGroup]] = mapped_column(SQLEnum(NovaGroup), index=True)
    nova_confidence: Mapped[Optional[float]] = mapped_column(Float)  # ML model confidence
    nova_predicted: Mapped[bool] = mapped_column(Boolean, default=False)  # True if ML-predicted

    # Nutri-Score
    nutriscore_grade: Mapped[Optional[NutriScore]] = mapped_column(SQLEnum(NutriScore), index=True)
    nutriscore_score: Mapped[Optional[int]] = mapped_column(Integer)

    # Nutritional values (per 100g)
    energy_kcal: Mapped[Optional[float]] = mapped_column(Float)
    fat: Mapped[Optional[float]] = mapped_column(Float)
    saturated_fat: Mapped[Optional[float]] = mapped_column(Float)
    carbohydrates: Mapped[Optional[float]] = mapped_column(Float)
    sugars: Mapped[Optional[float]] = mapped_column(Float)
    fiber: Mapped[Optional[float]] = mapped_column(Float)
    proteins: Mapped[Optional[float]] = mapped_column(Float)
    sodium: Mapped[Optional[float]] = mapped_column(Float)  # in grams
    salt: Mapped[Optional[float]] = mapped_column(Float)

    # MAHA Score (our custom health score)
    maha_score: Mapped[Optional[float]] = mapped_column(Float, index=True)  # 0-100, higher = healthier
    maha_score_components: Mapped[Optional[str]] = mapped_column(Text)  # JSON breakdown

    # Additive summary
    additives_count: Mapped[int] = mapped_column(Integer, default=0)
    flagged_additives_count: Mapped[int] = mapped_column(Integer, default=0)
    has_artificial_colors: Mapped[bool] = mapped_column(Boolean, default=False)
    has_artificial_sweeteners: Mapped[bool] = mapped_column(Boolean, default=False)

    # SNAP eligibility analysis
    snap_eligible: Mapped[Optional[bool]] = mapped_column(Boolean)
    snap_restriction_reason: Mapped[Optional[str]] = mapped_column(String(200))

    # Source tracking
    source: Mapped[str] = mapped_column(String(50), default="openfoodfacts")
    countries: Mapped[Optional[str]] = mapped_column(String(200))  # Comma-separated country codes
    image_url: Mapped[Optional[str]] = mapped_column(Text)

    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    product_additives: Mapped[List["ProductAdditive"]] = relationship(
        "ProductAdditive", back_populates="product", lazy="dynamic",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_food_products_brand_name", "brand", "product_name"),
        Index("ix_food_products_nova_maha", "nova_group", "maha_score"),
        Index("ix_food_products_category", "primary_category"),
    )

    def __repr__(self) -> str:
        return f"<FoodProduct(barcode={self.barcode}, name={self.product_name})>"

    @property
    def health_category(self) -> str:
        """Categorize product health based on MAHA score."""
        if self.maha_score is None:
            return "unknown"
        if self.maha_score >= 90:
            return "excellent"
        if self.maha_score >= 75:
            return "good"
        if self.maha_score >= 50:
            return "moderate"
        if self.maha_score >= 25:
            return "poor"
        return "very_poor"


class Additive(Base):
    """Food additive database with risk information."""

    __tablename__ = "additives"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Identifiers
    e_number: Mapped[Optional[str]] = mapped_column(String(10), unique=True, index=True)  # E100, etc.
    cas_number: Mapped[Optional[str]] = mapped_column(String(20))  # Chemical Abstracts Service number

    # Names
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    common_names: Mapped[Optional[str]] = mapped_column(Text)  # Pipe-separated aliases
    chemical_name: Mapped[Optional[str]] = mapped_column(String(500))

    # Classification
    additive_type: Mapped[AdditiveType] = mapped_column(
        SQLEnum(AdditiveType), nullable=False, index=True
    )
    is_artificial: Mapped[bool] = mapped_column(Boolean, default=False)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=False)

    # Regulatory status
    fda_status: Mapped[RegulatoryStatus] = mapped_column(
        SQLEnum(RegulatoryStatus), default=RegulatoryStatus.APPROVED
    )
    eu_status: Mapped[RegulatoryStatus] = mapped_column(
        SQLEnum(RegulatoryStatus), default=RegulatoryStatus.APPROVED
    )
    who_adi: Mapped[Optional[float]] = mapped_column(Float)  # Acceptable Daily Intake (mg/kg body weight)

    # Risk assessment
    risk_score: Mapped[int] = mapped_column(Integer, default=0)  # 0-100, higher = more concerning
    risk_category: Mapped[Optional[str]] = mapped_column(String(50))  # low, medium, high
    health_concerns: Mapped[Optional[str]] = mapped_column(Text)  # Pipe-separated concerns
    evidence_level: Mapped[Optional[str]] = mapped_column(String(50))  # strong, moderate, weak

    # Source references
    cspi_rating: Mapped[Optional[str]] = mapped_column(String(50))  # Center for Science in Public Interest
    efsa_assessment: Mapped[Optional[str]] = mapped_column(Text)
    study_count: Mapped[Optional[int]] = mapped_column(Integer)

    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    product_additives: Mapped[List["ProductAdditive"]] = relationship(
        "ProductAdditive", back_populates="additive", lazy="dynamic"
    )

    __table_args__ = (
        Index("ix_additives_type_risk", "additive_type", "risk_score"),
    )

    def __repr__(self) -> str:
        return f"<Additive(name={self.name}, risk={self.risk_score})>"

    @property
    def is_high_risk(self) -> bool:
        """Check if additive is high risk (score > 70)."""
        return self.risk_score > 70


class ProductAdditive(Base):
    """Association between products and their additives."""

    __tablename__ = "product_additives"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    product_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("food_products.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    additive_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("additives.id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    # Detection info
    detected_name: Mapped[str] = mapped_column(String(200), nullable=False)  # As found in ingredients
    position_in_list: Mapped[Optional[int]] = mapped_column(Integer)  # Order in ingredient list
    match_confidence: Mapped[float] = mapped_column(Float, default=1.0)  # For fuzzy matches

    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    product: Mapped["FoodProduct"] = relationship("FoodProduct", back_populates="product_additives")
    additive: Mapped["Additive"] = relationship("Additive", back_populates="product_additives")

    __table_args__ = (
        Index("ix_product_additives_product_additive", "product_id", "additive_id", unique=True),
    )

    def __repr__(self) -> str:
        return f"<ProductAdditive(product_id={self.product_id}, additive_id={self.additive_id})>"


class FoodCategory(Base):
    """Food category taxonomy for navigation and filtering."""

    __tablename__ = "food_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), unique=True, nullable=False, index=True)

    # Hierarchy
    parent_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("food_categories.id"), index=True
    )
    level: Mapped[int] = mapped_column(Integer, default=0)  # 0 = root

    # Category stats (cached)
    product_count: Mapped[int] = mapped_column(Integer, default=0)
    avg_maha_score: Mapped[Optional[float]] = mapped_column(Float)
    avg_nova_group: Mapped[Optional[float]] = mapped_column(Float)

    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self) -> str:
        return f"<FoodCategory(name={self.name})>"
