"""
HealthGuard America - All Models

This module imports all models from all modules to ensure they are registered
with SQLAlchemy's Base.metadata for Alembic migrations.

Import this module before running migrations or creating tables.
"""

# Core/Shared models
from core.models import (
    MAHAIndex,
    DataIngestionLog,
    SystemMetric,
    APIKey,
)

# PriceVision models
from pricevision.models import (
    Hospital,
    Procedure,
    HospitalPrice,
)

# DrugWatch models
from drugwatch.models import (
    Drug,
    DrugPriceUS,
    DrugPriceInternational,
    DrugComparison,
)

# FoodScore models
from foodscore.models import (
    FoodProduct,
    Additive,
    ProductAdditive,
    FoodCategory,
)

# RuralAccess models
from ruralaccess.models import (
    HPSA,
    County,
    Provider,
    AccessMetric,
)

# Re-export all models
__all__ = [
    # Core
    "MAHAIndex",
    "DataIngestionLog",
    "SystemMetric",
    "APIKey",
    # PriceVision
    "Hospital",
    "Procedure",
    "HospitalPrice",
    # DrugWatch
    "Drug",
    "DrugPriceUS",
    "DrugPriceInternational",
    "DrugComparison",
    # FoodScore
    "FoodProduct",
    "Additive",
    "ProductAdditive",
    "FoodCategory",
    # RuralAccess
    "HPSA",
    "County",
    "Provider",
    "AccessMetric",
]
