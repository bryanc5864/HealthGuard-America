"""
Public PriceVision Routes
Hospital price transparency for consumers
"""
from flask import render_template, request, jsonify
from . import public_bp
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from services.pricevision import PriceVisionService


@public_bp.route('/pricevision/')
def pricevision_home():
    """PriceVision module home"""
    stats = PriceVisionService.get_stats()
    hospitals = PriceVisionService.get_hospitals(limit=10)
    procedures = PriceVisionService.get_procedures(limit=10)
    return render_template('public/pricevision/home.html',
                          stats=stats, hospitals=hospitals, procedures=procedures)


@public_bp.route('/pricevision/search')
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
    return render_template('public/pricevision/search.html',
                          results=results, query=query, search_type=search_type,
                          state=state, states=states)


@public_bp.route('/pricevision/compare')
def pricevision_compare():
    """Compare prices across hospitals"""
    procedure = request.args.get('procedure', '')
    state = request.args.get('state', '')

    procedures = PriceVisionService.get_procedures(search=procedure if procedure else None, limit=20)
    prices = []
    if procedure:
        prices = PriceVisionService.get_prices(procedure_code=procedure, state=state if state else None, limit=50)

    states = PriceVisionService.get_states()
    return render_template('public/pricevision/compare.html',
                          procedures=procedures, prices=prices, query=procedure,
                          state=state, states=states)


@public_bp.route('/pricevision/hospital/<npi>')
def pricevision_hospital(npi):
    """View single hospital details"""
    hospital = PriceVisionService.get_hospital(npi)
    prices = PriceVisionService.get_prices(hospital_npi=npi, limit=100)
    return render_template('public/pricevision/hospital.html',
                          hospital=hospital or {}, npi=npi, prices=prices)


# API endpoints for AJAX
@public_bp.route('/api/pricevision/procedures')
def api_procedures():
    """API: Get procedures"""
    search = request.args.get('q', '')
    limit = int(request.args.get('limit', 50))
    procedures = PriceVisionService.get_procedures(search=search if search else None, limit=limit)
    return jsonify(procedures)


@public_bp.route('/api/pricevision/hospitals')
def api_hospitals():
    """API: Get hospitals"""
    state = request.args.get('state', '')
    limit = int(request.args.get('limit', 50))
    hospitals = PriceVisionService.get_hospitals(state=state if state else None, limit=limit)
    return jsonify(hospitals)
