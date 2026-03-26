"""
Government DrugWatch Routes
Drug price comparison with MFN analysis
"""
from flask import render_template, request, jsonify
from . import gov_bp, gov_required
import sys
from pathlib import Path

# Add project root to path for ML imports
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from services.drugwatch import DrugWatchService

# Module-level caches for expensive computations
_route_cache = {}
_mfn_cache = {}
_trends_cache = {}


@gov_bp.route('/drugwatch/')
@gov_required
def drugwatch_home():
    """DrugWatch module home - cached stats and top drugs"""
    if 'home_data' not in _route_cache:
        _route_cache['home_data'] = {
            'stats': DrugWatchService.get_stats(),
            'top_drugs': DrugWatchService.get_top_expensive_cached(limit=10),
        }
    data = _route_cache['home_data']
    return render_template('gov/drugwatch/home.html',
                          stats=data['stats'], top_drugs=data['top_drugs'])


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
    """Compare drug prices across countries - cached"""
    drug = DrugWatchService.get_drug(drug_id)
    comparison = DrugWatchService.get_cached_comparison(drug_id)
    return render_template('gov/drugwatch/compare.html',
                          drug_id=drug_id, drug=drug, comparison=comparison)


@gov_bp.route('/drugwatch/drug/<drug_id>')
@gov_required
def drugwatch_drug(drug_id):
    """View single drug details - cached"""
    drug = DrugWatchService.get_drug(drug_id)
    comparison = DrugWatchService.get_cached_comparison(drug_id)
    return render_template('gov/drugwatch/drug.html',
                          drug_id=drug_id, drug=drug, comparison=comparison)


@gov_bp.route('/drugwatch/mfn')
@gov_required
def drugwatch_mfn():
    """Most Favored Nation pricing analysis (gov-only) - cached"""
    search = request.args.get('q', '')
    try:
        limit = int(request.args.get('limit', 50) or 50)
    except (ValueError, TypeError):
        limit = 50

    # Cache key based on search and limit parameters
    mfn_cache_key = f'mfn_{search}_{limit}'
    if mfn_cache_key in _mfn_cache:
        cached = _mfn_cache[mfn_cache_key]
        return render_template('gov/drugwatch/mfn.html', **cached)

    stats = DrugWatchService.get_stats()

    # Get drugs - with search
    if search:
        all_drugs = DrugWatchService.get_us_drugs(search=search, limit=500)
        all_drugs = sorted(all_drugs, key=lambda x: float(x.get('total_spending_2023', 0) or 0), reverse=True)
    else:
        all_drugs = DrugWatchService.get_top_expensive_cached(limit=500)

    top_drugs = all_drugs[:limit]
    intl_prices = DrugWatchService.get_international_prices()

    # Calculate MFN savings potential
    mfn_analysis = []
    for drug in top_drugs:
        drug_name = drug.get('brand_name', '')
        us_spending = float(drug.get('total_spending_2023', 0) or 0)
        if drug_name and us_spending > 0:
            mfn_analysis.append({
                'drug': drug_name,
                'generic': drug.get('generic_name', ''),
                'us_spending': us_spending,
                'potential_savings': us_spending * 0.3  # Estimated 30% savings
            })

    template_data = {
        'stats': stats, 'top_drugs': top_drugs,
        'intl_prices': intl_prices[:100], 'mfn_analysis': mfn_analysis,
        'search': search, 'limit': limit, 'total_drugs': len(all_drugs),
    }

    # Cache result (limit to 50 entries)
    if len(_mfn_cache) >= 50:
        oldest_key = next(iter(_mfn_cache))
        del _mfn_cache[oldest_key]
    _mfn_cache[mfn_cache_key] = template_data

    return render_template('gov/drugwatch/mfn.html', **template_data)


@gov_bp.route('/drugwatch/trends')
@gov_required
def drugwatch_trends():
    """Drug spending trends analysis (gov-only) - cached"""
    search = request.args.get('q', '')
    try:
        limit = int(request.args.get('limit', 50) or 50)
    except (ValueError, TypeError):
        limit = 50
    try:
        page = int(request.args.get('page', 1) or 1)
    except (ValueError, TypeError):
        page = 1
    # Ensure limit and page are at least 1 to avoid division by zero
    limit = max(1, limit)
    page = max(1, page)

    # Cache key based on search, limit, and page
    trends_cache_key = f'trends_{search}_{limit}_{page}'
    if trends_cache_key in _trends_cache:
        cached = _trends_cache[trends_cache_key]
        return render_template('gov/drugwatch/trends.html', **cached)

    stats = DrugWatchService.get_stats()

    # Get drugs - with search and pagination
    if search:
        all_drugs = DrugWatchService.get_us_drugs(search=search, limit=1000)
        # Sort by spending
        all_drugs = sorted(all_drugs, key=lambda x: float(x.get('total_spending_2023', 0) or 0), reverse=True)
    else:
        all_drugs = DrugWatchService.get_top_expensive_cached(limit=500)

    # Pagination
    total_drugs = len(all_drugs)
    start = (page - 1) * limit
    end = start + limit
    drugs = all_drugs[start:end]
    total_pages = (total_drugs + limit - 1) // limit

    # Top 25 for chart
    top_drugs = all_drugs[:25] if not search else drugs[:25]

    # Calculate spending stats
    spending_data = {
        'total': sum(float(d.get('total_spending_2023', 0) or 0) for d in all_drugs[:100]),
        'drugs': drugs
    }

    template_data = {
        'stats': stats, 'spending_data': spending_data, 'top_drugs': top_drugs,
        'drugs': drugs, 'search': search, 'limit': limit, 'page': page,
        'total_drugs': total_drugs, 'total_pages': total_pages,
    }

    # Cache result (limit to 100 entries)
    if len(_trends_cache) >= 100:
        oldest_key = next(iter(_trends_cache))
        del _trends_cache[oldest_key]
    _trends_cache[trends_cache_key] = template_data

    return render_template('gov/drugwatch/trends.html', **template_data)
