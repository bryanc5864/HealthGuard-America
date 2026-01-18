"""
Public PriceVision Routes
Hospital price transparency for consumers
"""
from flask import render_template, request, jsonify
from . import public_bp
import csv
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent.parent.parent / 'data/raw'


@public_bp.route('/pricevision/')
def pricevision_home():
    """PriceVision module home"""
    return render_template('public/pricevision/home.html')


@public_bp.route('/pricevision/search')
def pricevision_search():
    """Search for procedures"""
    query = request.args.get('q', '')
    return render_template('public/pricevision/search.html', query=query)


@public_bp.route('/pricevision/compare')
def pricevision_compare():
    """Compare prices across hospitals"""
    procedure = request.args.get('procedure', '')
    return render_template('public/pricevision/compare.html', procedure=procedure)


@public_bp.route('/pricevision/hospital/<npi>')
def pricevision_hospital(npi):
    """View single hospital details"""
    hospital = get_hospital_by_npi(npi)
    return render_template('public/pricevision/hospital.html', hospital=hospital, npi=npi)


def get_hospital_by_npi(npi):
    """Get hospital info by NPI"""
    urls_file = DATA_DIR / 'pricevision/hospital_mrf_urls.csv'
    if urls_file.exists():
        with open(urls_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('npi', '').replace('.0', '') == npi:
                    return row
    return {'npi': npi, 'hospital_name': f'Hospital {npi}'}
