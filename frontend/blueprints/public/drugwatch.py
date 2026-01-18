"""
Public DrugWatch Routes
Drug price comparison for consumers
"""
from flask import render_template, request
from . import public_bp


@public_bp.route('/drugwatch/')
def drugwatch_home():
    """DrugWatch module home"""
    return render_template('public/drugwatch/home.html')


@public_bp.route('/drugwatch/search')
def drugwatch_search():
    """Search for drugs"""
    query = request.args.get('q', '')
    return render_template('public/drugwatch/search.html', query=query)


@public_bp.route('/drugwatch/compare/<drug_id>')
def drugwatch_compare(drug_id):
    """Compare drug prices across countries"""
    return render_template('public/drugwatch/compare.html', drug_id=drug_id)


@public_bp.route('/drugwatch/drug/<drug_id>')
def drugwatch_drug(drug_id):
    """View single drug details"""
    return render_template('public/drugwatch/drug.html', drug_id=drug_id)
