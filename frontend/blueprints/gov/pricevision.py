"""
Government PriceVision Routes
Hospital price transparency with analytics
"""
from flask import render_template, request
from . import gov_bp, gov_required


@gov_bp.route('/pricevision/')
@gov_required
def pricevision_home():
    """PriceVision module home"""
    return render_template('gov/pricevision/home.html')


@gov_bp.route('/pricevision/search')
@gov_required
def pricevision_search():
    """Search for procedures"""
    query = request.args.get('q', '')
    return render_template('gov/pricevision/search.html', query=query)


@gov_bp.route('/pricevision/compare')
@gov_required
def pricevision_compare():
    """Compare prices across hospitals"""
    procedure = request.args.get('procedure', '')
    return render_template('gov/pricevision/compare.html', procedure=procedure)


@gov_bp.route('/pricevision/hospital/<npi>')
@gov_required
def pricevision_hospital(npi):
    """View single hospital details"""
    return render_template('gov/pricevision/hospital.html', npi=npi)


@gov_bp.route('/pricevision/analytics')
@gov_required
def pricevision_analytics():
    """Hospital compliance analytics (gov-only)"""
    return render_template('gov/pricevision/analytics.html')
