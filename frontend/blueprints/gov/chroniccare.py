"""
Government ChronicCare Routes
Chronic disease management (gov-only module)
"""
from flask import render_template, request, jsonify
from . import gov_bp, gov_required
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from services.chroniccare import ChronicCareService


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
    state = request.args.get('state', '')
    stats = ChronicCareService.get_stats()
    trends = ChronicCareService.get_national_trends()
    counties = ChronicCareService.get_county_health(
        state=state if state else None, limit=100
    )
    states = ChronicCareService.get_states()
    return render_template('gov/chroniccare/dashboard.html',
                          stats=stats, trends=trends, counties=counties,
                          states=states, selected_state=state)


@gov_bp.route('/chroniccare/correlations')
@gov_required
def chroniccare_correlations():
    """Food-disease correlation analysis"""
    correlations = ChronicCareService.get_correlations()
    food_env = ChronicCareService.get_food_environment(limit=100)
    return render_template('gov/chroniccare/correlations.html',
                          correlations=correlations, food_env=food_env)


@gov_bp.route('/chroniccare/interventions')
@gov_required
def chroniccare_interventions():
    """ML-prioritized intervention targets"""
    priorities = ChronicCareService.get_intervention_priorities(limit=50)
    stats = ChronicCareService.get_stats()
    states = ChronicCareService.get_states()
    return render_template('gov/chroniccare/interventions.html',
                          priorities=priorities, stats=stats, states=states)


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
    return render_template('gov/chroniccare/county.html',
                          fips=fips, county=county, food_env=county_food)


# API endpoints
@gov_bp.route('/api/chroniccare/counties')
@gov_required
def api_chronic_counties():
    """API: Get county health data"""
    state = request.args.get('state', '')
    limit = int(request.args.get('limit', 100))
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
    limit = int(request.args.get('limit', 50))
    priorities = ChronicCareService.get_intervention_priorities(limit=limit)
    return jsonify(priorities)


@gov_bp.route('/api/chroniccare/stats')
@gov_required
def api_chronic_stats():
    """API: Get statistics"""
    stats = ChronicCareService.get_stats()
    return jsonify(stats)
