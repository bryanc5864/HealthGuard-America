"""
PriceVision Data Service
Load hospital and procedure pricing data - OPTIMIZED
"""
import pandas as pd
import numpy as np
import pyarrow.parquet as pq
from pathlib import Path
from . import VALID_US_STATES

BASE_DIR = Path(__file__).parent.parent.parent
DATA_DIR = BASE_DIR / 'data'


def clean_nan_records(records):
    """Replace NaN values with None in list of dicts"""
    cleaned = []
    for record in records:
        clean_record = {}
        for key, value in record.items():
            if pd.isna(value):
                clean_record[key] = None
            else:
                clean_record[key] = value
        cleaned.append(clean_record)
    return cleaned


class PriceVisionService:
    _cache = {}
    _price_file = None
    _hospital_by_id = None  # Fast lookup by facility ID

    @classmethod
    def get_procedures(cls, limit=100, search=None):
        """Get list of medical procedures"""
        if 'procedures' not in cls._cache:
            proc_file = DATA_DIR / 'processed/pricevision/medicare_procedures.csv'
            if proc_file.exists():
                df = pd.read_csv(proc_file)
                cls._cache['procedures'] = clean_nan_records(df.to_dict('records'))
            else:
                cls._cache['procedures'] = []

        procedures = cls._cache['procedures']
        if search:
            search = search.lower()
            procedures = [p for p in procedures if search in str(p.get('canonical_description', '')).lower()
                         or search in str(p.get('hcpcs_code', '')).lower()]
        return procedures[:limit]

    @classmethod
    def _ensure_hospital_cache(cls):
        """Ensure hospital data is loaded and indexed"""
        if 'hospitals' not in cls._cache:
            hosp_file = DATA_DIR / 'raw/pricevision/hospital_general_info.csv'
            if hosp_file.exists():
                df = pd.read_csv(hosp_file)
                cls._cache['hospitals'] = clean_nan_records(df.to_dict('records'))
            else:
                cls._cache['hospitals'] = []
            # Build fast lookup index
            cls._hospital_by_id = {
                str(h.get('Facility ID', '')): h for h in cls._cache['hospitals']
            }

    @classmethod
    def get_hospital_info_cache(cls):
        """Get cached hospital info dict for fast lookups"""
        cls._ensure_hospital_cache()
        if 'hospital_info' not in cls._cache:
            cls._cache['hospital_info'] = {
                str(h.get('Facility ID', '')): {
                    'name': h.get('Facility Name', ''),
                    'city': h.get('City/Town', ''),
                    'state': h.get('State', '')
                }
                for h in cls._cache['hospitals']
            }
        return cls._cache['hospital_info']

    @classmethod
    def get_hospitals(cls, state=None, limit=100):
        """Get list of hospitals"""
        cls._ensure_hospital_cache()
        hospitals = cls._cache['hospitals']
        if state:
            hospitals = [h for h in hospitals if h.get('State', '') == state]
        return hospitals[:limit]

    @classmethod
    def get_hospital(cls, facility_id):
        """Get single hospital by Facility ID - O(1) lookup"""
        cls._ensure_hospital_cache()
        return cls._hospital_by_id.get(str(facility_id))

    @classmethod
    def get_prices(cls, hospital_npi=None, procedure_code=None, state=None, limit=50):
        """Get price data using predicate pushdown - only loads matching rows"""
        if not hospital_npi and not procedure_code:
            return []  # Don't load without a filter

        price_file = DATA_DIR / 'processed/pricevision/all_prices_normalized.parquet'
        if not price_file.exists():
            return []

        try:
            # Get cached hospital info (fast - reuses cached data)
            hospital_cache = cls.get_hospital_info_cache()
            valid_npis = set(hospital_cache.keys())

            # If state filter provided, get hospital IDs in that state
            state_hospital_ids = None
            if state:
                state_hospital_ids = set(
                    npi for npi, info in hospital_cache.items()
                    if info.get('state', '') == state
                )

            # Build filter for predicate pushdown
            filters = []
            if procedure_code:
                filters.append(('procedure_code', '==', str(procedure_code)))
            if hospital_npi:
                filters.append(('hospital_npi', '==', str(hospital_npi)))

            # Read with filter - only loads matching rows from disk
            columns = ['description', 'procedure_code', 'gross_charge', 'hospital_npi',
                       'cash_price', 'min_price', 'max_price', 'payer_name']

            if filters:
                df = pd.read_parquet(price_file, columns=columns, filters=filters)
            else:
                # Fallback - shouldn't happen but handle gracefully
                df = pd.read_parquet(price_file, columns=columns)
                if len(df) > 5000:
                    df = df.sample(n=5000, random_state=42)

            # Filter by state if provided
            if state_hospital_ids:
                df = df[df['hospital_npi'].astype(str).isin(state_hospital_ids)]

            # Filter to only hospitals with valid info (exclude unknown hospitals)
            df = df[df['hospital_npi'].astype(str).isin(valid_npis)]

            # Filter out N/A records - must have description AND at least one price
            df = df[
                (df['description'].notna()) &
                (df['description'].str.strip() != '') &
                (df['cash_price'].notna() | df['gross_charge'].notna())
            ]

            # Sort by cash_price for best prices first
            if 'cash_price' in df.columns:
                df = df.sort_values('cash_price', ascending=True, na_position='last')

            # Deduplicate by hospital - keep only the best (lowest) price per hospital
            # Only for procedure searches, not for hospital detail pages
            if procedure_code and not hospital_npi:
                df = df.drop_duplicates(subset=['hospital_npi'], keep='first')

            # Add hospital info to results
            results = clean_nan_records(df.head(limit).to_dict('records'))
            for r in results:
                npi = str(r.get('hospital_npi', ''))
                if npi in hospital_cache:
                    r['hospital_name'] = hospital_cache[npi]['name']
                    r['hospital_city'] = hospital_cache[npi]['city']
                    r['hospital_state'] = hospital_cache[npi]['state']
            return results
        except Exception as e:
            print(f"Error loading prices: {e}")
            return []

    @classmethod
    def get_states(cls):
        """Get list of valid US states/territories with hospitals"""
        if 'states_list' not in cls._cache:
            hospital_info = cls.get_hospital_info_cache()
            states = set()
            for info in hospital_info.values():
                state = info.get('state', '')
                # Filter to only valid US states/territories (50 states + DC + territories)
                if state and str(state).upper() in VALID_US_STATES:
                    states.add(state)
            cls._cache['states_list'] = sorted(states)
        return cls._cache['states_list']

    @classmethod
    def get_hospitals_with_mrf(cls):
        """Get set of hospital IDs that have MRF/pricing data"""
        if 'hospitals_with_mrf' not in cls._cache:
            price_file = DATA_DIR / 'processed/pricevision/all_prices_normalized.parquet'
            if price_file.exists():
                try:
                    df = pd.read_parquet(price_file, columns=['hospital_npi'])
                    cls._cache['hospitals_with_mrf'] = set(df['hospital_npi'].astype(str).unique())
                except Exception as e:
                    print(f"Error loading MRF hospital IDs: {e}")
                    cls._cache['hospitals_with_mrf'] = set()
            else:
                cls._cache['hospitals_with_mrf'] = set()
        return cls._cache['hospitals_with_mrf']

    @classmethod
    def get_batch_transparency_data(cls, hospital_ids):
        """Get transparency data for multiple hospitals in one query (avoids N+1)."""
        if not hospital_ids:
            return {}

        price_file = DATA_DIR / 'processed/pricevision/all_prices_normalized.parquet'
        if not price_file.exists():
            return {}

        try:
            # Read all prices for the specified hospitals in one query
            df = pd.read_parquet(price_file, columns=[
                'hospital_npi', 'cash_price', 'gross_charge', 'payer_name', 'description'
            ])

            # Filter to only requested hospitals
            hospital_ids_str = set(str(h) for h in hospital_ids)
            df = df[df['hospital_npi'].astype(str).isin(hospital_ids_str)]

            # Group by hospital and calculate transparency metrics
            result = {}
            for npi, group in df.groupby(df['hospital_npi'].astype(str)):
                total = len(group)
                if total == 0:
                    continue

                prices_with_cash = group['cash_price'].notna().sum()
                prices_with_gross = group['gross_charge'].notna().sum()
                prices_with_payer = group['payer_name'].notna().sum()

                # Calculate transparency score (same logic as calculate_transparency_score)
                score = 30  # Base score for having data

                cash_ratio = prices_with_cash / total
                score += int(cash_ratio * 20)

                gross_ratio = prices_with_gross / total
                score += int(gross_ratio * 15)

                payer_ratio = prices_with_payer / total
                score += int(payer_ratio * 15)

                # Volume bonus
                if total >= 100:
                    score += 20
                elif total >= 50:
                    score += 15
                elif total >= 20:
                    score += 10
                elif total >= 5:
                    score += 5

                result[npi] = {
                    'transparency_score': min(score, 100),
                    'total_prices': total,
                    'prices_with_cash': int(prices_with_cash),
                    'cash_ratio': cash_ratio
                }

            return result
        except Exception as e:
            print(f"Error in batch transparency: {e}")
            return {}

    @classmethod
    def get_stats(cls):
        """Get summary statistics"""
        hospitals = cls.get_hospitals(limit=10000)
        procedures = cls.get_procedures(limit=10000)
        hospitals_with_mrf = cls.get_hospitals_with_mrf()
        return {
            'total_hospitals': len(hospitals),
            'total_procedures': len(procedures),
            'states_covered': len(cls.get_states()),
            'hospitals_with_mrf': len(hospitals_with_mrf)
        }
