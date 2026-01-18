"""
Government RuralAccess Routes
Healthcare access mapping (gov-only module)
"""
from flask import render_template, request
from . import gov_bp, gov_required


@gov_bp.route('/ruralaccess/')
@gov_required
def ruralaccess_home():
    """RuralAccess module home"""
    return render_template('gov/ruralaccess/home.html')


@gov_bp.route('/ruralaccess/map')
@gov_required
def ruralaccess_map():
    """Interactive healthcare shortage map"""
    return render_template('gov/ruralaccess/map.html')


@gov_bp.route('/ruralaccess/county/<fips>')
@gov_required
def ruralaccess_county(fips):
    """County detail view"""
    return render_template('gov/ruralaccess/county.html', fips=fips)


@gov_bp.route('/ruralaccess/hpsa/<hpsa_id>')
@gov_required
def ruralaccess_hpsa(hpsa_id):
    """HPSA designation detail"""
    return render_template('gov/ruralaccess/hpsa.html', hpsa_id=hpsa_id)
