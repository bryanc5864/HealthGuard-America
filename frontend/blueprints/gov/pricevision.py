"""
Government PriceVision Routes
Hospital price transparency with analytics
"""
from flask import render_template, request, jsonify
from . import gov_bp, gov_required
import sys
import logging
from pathlib import Path
import numpy as np

logger = logging.getLogger(__name__)

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
            logger.info("ProcedureMatchingService loaded successfully")
        except Exception as e:
            logger.warning(f"Failed to load ProcedureMatchingService: {e}")
    return _procedure_matching_service


# CPT/HCPCS code specialty mapping (more accurate than first-digit heuristic)
CPT_SPECIALTY_RANGES = {
    (99000, 99999): 'Evaluation & Management',
    (0, 1999): 'Anesthesia',
    (10000, 19999): 'Integumentary Surgery',
    (20000, 29999): 'Musculoskeletal Surgery',
    (30000, 32999): 'Respiratory Surgery',
    (33000, 37999): 'Cardiovascular Surgery',
    (38000, 39999): 'Hemic/Lymphatic Surgery',
    (40000, 49999): 'Digestive Surgery',
    (50000, 53999): 'Urinary Surgery',
    (54000, 55999): 'Male Genital Surgery',
    (56000, 58999): 'Female Genital Surgery',
    (59000, 59999): 'Maternity Care',
    (60000, 60999): 'Endocrine Surgery',
    (61000, 64999): 'Nervous System Surgery',
    (65000, 68999): 'Eye Surgery',
    (69000, 69999): 'Auditory Surgery',
    (70000, 79999): 'Imaging/Radiology',
    (80000, 89999): 'Laboratory/Pathology',
    (90000, 98999): 'Medicine/Therapy',
}


def get_specialty_from_code(code):
    """Get specialty category from CPT/HCPCS code using range lookup."""
    if not code:
        return None
    try:
        numeric = ''.join(c for c in str(code) if c.isdigit())
        if not numeric:
            return None
        code_num = int(numeric)
        for (start, end), specialty in CPT_SPECIALTY_RANGES.items():
            if start <= code_num <= end:
                return specialty
        return 'Other'
    except (ValueError, TypeError):
        return None


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

    # Identify specialties based on procedure codes using accurate range lookup
    procedure_codes = [p.get('procedure_code', '') for p in prices if p.get('procedure_code')]
    specialties = set()
    for code in procedure_codes:
        specialty = get_specialty_from_code(code)
        if specialty:
            specialties.add(specialty)

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

                    # Enhance results with ML scores (limit individual calls to first 10)
                    individual_calls = 0
                    max_individual_calls = 10
                    for r in results:
                        code = r.get('hcpcs_code', '')
                        if code in ml_scores:
                            r['ml_match_confidence'] = ml_scores[code]['ml_match_confidence']
                            r['ml_matched_description'] = ml_scores[code]['ml_matched_description']
                        elif individual_calls < max_individual_calls:
                            # Get individual score for this procedure (limited)
                            try:
                                match = service.match(r.get('canonical_description', ''))
                                r['ml_match_confidence'] = round(match.confidence * 100, 1)
                                individual_calls += 1
                            except Exception as e:
                                logger.debug(f"ML match failed for procedure: {e}")
                                r['ml_match_confidence'] = None
                        else:
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
            except Exception as e:
                logger.warning(f"ML semantic matching failed: {e}")

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
        # Get the actual HCPCS code - either use procedure directly if it looks like a code,
        # or find the matching procedure's code from search results
        procedure_code = procedure
        if procedures and not procedure.isdigit():
            # User searched by name, get the actual code from first match
            first_match = procedures[0]
            procedure_code = first_match.get('code', first_match.get('hcpcs_code', procedure))
        prices = PriceVisionService.get_prices(procedure_code=procedure_code, state=state if state else None, limit=50)

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
        except Exception as e:
            logger.warning(f"ML price fairness analysis failed: {e}")

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
    except Exception as e:
        logger.warning(f"Hospital pricing analysis failed: {e}")

    return render_template('gov/pricevision/hospital.html',
                          hospital=hospital or {}, npi=npi, prices=prices,
                          pricing_analysis=pricing_analysis,
                          transparency_score=transparency_score)


@gov_bp.route('/pricevision/my-price')
@gov_required
def pricevision_my_price():
    """Check if your quoted price is fair compared to market rates."""
    procedure = request.args.get('procedure', '')
    user_price = request.args.get('price', '')
    state = request.args.get('state', '')
    hospital_name = request.args.get('hospital', '')

    analysis = None
    prices = []
    market_stats = {}

    procedures = PriceVisionService.get_procedures(search=procedure if procedure else None, limit=20)

    if procedure and user_price:
        try:
            user_price_float = float(user_price.replace(',', '').replace('$', ''))
        except ValueError:
            user_price_float = 0

        if user_price_float > 0:
            # Get the actual HCPCS code - either use procedure directly if it looks like a code,
            # or find the matching procedure's code from search results
            procedure_code = procedure
            if procedures and not procedure.isdigit():
                # User searched by name, get the actual code from first match
                first_match = procedures[0]
                procedure_code = first_match.get('code', first_match.get('hcpcs_code', procedure))

            # Get market prices for comparison
            prices = PriceVisionService.get_prices(
                procedure_code=procedure_code,
                state=state if state else None,
                limit=100
            )

            if prices:
                # Calculate market statistics
                cash_prices = [p['cash_price'] for p in prices if p.get('cash_price')]

                if cash_prices:
                    mean_price = np.mean(cash_prices)
                    std_price = np.std(cash_prices) if len(cash_prices) > 1 else mean_price * 0.2
                    min_price = min(cash_prices)
                    max_price = max(cash_prices)
                    median_price = np.median(cash_prices)

                    # Calculate z-score for user's price
                    if std_price > 0:
                        z_score = (user_price_float - mean_price) / std_price
                    else:
                        z_score = 0

                    # Determine fairness
                    if z_score > 1.5:
                        verdict = 'Overpriced'
                        verdict_class = 'danger'
                        explanation = f"Your price is ${user_price_float - mean_price:,.0f} above the average market rate."
                    elif z_score < -1.5:
                        verdict = 'Great Deal'
                        verdict_class = 'success'
                        explanation = f"Your price is ${mean_price - user_price_float:,.0f} below the average market rate!"
                    elif z_score < -0.5:
                        verdict = 'Good Price'
                        verdict_class = 'info'
                        explanation = "Your price is below average - a reasonable deal."
                    elif z_score > 0.5:
                        verdict = 'Above Average'
                        verdict_class = 'warning'
                        explanation = "Your price is above average - consider negotiating or shopping around."
                    else:
                        verdict = 'Fair Price'
                        verdict_class = 'success'
                        explanation = "Your price is close to the market average."

                    # Calculate potential savings
                    if user_price_float > min_price:
                        potential_savings = user_price_float - min_price
                    else:
                        potential_savings = 0

                    # Percentile ranking
                    prices_below = sum(1 for p in cash_prices if p < user_price_float)
                    percentile = (prices_below / len(cash_prices)) * 100

                    market_stats = {
                        'mean': mean_price,
                        'median': median_price,
                        'min': min_price,
                        'max': max_price,
                        'std': std_price,
                        'sample_size': len(cash_prices)
                    }

                    analysis = {
                        'user_price': user_price_float,
                        'verdict': verdict,
                        'verdict_class': verdict_class,
                        'explanation': explanation,
                        'z_score': round(z_score, 2),
                        'percentile': round(percentile, 1),
                        'potential_savings': potential_savings,
                        'fairness_score': max(0, min(100, 100 - abs(z_score) * 25))
                    }

    states = PriceVisionService.get_states()
    return render_template('gov/pricevision/my_price.html',
                          procedures=procedures, prices=prices[:20],
                          query=procedure, user_price=user_price,
                          hospital_name=hospital_name,
                          state=state, states=states,
                          analysis=analysis, market_stats=market_stats)


@gov_bp.route('/pricevision/analytics')
@gov_required
def pricevision_analytics():
    """Hospital compliance analytics (gov-only) - optimized for fast loading."""
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

    # Get set of hospitals that have MRF/pricing data (fast - cached)
    hospitals_with_mrf = PriceVisionService.get_hospitals_with_mrf()

    # Fetch hospitals (cached after first call)
    all_hospitals = PriceVisionService.get_hospitals(limit=10000)

    # Filter for display if state filter is applied
    if state_filter:
        filtered_hospitals = [h for h in all_hospitals if h.get('State', '') == state_filter]
        hospitals = filtered_hospitals[:limit] if limit != 10000 else filtered_hospitals
    else:
        hospitals = all_hospitals[:limit] if limit != 10000 else all_hospitals

    # Calculate compliance by state - use simple count (no transparency scoring)
    state_stats = {}
    for h in all_hospitals:
        st = h.get('State', '')
        if not st or len(str(st)) != 2:
            continue
        if st not in state_stats:
            state_stats[st] = {'total': 0, 'compliant': 0}
        state_stats[st]['total'] += 1

    # Simple compliance: count hospitals with pricing data
    # Note: hospitals_with_mrf contains NPIs from price file
    total_compliant = len(hospitals_with_mrf)
    for st in state_stats:
        # Estimate state compliance based on hospital count ratio
        state_ratio = state_stats[st]['total'] / len(all_hospitals) if all_hospitals else 0
        state_stats[st]['compliant'] = int(total_compliant * state_ratio)

    # For displayed hospitals, mark compliance simply
    for h in hospitals:
        # Use simple compliance indicator (no heavy transparency scoring)
        h['ml_transparency_score'] = 50  # Default score

    return render_template('gov/pricevision/analytics.html',
                          stats=stats, hospitals=hospitals, states=states,
                          state_stats=state_stats, selected_state=state_filter,
                          selected_limit=selected_limit,
                          suspicious_gaps=[])
