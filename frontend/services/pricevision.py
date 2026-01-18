"""
PriceVision Data Service
Load hospital and procedure pricing data
"""
import pandas as pd
from pathlib import Path
import json

BASE_DIR = Path(__file__).parent.parent.parent
DATA_DIR = BASE_DIR / 'data'


class PriceVisionService:
    _cache = {}

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
    def get_prices(cls, hospital_id=None, procedure_code=None, limit=100):
        """Get price data"""
        if 'prices' not in cls._cache:
            price_file = DATA_DIR / 'processed/pricevision/all_prices_normalized.parquet'
            if price_file.exists():
                try:
                    df = pd.read_parquet(price_file)
                    # Sample for memory efficiency
                    if len(df) > 50000:
                        df = df.sample(n=50000, random_state=42)
                    cls._cache['prices'] = df.to_dict('records')
                except Exception:
                    cls._cache['prices'] = []
            else:
                cls._cache['prices'] = []

        prices = cls._cache['prices']
        if hospital_id:
            prices = [p for p in prices if str(p.get('npi', p.get('hospital_id', ''))) == str(hospital_id)]
        if procedure_code:
            prices = [p for p in prices if str(p.get('code', p.get('hcpcs_code', ''))) == str(procedure_code)]
        return prices[:limit]

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
