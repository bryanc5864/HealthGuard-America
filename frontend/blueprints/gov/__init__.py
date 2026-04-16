"""
Government Portal Blueprint
Access to: All 5 modules (PriceVision, DrugWatch, FoodScore, RuralAccess, ChronicCare)
Authentication required (unless DEV_MODE is set)
"""
import os
from functools import wraps
from flask import Blueprint, render_template, session, redirect, url_for, request, flash
from config import Config

gov_bp = Blueprint('gov', __name__, url_prefix='/gov')

_DEV_MODE = os.environ.get('DEV_MODE', '').lower() in ('1', 'true', 'yes')


def gov_required(f):
    """Decorator to require government authentication (bypassed in DEV_MODE)"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if _DEV_MODE:
            return f(*args, **kwargs)
        if not session.get('is_gov_user'):
            flash('Please log in to access the Government Portal.', 'warning')
            return redirect(url_for('gov.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


@gov_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Government portal login"""
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')

        if username in Config.GOV_USERS and Config.GOV_USERS[username] == password:
            session['is_gov_user'] = True
            session['gov_username'] = username
            flash('Welcome to the Government Portal.', 'success')
            next_url = request.args.get('next', url_for('gov.home'))
            return redirect(next_url)
        else:
            flash('Invalid credentials.', 'danger')

    return render_template('gov/login.html')


@gov_bp.route('/logout')
def logout():
    """Logout from government portal"""
    session.pop('is_gov_user', None)
    session.pop('gov_username', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('landing'))


@gov_bp.route('/')
@gov_required
def home():
    """Government portal home page"""
    modules = {k: v for k, v in Config.MODULES.items() if v['gov']}
    return render_template('gov/home.html', modules=modules)


# Import module routes
from . import pricevision, drugwatch, foodscore, ruralaccess, chroniccare
