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
            # Normalize ALL CAPS text from CMS data to title case
            for h in cls._cache['hospitals']:
                for field in ['Facility Name', 'City/Town', 'Address']:
                    val = h.get(field, '')
                    if val and val == val.upper() and len(val) > 2:
                        h[field] = val.title()

            # Build fast lookup index AND hospital info cache in one pass
            cls._hospital_by_id = {}
            cls._cache['hospital_info'] = {}
            for h in cls._cache['hospitals']:
                fid = str(h.get('Facility ID', ''))
                cls._hospital_by_id[fid] = h
                cls._cache['hospital_info'][fid] = {
                    'name': h.get('Facility Name', ''),
                    'city': h.get('City/Town', ''),
                    'state': h.get('State', '')
                }

    @classmethod
    def get_hospital_info_cache(cls):
        """Get cached hospital info dict for fast lookups"""
        cls._ensure_hospital_cache()
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
            price_file = DATA_DIR / 'processed/pricevision/prices_sample.parquet'
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
        """Get set of hospital IDs that have MRF/pricing data (with file cache)"""
        if 'hospitals_with_mrf' not in cls._cache:
            price_file = DATA_DIR / 'processed/pricevision/all_prices_normalized.parquet'
            if not price_file.exists():
                price_file = DATA_DIR / 'processed/pricevision/prices_sample.parquet'
            # Try to load from pre-computed cache file first (instant)
            cache_file = DATA_DIR / 'processed/pricevision/hospital_npi_cache.txt'
            if cache_file.exists():
                try:
                    with open(cache_file, 'r') as f:
                        cls._cache['hospitals_with_mrf'] = set(line.strip() for line in f if line.strip())
                    return cls._cache['hospitals_with_mrf']
                except Exception:
                    pass

            if price_file.exists():
                try:
                    # Read just the NPI column with pandas (faster than pyarrow for this)
                    df = pd.read_parquet(price_file, columns=['hospital_npi'])
                    cls._cache['hospitals_with_mrf'] = set(df['hospital_npi'].astype(str).unique())

                    # Cache to file for future fast loading
                    try:
                        cache_file.parent.mkdir(parents=True, exist_ok=True)
                        with open(cache_file, 'w') as f:
                            for npi in sorted(cls._cache['hospitals_with_mrf']):
                                f.write(npi + '\n')
                    except Exception:
                        pass
                except Exception as e:
                    print(f"Error loading MRF hospital IDs: {e}")
                    cls._cache['hospitals_with_mrf'] = set()
            else:
                cls._cache['hospitals_with_mrf'] = set()
        return cls._cache['hospitals_with_mrf']

    @classmethod
    def _get_all_transparency_data(cls):
        """Pre-compute and cache transparency data for ALL hospitals (one-time load)."""
        if 'all_transparency' in cls._cache:
            return cls._cache['all_transparency']

        price_file = DATA_DIR / 'processed/pricevision/all_prices_normalized.parquet'
        if not price_file.exists():
            price_file = DATA_DIR / 'processed/pricevision/prices_sample.parquet'
        if not price_file.exists():
            cls._cache['all_transparency'] = {}
            return {}

        try:
            # Read only the columns we need for aggregation
            df = pd.read_parquet(price_file, columns=[
                'hospital_npi', 'cash_price', 'gross_charge', 'payer_name'
            ])

            # Pre-aggregate by hospital using vectorized operations
            df['hospital_npi'] = df['hospital_npi'].astype(str)
            df['has_cash'] = df['cash_price'].notna().astype(int)
            df['has_gross'] = df['gross_charge'].notna().astype(int)
            df['has_payer'] = df['payer_name'].notna().astype(int)

            # Group and aggregate in one pass
            agg = df.groupby('hospital_npi').agg({
                'has_cash': ['sum', 'count'],
                'has_gross': 'sum',
                'has_payer': 'sum'
            }).reset_index()

            agg.columns = ['hospital_npi', 'prices_with_cash', 'total_prices', 'prices_with_gross', 'prices_with_payer']

            # Calculate transparency scores vectorized
            result = {}
            for _, row in agg.iterrows():
                npi = row['hospital_npi']
                total = row['total_prices']
                if total == 0:
                    continue

                cash_ratio = row['prices_with_cash'] / total
                gross_ratio = row['prices_with_gross'] / total
                payer_ratio = row['prices_with_payer'] / total

                score = 30  # Base score
                score += int(cash_ratio * 20)
                score += int(gross_ratio * 15)
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
                    'total_prices': int(total),
                    'prices_with_cash': int(row['prices_with_cash']),
                    'cash_ratio': cash_ratio
                }

            cls._cache['all_transparency'] = result
            return result
        except Exception as e:
            print(f"Error computing transparency data: {e}")
            cls._cache['all_transparency'] = {}
            return {}

    @classmethod
    def get_batch_transparency_data(cls, hospital_ids):
        """Get transparency data for multiple hospitals (uses cached data)."""
        if not hospital_ids:
            return {}

        # Use cached aggregated data
        all_data = cls._get_all_transparency_data()

        # Filter to requested hospitals
        hospital_ids_str = set(str(h) for h in hospital_ids)
        return {npi: data for npi, data in all_data.items() if npi in hospital_ids_str}

    @classmethod
    def get_stats(cls):
        """Get summary statistics (cached)"""
        if 'stats' not in cls._cache:
            hospitals = cls.get_hospitals(limit=10000)
            procedures = cls.get_procedures(limit=10000)
            hospitals_with_mrf = cls.get_hospitals_with_mrf()
            cls._cache['stats'] = {
                'total_hospitals': len(hospitals),
                'total_procedures': len(procedures),
                'states_covered': len(cls.get_states()),
                'hospitals_with_mrf': len(hospitals_with_mrf)
            }
        return cls._cache['stats']

    @classmethod
    def get_top_hospitals(cls, limit=50):
        """Get hospitals with the most pricing data (highest transparency scores).
        Cached as 'top_hospitals' in _cache."""
        if 'top_hospitals' not in cls._cache:
            all_transparency = cls._get_all_transparency_data()
            hospital_info = cls.get_hospital_info_cache()

            # Build list of hospitals ranked by transparency score
            ranked = []
            for npi, tdata in all_transparency.items():
                info = hospital_info.get(npi, {})
                ranked.append({
                    'npi': npi,
                    'name': info.get('name', ''),
                    'city': info.get('city', ''),
                    'state': info.get('state', ''),
                    'transparency_score': tdata.get('transparency_score', 0),
                    'total_prices': tdata.get('total_prices', 0),
                    'prices_with_cash': tdata.get('prices_with_cash', 0),
                    'cash_ratio': tdata.get('cash_ratio', 0)
                })

            # Sort by transparency score descending, then total_prices descending
            ranked.sort(key=lambda x: (x['transparency_score'], x['total_prices']), reverse=True)
            cls._cache['top_hospitals'] = ranked

        return cls._cache['top_hospitals'][:limit]

    @classmethod
    def get_procedure_stats(cls, procedure_code):
        """Get mean/median/min/max price statistics for a procedure code.
        Cached per procedure code in _cache."""
        cache_key = f'proc_stats_{procedure_code}'
        if cache_key not in cls._cache:
            price_file = DATA_DIR / 'processed/pricevision/all_prices_normalized.parquet'
            if not price_file.exists():
                price_file = DATA_DIR / 'processed/pricevision/prices_sample.parquet'
            if not price_file.exists():
                cls._cache[cache_key] = {}
                return cls._cache[cache_key]

            try:
                filters = [('procedure_code', '==', str(procedure_code))]
                df = pd.read_parquet(
                    price_file,
                    columns=['procedure_code', 'cash_price', 'gross_charge'],
                    filters=filters
                )

                cash_prices = df['cash_price'].dropna()
                gross_charges = df['gross_charge'].dropna()

                stats = {
                    'procedure_code': str(procedure_code),
                    'sample_size': len(df),
                }

                if len(cash_prices) > 0:
                    stats.update({
                        'cash_mean': float(np.mean(cash_prices)),
                        'cash_median': float(np.median(cash_prices)),
                        'cash_min': float(np.min(cash_prices)),
                        'cash_max': float(np.max(cash_prices)),
                        'cash_std': float(np.std(cash_prices)) if len(cash_prices) > 1 else 0.0,
                        'cash_count': int(len(cash_prices)),
                    })
                else:
                    stats.update({
                        'cash_mean': 0, 'cash_median': 0,
                        'cash_min': 0, 'cash_max': 0,
                        'cash_std': 0, 'cash_count': 0,
                    })

                if len(gross_charges) > 0:
                    stats.update({
                        'gross_mean': float(np.mean(gross_charges)),
                        'gross_median': float(np.median(gross_charges)),
                        'gross_min': float(np.min(gross_charges)),
                        'gross_max': float(np.max(gross_charges)),
                        'gross_count': int(len(gross_charges)),
                    })
                else:
                    stats.update({
                        'gross_mean': 0, 'gross_median': 0,
                        'gross_min': 0, 'gross_max': 0,
                        'gross_count': 0,
                    })

                cls._cache[cache_key] = stats
            except Exception as e:
                print(f'Error computing procedure stats for {procedure_code}: {e}')
                cls._cache[cache_key] = {}

        return cls._cache[cache_key]

    @classmethod
    def get_state_stats(cls):
        """Get per-state hospital counts and compliance data.
        Cached as 'state_stats' in _cache."""
        if 'state_stats' not in cls._cache:
            hospital_info = cls.get_hospital_info_cache()
            hospitals_with_mrf = cls.get_hospitals_with_mrf()

            # Count hospitals per state from hospital_info cache
            state_counts = {}
            for npi, info in hospital_info.items():
                state = info.get('state', '')
                if not state or len(str(state)) != 2:
                    continue
                if state not in state_counts:
                    state_counts[state] = {'total': 0, 'compliant': 0, 'npis': []}
                state_counts[state]['total'] += 1
                state_counts[state]['npis'].append(npi)

            # Cross-reference with hospitals_with_mrf for compliance rates
            for state, data in state_counts.items():
                compliant = sum(1 for npi in data['npis'] if npi in hospitals_with_mrf)
                data['compliant'] = compliant
                data['compliance_rate'] = round(
                    (compliant / data['total'] * 100) if data['total'] > 0 else 0, 1
                )
                # Remove npis list to keep cache lightweight
                del data['npis']

            cls._cache['state_stats'] = state_counts

        return cls._cache['state_stats']
