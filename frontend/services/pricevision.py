"""
PriceVision Data Service
Load hospital and procedure pricing data - OPTIMIZED
"""
import pandas as pd
import pyarrow.parquet as pq
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent
DATA_DIR = BASE_DIR / 'data'


class PriceVisionService:
    _cache = {}
    _price_file = None

    @classmethod
    def get_procedures(cls, limit=100, search=None):
        """Get list of medical procedures"""
        if 'procedures' not in cls._cache:
            proc_file = DATA_DIR / 'processed/pricevision/medicare_procedures.csv'
            if proc_file.exists():
                df = pd.read_csv(proc_file)
                cls._cache['procedures'] = df.to_dict('records')
            else:
                cls._cache['procedures'] = []

        procedures = cls._cache['procedures']
        if search:
            search = search.lower()
            procedures = [p for p in procedures if search in str(p.get('canonical_description', '')).lower()
                         or search in str(p.get('hcpcs_code', '')).lower()]
        return procedures[:limit]

    @classmethod
    def get_hospitals(cls, state=None, limit=100):
        """Get list of hospitals"""
        if 'hospitals' not in cls._cache:
            hosp_file = DATA_DIR / 'raw/pricevision/hospital_general_info.csv'
            if hosp_file.exists():
                df = pd.read_csv(hosp_file)
                cls._cache['hospitals'] = df.to_dict('records')
            else:
                cls._cache['hospitals'] = []

        hospitals = cls._cache['hospitals']
        if state:
            hospitals = [h for h in hospitals if h.get('State', '') == state]
        return hospitals[:limit]

    @classmethod
    def get_hospital(cls, facility_id):
        """Get single hospital by Facility ID"""
        hospitals = cls.get_hospitals(limit=10000)
        for h in hospitals:
            if str(h.get('Facility ID', '')) == str(facility_id):
                return h
        return None

    @classmethod
    def get_prices(cls, hospital_npi=None, procedure_code=None, state=None, limit=50):
        """Get price data using predicate pushdown - only loads matching rows"""
        if not hospital_npi and not procedure_code:
            return []  # Don't load without a filter

        price_file = DATA_DIR / 'processed/pricevision/all_prices_normalized.parquet'
        if not price_file.exists():
            return []

        try:
            # If state filter provided, get hospital IDs in that state
            state_hospital_ids = None
            if state:
                state_hospitals = cls.get_hospitals(state=state, limit=10000)
                state_hospital_ids = set(str(h.get('Facility ID', '')) for h in state_hospitals)

            # Build filter for predicate pushdown
            filters = []
            if procedure_code:
                filters.append(('procedure_code', '==', str(procedure_code)))

            # Read with filter - only loads matching rows from disk
            if filters:
                df = pd.read_parquet(
                    price_file,
                    columns=['description', 'procedure_code', 'gross_charge', 'hospital_npi',
                             'cash_price', 'min_price', 'max_price', 'payer_name'],
                    filters=filters
                )
            else:
                # For hospital_npi filter (string matching), read sample and filter
                df = pd.read_parquet(
                    price_file,
                    columns=['description', 'procedure_code', 'gross_charge', 'hospital_npi',
                             'cash_price', 'min_price', 'max_price', 'payer_name']
                )
                if len(df) > 10000:
                    df = df.sample(n=10000, random_state=42)

            # Additional filtering if needed
            if hospital_npi:
                df = df[df['hospital_npi'].astype(str) == str(hospital_npi)]

            # Filter by state if provided
            if state_hospital_ids:
                df = df[df['hospital_npi'].astype(str).isin(state_hospital_ids)]

            # Sort by cash_price for best prices first
            if 'cash_price' in df.columns:
                df = df.sort_values('cash_price', ascending=True, na_position='last')

            # Deduplicate by hospital - keep only the best (lowest) price per hospital
            df = df.drop_duplicates(subset=['hospital_npi'], keep='first')

            # Build hospital info cache
            hospital_cache = {}
            for h in cls.get_hospitals(limit=10000):
                hospital_cache[str(h.get('Facility ID', ''))] = {
                    'name': h.get('Facility Name', ''),
                    'city': h.get('City/Town', ''),
                    'state': h.get('State', '')
                }

            # Filter to only hospitals with valid info (exclude unknown hospitals)
            valid_npis = set(hospital_cache.keys())
            df = df[df['hospital_npi'].astype(str).isin(valid_npis)]

            # Add hospital info to results
            results = df.head(limit).to_dict('records')
            for r in results:
                npi = str(r.get('hospital_npi', ''))
                r['hospital_name'] = hospital_cache[npi]['name']
                r['hospital_city'] = hospital_cache[npi]['city']
                r['hospital_state'] = hospital_cache[npi]['state']
            return results
        except Exception as e:
            print(f"Error loading prices: {e}")
            return []

    @classmethod
    def get_states(cls):
        """Get list of states with hospitals"""
        hospitals = cls.get_hospitals(limit=10000)
        states = set()
        for h in hospitals:
            state = h.get('State', '')
            if state and len(str(state)) == 2:
                states.add(state)
        return sorted(states)

    @classmethod
    def get_stats(cls):
        """Get summary statistics"""
        hospitals = cls.get_hospitals(limit=10000)
        procedures = cls.get_procedures(limit=10000)
        return {
            'total_hospitals': len(hospitals),
            'total_procedures': len(procedures),
            'states_covered': len(cls.get_states())
        }
