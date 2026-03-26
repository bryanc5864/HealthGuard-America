"""
RuralAccess Data Service
Load healthcare access and shortage data - OPTIMIZED
"""
import pandas as pd
from pathlib import Path
from . import VALID_US_STATES

BASE_DIR = Path(__file__).parent.parent.parent
DATA_DIR = BASE_DIR / 'data'


class RuralAccessService:
    _cache = {}
    _df_cache = {}
    _hpsa_by_id = None
    _county_by_fips = None

    @classmethod
    def _get_hpsa_df(cls):
        """Get HPSA DataFrame (cached)"""
        if 'hpsa_df' not in cls._df_cache:
            # Try multiple file locations
            possible_files = [
                DATA_DIR / 'processed/ruralaccess/hpsa_designations.parquet',
                DATA_DIR / 'processed/ruralaccess/hpsa_designations.csv',
                DATA_DIR / 'raw/ruralaccess/hrsa_hpsa.csv',
            ]
            for f in possible_files:
                if f.exists():
                    if f.suffix == '.parquet':
                        cls._df_cache['hpsa_df'] = pd.read_parquet(f)
                    else:
                        cls._df_cache['hpsa_df'] = pd.read_csv(f, low_memory=False)
                    break
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
    def get_hpsa_designations(cls, state=None, discipline=None, shortage_level=None,
                               rural_status=None, designation_type=None, limit=100):
        """Get Health Professional Shortage Areas

        Args:
            state: Filter by state abbreviation (optional)
            discipline: Filter by discipline type (optional)
            shortage_level: Filter by shortage severity - 'critical', 'high', 'moderate', 'low' (optional)
            rural_status: Filter by rural status - 'Rural', 'Non-Rural', 'Partially Rural' (optional)
            designation_type: Filter by designation type (optional)
            limit: Maximum number of records to return. Use 0 or None for all records.
        """
        df = cls._get_hpsa_df()
        if df.empty:
            return []

        if state:
            state_col = 'state' if 'state' in df.columns else 'Common State Name'
            df = df[df[state_col] == state]

        if discipline:
            disc_col = 'discipline' if 'discipline' in df.columns else 'HPSA Discipline Class'
            df = df[df[disc_col].fillna('').str.lower().str.contains(discipline.lower(), regex=False)]

        if shortage_level and 'hpsa_score' in df.columns:
            # Critical: 20-25, High: 15-19, Moderate: 10-14, Low: 0-9
            if shortage_level == 'critical':
                df = df[df['hpsa_score'] >= 20]
            elif shortage_level == 'high':
                df = df[(df['hpsa_score'] >= 15) & (df['hpsa_score'] < 20)]
            elif shortage_level == 'moderate':
                df = df[(df['hpsa_score'] >= 10) & (df['hpsa_score'] < 15)]
            elif shortage_level == 'low':
                df = df[df['hpsa_score'] < 10]

        if rural_status and 'rural_status' in df.columns:
            df = df[df['rural_status'] == rural_status]

        if designation_type and 'designation_type' in df.columns:
            df = df[df['designation_type'] == designation_type]

        # If limit is 0 or None, return all records
        if limit is None or limit == 0:
            return df.to_dict('records')

        return df.head(limit).to_dict('records')

    @classmethod
    def get_total_hpsa_count(cls, state=None, discipline=None, shortage_level=None,
                             rural_status=None, designation_type=None):
        """Get total count of HPSAs (for pagination info)"""
        df = cls._get_hpsa_df()
        if df.empty:
            return 0

        if state:
            state_col = 'state' if 'state' in df.columns else 'Common State Name'
            df = df[df[state_col] == state]

        if discipline:
            disc_col = 'discipline' if 'discipline' in df.columns else 'HPSA Discipline Class'
            df = df[df[disc_col].fillna('').str.lower().str.contains(discipline.lower(), regex=False)]

        if shortage_level and 'hpsa_score' in df.columns:
            if shortage_level == 'critical':
                df = df[df['hpsa_score'] >= 20]
            elif shortage_level == 'high':
                df = df[(df['hpsa_score'] >= 15) & (df['hpsa_score'] < 20)]
            elif shortage_level == 'moderate':
                df = df[(df['hpsa_score'] >= 10) & (df['hpsa_score'] < 15)]
            elif shortage_level == 'low':
                df = df[df['hpsa_score'] < 10]

        if rural_status and 'rural_status' in df.columns:
            df = df[df['rural_status'] == rural_status]

        if designation_type and 'designation_type' in df.columns:
            df = df[df['designation_type'] == designation_type]

        return len(df)

    @classmethod
    def _ensure_hpsa_index(cls):
        """Build HPSA ID -> row index for O(1) lookup"""
        if cls._hpsa_by_id is None:
            df = cls._get_hpsa_df()
            if df.empty:
                cls._hpsa_by_id = {}
            else:
                id_col = 'hpsa_id' if 'hpsa_id' in df.columns else 'HPSA ID'
                cls._hpsa_by_id = {str(v): i for i, v in enumerate(df[id_col].values)}

    @classmethod
    def get_hpsa(cls, hpsa_id):
        """Get single HPSA by ID - O(1) indexed lookup"""
        df = cls._get_hpsa_df()
        if df.empty:
            return None

        cls._ensure_hpsa_index()
        idx = cls._hpsa_by_id.get(str(hpsa_id))
        if idx is not None:
            return df.iloc[idx].to_dict()
        return None

    @classmethod
    def get_counties(cls, state=None, limit=100):
        """Get county-level data

        Args:
            state: Filter by state abbreviation (optional)
            limit: Maximum number of records to return. Use 0 or None for all records.
        """
        df = cls._get_counties_df()
        if df.empty:
            return []

        if state:
            df = df[df['state'] == state]

        # If limit is 0 or None, return all records
        if limit is None or limit == 0:
            return df.to_dict('records')

        return df.head(limit).to_dict('records')

    @classmethod
    def get_total_counties_count(cls, state=None):
        """Get total count of counties (for pagination info)"""
        df = cls._get_counties_df()
        if df.empty:
            return 0

        if state:
            df = df[df['state'] == state]

        return len(df)

    @classmethod
    def _ensure_county_fips_index(cls):
        """Build county FIPS -> row index for O(1) lookup"""
        if cls._county_by_fips is None:
            df = cls._get_counties_df()
            if df.empty:
                cls._county_by_fips = {}
            else:
                cls._county_by_fips = {str(v): i for i, v in enumerate(df['county_fips'].values)}

    @classmethod
    def get_county(cls, fips):
        """Get single county by FIPS code - O(1) indexed lookup"""
        df = cls._get_counties_df()
        if df.empty:
            return None

        cls._ensure_county_fips_index()
        idx = cls._county_by_fips.get(str(fips))
        if idx is not None:
            return df.iloc[idx].to_dict()
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
        """Get list of valid US states/territories (cached)"""
        if 'states' not in cls._cache:
            df = cls._get_hpsa_df()
            if df.empty:
                cls._cache['states'] = []
            else:
                state_col = 'state' if 'state' in df.columns else 'Common State Name'
                states = df[state_col].dropna().unique()
                # Filter to only valid US states/territories (50 states + DC + territories)
                cls._cache['states'] = sorted([s for s in states if str(s).upper() in VALID_US_STATES])
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
        """Get data formatted for map visualization (cached, vectorized)"""
        if 'map_data' not in cls._cache:
            df = cls._get_hpsa_df()
            if df.empty or 'latitude' not in df.columns or 'longitude' not in df.columns:
                cls._cache['map_data'] = []
            else:
                df_valid = df.dropna(subset=['latitude', 'longitude']).head(5000)
                col_map = {
                    'hpsa_id': 'hpsa_id', 'hpsa_name': 'name',
                    'state': 'state', 'county': 'county',
                    'county_fips': 'county_fips', 'latitude': 'lat',
                    'longitude': 'lng', 'hpsa_score': 'shortage_score',
                    'population': 'population', 'discipline': 'discipline'
                }
                avail_cols = [c for c in col_map if c in df_valid.columns]
                result_df = df_valid[avail_cols].rename(columns=col_map)
                if 'shortage_score' not in result_df.columns:
                    result_df['shortage_score'] = 0
                if 'population' not in result_df.columns:
                    result_df['population'] = 0
                cls._cache['map_data'] = result_df.to_dict('records')
        return cls._cache['map_data']

    @classmethod
    def get_analytics(cls):
        """Get comprehensive analytics data (cached)"""
        if 'analytics' not in cls._cache:
            df = cls._get_hpsa_df()
            if df.empty:
                cls._cache['analytics'] = {}
                return cls._cache['analytics']

            analytics = {}

            # Shortage level distribution
            if 'hpsa_score' in df.columns:
                def get_level(score):
                    if score >= 20:
                        return 'Critical'
                    elif score >= 15:
                        return 'High'
                    elif score >= 10:
                        return 'Moderate'
                    else:
                        return 'Low'

                df['shortage_level'] = df['hpsa_score'].apply(get_level)
                analytics['by_shortage_level'] = df['shortage_level'].value_counts().to_dict()
                analytics['avg_hpsa_score'] = round(df['hpsa_score'].mean(), 1)
                analytics['max_hpsa_score'] = int(df['hpsa_score'].max())
                analytics['min_hpsa_score'] = int(df['hpsa_score'].min())

                # Score distribution histogram (buckets of 5)
                analytics['score_distribution'] = {
                    '0-4': len(df[df['hpsa_score'] < 5]),
                    '5-9': len(df[(df['hpsa_score'] >= 5) & (df['hpsa_score'] < 10)]),
                    '10-14': len(df[(df['hpsa_score'] >= 10) & (df['hpsa_score'] < 15)]),
                    '15-19': len(df[(df['hpsa_score'] >= 15) & (df['hpsa_score'] < 20)]),
                    '20-25': len(df[df['hpsa_score'] >= 20]),
                }

            # Rural status distribution
            if 'rural_status' in df.columns:
                analytics['by_rural_status'] = df['rural_status'].value_counts().to_dict()

            # Designation type distribution
            if 'designation_type' in df.columns:
                analytics['by_designation_type'] = df['designation_type'].value_counts().to_dict()

            # State breakdown with stats
            if 'state' in df.columns:
                state_stats = []
                for state in df['state'].unique():
                    state_df = df[df['state'] == state]
                    state_stats.append({
                        'state': state,
                        'total_hpsas': len(state_df),
                        'avg_score': round(state_df['hpsa_score'].mean(), 1) if 'hpsa_score' in state_df.columns else 0,
                        'critical_count': len(state_df[state_df['hpsa_score'] >= 20]) if 'hpsa_score' in state_df.columns else 0,
                        'total_population': int(state_df['population'].sum()) if 'population' in state_df.columns else 0,
                    })
                # Sort by total HPSAs descending
                state_stats = sorted(state_stats, key=lambda x: x['total_hpsas'], reverse=True)
                analytics['by_state'] = state_stats

                # Top 10 states by critical shortage count
                top_critical = sorted(state_stats, key=lambda x: x['critical_count'], reverse=True)[:10]
                analytics['top_critical_states'] = top_critical

                # Top 10 states by average score
                top_avg_score = sorted(state_stats, key=lambda x: x['avg_score'], reverse=True)[:10]
                analytics['top_avg_score_states'] = top_avg_score

            # Population affected
            if 'population' in df.columns:
                analytics['total_population_affected'] = int(df['population'].sum())
                analytics['avg_population_per_hpsa'] = int(df['population'].mean())

                # Population by shortage level
                if 'shortage_level' in df.columns:
                    pop_by_level = df.groupby('shortage_level')['population'].sum().to_dict()
                    analytics['population_by_shortage_level'] = {k: int(v) for k, v in pop_by_level.items()}

            # Poverty analysis
            if 'poverty_rate' in df.columns:
                analytics['avg_poverty_rate'] = round(df['poverty_rate'].mean(), 1)
                analytics['high_poverty_hpsas'] = len(df[df['poverty_rate'] > 20])

                # Correlation: high poverty areas tend to have higher shortage scores
                if 'hpsa_score' in df.columns:
                    high_poverty = df[df['poverty_rate'] > 20]
                    low_poverty = df[df['poverty_rate'] <= 20]
                    analytics['avg_score_high_poverty'] = round(high_poverty['hpsa_score'].mean(), 1) if len(high_poverty) > 0 else 0
                    analytics['avg_score_low_poverty'] = round(low_poverty['hpsa_score'].mean(), 1) if len(low_poverty) > 0 else 0

            cls._cache['analytics'] = analytics
        return cls._cache['analytics']

    @classmethod
    def get_designation_types(cls):
        """Get list of unique designation types"""
        df = cls._get_hpsa_df()
        if df.empty or 'designation_type' not in df.columns:
            return []
        return sorted(df['designation_type'].dropna().unique().tolist())

    @classmethod
    def get_rural_statuses(cls):
        """Get list of unique rural statuses"""
        df = cls._get_hpsa_df()
        if df.empty or 'rural_status' not in df.columns:
            return []
        return sorted(df['rural_status'].dropna().unique().tolist())
