"""
Government RuralAccess Routes
Healthcare access mapping (gov-only module)
"""
from flask import render_template, request, jsonify
from . import gov_bp, gov_required
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
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

    hpsas = RuralAccessService.get_hpsa_designations(
        state=state if state else None,
        discipline=discipline if discipline else None,
        limit=500
    )
    map_data = RuralAccessService.get_shortage_map_data()
    states = RuralAccessService.get_states()

    return render_template('gov/ruralaccess/map.html',
                          hpsas=hpsas, map_data=map_data, states=states,
                          selected_state=state, selected_discipline=discipline)


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
    """API: Get HPSA designations"""
    state = request.args.get('state', '')
    discipline = request.args.get('discipline', '')
    limit = int(request.args.get('limit', 100))
    hpsas = RuralAccessService.get_hpsa_designations(
        state=state if state else None,
        discipline=discipline if discipline else None,
        limit=limit
    )
    return jsonify(hpsas)


@gov_bp.route('/api/ruralaccess/counties')
@gov_required
def api_counties():
    """API: Get counties"""
    state = request.args.get('state', '')
    limit = int(request.args.get('limit', 100))
    counties = RuralAccessService.get_counties(state=state if state else None, limit=limit)
    return jsonify(counties)


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
