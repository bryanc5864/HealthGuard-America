"""
Government RuralAccess Routes
Healthcare access mapping (gov-only module)
"""
from flask import render_template, request, jsonify
from . import gov_bp, gov_required
import sys
from pathlib import Path

# Add project root to path for ML imports
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from services.ruralaccess import RuralAccessService


@gov_bp.route('/ruralaccess/')
@gov_required
def ruralaccess_home():
    """RuralAccess module home"""
    stats = RuralAccessService.get_stats()
    states = RuralAccessService.get_states()
    closures = RuralAccessService.get_hospital_closures(limit=10)
    return render_template('gov/ruralaccess/home.html',
                          stats=stats, states=states, closures=closures)


@gov_bp.route('/ruralaccess/map')
@gov_required
def ruralaccess_map():
    """Interactive healthcare shortage map"""
    state = request.args.get('state', '')
    discipline = request.args.get('discipline', '')
    shortage_level = request.args.get('shortage_level', '')
    rural_status = request.args.get('rural_status', '')
    designation_type = request.args.get('designation_type', '')
    limit_param = request.args.get('limit', '500')

    # Handle 'all' option for unlimited results
    if limit_param.lower() == 'all':
        limit = 0  # 0 means all records
    else:
        try:
            limit = int(limit_param)
        except ValueError:
            limit = 500

    hpsas = RuralAccessService.get_hpsa_designations(
        state=state if state else None,
        discipline=discipline if discipline else None,
        shortage_level=shortage_level if shortage_level else None,
        rural_status=rural_status if rural_status else None,
        designation_type=designation_type if designation_type else None,
        limit=limit
    )

    # Get total count for display
    total_hpsas = RuralAccessService.get_total_hpsa_count(
        state=state if state else None,
        discipline=discipline if discipline else None,
        shortage_level=shortage_level if shortage_level else None,
        rural_status=rural_status if rural_status else None,
        designation_type=designation_type if designation_type else None
    )

    map_data = RuralAccessService.get_shortage_map_data()
    states = RuralAccessService.get_states()
    designation_types = RuralAccessService.get_designation_types()
    rural_statuses = RuralAccessService.get_rural_statuses()

    return render_template('gov/ruralaccess/map.html',
                          hpsas=hpsas, map_data=map_data, states=states,
                          designation_types=designation_types, rural_statuses=rural_statuses,
                          selected_state=state, selected_discipline=discipline,
                          selected_shortage_level=shortage_level, selected_rural_status=rural_status,
                          selected_designation_type=designation_type,
                          selected_limit=limit_param, total_hpsas=total_hpsas)


@gov_bp.route('/ruralaccess/analytics')
@gov_required
def ruralaccess_analytics():
    """Healthcare shortage analytics and insights"""
    stats = RuralAccessService.get_stats()
    analytics = RuralAccessService.get_analytics()
    states = RuralAccessService.get_states()

    return render_template('gov/ruralaccess/analytics.html',
                          stats=stats, analytics=analytics, states=states)


@gov_bp.route('/ruralaccess/county/<fips>')
@gov_required
def ruralaccess_county(fips):
    """County detail view"""
    county = RuralAccessService.get_county(fips)
    hpsas = RuralAccessService.get_hpsa_designations(limit=100)
    # Filter HPSAs for this county
    county_hpsas = [h for h in hpsas if str(h.get('county_fips', '')) == str(fips)]
    fqhcs = RuralAccessService.get_fqhc_locations(limit=100)

    return render_template('gov/ruralaccess/county.html',
                          fips=fips, county=county, hpsas=county_hpsas, fqhcs=fqhcs)


@gov_bp.route('/ruralaccess/hpsa/<hpsa_id>')
@gov_required
def ruralaccess_hpsa(hpsa_id):
    """HPSA designation detail"""
    hpsa = RuralAccessService.get_hpsa(hpsa_id)
    return render_template('gov/ruralaccess/hpsa.html',
                          hpsa_id=hpsa_id, hpsa=hpsa)


# API endpoints
@gov_bp.route('/api/ruralaccess/hpsas')
@gov_required
def api_hpsas():
    """API: Get HPSA designations

    Query params:
        state: Filter by state abbreviation
        discipline: Filter by discipline type
        shortage_level: Filter by severity (critical, high, moderate, low)
        rural_status: Filter by rural status
        designation_type: Filter by designation type
        limit: Number of records (100, 500, 1000, or 'all' for unlimited)
    """
    state = request.args.get('state', '')
    discipline = request.args.get('discipline', '')
    shortage_level = request.args.get('shortage_level', '')
    rural_status = request.args.get('rural_status', '')
    designation_type = request.args.get('designation_type', '')
    limit_param = request.args.get('limit', '100')

    # Handle 'all' option for unlimited results
    if limit_param.lower() == 'all':
        limit = 0  # 0 means all records
    else:
        try:
            limit = int(limit_param)
        except ValueError:
            limit = 100

    hpsas = RuralAccessService.get_hpsa_designations(
        state=state if state else None,
        discipline=discipline if discipline else None,
        shortage_level=shortage_level if shortage_level else None,
        rural_status=rural_status if rural_status else None,
        designation_type=designation_type if designation_type else None,
        limit=limit
    )
    total = RuralAccessService.get_total_hpsa_count(
        state=state if state else None,
        discipline=discipline if discipline else None,
        shortage_level=shortage_level if shortage_level else None,
        rural_status=rural_status if rural_status else None,
        designation_type=designation_type if designation_type else None
    )

    return jsonify({
        'data': hpsas,
        'total': total,
        'returned': len(hpsas),
        'limit': limit_param
    })


@gov_bp.route('/api/ruralaccess/analytics')
@gov_required
def api_analytics():
    """API: Get comprehensive analytics data"""
    analytics = RuralAccessService.get_analytics()
    return jsonify(analytics)


@gov_bp.route('/api/ruralaccess/counties')
@gov_required
def api_counties():
    """API: Get counties

    Query params:
        state: Filter by state abbreviation
        limit: Number of records (100, 500, 1000, or 'all' for unlimited)
    """
    state = request.args.get('state', '')
    limit_param = request.args.get('limit', '100')

    # Handle 'all' option for unlimited results
    if limit_param.lower() == 'all':
        limit = 0  # 0 means all records
    else:
        try:
            limit = int(limit_param)
        except ValueError:
            limit = 100

    counties = RuralAccessService.get_counties(state=state if state else None, limit=limit)
    total = RuralAccessService.get_total_counties_count(state=state if state else None)

    return jsonify({
        'data': counties,
        'total': total,
        'returned': len(counties),
        'limit': limit_param
    })


@gov_bp.route('/api/ruralaccess/map-data')
@gov_required
def api_map_data():
    """API: Get map visualization data"""
    map_data = RuralAccessService.get_shortage_map_data()
    return jsonify(map_data)


@gov_bp.route('/api/ruralaccess/stats')
@gov_required
def api_rural_stats():
    """API: Get statistics"""
    stats = RuralAccessService.get_stats()
    return jsonify(stats)
