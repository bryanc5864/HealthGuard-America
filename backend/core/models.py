"""
HealthGuard America - Shared/Common Models
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from sqlalchemy import (
    String, Integer, Float, DateTime, Text, Boolean,
    Index, Numeric, Enum as SQLEnum
)
from sqlalchemy.orm import Mapped, mapped_column
import enum

from core.database import Base


class IndexStatus(str, enum.Enum):
    """Status of an index calculation."""
    CALCULATING = "calculating"
    COMPLETE = "complete"
    FAILED = "failed"
    STALE = "stale"


class MAHAIndex(Base):
    """
    MAHA (Make America Healthy Again) Index - composite health metric.

    The index combines four component scores:
    - Price Transparency (20%): Hospital price compliance
    - Drug Affordability (25%): US vs international drug prices
    - Food Supply Health (30%): Average MAHA score of food products
    - Access Equity (25%): Population within 30 min of primary care
    """

    __tablename__ = "maha_index"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Time period
    date: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    month: Mapped[int] = mapped_column(Integer, nullable=False)

    # Geographic scope
    scope: Mapped[str] = mapped_column(String(20), default="national")  # national, state
    state: Mapped[Optional[str]] = mapped_column(String(2), index=True)

    # Composite score (0-100)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    previous_score: Mapped[Optional[float]] = mapped_column(Float)
    score_change: Mapped[Optional[float]] = mapped_column(Float)
    trend: Mapped[Optional[str]] = mapped_column(String(20))  # improving, declining, stable

    # Component scores (each 0-100)
    price_transparency_score: Mapped[float] = mapped_column(Float, nullable=False)
    drug_affordability_score: Mapped[float] = mapped_column(Float, nullable=False)
    food_supply_score: Mapped[float] = mapped_column(Float, nullable=False)
    access_equity_score: Mapped[float] = mapped_column(Float, nullable=False)

    # Component weights (should sum to 1.0)
    price_transparency_weight: Mapped[float] = mapped_column(Float, default=0.20)
    drug_affordability_weight: Mapped[float] = mapped_column(Float, default=0.25)
    food_supply_weight: Mapped[float] = mapped_column(Float, default=0.30)
    access_equity_weight: Mapped[float] = mapped_column(Float, default=0.25)

    # Raw metrics behind scores
    hospital_compliance_pct: Mapped[Optional[float]] = mapped_column(Float)
    drug_price_ratio: Mapped[Optional[float]] = mapped_column(Float)  # US / avg international
    avg_product_maha_score: Mapped[Optional[float]] = mapped_column(Float)
    population_with_access_pct: Mapped[Optional[float]] = mapped_column(Float)

    # Data quality indicators
    status: Mapped[IndexStatus] = mapped_column(SQLEnum(IndexStatus), default=IndexStatus.COMPLETE)
    data_coverage: Mapped[Optional[float]] = mapped_column(Float)  # % of expected data available
    confidence: Mapped[Optional[float]] = mapped_column(Float)  # 0-1 confidence in calculation

    # Metadata
    calculated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    calculation_notes: Mapped[Optional[str]] = mapped_column(Text)

    __table_args__ = (
        Index("ix_maha_index_date_scope", "date", "scope"),
        Index("ix_maha_index_year_month", "year", "month"),
        Index("ix_maha_index_state", "state"),
    )

    def __repr__(self) -> str:
        return f"<MAHAIndex(date={self.date}, scope={self.scope}, score={self.score:.1f})>"

    @property
    def grade(self) -> str:
        """Return letter grade based on score."""
        if self.score >= 90:
            return "A"
        if self.score >= 80:
            return "B"
        if self.score >= 70:
            return "C"
        if self.score >= 60:
            return "D"
        return "F"

    @property
    def interpretation(self) -> str:
        """Return human-readable interpretation of score."""
        if self.score >= 90:
            return "Excellent"
        if self.score >= 75:
            return "Good"
        if self.score >= 50:
            return "Fair"
        if self.score >= 25:
            return "Poor"
        return "Critical"


class DataIngestionLog(Base):
    """Track data ingestion jobs for monitoring and debugging."""

    __tablename__ = "data_ingestion_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Job identification
    job_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    job_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # pricevision, drugwatch, etc.
    source: Mapped[str] = mapped_column(String(200), nullable=False)

    # Timing
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float)

    # Status
    status: Mapped[str] = mapped_column(String(20), default="running", index=True)  # running, success, failed
    error_message: Mapped[Optional[str]] = mapped_column(Text)

    # Metrics
    records_processed: Mapped[int] = mapped_column(Integer, default=0)
    records_inserted: Mapped[int] = mapped_column(Integer, default=0)
    records_updated: Mapped[int] = mapped_column(Integer, default=0)
    records_failed: Mapped[int] = mapped_column(Integer, default=0)

    # File info (if applicable)
    file_path: Mapped[Optional[str]] = mapped_column(Text)
    file_size_bytes: Mapped[Optional[int]] = mapped_column(Integer)
    file_format: Mapped[Optional[str]] = mapped_column(String(20))

    __table_args__ = (
        Index("ix_ingestion_type_status", "job_type", "status"),
        Index("ix_ingestion_started", "started_at"),
    )

    def __repr__(self) -> str:
        return f"<DataIngestionLog(job_id={self.job_id}, status={self.status})>"


class SystemMetric(Base):
    """System-level metrics for monitoring."""

    __tablename__ = "system_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Metric identification
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    module: Mapped[Optional[str]] = mapped_column(String(50), index=True)  # pricevision, drugwatch, etc.

    # Value
    value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[Optional[str]] = mapped_column(String(50))

    # Context
    dimension: Mapped[Optional[str]] = mapped_column(String(100))  # Additional grouping
    tags: Mapped[Optional[str]] = mapped_column(Text)  # JSON tags for filtering

    # Time
    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    __table_args__ = (
        Index("ix_system_metrics_name_time", "name", "recorded_at"),
        Index("ix_system_metrics_module", "module", "recorded_at"),
    )

    def __repr__(self) -> str:
        return f"<SystemMetric(name={self.name}, value={self.value})>"


class APIKey(Base):
    """API keys for external access."""

    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Key info
    key_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)

    # Owner
    owner_email: Mapped[str] = mapped_column(String(255), nullable=False)
    organization: Mapped[Optional[str]] = mapped_column(String(200))

    # Permissions
    scopes: Mapped[str] = mapped_column(Text, default="read")  # Comma-separated scopes
    rate_limit: Mapped[int] = mapped_column(Integer, default=1000)  # Requests per hour
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Usage tracking
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    total_requests: Mapped[int] = mapped_column(Integer, default=0)

    # Lifecycle
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    __table_args__ = (
        Index("ix_api_keys_owner", "owner_email"),
    )

    def __repr__(self) -> str:
        return f"<APIKey(name={self.name}, owner={self.owner_email})>"
