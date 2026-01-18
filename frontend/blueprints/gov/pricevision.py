"""
Government PriceVision Routes
Hospital price transparency with analytics
"""
from flask import render_template, request, jsonify
from . import gov_bp, gov_required
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from services.pricevision import PriceVisionService


@gov_bp.route('/pricevision/')
@gov_required
def pricevision_home():
    """PriceVision module home"""
    stats = PriceVisionService.get_stats()
    hospitals = PriceVisionService.get_hospitals(limit=10)
    procedures = PriceVisionService.get_procedures(limit=10)
    return render_template('gov/pricevision/home.html',
                          stats=stats, hospitals=hospitals, procedures=procedures)


@gov_bp.route('/pricevision/search')
@gov_required
def pricevision_search():
    """Search for procedures or hospitals"""
    query = request.args.get('q', '')
    search_type = request.args.get('type', 'procedure')
    state = request.args.get('state', '')

    if search_type == 'hospital':
        results = PriceVisionService.get_hospitals(state=state if state else None, limit=50)
        if query:
            query_lower = query.lower()
            results = [h for h in results if query_lower in str(h.get('hospital_name', h.get('Facility Name', ''))).lower()]
    else:
        results = PriceVisionService.get_procedures(search=query if query else None, limit=50)

    states = PriceVisionService.get_states()
    return render_template('gov/pricevision/search.html',
                          results=results, query=query, search_type=search_type,
                          state=state, states=states)


@gov_bp.route('/pricevision/compare')
@gov_required
def pricevision_compare():
    """Compare prices across hospitals"""
    procedure = request.args.get('procedure', '')
    state = request.args.get('state', '')

    procedures = PriceVisionService.get_procedures(search=procedure if procedure else None, limit=20)
    prices = []
    if procedure:
        prices = PriceVisionService.get_prices(procedure_code=procedure, state=state if state else None, limit=50)

    states = PriceVisionService.get_states()
    return render_template('gov/pricevision/compare.html',
                          procedures=procedures, prices=prices, query=procedure,
                          state=state, states=states)


@gov_bp.route('/pricevision/hospital/<npi>')
@gov_required
def pricevision_hospital(npi):
    """View single hospital details"""
    hospital = PriceVisionService.get_hospital(npi)
    prices = PriceVisionService.get_prices(hospital_npi=npi, limit=100)
    return render_template('gov/pricevision/hospital.html',
                          hospital=hospital or {}, npi=npi, prices=prices)


@gov_bp.route('/pricevision/analytics')
@gov_required
def pricevision_analytics():
    """Hospital compliance analytics (gov-only)"""
    stats = PriceVisionService.get_stats()
    hospitals = PriceVisionService.get_hospitals(limit=100)
    states = PriceVisionService.get_states()

    # Calculate compliance by state
    state_stats = {}
    for h in hospitals:
        state = h.get('state', h.get('State', 'Unknown'))
        if state not in state_stats:
            state_stats[state] = {'total': 0, 'compliant': 0}
        state_stats[state]['total'] += 1
        # Assume compliant if has MRF data
        if h.get('mrf_url') or h.get('has_mrf'):
            state_stats[state]['compliant'] += 1

    return render_template('gov/pricevision/analytics.html',
                          stats=stats, hospitals=hospitals, states=states,
                          state_stats=state_stats)
