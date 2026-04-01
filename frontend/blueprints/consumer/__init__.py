"""
Public Portal Blueprint
Access to: PriceVision, DrugWatch, FoodScore
No authentication required
"""
from flask import Blueprint, render_template

public_bp = Blueprint('public', __name__, url_prefix='/public')

# Public modules configuration
PUBLIC_MODULES = {
    'pricevision': {
        'name': 'PriceVision',
        'description': 'Compare hospital procedure prices across facilities',
        'icon': 'bi-currency-dollar',
        'color': '#fd7e14',
    },
    'drugwatch': {
        'name': 'DrugWatch',
        'description': 'Compare drug prices: US vs international markets',
        'icon': 'bi-capsule',
        'color': '#dc3545',
    },
    'foodscore': {
        'name': 'FoodScore',
        'description': 'Check health scores for food products',
        'icon': 'bi-basket',
        'color': '#28a745',
    },
}


@public_bp.route('/')
def home():
    """Public portal home page"""
    return render_template('consumer/home.html', modules=PUBLIC_MODULES)


# Import module routes
from . import pricevision, drugwatch, foodscore
