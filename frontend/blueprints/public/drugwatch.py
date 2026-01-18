"""
Public DrugWatch Routes
Drug price comparison for consumers
"""
from flask import render_template, request, jsonify
from . import public_bp
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from services.drugwatch import DrugWatchService


@public_bp.route('/drugwatch/')
def drugwatch_home():
    """DrugWatch module home"""
    stats = DrugWatchService.get_stats()
    top_drugs = DrugWatchService.get_top_expensive(limit=10)
    return render_template('public/drugwatch/home.html',
                          stats=stats, top_drugs=top_drugs)


@public_bp.route('/drugwatch/search')
def drugwatch_search():
    """Search for drugs"""
    query = request.args.get('q', '')
    drugs = DrugWatchService.get_us_drugs(search=query if query else None, limit=50)
    return render_template('public/drugwatch/search.html',
                          query=query, drugs=drugs)


@public_bp.route('/drugwatch/compare/<drug_id>')
def drugwatch_compare(drug_id):
    """Compare drug prices across countries"""
    drug = DrugWatchService.get_drug(drug_id)
    comparison = DrugWatchService.compare_prices(drug_id)
    return render_template('public/drugwatch/compare.html',
                          drug_id=drug_id, drug=drug, comparison=comparison)


@public_bp.route('/drugwatch/drug/<drug_id>')
def drugwatch_drug(drug_id):
    """View single drug details"""
    drug = DrugWatchService.get_drug(drug_id)
    comparison = DrugWatchService.compare_prices(drug_id)
    return render_template('public/drugwatch/drug.html',
                          drug_id=drug_id, drug=drug, comparison=comparison)


# API endpoints
@public_bp.route('/api/drugwatch/drugs')
def api_drugs():
    """API: Get drugs"""
    search = request.args.get('q', '')
    limit = int(request.args.get('limit', 50))
    drugs = DrugWatchService.get_us_drugs(search=search if search else None, limit=limit)
    return jsonify(drugs)


@public_bp.route('/api/drugwatch/compare/<drug_name>')
def api_compare(drug_name):
    """API: Compare drug prices"""
    comparison = DrugWatchService.compare_prices(drug_name)
    return jsonify(comparison)
