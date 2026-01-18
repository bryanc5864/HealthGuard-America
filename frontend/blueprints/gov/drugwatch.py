"""
Government DrugWatch Routes
Drug price comparison with MFN analysis
"""
from flask import render_template, request, jsonify
from . import gov_bp, gov_required
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from services.drugwatch import DrugWatchService


@gov_bp.route('/drugwatch/')
@gov_required
def drugwatch_home():
    """DrugWatch module home"""
    stats = DrugWatchService.get_stats()
    top_drugs = DrugWatchService.get_top_expensive(limit=10)
    return render_template('gov/drugwatch/home.html',
                          stats=stats, top_drugs=top_drugs)


@gov_bp.route('/drugwatch/search')
@gov_required
def drugwatch_search():
    """Search for drugs"""
    query = request.args.get('q', '')
    drugs = DrugWatchService.get_us_drugs(search=query if query else None, limit=50)
    return render_template('gov/drugwatch/search.html',
                          query=query, drugs=drugs)


@gov_bp.route('/drugwatch/compare/<drug_id>')
@gov_required
def drugwatch_compare(drug_id):
    """Compare drug prices across countries"""
    drug = DrugWatchService.get_drug(drug_id)
    comparison = DrugWatchService.compare_prices(drug_id)
    return render_template('gov/drugwatch/compare.html',
                          drug_id=drug_id, drug=drug, comparison=comparison)


@gov_bp.route('/drugwatch/drug/<drug_id>')
@gov_required
def drugwatch_drug(drug_id):
    """View single drug details"""
    drug = DrugWatchService.get_drug(drug_id)
    comparison = DrugWatchService.compare_prices(drug_id)
    return render_template('gov/drugwatch/drug.html',
                          drug_id=drug_id, drug=drug, comparison=comparison)


@gov_bp.route('/drugwatch/mfn')
@gov_required
def drugwatch_mfn():
    """Most Favored Nation pricing analysis (gov-only)"""
    stats = DrugWatchService.get_stats()
    top_drugs = DrugWatchService.get_top_expensive(limit=20)
    intl_prices = DrugWatchService.get_international_prices()

    # Calculate MFN savings potential
    mfn_analysis = []
    for drug in top_drugs:
        drug_name = drug.get('brand_name', '')
        us_spending = float(drug.get('total_spending_2023', 0) or 0)
        if drug_name and us_spending > 0:
            mfn_analysis.append({
                'drug': drug_name,
                'us_spending': us_spending,
                'potential_savings': us_spending * 0.3  # Estimated 30% savings
            })

    return render_template('gov/drugwatch/mfn.html',
                          stats=stats, top_drugs=top_drugs,
                          intl_prices=intl_prices[:50], mfn_analysis=mfn_analysis)


@gov_bp.route('/drugwatch/trends')
@gov_required
def drugwatch_trends():
    """Drug spending trends analysis (gov-only)"""
    stats = DrugWatchService.get_stats()
    top_drugs = DrugWatchService.get_top_expensive(limit=25)

    # Calculate spending by category
    spending_data = {
        'total': sum(float(d.get('total_spending_2023', 0) or 0) for d in top_drugs),
        'drugs': top_drugs
    }

    return render_template('gov/drugwatch/trends.html',
                          stats=stats, spending_data=spending_data, top_drugs=top_drugs)
