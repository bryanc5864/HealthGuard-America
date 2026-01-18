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

# Import services after VALID_US_STATES is defined
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
    'VALID_US_STATES'
]
