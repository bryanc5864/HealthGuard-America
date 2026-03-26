"""
HealthGuard Frontend Configuration
"""
import os
from pathlib import Path

class Config:
    """Base configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'healthguard-dev-key-change-in-production')
    BASE_DIR = Path(__file__).parent.parent
    DATA_DIR = BASE_DIR / 'data/raw'

    # Portal settings
    PORTAL_PUBLIC_NAME = "HealthGuard Public"
    PORTAL_GOV_NAME = "HealthGuard Government"

    # Module definitions
    MODULES = {
        'pricevision': {
            'name': 'PriceVision',
            'description': 'Compare hospital procedure prices across facilities',
            'icon': 'bi-currency-dollar',
            'color': '#fd7e14',
            'public': True,
            'gov': True
        },
        'drugwatch': {
            'name': 'DrugWatch',
            'description': 'Compare drug prices: US vs international markets',
            'icon': 'bi-capsule',
            'color': '#dc3545',
            'public': True,
            'gov': True
        },
        'foodscore': {
            'name': 'FoodScore',
            'description': 'Check health scores for food products',
            'icon': 'bi-basket',
            'color': '#28a745',
            'public': True,
            'gov': True
        },
        'ruralaccess': {
            'name': 'RuralAccess',
            'description': 'Map healthcare deserts and provider shortages',
            'icon': 'bi-geo-alt',
            'color': '#6f42c1',
            'public': False,
            'gov': True
        },
        'chroniccare': {
            'name': 'ChronicCare',
            'description': 'Chronic disease risk and intervention planning',
            'icon': 'bi-activity',
            'color': '#0dcaf0',
            'public': False,
            'gov': True
        }
    }

    # Government users (simple auth for MVP)
    GOV_USERS = {
        'admin': 'healthguard2026',
        'analyst': 'maha2026'
    }


class DevelopmentConfig(Config):
    DEBUG = True
    TEMPLATES_AUTO_RELOAD = True  # Only in dev
    SEND_FILE_MAX_AGE_DEFAULT = 3600  # Cache static files 1hr


class ProductionConfig(Config):
    DEBUG = False
    SECRET_KEY = os.environ.get('SECRET_KEY')  # Must be set in production
    TEMPLATES_AUTO_RELOAD = False
    SEND_FILE_MAX_AGE_DEFAULT = 3600  # Cache static files 1hr
