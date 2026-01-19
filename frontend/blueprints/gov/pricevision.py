"""
Government PriceVision Routes
Hospital price transparency with analytics
"""
from flask import render_template, request, jsonify
from . import gov_bp, gov_required
import sys
from pathlib import Path
import numpy as np

# Add project root to path for ML imports
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from services.pricevision import PriceVisionService

# ML Service singleton (lazy loaded)
_procedure_matching_service = None


def get_procedure_matching_service():
    """Lazy load the ProcedureMatchingService."""
    global _procedure_matching_service
    if _procedure_matching_service is None:
        try:
            from ml.procedure_encoder.inference import ProcedureMatchingService
            _procedure_matching_service = ProcedureMatchingService.load()
        except Exception:
            pass
    return _procedure_matching_service


def analyze_price_fairness(prices):
    """Analyze prices and return fairness scores."""
    if not prices:
        return {}
    cash_prices = [p['cash_price'] for p in prices if p.get('cash_price')]
    if len(cash_prices) < 3:
        return {}
    mean_price = np.mean(cash_prices)
    std_price = np.std(cash_prices)

    results = {}
    for p in prices:
        price = p.get('cash_price', 0)
        hospital_npi = p.get('hospital_npi', '')
        if price and std_price > 0:
            z_score = (price - mean_price) / std_price
            if z_score > 1.5:
                cluster = 'Overpriced'
            elif z_score < -1.5:
                cluster = 'Discount'
            else:
                cluster = 'Fair'
            results[hospital_npi] = {
                'fairness_score': max(0, 100 - abs(z_score) * 25),
                'cluster': cluster,
                'is_outlier': abs(z_score) > 2,
                'z_score': z_score
            }
    return results


def analyze_hospital_pricing(prices):
    """Analyze hospital's pricing patterns across all procedures."""
    if not prices:
        return {}

    # Calculate average markup vs market (gross vs cash)
    markups = []
    cash_prices = []
    gross_prices = []

    for p in prices:
        cash = p.get('cash_price', 0)
        gross = p.get('gross_charge', 0)
        if cash and gross and cash > 0:
            markups.append((gross - cash) / cash * 100)
            cash_prices.append(cash)
            gross_prices.append(gross)

    if len(markups) < 2:
        return {}

    avg_markup = np.mean(markups)
    markup_std = np.std(markups)
    pricing_consistency = max(0, 100 - markup_std)  # Higher consistency = lower std

    # Identify specialties based on procedure codes
    procedure_codes = [p.get('procedure_code', '') for p in prices if p.get('procedure_code')]
    specialties = set()
    for code in procedure_codes:
        if code.startswith('7'):
            specialties.add('Imaging/Radiology')
        elif code.startswith('2'):
            specialties.add('Surgery')
        elif code.startswith('9'):
            specialties.add('Evaluation & Management')
        elif code.startswith('8'):
            specialties.add('Laboratory')
        elif code.startswith('3') or code.startswith('4'):
            specialties.add('Diagnostic')

    return {
        'avg_markup': round(avg_markup, 1),
        'pricing_consistency': round(pricing_consistency, 1),
        'specialties': list(specialties)[:5],
        'total_procedures': len(prices),
        'avg_cash_price': round(np.mean(cash_prices), 2) if cash_prices else 0,
        'price_range': (round(min(cash_prices), 2), round(max(cash_prices), 2)) if cash_prices else (0, 0)
    }


def calculate_transparency_score(hospital, prices):
    """Calculate transparency score based on data completeness."""
    score = 0
    max_score = 100

    # Has any price data (30 points)
    if prices:
        score += 30

        # Data completeness checks
        prices_with_cash = sum(1 for p in prices if p.get('cash_price'))
        prices_with_gross = sum(1 for p in prices if p.get('gross_charge'))
        prices_with_payer = sum(1 for p in prices if p.get('payer_name'))

        # Cash price completeness (20 points)
        if len(prices) > 0:
            cash_ratio = prices_with_cash / len(prices)
            score += int(cash_ratio * 20)

        # Gross charge completeness (15 points)
        if len(prices) > 0:
            gross_ratio = prices_with_gross / len(prices)
            score += int(gross_ratio * 15)

        # Payer info completeness (15 points)
        if len(prices) > 0:
            payer_ratio = prices_with_payer / len(prices)
            score += int(payer_ratio * 15)

        # Volume of procedures (20 points)
        if len(prices) >= 100:
            score += 20
        elif len(prices) >= 50:
            score += 15
        elif len(prices) >= 20:
            score += 10
        elif len(prices) >= 5:
            score += 5

    return min(score, max_score)


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
    """Search for procedures or hospitals with ML semantic matching."""
    query = request.args.get('q', '')
    search_type = request.args.get('type', 'procedure')
    state = request.args.get('state', '')
    ml_related_procedures = []

    if search_type == 'hospital':
        results = PriceVisionService.get_hospitals(state=state if state else None, limit=50)
        if query:
            query_lower = query.lower()
            results = [h for h in results if query_lower in str(h.get('hospital_name', h.get('Facility Name', ''))).lower()]
    else:
        results = PriceVisionService.get_procedures(search=query if query else None, limit=50)

        # ML semantic matching for procedure search
        if query and results:
            try:
                service = get_procedure_matching_service()
                if service:
                    # Get semantic matches for the query
                    similar = service.find_similar(query, top_k=10)

                    # Create a mapping of code -> confidence
                    ml_scores = {}
                    for code, desc, confidence in similar:
                        ml_scores[code] = {
                            'ml_match_confidence': round(confidence * 100, 1),
                            'ml_matched_description': desc
                        }

                    # Enhance results with ML scores
                    for r in results:
                        code = r.get('hcpcs_code', '')
                        if code in ml_scores:
                            r['ml_match_confidence'] = ml_scores[code]['ml_match_confidence']
                            r['ml_matched_description'] = ml_scores[code]['ml_matched_description']
                        else:
                            # Get individual score for this procedure
                            try:
                                match = service.match(r.get('canonical_description', ''))
                                r['ml_match_confidence'] = round(match.confidence * 100, 1)
                            except Exception:
                                r['ml_match_confidence'] = None

                    # Sort by ML confidence (highest first)
                    results_with_ml = [r for r in results if r.get('ml_match_confidence') is not None]
                    results_without_ml = [r for r in results if r.get('ml_match_confidence') is None]
                    results_with_ml.sort(key=lambda x: x.get('ml_match_confidence', 0), reverse=True)
                    results = results_with_ml + results_without_ml

                    # Get related procedures
                    ml_related_procedures = [
                        {'code': code, 'description': desc, 'confidence': round(conf * 100, 1)}
                        for code, desc, conf in similar[:5]
                    ]
            except Exception:
                pass  # Continue without ML features

    states = PriceVisionService.get_states()
    return render_template('gov/pricevision/search.html',
                          results=results, query=query, search_type=search_type,
                          state=state, states=states,
                          ml_related_procedures=ml_related_procedures)


@gov_bp.route('/pricevision/compare')
@gov_required
def pricevision_compare():
    """Compare prices across hospitals with ML fairness analysis."""
    procedure = request.args.get('procedure', '')
    state = request.args.get('state', '')
    fairness_data = {}
    best_value_npi = None

    procedures = PriceVisionService.get_procedures(search=procedure if procedure else None, limit=20)
    prices = []
    if procedure:
        prices = PriceVisionService.get_prices(procedure_code=procedure, state=state if state else None, limit=50)

        # ML price fairness analysis
        try:
            fairness_data = analyze_price_fairness(prices)

            # Add ML data to each price entry
            for p in prices:
                npi = p.get('hospital_npi', '')
                if npi in fairness_data:
                    p['ml_fairness_score'] = round(fairness_data[npi]['fairness_score'], 1)
                    p['ml_price_cluster'] = fairness_data[npi]['cluster']
                    p['ml_is_outlier'] = fairness_data[npi]['is_outlier']
                    p['ml_z_score'] = round(fairness_data[npi]['z_score'], 2)

            # Find best value (lowest price among Fair-priced hospitals)
            fair_prices = [p for p in prices if p.get('ml_price_cluster') == 'Fair' and p.get('cash_price')]
            if fair_prices:
                best = min(fair_prices, key=lambda x: x.get('cash_price', float('inf')))
                best_value_npi = best.get('hospital_npi')
            elif prices:
                # If no fair prices, find lowest among all
                prices_with_cash = [p for p in prices if p.get('cash_price')]
                if prices_with_cash:
                    best = min(prices_with_cash, key=lambda x: x.get('cash_price', float('inf')))
                    best_value_npi = best.get('hospital_npi')
        except Exception:
            pass  # Continue without ML features

    states = PriceVisionService.get_states()
    return render_template('gov/pricevision/compare.html',
                          procedures=procedures, prices=prices, query=procedure,
                          state=state, states=states, fairness_data=fairness_data,
                          best_value_npi=best_value_npi)


@gov_bp.route('/pricevision/hospital/<npi>')
@gov_required
def pricevision_hospital(npi):
    """View single hospital details with ML pricing pattern analysis."""
    hospital = PriceVisionService.get_hospital(npi)
    prices = PriceVisionService.get_prices(hospital_npi=npi, limit=100)
    pricing_analysis = {}
    transparency_score = 0

    # ML pricing pattern analysis
    try:
        pricing_analysis = analyze_hospital_pricing(prices)
        transparency_score = calculate_transparency_score(hospital, prices)
    except Exception:
        pass  # Continue without ML features

    return render_template('gov/pricevision/hospital.html',
                          hospital=hospital or {}, npi=npi, prices=prices,
                          pricing_analysis=pricing_analysis,
                          transparency_score=transparency_score)


@gov_bp.route('/pricevision/analytics')
@gov_required
def pricevision_analytics():
    """Hospital compliance analytics (gov-only) with ML transparency scoring."""
    state_filter = request.args.get('state', '')
    limit_param = request.args.get('limit', '100')

    # Handle 'all' option for limit
    if limit_param.lower() == 'all':
        limit = 10000  # Practical maximum
        selected_limit = 'all'
    else:
        limit = int(limit_param)
        selected_limit = limit

    stats = PriceVisionService.get_stats()
    states = PriceVisionService.get_states()

    # Get set of hospitals that have MRF/pricing data (for compliance check)
    hospitals_with_mrf = PriceVisionService.get_hospitals_with_mrf()

    # Always fetch all hospitals first for state stats calculation
    all_hospitals = PriceVisionService.get_hospitals(limit=10000)

    # Filter for display if state filter is applied
    if state_filter:
        filtered_hospitals = [h for h in all_hospitals if h.get('State', '') == state_filter]
        hospitals = filtered_hospitals[:limit] if limit != 10000 else filtered_hospitals
    else:
        hospitals = all_hospitals[:limit] if limit != 10000 else all_hospitals

    # Calculate compliance by state from ALL hospitals (not just displayed subset)
    state_stats = {}
    for h in all_hospitals:
        st = h.get('State', '')
        if not st or len(str(st)) != 2:
            continue
        if st not in state_stats:
            state_stats[st] = {'total': 0, 'compliant': 0}
        state_stats[st]['total'] += 1
        # Hospital is compliant if it has MRF/pricing data
        facility_id = str(h.get('Facility ID', ''))
        if facility_id in hospitals_with_mrf:
            state_stats[st]['compliant'] += 1

    # ML transparency scoring for displayed hospitals
    suspicious_gaps = []
    try:
        for h in hospitals:
            facility_id = str(h.get('Facility ID', ''))
            if facility_id in hospitals_with_mrf:
                # Get prices for this hospital to calculate transparency
                prices = PriceVisionService.get_prices(hospital_npi=facility_id, limit=50)
                h['ml_transparency_score'] = calculate_transparency_score(h, prices)

                # Flag suspicious pricing gaps
                if prices:
                    prices_with_cash = sum(1 for p in prices if p.get('cash_price'))
                    cash_ratio = prices_with_cash / len(prices) if len(prices) > 0 else 0
                    if cash_ratio < 0.5 and len(prices) > 10:
                        suspicious_gaps.append({
                            'facility_name': h.get('Facility Name', 'Unknown'),
                            'facility_id': facility_id,
                            'total_prices': len(prices),
                            'missing_cash': len(prices) - prices_with_cash,
                            'gap_ratio': round((1 - cash_ratio) * 100, 1)
                        })
            else:
                h['ml_transparency_score'] = 0
    except Exception:
        pass  # Continue without ML features

    return render_template('gov/pricevision/analytics.html',
                          stats=stats, hospitals=hospitals, states=states,
                          state_stats=state_stats, selected_state=state_filter,
                          selected_limit=selected_limit,
                          suspicious_gaps=suspicious_gaps[:10] if suspicious_gaps else [])
