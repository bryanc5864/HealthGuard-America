"""
Government DrugWatch Routes
Drug price comparison with MFN analysis
"""
from flask import render_template, request
from . import gov_bp, gov_required


@gov_bp.route('/drugwatch/')
@gov_required
def drugwatch_home():
    """DrugWatch module home"""
    return render_template('gov/drugwatch/home.html')


@gov_bp.route('/drugwatch/search')
@gov_required
def drugwatch_search():
    """Search for drugs"""
    query = request.args.get('q', '')
    return render_template('gov/drugwatch/search.html', query=query)


@gov_bp.route('/drugwatch/compare/<drug_id>')
@gov_required
def drugwatch_compare(drug_id):
    """Compare drug prices across countries"""
    return render_template('gov/drugwatch/compare.html', drug_id=drug_id)


@gov_bp.route('/drugwatch/drug/<drug_id>')
@gov_required
def drugwatch_drug(drug_id):
    """View single drug details"""
    return render_template('gov/drugwatch/drug.html', drug_id=drug_id)


@gov_bp.route('/drugwatch/mfn')
@gov_required
def drugwatch_mfn():
    """Most Favored Nation pricing analysis (gov-only)"""
    return render_template('gov/drugwatch/mfn.html')
