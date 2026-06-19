"""
HealthGuard Data Services
Load processed data files for frontend display
"""

# Valid US States (50) + DC + Territories (PR, GU, VI, AS, MP)
# MUST be defined before imports since services use this constant
VALID_US_STATES = {
    # 50 US States
    'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA',
    'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
    'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
    'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
    'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY',
    # District of Columbia
    'DC',
    # US Territories
    'PR',  # Puerto Rico
    'GU',  # Guam
    'VI',  # US Virgin Islands
    'AS',  # American Samoa
    'MP',  # Northern Mariana Islands
}

import pandas as pd


def clean_nan_records(records):
    """Replace NaN values with None in a list of dicts (JSON-safe)."""
    cleaned = []
    for record in records:
        clean_record = {}
        for key, value in record.items():
            clean_record[key] = None if pd.isna(value) else value
        cleaned.append(clean_record)
    return cleaned


def cache_set_bounded(cache, key, value, prefix, max_entries=256):
    """Store ``value`` under ``key`` in a dict ``cache``, evicting the oldest
    entry sharing ``prefix`` (FIFO) once ``max_entries`` such keys exist.

    Bounds memory growth for caches keyed by user input (e.g. procedure codes,
    drug names), which would otherwise grow without limit in a long-running
    process.
    """
    if key not in cache:
        prefixed = [k for k in cache if isinstance(k, str) and k.startswith(prefix)]
        if len(prefixed) >= max_entries:
            del cache[prefixed[0]]
    cache[key] = value
    return value


# Import services after VALID_US_STATES / clean_nan_records are defined
from .pricevision import PriceVisionService
from .drugwatch import DrugWatchService
from .foodscore import FoodScoreService
from .ruralaccess import RuralAccessService
from .chroniccare import ChronicCareService

__all__ = [
    'PriceVisionService',
    'DrugWatchService',
    'FoodScoreService',
    'RuralAccessService',
    'ChronicCareService',
    'VALID_US_STATES',
    'clean_nan_records',
    'cache_set_bounded',
]
