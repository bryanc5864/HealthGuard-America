#!/usr/bin/env python3
"""
HealthGuard America - Dual Portal Application
Government Portal: All 5 modules (requires authentication)
Public Portal: PriceVision, DrugWatch, FoodScore (no auth required)

Run: python frontend/app.py
Then open: http://localhost:5000
"""

import sys
from pathlib import Path

# Add frontend directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from flask import Flask, render_template, jsonify, send_from_directory, request
import csv
import json
import os
from collections import defaultdict
from config import Config, DevelopmentConfig

app = Flask(__name__)
app.config.from_object(DevelopmentConfig)

# Register blueprints
from blueprints.public import public_bp
from blueprints.gov import gov_bp

app.register_blueprint(public_bp)
app.register_blueprint(gov_bp)


@app.after_request
def add_cache_headers(response):
    """Add caching and security headers"""
    if 'static' in request.path:
        if any(request.path.endswith(ext) for ext in ('.webp', '.jpg', '.png', '.avif', '.woff2')):
            response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
        elif request.path.endswith(('.css', '.js')):
            response.headers['Cache-Control'] = 'public, max-age=604800'
        else:
            response.headers['Cache-Control'] = 'public, max-age=86400'
    elif request.path.startswith('/api/'):
        response.headers['Cache-Control'] = 'public, max-age=300'
    if response.content_type and ('text/' in response.content_type or
        'application/json' in response.content_type or
        'application/javascript' in response.content_type):
        response.headers['X-Content-Type-Options'] = 'nosniff'
    return response


@app.context_processor
def inject_common_data():
    """Inject commonly used data into all templates"""
    return {
        'current_year': 2026,
        'app_version': '1.0',
        'asset_version': app.config.get('DATA_VERSION', 'v1'),
    }


# Data paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / 'data/raw'

# Cache for data
_cache = {}


def get_data_inventory():
    """Get inventory of all available data"""
    if 'inventory' in _cache:
        return _cache['inventory']

    inventory = {
        'drugwatch': {
            'name': 'DrugWatch',
            'description': 'Drug price comparison (US vs international)',
            'datasets': []
        },
        'foodscore': {
            'name': 'FoodScore',
            'description': 'Food product health scoring',
            'datasets': []
        },
        'ruralaccess': {
            'name': 'RuralAccess',
            'description': 'Healthcare desert mapping',
            'datasets': []
        },
        'pricevision': {
            'name': 'PriceVision',
            'description': 'Hospital price transparency',
            'datasets': []
        },
        'chroniccare': {
            'name': 'ChronicCare',
            'description': 'Chronic disease management',
            'datasets': []
        }
    }

    # Scan each module directory
    for module in inventory.keys():
        module_dir = DATA_DIR / module
        if module_dir.exists():
            for f in module_dir.rglob('*'):
                if f.is_file() and f.suffix in ['.csv', '.json', '.txt', '.xlsx', '.zip', '.gz', '.parquet']:
                    size = f.stat().st_size
                    inventory[module]['datasets'].append({
                        'name': f.name,
                        'path': str(f.relative_to(DATA_DIR)),
                        'size': size,
                        'size_human': format_size(size),
                        'type': f.suffix
                    })

    # Calculate totals
    for module in inventory:
        datasets = inventory[module]['datasets']
        inventory[module]['total_files'] = len(datasets)
        inventory[module]['total_size'] = sum(d['size'] for d in datasets)
        inventory[module]['total_size_human'] = format_size(inventory[module]['total_size'])

    _cache['inventory'] = inventory
    return inventory


def format_size(size):
    """Format bytes to human readable"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} PB"


def get_hospitals():
    """Get list of hospitals with MRF data"""
    if 'hospitals' in _cache:
        return _cache['hospitals']

    hospitals = []
    mrfs_dir = DATA_DIR / 'pricevision/mrfs'
    urls_file = DATA_DIR / 'pricevision/hospital_mrf_urls.csv'

    # Load URL database
    url_map = {}
    if urls_file.exists():
        with open(urls_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                npi = row.get('npi', '').replace('.0', '')
                if npi:
                    url_map[npi] = row

    # Get downloaded files
    if mrfs_dir.exists():
        for f in mrfs_dir.glob('*'):
            if f.is_file():
                npi = f.stem.split('_')[0]
                info = url_map.get(npi, {})
                hospitals.append({
                    'npi': npi,
                    'name': info.get('hospital_name', f'Hospital {npi}'),
                    'state': info.get('state', ''),
                    'city': info.get('city', ''),
                    'file': f.name,
                    'size': f.stat().st_size,
                    'size_human': format_size(f.stat().st_size),
                    'type': f.suffix,
                    'url': info.get('mrf_url', '')
                })

    hospitals.sort(key=lambda x: x['name'])
    _cache['hospitals'] = hospitals
    return hospitals


def get_mrf_urls():
    """Get all MRF URLs"""
    if 'urls' in _cache:
        return _cache['urls']

    urls = []
    urls_file = DATA_DIR / 'pricevision/hospital_mrf_urls.csv'

    if urls_file.exists():
        with open(urls_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                urls.append({
                    'hospital_name': row.get('hospital_name', ''),
                    'state': row.get('state', ''),
                    'npi': row.get('npi', '').replace('.0', ''),
                    'url': row.get('mrf_url', ''),
                    'source': row.get('source', '')
                })

    urls.sort(key=lambda x: x['hospital_name'])
    _cache['urls'] = urls
    return urls


# Routes

@app.route('/')
def landing():
    """Landing page with portal selector"""
    return render_template('landing.html', modules=Config.MODULES)


# Legacy routes (redirect to new structure)
@app.route('/dashboard')
def dashboard():
    """Legacy dashboard - now shows inventory"""
    inventory = get_data_inventory()
    hospitals = get_hospitals()
    urls = get_mrf_urls()

    stats = {
        'total_files': sum(m['total_files'] for m in inventory.values()),
        'total_size': format_size(sum(m['total_size'] for m in inventory.values())),
        'hospitals_downloaded': len(hospitals),
        'urls_available': len(urls),
        'cms_hospitals': 5421,
        'coverage': f"{len(hospitals)/5421*100:.1f}%"
    }

    return render_template('index.html', inventory=inventory, stats=stats)


@app.route('/module/<module_name>')
def module_view(module_name):
    inventory = get_data_inventory()
    if module_name not in inventory:
        return "Module not found", 404

    module = inventory[module_name]
    return render_template('module.html', module=module, module_name=module_name)


@app.route('/hospitals')
def hospitals_view():
    hospitals = get_hospitals()
    states = sorted(set(h['state'] for h in hospitals if h['state']))
    return render_template('hospitals.html', hospitals=hospitals, states=states)


@app.route('/urls')
def urls_view():
    urls = get_mrf_urls()
    states = sorted(set(u['state'] for u in urls if u['state']))
    return render_template('urls.html', urls=urls, states=states)


# API endpoints
@app.route('/api/inventory')
def api_inventory():
    return jsonify(get_data_inventory())


@app.route('/api/hospitals')
def api_hospitals():
    state = request.args.get('state', '')
    hospitals = get_hospitals()
    if state:
        hospitals = [h for h in hospitals if h['state'] == state]
    return jsonify(hospitals)


@app.route('/api/urls')
def api_urls():
    state = request.args.get('state', '')
    urls = get_mrf_urls()
    if state:
        urls = [u for u in urls if u['state'] == state]
    return jsonify(urls)


_api_stats_cache = {}

@app.route('/api/stats')
def api_stats():
    import time as _time
    now = _time.time()
    if 'data' in _api_stats_cache and now - _api_stats_cache.get('ts', 0) < 300:
        return jsonify(_api_stats_cache['data'])

    inventory = get_data_inventory()
    hospitals = get_hospitals()
    urls = get_mrf_urls()

    result = {
        'modules': {name: {'files': m['total_files'], 'size': m['total_size_human']}
                   for name, m in inventory.items()},
        'hospitals_downloaded': len(hospitals),
        'urls_available': len(urls),
        'cms_hospitals': 5421,
        'coverage_percent': round(len(hospitals)/5421*100, 1)
    }
    _api_stats_cache['data'] = result
    _api_stats_cache['ts'] = now
    return jsonify(result)


@app.route('/download/<path:filepath>')
def download_file(filepath):
    """Serve data files for download"""
    return send_from_directory(DATA_DIR, filepath)


def preload_all():
    """Pre-load data and ML models at startup for faster first requests"""
    import threading

    def _load_data():
        try:
            from services import (PriceVisionService, DrugWatchService,
                                  FoodScoreService, RuralAccessService, ChronicCareService)

            print("  Loading PriceVision data...")
            PriceVisionService.get_procedures(limit=1)
            PriceVisionService._ensure_hospital_cache()
            PriceVisionService.get_hospital_info_cache()
            PriceVisionService.get_states()
            PriceVisionService.get_hospitals_with_mrf()

            print("  Loading DrugWatch data...")
            DrugWatchService._get_us_drugs_df()
            DrugWatchService.get_international_prices()

            print("  Loading FoodScore data...")
            FoodScoreService._get_products_df()
            FoodScoreService.get_additives(limit=1)
            FoodScoreService.get_categories()
            FoodScoreService.get_nova_distribution()

            print("  Loading RuralAccess data...")
            RuralAccessService._get_hpsa_df()
            RuralAccessService._get_counties_df()
            RuralAccessService.get_states()

            print("  Loading ChronicCare data...")
            ChronicCareService._get_county_health_df()
            ChronicCareService.get_states()

            print("  All data loaded successfully!")
        except Exception as e:
            print(f"  Warning: Data preload failed: {e}")

    def _load_models():
        try:
            print("  Loading PriceVision ML model...")
            from ml.procedure_encoder.inference import ProcedureMatchingService
            ProcedureMatchingService.load()
            print("  Loading FoodScore ML models...")
            from ml.nova_classifier.inference import NovaClassificationService
            from ml.additive_scorer.inference import AdditiveRiskService
            NovaClassificationService.load()
            AdditiveRiskService.load()
            print("  Loading ChronicCare ML models...")
            from ml.chroniccare.inference import ChronicRiskService, InterventionPrioritizationService
            ChronicRiskService().load()
            InterventionPrioritizationService().load()
            print("  ML models loaded successfully!")
        except Exception as e:
            print(f"  Warning: ML model preload failed: {e}")

    import hashlib
    import time
    app.config['DATA_VERSION'] = hashlib.md5(str(time.time()).encode()).hexdigest()[:8]

    # Load data first (faster, more critical), then ML models
    data_thread = threading.Thread(target=_load_data, daemon=True)
    model_thread = threading.Thread(target=_load_models, daemon=True)
    data_thread.start()
    model_thread.start()


if __name__ == '__main__':
    print("="*60)
    print("HealthGuard America - Dual Portal Application")
    print("="*60)
    print("Pre-loading data and ML models...")
    preload_all()
    print("")
    print("Starting server at http://localhost:5000")
    print("")
    print("Portals:")
    print("  Public:     http://localhost:5000/public/")
    print("  Government: http://localhost:5000/gov/")
    print("")
    print("Press Ctrl+C to stop")
    print("="*60)
    app.run(debug=True, host='0.0.0.0', port=5000)
