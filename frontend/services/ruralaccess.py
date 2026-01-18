"""
RuralAccess Data Service
Load healthcare access and shortage data - OPTIMIZED
"""
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent
DATA_DIR = BASE_DIR / 'data'


class RuralAccessService:
    _cache = {}
    _df_cache = {}

    @classmethod
    def _get_hpsa_df(cls):
        """Get HPSA DataFrame (cached)"""
        if 'hpsa_df' not in cls._df_cache:
            hpsa_file = DATA_DIR / 'processed/ruralaccess/hpsa_designations.parquet'
            if hpsa_file.exists():
                cls._df_cache['hpsa_df'] = pd.read_parquet(hpsa_file)
            else:
                raw_file = DATA_DIR / 'raw/ruralaccess/hrsa_hpsa.csv'
                if raw_file.exists():
                    cls._df_cache['hpsa_df'] = pd.read_csv(raw_file, low_memory=False, nrows=10000)
                else:
                    cls._df_cache['hpsa_df'] = pd.DataFrame()
        return cls._df_cache['hpsa_df']

    @classmethod
    def _get_counties_df(cls):
        """Get counties DataFrame (cached)"""
        if 'counties_df' not in cls._df_cache:
            county_file = DATA_DIR / 'processed/ruralaccess/county_shortage_summary.parquet'
            if county_file.exists():
                cls._df_cache['counties_df'] = pd.read_parquet(county_file)
            else:
                cls._df_cache['counties_df'] = pd.DataFrame()
        return cls._df_cache['counties_df']

    @classmethod
    def get_hpsa_designations(cls, state=None, discipline=None, limit=100):
        """Get Health Professional Shortage Areas"""
        df = cls._get_hpsa_df()
        if df.empty:
            return []

        if state:
            state_col = 'state' if 'state' in df.columns else 'Common State Name'
            df = df[df[state_col] == state]

        if discipline:
            disc_col = 'discipline' if 'discipline' in df.columns else 'HPSA Discipline Class'
            df = df[df[disc_col].fillna('').str.lower().str.contains(discipline.lower(), regex=False)]

        return df.head(limit).to_dict('records')

    @classmethod
    def get_hpsa(cls, hpsa_id):
        """Get single HPSA by ID"""
        df = cls._get_hpsa_df()
        if df.empty:
            return None

        hpsa_str = str(hpsa_id)
        id_col = 'hpsa_id' if 'hpsa_id' in df.columns else 'HPSA ID'
        matches = df[df[id_col].astype(str) == hpsa_str]
        if not matches.empty:
            return matches.iloc[0].to_dict()
        return None

    @classmethod
    def get_counties(cls, state=None, limit=100):
        """Get county-level data"""
        df = cls._get_counties_df()
        if df.empty:
            return []

        if state:
            df = df[df['state'] == state]

        return df.head(limit).to_dict('records')

    @classmethod
    def get_county(cls, fips):
        """Get single county by FIPS code"""
        df = cls._get_counties_df()
        if df.empty:
            return None

        fips_str = str(fips)
        matches = df[df['county_fips'].astype(str) == fips_str]
        if not matches.empty:
            return matches.iloc[0].to_dict()
        return None

    @classmethod
    def get_fqhc_locations(cls, state=None, limit=100):
        """Get Federally Qualified Health Centers"""
        if 'fqhc_df' not in cls._df_cache:
            fqhc_file = DATA_DIR / 'processed/ruralaccess/fqhc_locations.parquet'
            if fqhc_file.exists():
                cls._df_cache['fqhc_df'] = pd.read_parquet(fqhc_file)
            else:
                cls._df_cache['fqhc_df'] = pd.DataFrame()

        df = cls._df_cache['fqhc_df']
        if df.empty:
            return []

        if state:
            df = df[df['state'] == state]

        return df.head(limit).to_dict('records')

    @classmethod
    def get_hospital_closures(cls, limit=100):
        """Get rural hospital closures"""
        if 'closures_df' not in cls._df_cache:
            closure_file = DATA_DIR / 'processed/ruralaccess/rural_hospital_closures.parquet'
            if closure_file.exists():
                cls._df_cache['closures_df'] = pd.read_parquet(closure_file)
            else:
                cls._df_cache['closures_df'] = pd.DataFrame()

        df = cls._df_cache['closures_df']
        if df.empty:
            return []

        return df.head(limit).to_dict('records')

    @classmethod
    def get_states(cls):
        """Get list of states (cached)"""
        if 'states' not in cls._cache:
            df = cls._get_hpsa_df()
            if df.empty:
                cls._cache['states'] = []
            else:
                state_col = 'state' if 'state' in df.columns else 'Common State Name'
                states = df[state_col].dropna().unique()
                cls._cache['states'] = sorted([s for s in states if len(str(s)) == 2])
        return cls._cache['states']

    @classmethod
    def get_stats(cls):
        """Get summary statistics (cached)"""
        if 'stats' not in cls._cache:
            hpsa_df = cls._get_hpsa_df()
            counties_df = cls._get_counties_df()
            fqhc_list = cls.get_fqhc_locations(limit=50000)
            closures_list = cls.get_hospital_closures(limit=1000)

            # Count by discipline
            disciplines = {}
            if not hpsa_df.empty:
                disc_col = 'discipline' if 'discipline' in hpsa_df.columns else 'HPSA Discipline Class'
                disciplines = hpsa_df[disc_col].value_counts().to_dict()

            cls._cache['stats'] = {
                'total_hpsas': len(hpsa_df),
                'total_counties': len(counties_df),
                'total_fqhcs': len(fqhc_list),
                'hospital_closures': len(closures_list),
                'states_covered': len(cls.get_states()),
                'by_discipline': disciplines
            }
        return cls._cache['stats']

    @classmethod
    def get_shortage_map_data(cls):
        """Get data formatted for map visualization (cached)"""
        if 'map_data' not in cls._cache:
            df = cls._get_hpsa_df()
            if df.empty or 'latitude' not in df.columns or 'longitude' not in df.columns:
                cls._cache['map_data'] = []
            else:
                # Filter for valid coordinates
                df_valid = df.dropna(subset=['latitude', 'longitude']).head(5000)
                map_data = []
                for _, row in df_valid.iterrows():
                    map_data.append({
                        'hpsa_id': row.get('hpsa_id'),
                        'name': row.get('hpsa_name'),
                        'state': row.get('state'),
                        'county': row.get('county'),
                        'county_fips': row.get('county_fips'),
                        'lat': row.get('latitude'),
                        'lng': row.get('longitude'),
                        'shortage_score': row.get('hpsa_score', 0),
                        'population': row.get('population', 0),
                        'discipline': row.get('discipline')
                    })
                cls._cache['map_data'] = map_data
        return cls._cache['map_data']
