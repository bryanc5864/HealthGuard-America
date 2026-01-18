"""
Government ChronicCare Routes
Chronic disease management (gov-only module)
"""
from flask import render_template, request
from . import gov_bp, gov_required


@gov_bp.route('/chroniccare/')
@gov_required
def chroniccare_home():
    """ChronicCare module home"""
    return render_template('gov/chroniccare/home.html')


@gov_bp.route('/chroniccare/dashboard')
@gov_required
def chroniccare_dashboard():
    """MAHA metrics dashboard"""
    return render_template('gov/chroniccare/dashboard.html')


@gov_bp.route('/chroniccare/correlations')
@gov_required
def chroniccare_correlations():
    """Food-disease correlation analysis"""
    return render_template('gov/chroniccare/correlations.html')


@gov_bp.route('/chroniccare/interventions')
@gov_required
def chroniccare_interventions():
    """ML-prioritized intervention targets"""
    return render_template('gov/chroniccare/interventions.html')


@gov_bp.route('/chroniccare/county/<fips>')
@gov_required
def chroniccare_county(fips):
    """County chronic disease profile"""
    return render_template('gov/chroniccare/county.html', fips=fips)
