"""
Comprehensive HealthGuard Backend Services Test Suite
Tests all service methods for functionality, performance, and edge cases
"""
import sys
import time
import traceback
from datetime import datetime

sys.path.insert(0, 'frontend')

from services.pricevision import PriceVisionService
from services.drugwatch import DrugWatchService
from services.foodscore import FoodScoreService
from services.ruralaccess import RuralAccessService
from services.chroniccare import ChronicCareService

# Test Results Storage
test_results = []

def run_test(service_name, method_name, test_description, test_func, expected_type=None, allow_empty=False):
    """Run a single test and record results"""
    result = {
        'service': service_name,
        'method': method_name,
        'description': test_description,
        'status': 'PASS',
        'response_time_ms': 0,
        'data_count': 0,
        'error': None,
        'warnings': [],
        'details': None
    }

    try:
        start = time.time()
        data = test_func()
        end = time.time()
        result['response_time_ms'] = round((end - start) * 1000, 2)

        # Validate response
        if data is None and not allow_empty:
            result['status'] = 'FAIL'
            result['error'] = 'Returned None when data was expected'
        elif isinstance(data, list):
            result['data_count'] = len(data)
            if len(data) == 0 and not allow_empty:
                result['warnings'].append('Empty list returned')
            # Check for N/A or null values in first few records
            for i, record in enumerate(data[:3]):
                if isinstance(record, dict):
                    for key, value in record.items():
                        if value == 'N/A' or value == 'n/a':
                            result['warnings'].append(f'N/A value found in key: {key}')
        elif isinstance(data, dict):
            result['data_count'] = len(data)
            if len(data) == 0 and not allow_empty:
                result['warnings'].append('Empty dict returned')
            # Check for N/A values
            for key, value in data.items():
                if value == 'N/A' or value == 'n/a':
                    result['warnings'].append(f'N/A value found in key: {key}')

        if expected_type and not isinstance(data, expected_type):
            result['status'] = 'FAIL'
            result['error'] = f'Expected {expected_type.__name__}, got {type(data).__name__}'

        result['details'] = str(data)[:200] if data else 'None'

    except Exception as e:
        result['status'] = 'FAIL'
        result['error'] = f'{type(e).__name__}: {str(e)}'
        result['details'] = traceback.format_exc()[:500]

    test_results.append(result)
    status_symbol = 'PASS' if result['status'] == 'PASS' else 'FAIL'
    print(f"  [{status_symbol}] {test_description} - {result['response_time_ms']}ms")
    if result['error']:
        print(f"    ERROR: {result['error']}")
    for warning in result['warnings']:
        print(f"    WARNING: {warning}")

    return result


def test_pricevision_service():
    """Test all PriceVisionService methods"""
    print("\n" + "="*60)
    print("TESTING: PriceVisionService")
    print("="*60)

    # Test get_procedures
    run_test('PriceVisionService', 'get_procedures',
             'get_procedures() - default call',
             lambda: PriceVisionService.get_procedures(), list)

    run_test('PriceVisionService', 'get_procedures',
             'get_procedures(limit=5) - with limit',
             lambda: PriceVisionService.get_procedures(limit=5), list)

    run_test('PriceVisionService', 'get_procedures',
             'get_procedures(search="knee") - with search',
             lambda: PriceVisionService.get_procedures(search="knee"), list, allow_empty=True)

    run_test('PriceVisionService', 'get_procedures',
             'get_procedures(search="") - empty search',
             lambda: PriceVisionService.get_procedures(search=""), list)

    run_test('PriceVisionService', 'get_procedures',
             'get_procedures(search=None) - None search',
             lambda: PriceVisionService.get_procedures(search=None), list)

    # Test get_hospitals
    run_test('PriceVisionService', 'get_hospitals',
             'get_hospitals() - default call',
             lambda: PriceVisionService.get_hospitals(), list)

    run_test('PriceVisionService', 'get_hospitals',
             'get_hospitals(state="CA") - filter by state',
             lambda: PriceVisionService.get_hospitals(state="CA"), list, allow_empty=True)

    run_test('PriceVisionService', 'get_hospitals',
             'get_hospitals(state="XX") - invalid state',
             lambda: PriceVisionService.get_hospitals(state="XX"), list, allow_empty=True)

    run_test('PriceVisionService', 'get_hospitals',
             'get_hospitals(limit=3) - with limit',
             lambda: PriceVisionService.get_hospitals(limit=3), list)

    # Test get_hospital (single)
    hospitals = PriceVisionService.get_hospitals(limit=1)
    if hospitals:
        facility_id = hospitals[0].get('Facility ID')
        run_test('PriceVisionService', 'get_hospital',
                 f'get_hospital({facility_id}) - valid ID',
                 lambda: PriceVisionService.get_hospital(facility_id), dict)

    run_test('PriceVisionService', 'get_hospital',
             'get_hospital("999999999") - invalid ID',
             lambda: PriceVisionService.get_hospital("999999999"), type(None), allow_empty=True)

    run_test('PriceVisionService', 'get_hospital',
             'get_hospital(None) - None ID',
             lambda: PriceVisionService.get_hospital(None), type(None), allow_empty=True)

    run_test('PriceVisionService', 'get_hospital',
             'get_hospital("") - empty string ID',
             lambda: PriceVisionService.get_hospital(""), type(None), allow_empty=True)

    # Test get_prices
    procedures = PriceVisionService.get_procedures(limit=1)
    if procedures:
        proc_code = procedures[0].get('hcpcs_code')
        run_test('PriceVisionService', 'get_prices',
                 f'get_prices(procedure_code="{proc_code}") - by procedure',
                 lambda: PriceVisionService.get_prices(procedure_code=proc_code), list, allow_empty=True)

    if hospitals:
        hospital_npi = str(hospitals[0].get('Facility ID', ''))
        run_test('PriceVisionService', 'get_prices',
                 f'get_prices(hospital_npi="{hospital_npi}") - by hospital',
                 lambda: PriceVisionService.get_prices(hospital_npi=hospital_npi), list, allow_empty=True)

    run_test('PriceVisionService', 'get_prices',
             'get_prices() - no filters (should return empty)',
             lambda: PriceVisionService.get_prices(), list, allow_empty=True)

    run_test('PriceVisionService', 'get_prices',
             'get_prices(state="CA", procedure_code="99213") - with state filter',
             lambda: PriceVisionService.get_prices(state="CA", procedure_code="99213"), list, allow_empty=True)

    # Test get_states
    run_test('PriceVisionService', 'get_states',
             'get_states() - get all states',
             lambda: PriceVisionService.get_states(), list)

    # Test get_hospitals_with_mrf
    run_test('PriceVisionService', 'get_hospitals_with_mrf',
             'get_hospitals_with_mrf() - hospitals with MRF data',
             lambda: PriceVisionService.get_hospitals_with_mrf(), set)

    # Test get_stats
    run_test('PriceVisionService', 'get_stats',
             'get_stats() - summary statistics',
             lambda: PriceVisionService.get_stats(), dict)

    # Test get_hospital_info_cache
    run_test('PriceVisionService', 'get_hospital_info_cache',
             'get_hospital_info_cache() - cached hospital info',
             lambda: PriceVisionService.get_hospital_info_cache(), dict)


def test_drugwatch_service():
    """Test all DrugWatchService methods"""
    print("\n" + "="*60)
    print("TESTING: DrugWatchService")
    print("="*60)

    # Test get_us_drugs
    run_test('DrugWatchService', 'get_us_drugs',
             'get_us_drugs() - default call',
             lambda: DrugWatchService.get_us_drugs(), list)

    run_test('DrugWatchService', 'get_us_drugs',
             'get_us_drugs(limit=5) - with limit',
             lambda: DrugWatchService.get_us_drugs(limit=5), list)

    run_test('DrugWatchService', 'get_us_drugs',
             'get_us_drugs(search="aspirin") - with search',
             lambda: DrugWatchService.get_us_drugs(search="aspirin"), list, allow_empty=True)

    run_test('DrugWatchService', 'get_us_drugs',
             'get_us_drugs(search="") - empty search',
             lambda: DrugWatchService.get_us_drugs(search=""), list)

    run_test('DrugWatchService', 'get_us_drugs',
             'get_us_drugs(search=None) - None search',
             lambda: DrugWatchService.get_us_drugs(search=None), list)

    run_test('DrugWatchService', 'get_us_drugs',
             'get_us_drugs(search="xyznonexistent") - non-existent drug',
             lambda: DrugWatchService.get_us_drugs(search="xyznonexistent"), list, allow_empty=True)

    # Test get_drug (single)
    drugs = DrugWatchService.get_us_drugs(limit=1)
    if drugs:
        drug_name = drugs[0].get('brand_name') or drugs[0].get('generic_name')
        if drug_name:
            run_test('DrugWatchService', 'get_drug',
                     f'get_drug("{drug_name}") - valid drug name',
                     lambda: DrugWatchService.get_drug(drug_name), dict)

    run_test('DrugWatchService', 'get_drug',
             'get_drug("nonexistentdrug123") - invalid drug',
             lambda: DrugWatchService.get_drug("nonexistentdrug123"), type(None), allow_empty=True)

    run_test('DrugWatchService', 'get_drug',
             'get_drug(None) - None input',
             lambda: DrugWatchService.get_drug(None), type(None), allow_empty=True)

    run_test('DrugWatchService', 'get_drug',
             'get_drug("") - empty string',
             lambda: DrugWatchService.get_drug(""), type(None), allow_empty=True)

    # Test get_international_prices
    run_test('DrugWatchService', 'get_international_prices',
             'get_international_prices() - all countries',
             lambda: DrugWatchService.get_international_prices(), list)

    run_test('DrugWatchService', 'get_international_prices',
             'get_international_prices(country="australia") - Australia only',
             lambda: DrugWatchService.get_international_prices(country="australia"), list, allow_empty=True)

    run_test('DrugWatchService', 'get_international_prices',
             'get_international_prices(country="canada") - Canada only',
             lambda: DrugWatchService.get_international_prices(country="canada"), list, allow_empty=True)

    run_test('DrugWatchService', 'get_international_prices',
             'get_international_prices(country="invalidcountry") - invalid country',
             lambda: DrugWatchService.get_international_prices(country="invalidcountry"), list, allow_empty=True)

    # Test get_nadac_prices
    run_test('DrugWatchService', 'get_nadac_prices',
             'get_nadac_prices() - default call',
             lambda: DrugWatchService.get_nadac_prices(), list)

    run_test('DrugWatchService', 'get_nadac_prices',
             'get_nadac_prices(limit=5) - with limit',
             lambda: DrugWatchService.get_nadac_prices(limit=5), list)

    run_test('DrugWatchService', 'get_nadac_prices',
             'get_nadac_prices(search="tablet") - with search',
             lambda: DrugWatchService.get_nadac_prices(search="tablet"), list, allow_empty=True)

    # Test compare_prices
    if drugs and drugs[0].get('brand_name'):
        drug_name = drugs[0].get('brand_name')
        run_test('DrugWatchService', 'compare_prices',
                 f'compare_prices("{drug_name}") - valid drug',
                 lambda: DrugWatchService.compare_prices(drug_name), dict)

    run_test('DrugWatchService', 'compare_prices',
             'compare_prices("nonexistent") - non-existent drug',
             lambda: DrugWatchService.compare_prices("nonexistent"), dict)

    # Test get_stats
    run_test('DrugWatchService', 'get_stats',
             'get_stats() - summary statistics',
             lambda: DrugWatchService.get_stats(), dict)

    # Test get_top_expensive
    run_test('DrugWatchService', 'get_top_expensive',
             'get_top_expensive() - default call',
             lambda: DrugWatchService.get_top_expensive(), list)

    run_test('DrugWatchService', 'get_top_expensive',
             'get_top_expensive(limit=5) - with limit',
             lambda: DrugWatchService.get_top_expensive(limit=5), list)


def test_foodscore_service():
    """Test all FoodScoreService methods"""
    print("\n" + "="*60)
    print("TESTING: FoodScoreService")
    print("="*60)

    # Test get_products
    run_test('FoodScoreService', 'get_products',
             'get_products() - default call',
             lambda: FoodScoreService.get_products(), list)

    run_test('FoodScoreService', 'get_products',
             'get_products(limit=5) - with limit',
             lambda: FoodScoreService.get_products(limit=5), list)

    run_test('FoodScoreService', 'get_products',
             'get_products(search="chips") - with search',
             lambda: FoodScoreService.get_products(search="chips"), list, allow_empty=True)

    run_test('FoodScoreService', 'get_products',
             'get_products(category="snacks") - with category',
             lambda: FoodScoreService.get_products(category="snacks"), list, allow_empty=True)

    run_test('FoodScoreService', 'get_products',
             'get_products(search="", category="") - empty filters',
             lambda: FoodScoreService.get_products(search="", category=""), list)

    run_test('FoodScoreService', 'get_products',
             'get_products(search=None, category=None) - None filters',
             lambda: FoodScoreService.get_products(search=None, category=None), list)

    # Test get_product (single)
    products = FoodScoreService.get_products(limit=1)
    if products:
        barcode = products[0].get('code')
        if barcode:
            run_test('FoodScoreService', 'get_product',
                     f'get_product("{barcode}") - valid barcode',
                     lambda: FoodScoreService.get_product(barcode), dict)

    run_test('FoodScoreService', 'get_product',
             'get_product("0000000000000") - invalid barcode',
             lambda: FoodScoreService.get_product("0000000000000"), type(None), allow_empty=True)

    run_test('FoodScoreService', 'get_product',
             'get_product(None) - None barcode',
             lambda: FoodScoreService.get_product(None), type(None), allow_empty=True)

    run_test('FoodScoreService', 'get_product',
             'get_product("") - empty barcode',
             lambda: FoodScoreService.get_product(""), type(None), allow_empty=True)

    # Test get_additives
    run_test('FoodScoreService', 'get_additives',
             'get_additives() - default call',
             lambda: FoodScoreService.get_additives(), list)

    run_test('FoodScoreService', 'get_additives',
             'get_additives(limit=5) - with limit',
             lambda: FoodScoreService.get_additives(limit=5), list)

    run_test('FoodScoreService', 'get_additives',
             'get_additives(search="E100") - search E-number',
             lambda: FoodScoreService.get_additives(search="E100"), list, allow_empty=True)

    # Test get_additive (single)
    additives = FoodScoreService.get_additives(limit=1)
    if additives:
        additive_id = additives[0].get('e_number') or additives[0].get('name')
        if additive_id:
            run_test('FoodScoreService', 'get_additive',
                     f'get_additive("{additive_id}") - valid additive',
                     lambda: FoodScoreService.get_additive(additive_id), dict)

    run_test('FoodScoreService', 'get_additive',
             'get_additive("E99999") - invalid additive',
             lambda: FoodScoreService.get_additive("E99999"), type(None), allow_empty=True)

    # Test get_categories
    run_test('FoodScoreService', 'get_categories',
             'get_categories() - get all categories',
             lambda: FoodScoreService.get_categories(), list)

    # Test get_nova_distribution
    run_test('FoodScoreService', 'get_nova_distribution',
             'get_nova_distribution() - NOVA classification',
             lambda: FoodScoreService.get_nova_distribution(), dict)

    # Test get_high_risk_products
    run_test('FoodScoreService', 'get_high_risk_products',
             'get_high_risk_products() - default call',
             lambda: FoodScoreService.get_high_risk_products(), list)

    run_test('FoodScoreService', 'get_high_risk_products',
             'get_high_risk_products(limit=5) - with limit',
             lambda: FoodScoreService.get_high_risk_products(limit=5), list)

    # Test get_stats
    run_test('FoodScoreService', 'get_stats',
             'get_stats() - summary statistics',
             lambda: FoodScoreService.get_stats(), dict)


def test_ruralaccess_service():
    """Test all RuralAccessService methods"""
    print("\n" + "="*60)
    print("TESTING: RuralAccessService")
    print("="*60)

    # Test get_hpsa_designations
    run_test('RuralAccessService', 'get_hpsa_designations',
             'get_hpsa_designations() - default call',
             lambda: RuralAccessService.get_hpsa_designations(), list)

    run_test('RuralAccessService', 'get_hpsa_designations',
             'get_hpsa_designations(limit=5) - with limit',
             lambda: RuralAccessService.get_hpsa_designations(limit=5), list)

    run_test('RuralAccessService', 'get_hpsa_designations',
             'get_hpsa_designations(state="TX") - filter by state',
             lambda: RuralAccessService.get_hpsa_designations(state="TX"), list, allow_empty=True)

    run_test('RuralAccessService', 'get_hpsa_designations',
             'get_hpsa_designations(discipline="primary") - filter by discipline',
             lambda: RuralAccessService.get_hpsa_designations(discipline="primary"), list, allow_empty=True)

    run_test('RuralAccessService', 'get_hpsa_designations',
             'get_hpsa_designations(shortage_level="critical") - critical shortage',
             lambda: RuralAccessService.get_hpsa_designations(shortage_level="critical"), list, allow_empty=True)

    run_test('RuralAccessService', 'get_hpsa_designations',
             'get_hpsa_designations(rural_status="Rural") - rural areas',
             lambda: RuralAccessService.get_hpsa_designations(rural_status="Rural"), list, allow_empty=True)

    run_test('RuralAccessService', 'get_hpsa_designations',
             'get_hpsa_designations(limit=0) - unlimited (all records)',
             lambda: RuralAccessService.get_hpsa_designations(limit=0), list)

    run_test('RuralAccessService', 'get_hpsa_designations',
             'get_hpsa_designations(state="XX") - invalid state',
             lambda: RuralAccessService.get_hpsa_designations(state="XX"), list, allow_empty=True)

    # Test get_total_hpsa_count
    run_test('RuralAccessService', 'get_total_hpsa_count',
             'get_total_hpsa_count() - total count',
             lambda: RuralAccessService.get_total_hpsa_count(), int)

    run_test('RuralAccessService', 'get_total_hpsa_count',
             'get_total_hpsa_count(state="CA") - count by state',
             lambda: RuralAccessService.get_total_hpsa_count(state="CA"), int)

    # Test get_hpsa (single)
    hpsas = RuralAccessService.get_hpsa_designations(limit=1)
    if hpsas:
        hpsa_id = hpsas[0].get('hpsa_id') or hpsas[0].get('HPSA ID')
        if hpsa_id:
            run_test('RuralAccessService', 'get_hpsa',
                     f'get_hpsa("{hpsa_id}") - valid HPSA ID',
                     lambda: RuralAccessService.get_hpsa(hpsa_id), dict)

    run_test('RuralAccessService', 'get_hpsa',
             'get_hpsa("INVALID123") - invalid HPSA ID',
             lambda: RuralAccessService.get_hpsa("INVALID123"), type(None), allow_empty=True)

    # Test get_counties
    run_test('RuralAccessService', 'get_counties',
             'get_counties() - default call',
             lambda: RuralAccessService.get_counties(), list)

    run_test('RuralAccessService', 'get_counties',
             'get_counties(state="FL") - filter by state',
             lambda: RuralAccessService.get_counties(state="FL"), list, allow_empty=True)

    run_test('RuralAccessService', 'get_counties',
             'get_counties(limit=0) - unlimited',
             lambda: RuralAccessService.get_counties(limit=0), list)

    # Test get_total_counties_count
    run_test('RuralAccessService', 'get_total_counties_count',
             'get_total_counties_count() - total count',
             lambda: RuralAccessService.get_total_counties_count(), int)

    # Test get_county (single)
    counties = RuralAccessService.get_counties(limit=1)
    if counties:
        fips = counties[0].get('county_fips')
        if fips:
            run_test('RuralAccessService', 'get_county',
                     f'get_county("{fips}") - valid FIPS',
                     lambda: RuralAccessService.get_county(fips), dict)

    run_test('RuralAccessService', 'get_county',
             'get_county("00000") - invalid FIPS',
             lambda: RuralAccessService.get_county("00000"), type(None), allow_empty=True)

    # Test get_fqhc_locations
    run_test('RuralAccessService', 'get_fqhc_locations',
             'get_fqhc_locations() - default call',
             lambda: RuralAccessService.get_fqhc_locations(), list)

    run_test('RuralAccessService', 'get_fqhc_locations',
             'get_fqhc_locations(state="NY") - filter by state',
             lambda: RuralAccessService.get_fqhc_locations(state="NY"), list, allow_empty=True)

    # Test get_hospital_closures
    run_test('RuralAccessService', 'get_hospital_closures',
             'get_hospital_closures() - default call',
             lambda: RuralAccessService.get_hospital_closures(), list)

    run_test('RuralAccessService', 'get_hospital_closures',
             'get_hospital_closures(limit=5) - with limit',
             lambda: RuralAccessService.get_hospital_closures(limit=5), list)

    # Test get_states
    run_test('RuralAccessService', 'get_states',
             'get_states() - get all states',
             lambda: RuralAccessService.get_states(), list)

    # Test get_stats
    run_test('RuralAccessService', 'get_stats',
             'get_stats() - summary statistics',
             lambda: RuralAccessService.get_stats(), dict)

    # Test get_shortage_map_data
    run_test('RuralAccessService', 'get_shortage_map_data',
             'get_shortage_map_data() - map visualization data',
             lambda: RuralAccessService.get_shortage_map_data(), list)

    # Test get_analytics
    run_test('RuralAccessService', 'get_analytics',
             'get_analytics() - comprehensive analytics',
             lambda: RuralAccessService.get_analytics(), dict)

    # Test get_designation_types
    run_test('RuralAccessService', 'get_designation_types',
             'get_designation_types() - unique designation types',
             lambda: RuralAccessService.get_designation_types(), list)

    # Test get_rural_statuses
    run_test('RuralAccessService', 'get_rural_statuses',
             'get_rural_statuses() - unique rural statuses',
             lambda: RuralAccessService.get_rural_statuses(), list)


def test_chroniccare_service():
    """Test all ChronicCareService methods"""
    print("\n" + "="*60)
    print("TESTING: ChronicCareService")
    print("="*60)

    # Test get_county_health
    run_test('ChronicCareService', 'get_county_health',
             'get_county_health() - default call',
             lambda: ChronicCareService.get_county_health(), list)

    run_test('ChronicCareService', 'get_county_health',
             'get_county_health(limit=5) - with limit',
             lambda: ChronicCareService.get_county_health(limit=5), list)

    run_test('ChronicCareService', 'get_county_health',
             'get_county_health(state="GA") - filter by state',
             lambda: ChronicCareService.get_county_health(state="GA"), list, allow_empty=True)

    run_test('ChronicCareService', 'get_county_health',
             'get_county_health(state="XX") - invalid state',
             lambda: ChronicCareService.get_county_health(state="XX"), list, allow_empty=True)

    # Test get_county (single)
    counties = ChronicCareService.get_county_health(limit=1)
    if counties:
        fips = counties[0].get('fips') or counties[0].get('FIPS')
        if fips:
            run_test('ChronicCareService', 'get_county',
                     f'get_county("{fips}") - valid FIPS',
                     lambda: ChronicCareService.get_county(fips), dict)

    run_test('ChronicCareService', 'get_county',
             'get_county("00000") - invalid FIPS',
             lambda: ChronicCareService.get_county("00000"), type(None), allow_empty=True)

    run_test('ChronicCareService', 'get_county',
             'get_county(None) - None FIPS',
             lambda: ChronicCareService.get_county(None), type(None), allow_empty=True)

    # Test get_cdc_places
    run_test('ChronicCareService', 'get_cdc_places',
             'get_cdc_places() - default call',
             lambda: ChronicCareService.get_cdc_places(), list)

    run_test('ChronicCareService', 'get_cdc_places',
             'get_cdc_places(state="OH") - filter by state',
             lambda: ChronicCareService.get_cdc_places(state="OH"), list, allow_empty=True)

    run_test('ChronicCareService', 'get_cdc_places',
             'get_cdc_places(limit=5) - with limit',
             lambda: ChronicCareService.get_cdc_places(limit=5), list)

    # Test get_food_environment
    run_test('ChronicCareService', 'get_food_environment',
             'get_food_environment() - default call',
             lambda: ChronicCareService.get_food_environment(), list)

    run_test('ChronicCareService', 'get_food_environment',
             'get_food_environment(state="MI") - filter by state',
             lambda: ChronicCareService.get_food_environment(state="MI"), list, allow_empty=True)

    # Test get_correlations
    run_test('ChronicCareService', 'get_correlations',
             'get_correlations() - disease-food correlations',
             lambda: ChronicCareService.get_correlations(), list)

    # Test get_intervention_priorities
    run_test('ChronicCareService', 'get_intervention_priorities',
             'get_intervention_priorities() - default call',
             lambda: ChronicCareService.get_intervention_priorities(), list)

    run_test('ChronicCareService', 'get_intervention_priorities',
             'get_intervention_priorities(limit=10) - with limit',
             lambda: ChronicCareService.get_intervention_priorities(limit=10), list)

    run_test('ChronicCareService', 'get_intervention_priorities',
             'get_intervention_priorities(limit=0) - zero limit',
             lambda: ChronicCareService.get_intervention_priorities(limit=0), list, allow_empty=True)

    # Test get_states
    run_test('ChronicCareService', 'get_states',
             'get_states() - get all states',
             lambda: ChronicCareService.get_states(), list)

    # Test get_stats
    run_test('ChronicCareService', 'get_stats',
             'get_stats() - summary statistics',
             lambda: ChronicCareService.get_stats(), dict)

    # Test get_national_trends
    run_test('ChronicCareService', 'get_national_trends',
             'get_national_trends() - national health trends',
             lambda: ChronicCareService.get_national_trends(), dict)

    # Test get_state_statistics
    run_test('ChronicCareService', 'get_state_statistics',
             'get_state_statistics() - state-by-state stats',
             lambda: ChronicCareService.get_state_statistics(), dict)


def generate_report():
    """Generate comprehensive test report"""
    print("\n" + "="*80)
    print("COMPREHENSIVE TEST REPORT - HealthGuard Backend Services")
    print("="*80)
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-"*80)

    # Summary
    total = len(test_results)
    passed = len([r for r in test_results if r['status'] == 'PASS'])
    failed = len([r for r in test_results if r['status'] == 'FAIL'])
    with_warnings = len([r for r in test_results if r['warnings']])

    print(f"\nSUMMARY:")
    print(f"  Total Tests: {total}")
    print(f"  Passed: {passed} ({round(passed/total*100, 1)}%)")
    print(f"  Failed: {failed} ({round(failed/total*100, 1)}%)")
    print(f"  Tests with Warnings: {with_warnings}")

    # Performance Summary
    response_times = [r['response_time_ms'] for r in test_results if r['response_time_ms'] > 0]
    if response_times:
        print(f"\nPERFORMANCE:")
        print(f"  Avg Response Time: {round(sum(response_times)/len(response_times), 2)}ms")
        print(f"  Max Response Time: {max(response_times)}ms")
        print(f"  Min Response Time: {min(response_times)}ms")

        # Slow tests (>500ms)
        slow_tests = [r for r in test_results if r['response_time_ms'] > 500]
        if slow_tests:
            print(f"\n  SLOW TESTS (>500ms):")
            for t in sorted(slow_tests, key=lambda x: x['response_time_ms'], reverse=True):
                print(f"    - {t['service']}.{t['method']}: {t['response_time_ms']}ms")

    # Results by Service
    services = ['PriceVisionService', 'DrugWatchService', 'FoodScoreService',
                'RuralAccessService', 'ChronicCareService']

    print("\n" + "-"*80)
    print("RESULTS BY SERVICE:")
    print("-"*80)

    for service in services:
        service_results = [r for r in test_results if r['service'] == service]
        service_passed = len([r for r in service_results if r['status'] == 'PASS'])
        service_failed = len([r for r in service_results if r['status'] == 'FAIL'])

        print(f"\n{service}:")
        print(f"  Tests: {len(service_results)} | Passed: {service_passed} | Failed: {service_failed}")

        # Show failures
        failures = [r for r in service_results if r['status'] == 'FAIL']
        if failures:
            print(f"  FAILURES:")
            for f in failures:
                print(f"    - {f['method']}: {f['description']}")
                print(f"      Error: {f['error']}")

        # Show warnings
        warnings = [r for r in service_results if r['warnings']]
        if warnings:
            print(f"  WARNINGS:")
            for w in warnings:
                for warning in w['warnings']:
                    print(f"    - {w['method']}: {warning}")

    # Failed Tests Detail
    if failed > 0:
        print("\n" + "-"*80)
        print("FAILED TESTS DETAIL:")
        print("-"*80)
        for r in test_results:
            if r['status'] == 'FAIL':
                print(f"\n{r['service']}.{r['method']}:")
                print(f"  Description: {r['description']}")
                print(f"  Error: {r['error']}")
                if r['details']:
                    print(f"  Details: {r['details'][:300]}")

    # Data Quality Issues
    print("\n" + "-"*80)
    print("DATA QUALITY ANALYSIS:")
    print("-"*80)

    all_warnings = []
    for r in test_results:
        for w in r['warnings']:
            all_warnings.append({'service': r['service'], 'method': r['method'], 'warning': w})

    if all_warnings:
        print("\nWarnings Found:")
        for w in all_warnings:
            print(f"  - {w['service']}.{w['method']}: {w['warning']}")
    else:
        print("\nNo data quality warnings found.")

    # Empty Results Analysis
    empty_results = [r for r in test_results if r['data_count'] == 0 and r['status'] == 'PASS']
    if empty_results:
        print("\nMethods Returning Empty Results (may need investigation):")
        for e in empty_results:
            print(f"  - {e['service']}.{e['method']}: {e['description']}")

    # Recommendations
    print("\n" + "-"*80)
    print("RECOMMENDATIONS:")
    print("-"*80)

    recommendations = []

    # Check for slow methods
    slow_methods = [r for r in test_results if r['response_time_ms'] > 1000]
    if slow_methods:
        recommendations.append("PERFORMANCE: The following methods are slow (>1s) and may need optimization:")
        for s in slow_methods:
            recommendations.append(f"  - {s['service']}.{s['method']}: {s['response_time_ms']}ms")

    # Check for failures
    if failed > 0:
        recommendations.append(f"RELIABILITY: {failed} test(s) failed. Review error details above.")

    # Check for empty results
    unexpected_empty = [r for r in test_results
                       if r['data_count'] == 0
                       and r['status'] == 'PASS'
                       and 'invalid' not in r['description'].lower()
                       and 'empty' not in r['description'].lower()
                       and 'None' not in r['description']]
    if unexpected_empty:
        recommendations.append("DATA: Some queries returned empty results that may indicate missing data:")
        for e in unexpected_empty[:5]:
            recommendations.append(f"  - {e['service']}.{e['method']}: {e['description']}")

    # Check for N/A values
    na_warnings = [w for w in all_warnings if 'N/A' in w['warning']]
    if na_warnings:
        recommendations.append("DATA QUALITY: N/A values found in some records - consider data cleaning")

    if not recommendations:
        recommendations.append("All services are functioning correctly with good performance!")

    for rec in recommendations:
        print(f"\n{rec}")

    print("\n" + "="*80)
    print("END OF REPORT")
    print("="*80)

    return {
        'total': total,
        'passed': passed,
        'failed': failed,
        'warnings': with_warnings,
        'results': test_results
    }


if __name__ == '__main__':
    print("="*80)
    print("HealthGuard Backend Services - Comprehensive Test Suite")
    print("="*80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Run all tests
    test_pricevision_service()
    test_drugwatch_service()
    test_foodscore_service()
    test_ruralaccess_service()
    test_chroniccare_service()

    # Generate report
    report = generate_report()

    print(f"\nTest suite completed: {report['passed']}/{report['total']} tests passed")
