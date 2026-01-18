"""
Public Portal Blueprint
Access to: PriceVision, DrugWatch, FoodScore
No authentication required
"""
from flask import Blueprint, render_template
from config import Config

public_bp = Blueprint('public', __name__, url_prefix='/public')


@public_bp.route('/')
def home():
    """Public portal home page"""
    modules = {k: v for k, v in Config.MODULES.items() if v['public']}
    return render_template('public/home.html', modules=modules)


# Import module routes
from . import pricevision, drugwatch, foodscore
