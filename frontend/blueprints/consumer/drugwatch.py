"""
Public DrugWatch Routes
Drug price comparison for consumers
"""
from flask import render_template, request, jsonify
from . import public_bp
import sys
from pathlib import Path

# Add frontend directory to path for service imports
FRONTEND_DIR = Path(__file__).parent.parent.parent
PROJECT_ROOT = FRONTEND_DIR.parent
sys.path.insert(0, str(FRONTEND_DIR))
sys.path.insert(0, str(PROJECT_ROOT))

from services.drugwatch import DrugWatchService

# Module-level cache for route results
_route_cache = {}


@public_bp.route('/drugwatch/')
def drugwatch_home():
    """DrugWatch module home - cached stats and top drugs"""
    if 'home_data' not in _route_cache:
        _route_cache['home_data'] = {
            'stats': DrugWatchService.get_stats(),
            'top_drugs': DrugWatchService.get_top_expensive_cached(limit=10),
        }
    data = _route_cache['home_data']
    return render_template('public/drugwatch/home.html',
                          stats=data['stats'], top_drugs=data['top_drugs'])


@public_bp.route('/drugwatch/search')
def drugwatch_search():
    """Search for drugs"""
    query = request.args.get('q', '')
    drugs = DrugWatchService.get_us_drugs(search=query if query else None, limit=50)
    return render_template('public/drugwatch/search.html',
                          query=query, drugs=drugs)


@public_bp.route('/drugwatch/compare')
@public_bp.route('/drugwatch/compare/<drug_id>')
def drugwatch_compare(drug_id=None):
    """Compare drug prices across countries - cached by drug name"""
    # Support both /compare/aspirin and /compare?drug=aspirin
    if not drug_id:
        drug_id = request.args.get('drug', '')
    if not drug_id:
        return render_template('public/drugwatch/compare.html',
                              drug_id=None, drug=None, comparison=None)
    # Use cached comparison and drug detail lookups
    drug = DrugWatchService.get_drug(drug_id)
    comparison = DrugWatchService.get_cached_comparison(drug_id)
    return render_template('public/drugwatch/compare.html',
                          drug_id=drug_id, drug=drug, comparison=comparison)


@public_bp.route('/drugwatch/drug/<drug_id>')
def drugwatch_drug(drug_id):
    """View single drug details - cached drug and comparison"""
    drug = DrugWatchService.get_drug(drug_id)
    comparison = DrugWatchService.get_cached_comparison(drug_id)
    return render_template('public/drugwatch/drug.html',
                          drug_id=drug_id, drug=drug, comparison=comparison)


# API endpoints
@public_bp.route('/api/drugwatch/drugs')
def api_drugs():
    """API: Get drugs"""
    search = request.args.get('q', '')
    try:
        limit = int(request.args.get('limit', 50) or 50)
    except (ValueError, TypeError):
        limit = 50
    drugs = DrugWatchService.get_us_drugs(search=search if search else None, limit=limit)
    return jsonify(drugs)


@public_bp.route('/api/drugwatch/compare/<drug_name>')
def api_compare(drug_name):
    """API: Compare drug prices - cached"""
    comparison = DrugWatchService.get_cached_comparison(drug_name)
    return jsonify(comparison)
