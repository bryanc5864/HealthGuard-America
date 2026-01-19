#!/usr/bin/env python3
"""
Comprehensive Route Testing for HealthGuard Flask Application
Tests all routes for functionality and performance.
"""

import sys
import time
import json
from pathlib import Path

# Add frontend directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app import app

# Test results storage
results = {
    'passed': [],
    'failed': [],
    'slow': [],  # > 3 seconds
    'errors': [],
}

SLOW_THRESHOLD = 3.0  # seconds


def test_route(client, method, path, expected_status=200, description="",
               requires_auth=False, session_data=None, params=None, check_content=None):
    """
    Test a single route and record results.

    Args:
        client: Flask test client
        method: HTTP method (GET, POST, etc.)
        path: URL path to test
        expected_status: Expected HTTP status code
        description: Human-readable description of the route
        requires_auth: Whether route requires gov authentication
        session_data: Dict to add to session before request
        params: Query parameters
        check_content: List of strings that should be in response

    Returns:
        Dict with test results
    """
    result = {
        'path': path,
        'method': method,
        'description': description,
        'expected_status': expected_status,
        'requires_auth': requires_auth,
    }

    try:
        # Set up session if needed
        if session_data:
            with client.session_transaction() as sess:
                for key, value in session_data.items():
                    sess[key] = value

        # Build full URL with params
        url = path
        if params:
            param_str = '&'.join(f"{k}={v}" for k, v in params.items())
            url = f"{path}?{param_str}"

        # Make request and measure time
        start_time = time.time()
        if method == 'GET':
            response = client.get(url)
        elif method == 'POST':
            response = client.post(url)
        else:
            response = client.get(url)
        elapsed = time.time() - start_time

        result['status_code'] = response.status_code
        result['response_time'] = round(elapsed, 3)
        result['content_length'] = len(response.data)

        # Check status code
        status_ok = response.status_code == expected_status
        result['status_ok'] = status_ok

        # Check content
        content_ok = True
        content_errors = []
        if check_content and status_ok:
            response_text = response.data.decode('utf-8', errors='ignore')
            for content_check in check_content:
                if content_check not in response_text:
                    content_ok = False
                    content_errors.append(f"Missing: '{content_check}'")

        result['content_ok'] = content_ok
        result['content_errors'] = content_errors

        # Check for error indicators in response
        if status_ok:
            response_text = response.data.decode('utf-8', errors='ignore')
            if 'Traceback' in response_text or 'Internal Server Error' in response_text:
                result['has_error_content'] = True
                content_ok = False
            else:
                result['has_error_content'] = False

        # Determine pass/fail
        result['passed'] = status_ok and content_ok
        result['is_slow'] = elapsed > SLOW_THRESHOLD

        # Categorize result
        if not result['passed']:
            results['failed'].append(result)
        else:
            results['passed'].append(result)

        if result['is_slow']:
            results['slow'].append(result)

    except Exception as e:
        result['passed'] = False
        result['error'] = str(e)
        result['error_type'] = type(e).__name__
        results['errors'].append(result)
        results['failed'].append(result)

    return result


def print_result(result, verbose=True):
    """Print a single test result."""
    status = "PASS" if result.get('passed') else "FAIL"
    slow = " [SLOW]" if result.get('is_slow') else ""

    if verbose:
        print(f"  [{status}]{slow} {result['method']} {result['path']}")
        print(f"         Status: {result.get('status_code', 'N/A')} (expected {result.get('expected_status', 200)})")
        print(f"         Time: {result.get('response_time', 'N/A')}s")
        if result.get('content_errors'):
            print(f"         Content issues: {result['content_errors']}")
        if result.get('error'):
            print(f"         Error: {result['error']}")
    else:
        time_str = f"{result.get('response_time', 0):.3f}s"
        print(f"  [{status}]{slow} {result['path']} ({time_str})")


def run_all_tests():
    """Run all route tests."""
    print("=" * 70)
    print("HealthGuard Flask Route Testing")
    print("=" * 70)

    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False

    with app.test_client() as client:
        # ============================================================
        # 1. LANDING PAGE AND LEGACY ROUTES
        # ============================================================
        print("\n" + "=" * 70)
        print("1. LANDING PAGE & LEGACY ROUTES")
        print("=" * 70)

        landing_routes = [
            ('GET', '/', 'Landing page', ['HealthGuard']),
            ('GET', '/dashboard', 'Legacy dashboard', ['HealthGuard']),
            ('GET', '/hospitals', 'Hospitals list', ['Hospital']),
            ('GET', '/urls', 'MRF URLs list', []),
            ('GET', '/module/pricevision', 'Module view - PriceVision', ['PriceVision']),
            ('GET', '/module/drugwatch', 'Module view - DrugWatch', ['DrugWatch']),
            ('GET', '/module/foodscore', 'Module view - FoodScore', ['FoodScore']),
            ('GET', '/module/ruralaccess', 'Module view - RuralAccess', ['RuralAccess']),
            ('GET', '/module/chroniccare', 'Module view - ChronicCare', ['ChronicCare']),
            ('GET', '/module/nonexistent', 'Module view - Non-existent (404)', [], 404),
        ]

        for route in landing_routes:
            method, path, desc = route[0], route[1], route[2]
            check = route[3] if len(route) > 3 else []
            expected = route[4] if len(route) > 4 else 200
            result = test_route(client, method, path, expected_status=expected,
                              description=desc, check_content=check)
            print_result(result)

        # ============================================================
        # 2. PUBLIC PORTAL ROUTES
        # ============================================================
        print("\n" + "=" * 70)
        print("2. PUBLIC PORTAL ROUTES")
        print("=" * 70)

        # Public home
        print("\n  --- Public Home ---")
        result = test_route(client, 'GET', '/public/',
                          description='Public portal home',
                          check_content=['PriceVision', 'DrugWatch', 'FoodScore'])
        print_result(result)

        # PriceVision Public
        print("\n  --- Public PriceVision ---")
        pricevision_public = [
            ('GET', '/public/pricevision/', 'PriceVision home', ['PriceVision']),
            ('GET', '/public/pricevision/search', 'PriceVision search (no query)', []),
            ('GET', '/public/pricevision/search', 'PriceVision search (with query)', [], {'q': 'mri'}),
            ('GET', '/public/pricevision/search', 'PriceVision search (hospital type)', [], {'type': 'hospital'}),
            ('GET', '/public/pricevision/search', 'PriceVision search (with state)', [], {'state': 'CA'}),
            ('GET', '/public/pricevision/compare', 'PriceVision compare (no params)', []),
            ('GET', '/public/pricevision/compare', 'PriceVision compare (with procedure)', [], {'procedure': '99213'}),
            ('GET', '/public/pricevision/hospital/1234567890', 'PriceVision hospital detail', []),
        ]

        for route in pricevision_public:
            method, path, desc = route[0], route[1], route[2]
            check = route[3] if len(route) > 3 else []
            params = route[4] if len(route) > 4 else None
            result = test_route(client, method, path, description=desc,
                              check_content=check, params=params)
            print_result(result)

        # DrugWatch Public
        print("\n  --- Public DrugWatch ---")
        drugwatch_public = [
            ('GET', '/public/drugwatch/', 'DrugWatch home', ['DrugWatch']),
            ('GET', '/public/drugwatch/search', 'DrugWatch search (no query)', []),
            ('GET', '/public/drugwatch/search', 'DrugWatch search (with query)', [], {'q': 'insulin'}),
            ('GET', '/public/drugwatch/compare/humira', 'DrugWatch compare', []),
            ('GET', '/public/drugwatch/drug/humira', 'DrugWatch drug detail', []),
        ]

        for route in drugwatch_public:
            method, path, desc = route[0], route[1], route[2]
            check = route[3] if len(route) > 3 else []
            params = route[4] if len(route) > 4 else None
            result = test_route(client, method, path, description=desc,
                              check_content=check, params=params)
            print_result(result)

        # FoodScore Public
        print("\n  --- Public FoodScore ---")
        foodscore_public = [
            ('GET', '/public/foodscore/', 'FoodScore home', ['FoodScore']),
            ('GET', '/public/foodscore/search', 'FoodScore search (no query)', []),
            ('GET', '/public/foodscore/search', 'FoodScore search (with query)', [], {'q': 'chips'}),
            ('GET', '/public/foodscore/search', 'FoodScore search (with category)', [], {'category': 'snacks'}),
            ('GET', '/public/foodscore/scan', 'FoodScore barcode scanner', []),
            ('GET', '/public/foodscore/product/5000112546415', 'FoodScore product detail', []),
            ('GET', '/public/foodscore/additives', 'FoodScore additives list', []),
        ]

        for route in foodscore_public:
            method, path, desc = route[0], route[1], route[2]
            check = route[3] if len(route) > 3 else []
            params = route[4] if len(route) > 4 else None
            result = test_route(client, method, path, description=desc,
                              check_content=check, params=params)
            print_result(result)

        # ============================================================
        # 3. GOVERNMENT PORTAL ROUTES (requires auth)
        # ============================================================
        print("\n" + "=" * 70)
        print("3. GOVERNMENT PORTAL ROUTES (Authenticated)")
        print("=" * 70)

        gov_session = {
            'is_gov_user': True,
            'gov_username': 'test_admin'
        }

        # Test login page (no auth needed)
        print("\n  --- Gov Login ---")
        result = test_route(client, 'GET', '/gov/login',
                          description='Gov login page')
        print_result(result)

        # Test redirect without auth
        result = test_route(client, 'GET', '/gov/', expected_status=302,
                          description='Gov home (no auth - should redirect)')
        print_result(result)

        # Gov home with auth
        print("\n  --- Gov Home (authenticated) ---")
        result = test_route(client, 'GET', '/gov/',
                          description='Gov portal home',
                          session_data=gov_session,
                          check_content=['Government Portal'])
        print_result(result)

        # PriceVision Gov
        print("\n  --- Gov PriceVision ---")
        pricevision_gov = [
            ('GET', '/gov/pricevision/', 'Gov PriceVision home'),
            ('GET', '/gov/pricevision/search', 'Gov PriceVision search'),
            ('GET', '/gov/pricevision/search', 'Gov PriceVision search (query)', [], {'q': 'xray'}),
            ('GET', '/gov/pricevision/compare', 'Gov PriceVision compare'),
            ('GET', '/gov/pricevision/compare', 'Gov PriceVision compare (procedure)', [], {'procedure': '99213'}),
            ('GET', '/gov/pricevision/hospital/1234567890', 'Gov PriceVision hospital'),
            ('GET', '/gov/pricevision/analytics', 'Gov PriceVision analytics'),
            ('GET', '/gov/pricevision/analytics', 'Gov PriceVision analytics (state)', [], {'state': 'NY'}),
            ('GET', '/gov/pricevision/analytics', 'Gov PriceVision analytics (limit)', [], {'limit': '50'}),
        ]

        for route in pricevision_gov:
            method, path, desc = route[0], route[1], route[2]
            check = route[3] if len(route) > 3 else []
            params = route[4] if len(route) > 4 else None
            result = test_route(client, method, path, description=desc,
                              session_data=gov_session, check_content=check, params=params)
            print_result(result)

        # DrugWatch Gov
        print("\n  --- Gov DrugWatch ---")
        drugwatch_gov = [
            ('GET', '/gov/drugwatch/', 'Gov DrugWatch home'),
            ('GET', '/gov/drugwatch/search', 'Gov DrugWatch search'),
            ('GET', '/gov/drugwatch/search', 'Gov DrugWatch search (query)', [], {'q': 'metformin'}),
            ('GET', '/gov/drugwatch/compare/humira', 'Gov DrugWatch compare'),
            ('GET', '/gov/drugwatch/drug/humira', 'Gov DrugWatch drug detail'),
            ('GET', '/gov/drugwatch/mfn', 'Gov DrugWatch MFN analysis'),
            ('GET', '/gov/drugwatch/mfn', 'Gov DrugWatch MFN (search)', [], {'q': 'insulin'}),
            ('GET', '/gov/drugwatch/trends', 'Gov DrugWatch trends'),
            ('GET', '/gov/drugwatch/trends', 'Gov DrugWatch trends (search)', [], {'q': 'humira'}),
            ('GET', '/gov/drugwatch/trends', 'Gov DrugWatch trends (pagination)', [], {'page': '2', 'limit': '25'}),
        ]

        for route in drugwatch_gov:
            method, path, desc = route[0], route[1], route[2]
            check = route[3] if len(route) > 3 else []
            params = route[4] if len(route) > 4 else None
            result = test_route(client, method, path, description=desc,
                              session_data=gov_session, check_content=check, params=params)
            print_result(result)

        # FoodScore Gov
        print("\n  --- Gov FoodScore ---")
        foodscore_gov = [
            ('GET', '/gov/foodscore/', 'Gov FoodScore home'),
            ('GET', '/gov/foodscore/search', 'Gov FoodScore search'),
            ('GET', '/gov/foodscore/search', 'Gov FoodScore search (query)', [], {'q': 'cola'}),
            ('GET', '/gov/foodscore/product/5000112546415', 'Gov FoodScore product'),
            ('GET', '/gov/foodscore/snap', 'Gov FoodScore SNAP analysis'),
            ('GET', '/gov/foodscore/additives', 'Gov FoodScore additives'),
            ('GET', '/gov/foodscore/additives', 'Gov FoodScore additives (search)', [], {'q': 'color'}),
        ]

        for route in foodscore_gov:
            method, path, desc = route[0], route[1], route[2]
            check = route[3] if len(route) > 3 else []
            params = route[4] if len(route) > 4 else None
            result = test_route(client, method, path, description=desc,
                              session_data=gov_session, check_content=check, params=params)
            print_result(result)

        # RuralAccess Gov
        print("\n  --- Gov RuralAccess ---")
        ruralaccess_gov = [
            ('GET', '/gov/ruralaccess/', 'Gov RuralAccess home'),
            ('GET', '/gov/ruralaccess/map', 'Gov RuralAccess map'),
            ('GET', '/gov/ruralaccess/map', 'Gov RuralAccess map (state)', [], {'state': 'TX'}),
            ('GET', '/gov/ruralaccess/map', 'Gov RuralAccess map (discipline)', [], {'discipline': 'primary'}),
            ('GET', '/gov/ruralaccess/map', 'Gov RuralAccess map (limit)', [], {'limit': '100'}),
            ('GET', '/gov/ruralaccess/analytics', 'Gov RuralAccess analytics'),
            ('GET', '/gov/ruralaccess/county/06037', 'Gov RuralAccess county (LA County)'),
            ('GET', '/gov/ruralaccess/hpsa/123', 'Gov RuralAccess HPSA detail'),
        ]

        for route in ruralaccess_gov:
            method, path, desc = route[0], route[1], route[2]
            check = route[3] if len(route) > 3 else []
            params = route[4] if len(route) > 4 else None
            result = test_route(client, method, path, description=desc,
                              session_data=gov_session, check_content=check, params=params)
            print_result(result)

        # ChronicCare Gov
        print("\n  --- Gov ChronicCare ---")
        chroniccare_gov = [
            ('GET', '/gov/chroniccare/', 'Gov ChronicCare home'),
            ('GET', '/gov/chroniccare/dashboard', 'Gov ChronicCare dashboard'),
            ('GET', '/gov/chroniccare/dashboard', 'Gov ChronicCare dashboard (state)', [], {'state': 'CA'}),
            ('GET', '/gov/chroniccare/dashboard', 'Gov ChronicCare dashboard (limit)', [], {'limit': '50'}),
            ('GET', '/gov/chroniccare/county/06037', 'Gov ChronicCare county'),
            ('GET', '/gov/chroniccare/correlations', 'Gov ChronicCare correlations'),
            ('GET', '/gov/chroniccare/correlations', 'Gov ChronicCare correlations (state)', [], {'state': 'TX'}),
            ('GET', '/gov/chroniccare/interventions', 'Gov ChronicCare interventions'),
            ('GET', '/gov/chroniccare/interventions', 'Gov ChronicCare interventions (state)', [], {'state': 'FL'}),
            ('GET', '/gov/chroniccare/interventions', 'Gov ChronicCare interventions (priority)', [], {'priority': 'critical'}),
            ('GET', '/gov/chroniccare/analytics', 'Gov ChronicCare analytics'),
        ]

        for route in chroniccare_gov:
            method, path, desc = route[0], route[1], route[2]
            check = route[3] if len(route) > 3 else []
            params = route[4] if len(route) > 4 else None
            result = test_route(client, method, path, description=desc,
                              session_data=gov_session, check_content=check, params=params)
            print_result(result)

        # ============================================================
        # 4. API ENDPOINTS
        # ============================================================
        print("\n" + "=" * 70)
        print("4. API ENDPOINTS")
        print("=" * 70)

        # Main app API
        print("\n  --- Main API ---")
        main_api = [
            ('GET', '/api/inventory', 'API inventory'),
            ('GET', '/api/hospitals', 'API hospitals'),
            ('GET', '/api/hospitals', 'API hospitals (state filter)', [], {'state': 'CA'}),
            ('GET', '/api/urls', 'API URLs'),
            ('GET', '/api/stats', 'API stats'),
        ]

        for route in main_api:
            method, path, desc = route[0], route[1], route[2]
            check = route[3] if len(route) > 3 else []
            params = route[4] if len(route) > 4 else None
            result = test_route(client, method, path, description=desc,
                              check_content=check, params=params)
            print_result(result)

        # Public API endpoints
        print("\n  --- Public API ---")
        public_api = [
            ('GET', '/public/api/pricevision/procedures', 'API procedures'),
            ('GET', '/public/api/pricevision/procedures', 'API procedures (search)', [], {'q': 'mri'}),
            ('GET', '/public/api/pricevision/hospitals', 'API hospitals'),
            ('GET', '/public/api/drugwatch/drugs', 'API drugs'),
            ('GET', '/public/api/drugwatch/drugs', 'API drugs (search)', [], {'q': 'insulin'}),
            ('GET', '/public/api/drugwatch/compare/humira', 'API drug compare'),
            ('GET', '/public/api/foodscore/products', 'API products'),
            ('GET', '/public/api/foodscore/products', 'API products (search)', [], {'q': 'chips'}),
            ('GET', '/public/api/foodscore/product/5000112546415', 'API product detail'),
            ('GET', '/public/api/foodscore/additives', 'API additives'),
            ('GET', '/public/api/foodscore/stats', 'API FoodScore stats'),
        ]

        for route in public_api:
            method, path, desc = route[0], route[1], route[2]
            check = route[3] if len(route) > 3 else []
            params = route[4] if len(route) > 4 else None
            result = test_route(client, method, path, description=desc,
                              check_content=check, params=params)
            print_result(result)

        # Gov API endpoints (require auth)
        print("\n  --- Gov API (authenticated) ---")
        gov_api = [
            ('GET', '/gov/api/ruralaccess/hpsas', 'API HPSAs'),
            ('GET', '/gov/api/ruralaccess/hpsas', 'API HPSAs (state)', [], {'state': 'TX'}),
            ('GET', '/gov/api/ruralaccess/analytics', 'API RuralAccess analytics'),
            ('GET', '/gov/api/ruralaccess/counties', 'API counties'),
            ('GET', '/gov/api/ruralaccess/map-data', 'API map data'),
            ('GET', '/gov/api/ruralaccess/stats', 'API RuralAccess stats'),
            ('GET', '/gov/api/chroniccare/counties', 'API ChronicCare counties'),
            ('GET', '/gov/api/chroniccare/counties', 'API ChronicCare counties (state)', [], {'state': 'CA'}),
            ('GET', '/gov/api/chroniccare/correlations', 'API correlations'),
            ('GET', '/gov/api/chroniccare/interventions', 'API interventions'),
            ('GET', '/gov/api/chroniccare/stats', 'API ChronicCare stats'),
            ('GET', '/gov/api/chroniccare/state-stats', 'API state stats'),
        ]

        for route in gov_api:
            method, path, desc = route[0], route[1], route[2]
            check = route[3] if len(route) > 3 else []
            params = route[4] if len(route) > 4 else None
            result = test_route(client, method, path, description=desc,
                              session_data=gov_session, check_content=check, params=params)
            print_result(result)

    # ============================================================
    # SUMMARY REPORT
    # ============================================================
    print("\n" + "=" * 70)
    print("TEST SUMMARY REPORT")
    print("=" * 70)

    total = len(results['passed']) + len(results['failed'])
    passed = len(results['passed'])
    failed = len(results['failed'])
    slow = len(results['slow'])
    errors = len(results['errors'])

    print(f"\nTotal Routes Tested: {total}")
    print(f"  PASSED: {passed} ({passed/total*100:.1f}%)")
    print(f"  FAILED: {failed} ({failed/total*100:.1f}%)")
    print(f"  SLOW (>{SLOW_THRESHOLD}s): {slow}")
    print(f"  ERRORS: {errors}")

    if results['failed']:
        print("\n" + "-" * 70)
        print("FAILED ROUTES:")
        print("-" * 70)
        for r in results['failed']:
            print(f"\n  Path: {r['path']}")
            print(f"  Description: {r.get('description', 'N/A')}")
            print(f"  Expected: {r.get('expected_status', 200)}, Got: {r.get('status_code', 'N/A')}")
            if r.get('error'):
                print(f"  Error: {r['error']}")
            if r.get('content_errors'):
                print(f"  Content issues: {r['content_errors']}")

    if results['slow']:
        print("\n" + "-" * 70)
        print("SLOW ROUTES (>{:.1f}s):".format(SLOW_THRESHOLD))
        print("-" * 70)
        sorted_slow = sorted(results['slow'], key=lambda x: x.get('response_time', 0), reverse=True)
        for r in sorted_slow:
            print(f"  {r['path']}: {r.get('response_time', 'N/A')}s")

    # Response time analysis
    print("\n" + "-" * 70)
    print("RESPONSE TIME ANALYSIS:")
    print("-" * 70)

    all_times = [r.get('response_time', 0) for r in results['passed'] + results['failed'] if r.get('response_time')]
    if all_times:
        avg_time = sum(all_times) / len(all_times)
        max_time = max(all_times)
        min_time = min(all_times)
        print(f"  Average: {avg_time:.3f}s")
        print(f"  Min: {min_time:.3f}s")
        print(f"  Max: {max_time:.3f}s")

        # Time distribution
        fast = sum(1 for t in all_times if t < 0.5)
        medium = sum(1 for t in all_times if 0.5 <= t < 1.0)
        slow_med = sum(1 for t in all_times if 1.0 <= t < 3.0)
        very_slow = sum(1 for t in all_times if t >= 3.0)

        print(f"\n  Distribution:")
        print(f"    <0.5s (Fast): {fast} routes")
        print(f"    0.5-1.0s (OK): {medium} routes")
        print(f"    1.0-3.0s (Slow): {slow_med} routes")
        print(f"    >3.0s (Very Slow): {very_slow} routes")

    # Recommendations
    print("\n" + "-" * 70)
    print("RECOMMENDATIONS:")
    print("-" * 70)

    recommendations = []

    if failed > 0:
        recommendations.append("- Fix failed routes before deployment")

    if slow > 0:
        recommendations.append(f"- Optimize {slow} slow routes (>{SLOW_THRESHOLD}s response time)")
        for r in sorted(results['slow'], key=lambda x: x.get('response_time', 0), reverse=True)[:3]:
            recommendations.append(f"  * {r['path']}: Consider caching or query optimization")

    if errors > 0:
        recommendations.append("- Review error handling for routes with exceptions")

    if not recommendations:
        recommendations.append("- All routes are functioning correctly!")

    for rec in recommendations:
        print(rec)

    print("\n" + "=" * 70)
    print("END OF REPORT")
    print("=" * 70)

    return results


if __name__ == '__main__':
    run_all_tests()
