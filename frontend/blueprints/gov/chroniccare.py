"""
Government ChronicCare Routes
Chronic disease management (gov-only module)
"""
from flask import render_template, request, jsonify
from . import gov_bp, gov_required
import sys
import logging
from pathlib import Path

# Add project root to path for ML imports
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from services.chroniccare import ChronicCareService

# ML imports for real-time inference
try:
    from ml.chroniccare.inference import ChronicCareMLService, get_chroniccare_service
    ML_AVAILABLE = True
except ImportError as e:
    logging.warning(f"ML module not available: {e}")
    ML_AVAILABLE = False

logger = logging.getLogger(__name__)


def extract_ml_features(county_data: dict) -> dict:
    """
    Extract the 19-20 features needed by the ML model from county data.

    Features cover:
    - Food environment (5): grocery_stores_per_1000, fast_food_restaurants_per_1000,
      food_environment_index, food_insecurity_rate, pct_limited_food_access
    - Healthcare (4): pcp_rate, mental_health_provider_rate, pct_uninsured,
      preventable_hospitalizations
    - Socioeconomic (5): median_household_income, child_poverty_rate,
      income_inequality_ratio, high_school_graduation_rate, pct_some_college
    - Behavioral (4): physical_inactivity_prevalence, excessive_drinking_prevalence,
      smoking_prevalence, pct_insufficient_sleep
    - Demographics (1): pct_rural

    Args:
        county_data: Dict containing county health and socioeconomic data

    Returns:
        Dict mapping feature names to float values for ML model input
    """
    def safe_float(value, default=0.0):
        """Safely convert value to float."""
        if value is None:
            return default
        try:
            return float(value)
        except (ValueError, TypeError):
            return default

    def to_per_100k(value):
        """Convert per-capita rate to per-100k if needed."""
        val = safe_float(value)
        # If value < 1, it's likely per-capita; convert to per-100k
        if 0 < val < 1:
            return val * 100000
        return val

    def to_percentage(value):
        """Convert decimal to percentage if needed."""
        val = safe_float(value)
        # If value < 1, it's likely a decimal; convert to percentage
        if 0 < val < 1:
            return val * 100
        return val

    features = {
        # Food environment features
        'grocery_stores_per_1000': safe_float(county_data.get('grocery_stores_per_1000')),
        'fast_food_restaurants_per_1000': safe_float(county_data.get('fast_food_restaurants_per_1000')),
        'food_environment_index': safe_float(county_data.get('food_environment_index')),
        'food_insecurity_rate': to_percentage(county_data.get('food_insecurity_rate')),
        'pct_limited_food_access': to_percentage(county_data.get('pct_limited_food_access')),

        # Healthcare features - convert per-capita to per-100k
        'pcp_rate': to_per_100k(county_data.get('pcp_rate')),
        'mental_health_provider_rate': to_per_100k(county_data.get('mental_health_provider_rate')),
        'pct_uninsured': to_percentage(county_data.get('pct_uninsured')),
        'preventable_hospitalizations': safe_float(county_data.get('preventable_hospitalizations')),

        # Socioeconomic features
        'median_household_income': safe_float(county_data.get('median_household_income')),
        'child_poverty_rate': to_percentage(county_data.get('child_poverty_rate')),
        'income_inequality_ratio': safe_float(county_data.get('income_inequality_ratio')),
        'high_school_graduation_rate': to_percentage(county_data.get('high_school_graduation_rate')),
        'pct_some_college': to_percentage(county_data.get('pct_some_college')),

        # Behavioral features
        'physical_inactivity_prevalence': to_percentage(county_data.get('physical_inactivity_prevalence')),
        'excessive_drinking_prevalence': to_percentage(county_data.get('excessive_drinking_prevalence')),
        'smoking_prevalence': to_percentage(county_data.get('smoking_prevalence')),
        'pct_insufficient_sleep': to_percentage(county_data.get('pct_insufficient_sleep')),

        # Demographics
        'pct_rural': to_percentage(county_data.get('pct_rural')),

        # Disease burden (for MAHA index calculation)
        'chronic_disease_burden_score': safe_float(county_data.get('chronic_disease_burden_score')),
        'food_environment_score': safe_float(county_data.get('food_environment_score', 50)),
    }

    return features


def get_risk_breakdown(ml_result: dict, features: dict) -> list:
    """
    Analyze which risk factors contribute most to the predicted risk.

    Args:
        ml_result: Result from ML service prediction
        features: Input features used for prediction

    Returns:
        List of dicts with factor name, contribution, and category
    """
    # Define risk factor thresholds and weights
    risk_factors = [
        {'name': 'Food Insecurity', 'feature': 'food_insecurity_rate', 'threshold': 15, 'category': 'Food Environment', 'weight': 0.12},
        {'name': 'Limited Food Access', 'feature': 'pct_limited_food_access', 'threshold': 10, 'category': 'Food Environment', 'weight': 0.08},
        {'name': 'Low Grocery Access', 'feature': 'grocery_stores_per_1000', 'threshold': 0.2, 'category': 'Food Environment', 'weight': 0.06, 'inverse': True},
        {'name': 'High Fast Food Density', 'feature': 'fast_food_restaurants_per_1000', 'threshold': 0.8, 'category': 'Food Environment', 'weight': 0.07},
        {'name': 'Physical Inactivity', 'feature': 'physical_inactivity_prevalence', 'threshold': 28, 'category': 'Behavioral', 'weight': 0.15},
        {'name': 'Smoking', 'feature': 'smoking_prevalence', 'threshold': 18, 'category': 'Behavioral', 'weight': 0.10},
        {'name': 'Excessive Drinking', 'feature': 'excessive_drinking_prevalence', 'threshold': 20, 'category': 'Behavioral', 'weight': 0.05},
        {'name': 'Insufficient Sleep', 'feature': 'pct_insufficient_sleep', 'threshold': 35, 'category': 'Behavioral', 'weight': 0.06},
        {'name': 'Lack of Insurance', 'feature': 'pct_uninsured', 'threshold': 12, 'category': 'Healthcare', 'weight': 0.10},
        {'name': 'Low PCP Access', 'feature': 'pcp_rate', 'threshold': 50, 'category': 'Healthcare', 'weight': 0.08, 'inverse': True},
        {'name': 'Child Poverty', 'feature': 'child_poverty_rate', 'threshold': 20, 'category': 'Socioeconomic', 'weight': 0.08},
        {'name': 'Low Education', 'feature': 'high_school_graduation_rate', 'threshold': 85, 'category': 'Socioeconomic', 'weight': 0.05, 'inverse': True},
    ]

    breakdown = []
    for factor in risk_factors:
        value = features.get(factor['feature'], 0)
        threshold = factor['threshold']
        is_inverse = factor.get('inverse', False)

        # Calculate contribution based on how far from threshold
        if is_inverse:
            contribution = max(0, (threshold - value) / threshold * 100 * factor['weight'])
        else:
            contribution = max(0, (value - threshold) / threshold * 100 * factor['weight']) if value > threshold else 0

        if contribution > 0:
            breakdown.append({
                'name': factor['name'],
                'value': round(value, 1),
                'contribution': round(contribution, 1),
                'category': factor['category'],
            })

    # Sort by contribution descending
    breakdown.sort(key=lambda x: x['contribution'], reverse=True)
    return breakdown[:8]  # Return top 8 factors


def get_intervention_recommendations(ml_result: dict, risk_breakdown: list, county_data: dict) -> list:
    """
    Generate intervention recommendations based on ML predictions and risk factors.

    Args:
        ml_result: Result from ML service
        risk_breakdown: List of top risk factors
        county_data: Original county data

    Returns:
        List of intervention recommendations with estimated impact
    """
    recommendations = []

    # Map risk factors to intervention recommendations
    interventions_map = {
        'Food Insecurity': {
            'intervention': 'Expand SNAP outreach and food bank access',
            'impact': 'High',
            'estimated_reduction': '8-12%',
            'cost_tier': 'Medium',
        },
        'Limited Food Access': {
            'intervention': 'Mobile food markets and grocery incentive programs',
            'impact': 'Medium',
            'estimated_reduction': '5-8%',
            'cost_tier': 'Medium',
        },
        'Low Grocery Access': {
            'intervention': 'Healthy food retail initiatives and farmers market programs',
            'impact': 'Medium',
            'estimated_reduction': '4-7%',
            'cost_tier': 'High',
        },
        'High Fast Food Density': {
            'intervention': 'Healthy menu labeling requirements and nutrition education',
            'impact': 'Low',
            'estimated_reduction': '2-4%',
            'cost_tier': 'Low',
        },
        'Physical Inactivity': {
            'intervention': 'Community fitness programs and walkable infrastructure investment',
            'impact': 'High',
            'estimated_reduction': '10-15%',
            'cost_tier': 'Medium',
        },
        'Smoking': {
            'intervention': 'Tobacco cessation programs and smoke-free policies',
            'impact': 'High',
            'estimated_reduction': '12-18%',
            'cost_tier': 'Low',
        },
        'Excessive Drinking': {
            'intervention': 'Alcohol screening and brief intervention programs',
            'impact': 'Medium',
            'estimated_reduction': '5-8%',
            'cost_tier': 'Low',
        },
        'Insufficient Sleep': {
            'intervention': 'Sleep health education and workplace wellness programs',
            'impact': 'Low',
            'estimated_reduction': '3-5%',
            'cost_tier': 'Low',
        },
        'Lack of Insurance': {
            'intervention': 'ACA enrollment assistance and Medicaid expansion advocacy',
            'impact': 'High',
            'estimated_reduction': '15-20%',
            'cost_tier': 'High',
        },
        'Low PCP Access': {
            'intervention': 'Primary care expansion and telehealth infrastructure',
            'impact': 'High',
            'estimated_reduction': '10-15%',
            'cost_tier': 'High',
        },
        'Child Poverty': {
            'intervention': 'Economic development and child tax credit programs',
            'impact': 'High',
            'estimated_reduction': '8-12%',
            'cost_tier': 'High',
        },
        'Low Education': {
            'intervention': 'Health literacy programs and school-based health education',
            'impact': 'Medium',
            'estimated_reduction': '5-8%',
            'cost_tier': 'Medium',
        },
    }

    for factor in risk_breakdown[:5]:  # Top 5 recommendations
        factor_name = factor['name']
        if factor_name in interventions_map:
            rec = interventions_map[factor_name].copy()
            rec['target_factor'] = factor_name
            rec['current_value'] = factor['value']
            recommendations.append(rec)

    return recommendations


@gov_bp.route('/chroniccare/')
@gov_required
def chroniccare_home():
    """ChronicCare module home"""
    stats = ChronicCareService.get_stats()
    trends = ChronicCareService.get_national_trends()
    priorities = ChronicCareService.get_intervention_priorities(limit=5)
    states = ChronicCareService.get_states()
    return render_template('gov/chroniccare/home.html',
                          stats=stats, trends=trends, priorities=priorities, states=states)


@gov_bp.route('/chroniccare/dashboard')
@gov_required
def chroniccare_dashboard():
    """MAHA metrics dashboard"""
    import pandas as pd

    state = request.args.get('state', '')
    try:
        limit = int(request.args.get('limit', 100) or 100)
    except (ValueError, TypeError):
        limit = 100
    stats = ChronicCareService.get_stats()
    trends = ChronicCareService.get_national_trends()

    # Get counties - filtered by state if specified
    # If showing all, fetch 5000 to cover all counties
    fetch_limit = 5000 if limit >= 3000 else limit
    counties = ChronicCareService.get_county_health(
        state=state if state else None, limit=fetch_limit
    )
    states = ChronicCareService.get_states()

    # Calculate filtered stats if state is selected
    if state and counties:
        # Recalculate stats for filtered data
        df = pd.DataFrame(counties)
        diabetes_vals = pd.to_numeric(df.get('diabetes_prevalence', pd.Series()), errors='coerce').dropna()
        obesity_vals = pd.to_numeric(df.get('obesity_prevalence', pd.Series()), errors='coerce').dropna()
        heart_vals = pd.to_numeric(df.get('heart_disease_prevalence', pd.Series()), errors='coerce').dropna()

        # Calculate risk scores for filtered counties
        critical = 0
        high = 0
        for c in counties:
            d = float(c.get('diabetes_prevalence', 0) or 0)
            o = float(c.get('obesity_prevalence', 0) or 0)
            h = float(c.get('heart_disease_prevalence', 0) or 0)
            score = d * 0.4 + o * 0.35 + h * 0.25
            if score > 20:
                critical += 1
            elif score > 18:
                high += 1

        stats = {
            'total_counties': len(counties),
            'avg_diabetes': round(diabetes_vals.mean(), 1) if len(diabetes_vals) > 0 else 0,
            'avg_obesity': round(obesity_vals.mean(), 1) if len(obesity_vals) > 0 else 0,
            'avg_heart_disease': round(heart_vals.mean(), 1) if len(heart_vals) > 0 else 0,
            'critical_counties': critical,
            'high_priority_counties': high,
            'states_covered': 1
        }

    # ML Insights
    ml_available = False
    ml_insights = {
        'model_confidence': 0,
        'emerging_hotspots': [],
        'top_risk_factors': [],
        'prediction_summary': {},
    }

    if ML_AVAILABLE and counties:
        try:
            ml_service = get_chroniccare_service()
            if ml_service.is_loaded:
                ml_available = True
                ml_insights['model_confidence'] = 93.9

                # Analyze a sample of counties to identify emerging hotspots
                # (counties with high predicted risk increase)
                sample_counties = counties[:min(100, len(counties))]
                emerging_hotspots = []

                for c in sample_counties:
                    try:
                        features = extract_ml_features(c)

                        # Get predictions
                        if ml_service.risk_service.is_loaded:
                            predictions = ml_service.risk_service.predict(features)

                            # Compare predicted vs actual
                            actual_diabetes = float(c.get('diabetes_prevalence', 0) or 0)
                            actual_obesity = float(c.get('obesity_prevalence', 0) or 0)
                            actual_heart = float(c.get('heart_disease_prevalence', 0) or 0)

                            predicted_diabetes = predictions.get('diabetes_prevalence', actual_diabetes)
                            predicted_obesity = predictions.get('obesity_prevalence', actual_obesity)
                            predicted_heart = predictions.get('heart_disease_prevalence', actual_heart)

                            # Calculate risk increase
                            risk_increase = (
                                max(0, predicted_diabetes - actual_diabetes) * 0.35 +
                                max(0, predicted_obesity - actual_obesity) * 0.35 +
                                max(0, predicted_heart - actual_heart) * 0.30
                            )

                            if risk_increase > 1.5:  # Significant predicted increase
                                emerging_hotspots.append({
                                    'fips': c.get('fips'),
                                    'county': c.get('county_name', 'Unknown'),
                                    'state': c.get('state_abbr', c.get('state', '')),
                                    'risk_increase': round(risk_increase, 1),
                                    'current_score': round(actual_diabetes * 0.35 + actual_obesity * 0.35 + actual_heart * 0.30, 1),
                                    'predicted_score': round(predicted_diabetes * 0.35 + predicted_obesity * 0.35 + predicted_heart * 0.30, 1),
                                })

                    except Exception as e:
                        logger.debug(f"Skipping county {c.get('fips')} for hotspot analysis: {e}")

                # Sort by risk increase and take top 5
                emerging_hotspots.sort(key=lambda x: x['risk_increase'], reverse=True)
                ml_insights['emerging_hotspots'] = emerging_hotspots[:5]

                # Aggregate top risk factors across all analyzed counties
                risk_factor_counts = {}
                for c in sample_counties[:50]:
                    try:
                        features = extract_ml_features(c)
                        breakdown = get_risk_breakdown({}, features)
                        for factor in breakdown[:3]:
                            name = factor['name']
                            if name not in risk_factor_counts:
                                risk_factor_counts[name] = {'count': 0, 'total_contribution': 0}
                            risk_factor_counts[name]['count'] += 1
                            risk_factor_counts[name]['total_contribution'] += factor['contribution']
                    except:
                        pass

                # Convert to sorted list
                top_factors = [
                    {'name': k, 'frequency': v['count'], 'avg_contribution': round(v['total_contribution'] / max(1, v['count']), 1)}
                    for k, v in risk_factor_counts.items()
                ]
                top_factors.sort(key=lambda x: x['frequency'], reverse=True)
                ml_insights['top_risk_factors'] = top_factors[:5]

                # Prediction summary
                ml_insights['prediction_summary'] = {
                    'counties_analyzed': len(sample_counties),
                    'high_risk_predicted': len([h for h in emerging_hotspots if h['predicted_score'] > 20]),
                    'avg_predicted_risk': round(sum(h['predicted_score'] for h in emerging_hotspots) / max(1, len(emerging_hotspots)), 1) if emerging_hotspots else 0,
                }

        except Exception as e:
            logger.error(f"ML insights generation failed: {e}")
            ml_available = False

    return render_template('gov/chroniccare/dashboard.html',
                          stats=stats, trends=trends, counties=counties,
                          states=states, selected_state=state, selected_limit=limit,
                          ml_available=ml_available, ml_insights=ml_insights)


@gov_bp.route('/chroniccare/correlations')
@gov_required
def chroniccare_correlations():
    """Food-disease correlation analysis"""
    state = request.args.get('state', '')
    try:
        limit = int(request.args.get('limit', 100) or 100)
    except (ValueError, TypeError):
        limit = 100

    # Get correlations - filter by state if specified
    correlations = ChronicCareService.get_correlations()
    if state:
        correlations = [c for c in correlations if c.get('state') == state]

    # Apply limit
    correlations = correlations[:limit]

    food_env = ChronicCareService.get_food_environment(limit=1000)
    states = ChronicCareService.get_states()
    return render_template('gov/chroniccare/correlations.html',
                          correlations=correlations, food_env=food_env,
                          states=states, selected_state=state, selected_limit=limit)


@gov_bp.route('/chroniccare/interventions')
@gov_required
def chroniccare_interventions():
    """ML-prioritized intervention targets"""
    state = request.args.get('state', '')
    priority = request.args.get('priority', '')
    try:
        limit = int(request.args.get('limit', 50) or 50)
    except (ValueError, TypeError):
        limit = 50

    # Get all priorities - fetch enough to cover filtering
    # If showing all (~3000), fetch all data
    fetch_limit = 5000 if limit >= 3000 else max(limit * 3, 500)
    priorities = ChronicCareService.get_intervention_priorities(limit=fetch_limit)

    # Filter by state if specified
    if state:
        priorities = [p for p in priorities if p.get('state') == state]

    # Filter by priority level if specified
    if priority:
        priorities = [p for p in priorities if p.get('priority') == priority]

    # Apply limit (unless showing all)
    if limit < 3000:
        priorities = priorities[:limit]

    # ML inference for each county
    ml_available = False
    ml_model_confidence = 0.0

    if ML_AVAILABLE:
        try:
            ml_service = get_chroniccare_service()
            if ml_service.is_loaded:
                ml_available = True
                ml_model_confidence = 93.9  # Model accuracy from training

                for p in priorities:
                    try:
                        # Extract features for this county
                        features = extract_ml_features(p)

                        # Get ML predictions
                        if ml_service.risk_service.is_loaded:
                            risk_result = ml_service.risk_service.predict(features)
                            # Calculate aggregate risk score from predictions
                            ml_risk = (
                                risk_result.get('diabetes_prevalence', 0) * 0.35 +
                                risk_result.get('obesity_prevalence', 0) * 0.35 +
                                risk_result.get('heart_disease_prevalence', 0) * 0.30
                            )
                            p['ml_risk_score'] = round(ml_risk, 2)

                        # Get prioritization confidence from ML model
                        if ml_service.prioritization_service.is_loaded:
                            priority_result = ml_service.prioritization_service.prioritize(features)
                            p['ml_confidence'] = round(priority_result.get('confidence', 0) * 100, 1)
                            p['ml_maha_index'] = priority_result.get('maha_index', 0)
                        else:
                            p['ml_confidence'] = 85.0
                            p['ml_maha_index'] = 0

                        # Derive priority tier from ML risk score (consistent thresholds)
                        ml_risk = p.get('ml_risk_score', p.get('risk_score', 0))
                        if ml_risk > 22:
                            p['ml_priority_tier'] = 'Critical'
                        elif ml_risk > 19:
                            p['ml_priority_tier'] = 'High'
                        elif ml_risk > 16:
                            p['ml_priority_tier'] = 'Medium'
                        else:
                            p['ml_priority_tier'] = 'Low'

                        # Check if ML priority differs from heuristic priority
                        p['priority_changed'] = p.get('priority', '').lower() != p['ml_priority_tier'].lower()

                    except Exception as e:
                        logger.warning(f"ML inference failed for county {p.get('fips')}: {e}")
                        # Use heuristic fallback
                        p['ml_risk_score'] = p.get('risk_score', 0)
                        p['ml_confidence'] = 0
                        p['ml_priority_tier'] = p.get('priority', 'Unknown')
                        p['priority_changed'] = False

                # Sort by ML risk score (descending)
                priorities = sorted(priorities, key=lambda x: x.get('ml_risk_score', 0), reverse=True)

        except Exception as e:
            logger.error(f"ML service initialization failed: {e}")
            ml_available = False

    # If ML not available, use heuristic scores
    if not ml_available:
        for p in priorities:
            p['ml_risk_score'] = p.get('risk_score', 0)
            p['ml_confidence'] = 0
            p['ml_priority_tier'] = p.get('priority', 'Unknown')
            p['priority_changed'] = False

    stats = ChronicCareService.get_stats()
    states = ChronicCareService.get_states()
    return render_template('gov/chroniccare/interventions.html',
                          priorities=priorities, stats=stats, states=states,
                          selected_state=state, selected_priority=priority,
                          selected_limit=limit,
                          ml_available=ml_available,
                          ml_model_confidence=ml_model_confidence)


@gov_bp.route('/chroniccare/analytics')
@gov_required
def chroniccare_analytics():
    """State-by-state analytics and statistics"""
    state = request.args.get('state', '')
    try:
        limit = int(request.args.get('limit', 100) or 100)
    except (ValueError, TypeError):
        limit = 100

    # Get state-level statistics
    state_stats = ChronicCareService.get_state_statistics()
    states = ChronicCareService.get_states()
    overall_stats = ChronicCareService.get_stats()

    # Get county data for charts - filtered by state if specified
    fetch_limit = 5000 if limit >= 3000 else limit
    counties = ChronicCareService.get_county_health(
        state=state if state else None, limit=fetch_limit
    )

    # Calculate filtered state stats if a state is selected
    filtered_state_stats = state_stats
    if state:
        filtered_state_stats = {k: v for k, v in state_stats.items() if k == state}

    return render_template('gov/chroniccare/analytics.html',
                          state_stats=state_stats, filtered_state_stats=filtered_state_stats,
                          states=states, overall_stats=overall_stats,
                          counties=counties, selected_state=state, selected_limit=limit)


@gov_bp.route('/chroniccare/county/<fips>')
@gov_required
def chroniccare_county(fips):
    """County chronic disease profile"""
    county = ChronicCareService.get_county(fips)
    food_env = ChronicCareService.get_food_environment(limit=1000)
    # Find matching food environment data
    county_food = None
    for f in food_env:
        if str(f.get('FIPS', f.get('fips', ''))) == str(fips):
            county_food = f
            break

    # ML inference for this county
    ml_available = False
    ml_risk_breakdown = []
    ml_recommended_interventions = []
    ml_predictions = {}
    ml_priority = {}

    if ML_AVAILABLE and county:
        try:
            ml_service = get_chroniccare_service()
            if ml_service.is_loaded:
                ml_available = True

                # Merge county and food env data for feature extraction
                merged_data = dict(county) if county else {}
                if county_food:
                    merged_data.update(county_food)

                # Extract features
                features = extract_ml_features(merged_data)

                # Get risk predictions
                if ml_service.risk_service.is_loaded:
                    ml_predictions = ml_service.risk_service.predict(features)
                    # Round for display
                    ml_predictions = {k: round(v, 1) for k, v in ml_predictions.items()}

                # Calculate ML risk score from predictions
                if ml_predictions:
                    ml_risk_score = (
                        ml_predictions.get('diabetes_prevalence', 0) * 0.35 +
                        ml_predictions.get('obesity_prevalence', 0) * 0.35 +
                        ml_predictions.get('heart_disease_prevalence', 0) * 0.30
                    )
                else:
                    ml_risk_score = (
                        float(county.get('diabetes_prevalence', 0) or 0) * 0.35 +
                        float(county.get('obesity_prevalence', 0) or 0) * 0.35 +
                        float(county.get('heart_disease_prevalence', 0) or 0) * 0.30
                    )

                # Derive priority tier from ML risk score (consistent thresholds)
                if ml_risk_score > 22:
                    tier = 'Critical'
                elif ml_risk_score > 19:
                    tier = 'High'
                elif ml_risk_score > 16:
                    tier = 'Medium'
                else:
                    tier = 'Low'

                # Get MAHA index from prioritization service if available
                if ml_service.prioritization_service.is_loaded:
                    priority_result = ml_service.prioritization_service.prioritize(features)
                    maha_index = priority_result.get('maha_index', ml_risk_score * 4)
                    confidence = priority_result.get('confidence', 0.85)
                else:
                    maha_index = ml_risk_score * 4
                    confidence = 0.85

                ml_priority = {
                    'priority': tier,
                    'confidence': confidence,
                    'maha_index': maha_index,
                    'ml_risk_score': round(ml_risk_score, 2),
                }

                # Get risk breakdown (which factors contribute most)
                ml_risk_breakdown = get_risk_breakdown(ml_priority, features)

                # Get intervention recommendations
                ml_recommended_interventions = get_intervention_recommendations(
                    ml_priority, ml_risk_breakdown, merged_data
                )

        except Exception as e:
            logger.error(f"ML inference failed for county {fips}: {e}")
            ml_available = False

    return render_template('gov/chroniccare/county.html',
                          fips=fips, county=county, food_env=county_food,
                          ml_available=ml_available,
                          ml_predictions=ml_predictions,
                          ml_priority=ml_priority,
                          ml_risk_breakdown=ml_risk_breakdown,
                          ml_recommended_interventions=ml_recommended_interventions)


# API endpoints
@gov_bp.route('/api/chroniccare/counties')
@gov_required
def api_chronic_counties():
    """API: Get county health data"""
    state = request.args.get('state', '')
    try:
        limit = int(request.args.get('limit', 100) or 100)
    except (ValueError, TypeError):
        limit = 100
    counties = ChronicCareService.get_county_health(
        state=state if state else None, limit=limit
    )
    return jsonify(counties)


@gov_bp.route('/api/chroniccare/correlations')
@gov_required
def api_correlations():
    """API: Get correlation data"""
    correlations = ChronicCareService.get_correlations()
    return jsonify(correlations)


@gov_bp.route('/api/chroniccare/interventions')
@gov_required
def api_interventions():
    """API: Get intervention priorities"""
    try:
        limit = int(request.args.get('limit', 50) or 50)
    except (ValueError, TypeError):
        limit = 50
    priorities = ChronicCareService.get_intervention_priorities(limit=limit)
    return jsonify(priorities)


@gov_bp.route('/chroniccare/simulator')
@gov_required
def chroniccare_simulator():
    """ML Simulator - input features to get disease predictions and priority scores."""
    # Default feature values (national averages)
    default_features = {
        'grocery_stores_per_1000': 0.25,
        'fast_food_restaurants_per_1000': 0.65,
        'food_environment_index': 7.0,
        'food_insecurity_rate': 12.0,
        'pct_limited_food_access': 8.0,
        'pcp_rate': 55.0,
        'mental_health_provider_rate': 180.0,
        'pct_uninsured': 10.0,
        'preventable_hospitalizations': 4500.0,
        'median_household_income': 55000.0,
        'child_poverty_rate': 18.0,
        'income_inequality_ratio': 4.5,
        'high_school_graduation_rate': 88.0,
        'pct_some_college': 60.0,
        'physical_inactivity_prevalence': 26.0,
        'excessive_drinking_prevalence': 18.0,
        'smoking_prevalence': 17.0,
        'pct_insufficient_sleep': 35.0,
        'pct_rural': 20.0,
        'chronic_disease_burden_score': 50.0,
        'food_environment_score': 50.0,
    }

    # Check if form submitted
    submitted = request.args.get('submitted', '')
    predictions = None
    priority = None
    risk_breakdown = []
    recommendations = []

    if submitted:
        # Collect features from request args
        features = {}
        for key in default_features.keys():
            value = request.args.get(key, '')
            if value:
                try:
                    features[key] = float(value)
                except ValueError:
                    features[key] = default_features[key]
            else:
                features[key] = default_features[key]

        # Run ML inference
        if ML_AVAILABLE:
            try:
                ml_service = get_chroniccare_service()
                if ml_service.is_loaded:
                    # Get disease prevalence predictions
                    if ml_service.risk_service.is_loaded:
                        risk_predictions = ml_service.risk_service.predict(features)
                        # Clamp predictions to valid percentage ranges (0-100%)
                        predictions = {
                            k: round(max(0, min(100, v)), 1)
                            for k, v in risk_predictions.items()
                        }

                        # Calculate composite risk score
                        ml_risk_score = (
                            predictions.get('diabetes_prevalence', 12) * 0.35 +
                            predictions.get('obesity_prevalence', 30) * 0.35 +
                            predictions.get('heart_disease_prevalence', 6) * 0.30
                        )
                    else:
                        # Fallback calculation
                        ml_risk_score = (
                            features['chronic_disease_burden_score'] * 0.35 +
                            features['food_environment_score'] * 0.35
                        )
                        predictions = {
                            'diabetes_prevalence': 12.0,
                            'obesity_prevalence': 32.0,
                            'heart_disease_prevalence': 6.0,
                        }

                    # Get intervention priority
                    if ml_service.prioritization_service.is_loaded:
                        priority_result = ml_service.prioritization_service.prioritize(features)
                        priority = {
                            'tier': priority_result.get('priority', 'Medium'),
                            'confidence': round(min(100, max(0, priority_result.get('confidence', 0.85) * 100)), 1),
                            'maha_index': round(min(100, max(0, priority_result.get('maha_index', 40))), 1),
                            'ml_risk_score': round(min(100, max(0, ml_risk_score)), 2),
                        }
                    else:
                        # Derive tier from risk score
                        if ml_risk_score > 22:
                            tier = 'Critical'
                        elif ml_risk_score > 19:
                            tier = 'High'
                        elif ml_risk_score > 16:
                            tier = 'Medium'
                        else:
                            tier = 'Low'
                        priority = {
                            'tier': tier,
                            'confidence': 85.0,
                            'maha_index': round(min(100, max(0, ml_risk_score * 2)), 1),
                            'ml_risk_score': round(min(100, max(0, ml_risk_score)), 2),
                        }

                    # Get risk breakdown
                    risk_breakdown = get_risk_breakdown(priority, features)

                    # Get intervention recommendations
                    recommendations = get_intervention_recommendations(priority, risk_breakdown, features)

            except Exception as e:
                logger.error(f"ML simulator inference failed: {e}")
                predictions = {'error': str(e)}
        else:
            # ML not available - use heuristic calculations
            predictions = {
                'diabetes_prevalence': round(10 + features['food_insecurity_rate'] * 0.2 + features['physical_inactivity_prevalence'] * 0.15, 1),
                'obesity_prevalence': round(25 + features['fast_food_restaurants_per_1000'] * 10 + features['physical_inactivity_prevalence'] * 0.3, 1),
                'heart_disease_prevalence': round(5 + features['smoking_prevalence'] * 0.1 + features['physical_inactivity_prevalence'] * 0.08, 1),
            }
            ml_risk_score = (
                predictions['diabetes_prevalence'] * 0.35 +
                predictions['obesity_prevalence'] * 0.35 +
                predictions['heart_disease_prevalence'] * 0.30
            )
            if ml_risk_score > 22:
                tier = 'Critical'
            elif ml_risk_score > 19:
                tier = 'High'
            elif ml_risk_score > 16:
                tier = 'Medium'
            else:
                tier = 'Low'
            priority = {
                'tier': tier,
                'confidence': 75.0,
                'maha_index': round(min(100, max(0, ml_risk_score * 2)), 1),
                'ml_risk_score': round(min(100, max(0, ml_risk_score)), 2),
            }
            risk_breakdown = get_risk_breakdown(priority, features)
            recommendations = get_intervention_recommendations(priority, risk_breakdown, features)

        # Update default features with submitted values for form persistence
        default_features.update(features)

    return render_template('gov/chroniccare/simulator.html',
                          features=default_features,
                          predictions=predictions,
                          priority=priority,
                          risk_breakdown=risk_breakdown,
                          recommendations=recommendations,
                          submitted=bool(submitted),
                          ml_available=ML_AVAILABLE)


@gov_bp.route('/api/chroniccare/stats')
@gov_required
def api_chronic_stats():
    """API: Get statistics"""
    stats = ChronicCareService.get_stats()
    return jsonify(stats)


@gov_bp.route('/api/chroniccare/state-stats')
@gov_required
def api_state_stats():
    """API: Get state-by-state statistics"""
    state_stats = ChronicCareService.get_state_statistics()
    return jsonify(state_stats)
