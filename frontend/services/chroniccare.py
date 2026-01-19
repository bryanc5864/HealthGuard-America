"""
ChronicCare Data Service
Load chronic disease and food environment data - OPTIMIZED
"""
import pandas as pd
from pathlib import Path
from . import VALID_US_STATES

BASE_DIR = Path(__file__).parent.parent.parent
DATA_DIR = BASE_DIR / 'data'


class ChronicCareService:
    _cache = {}
    _df_cache = {}

    @classmethod
    def _get_county_health_df(cls):
        """Get county health DataFrame (cached)"""
        if 'county_health_df' not in cls._df_cache:
            # Try multiple file locations
            possible_files = [
                DATA_DIR / 'processed/chroniccare/chroniccare_merged.parquet',
                DATA_DIR / 'processed/chroniccare/chroniccare_merged.csv',
                DATA_DIR / 'processed/chroniccare/county_health_metrics.csv',
            ]
            for f in possible_files:
                if f.exists():
                    if f.suffix == '.parquet':
                        cls._df_cache['county_health_df'] = pd.read_parquet(f)
                    else:
                        cls._df_cache['county_health_df'] = pd.read_csv(f)
                    break
            else:
                cls._df_cache['county_health_df'] = pd.DataFrame()
        return cls._df_cache['county_health_df']

    @classmethod
    def get_county_health(cls, state=None, limit=100):
        """Get county-level chronic disease data"""
        df = cls._get_county_health_df()
        if df.empty:
            return []

        if state:
            # Try multiple column names for state
            state_col = None
            for col in ['state_abbr', 'state', 'State']:
                if col in df.columns:
                    state_col = col
                    break
            if state_col:
                df = df[df[state_col] == state]

        return df.head(limit).to_dict('records')

    @classmethod
    def get_county(cls, fips):
        """Get single county by FIPS"""
        df = cls._get_county_health_df()
        if df.empty:
            return None

        fips_str = str(fips)
        fips_col = 'fips' if 'fips' in df.columns else 'FIPS'
        matches = df[df[fips_col].astype(str) == fips_str]
        if not matches.empty:
            return matches.iloc[0].to_dict()
        return None

    @classmethod
    def get_cdc_places(cls, state=None, limit=100):
        """Get CDC PLACES data"""
        if 'cdc_places_df' not in cls._df_cache:
            places_file = DATA_DIR / 'processed/chroniccare/cdc_places_county.csv'
            if places_file.exists():
                cls._df_cache['cdc_places_df'] = pd.read_csv(places_file)
            else:
                cls._df_cache['cdc_places_df'] = pd.DataFrame()

        df = cls._df_cache['cdc_places_df']
        if df.empty:
            return []

        if state:
            # Try multiple column names for state
            state_col = None
            for col in ['StateAbbr', 'state_abbr', 'state']:
                if col in df.columns:
                    state_col = col
                    break
            if state_col:
                df = df[df[state_col] == state]

        return df.head(limit).to_dict('records')

    @classmethod
    def get_food_environment(cls, state=None, limit=100):
        """Get USDA food environment data"""
        if 'food_env_df' not in cls._df_cache:
            food_file = DATA_DIR / 'processed/chroniccare/usda_food_environment.csv'
            if food_file.exists():
                cls._df_cache['food_env_df'] = pd.read_csv(food_file)
            else:
                cls._df_cache['food_env_df'] = pd.DataFrame()

        df = cls._df_cache['food_env_df']
        if df.empty:
            return []

        if state:
            # Try multiple column names for state
            state_col = None
            for col in ['State', 'state_abbr', 'state']:
                if col in df.columns:
                    state_col = col
                    break
            if state_col:
                df = df[df[state_col] == state]

        return df.head(limit).to_dict('records')

    @classmethod
    def get_correlations(cls):
        """Get disease-food correlations (cached) - all counties, no artificial cap"""
        if 'correlations' not in cls._cache:
            df = cls._get_county_health_df()
            if df.empty:
                cls._cache['correlations'] = []
            else:
                correlations = []
                # Process all counties - no artificial cap
                for _, row in df.iterrows():
                    diabetes = row.get('diabetes_prevalence', 0)
                    obesity = row.get('obesity_prevalence', 0)
                    fast_food = row.get('fast_food_restaurants_per_1000', row.get('FFRPTH16', 0))
                    food_insecurity = row.get('food_insecurity_rate', 0)

                    if diabetes and obesity:
                        correlations.append({
                            'fips': row.get('fips', ''),
                            'county': row.get('county_name', ''),
                            'state': row.get('state_abbr', ''),
                            'diabetes': float(diabetes) if diabetes else 0,
                            'obesity': float(obesity) if obesity else 0,
                            'fast_food': float(fast_food) if fast_food else 0,
                            'food_insecurity': float(food_insecurity) if food_insecurity else 0
                        })
                cls._cache['correlations'] = correlations
        return cls._cache['correlations']

    @classmethod
    def get_intervention_priorities(cls, limit=50):
        """Get counties prioritized for intervention (cached) with all ML features"""
        if 'priorities' not in cls._cache:
            df = cls._get_county_health_df()
            if df.empty:
                cls._cache['priorities'] = []
            else:
                # Calculate risk scores
                df = df.copy()
                df['diabetes_prev'] = pd.to_numeric(df.get('diabetes_prevalence', 0), errors='coerce').fillna(0)
                df['obesity_prev'] = pd.to_numeric(df.get('obesity_prevalence', 0), errors='coerce').fillna(0)
                df['heart_prev'] = pd.to_numeric(df.get('heart_disease_prevalence', 0), errors='coerce').fillna(0)

                df['risk_score'] = (df['diabetes_prev'] * 0.4 + df['obesity_prev'] * 0.35 + df['heart_prev'] * 0.25)
                df = df[df['risk_score'] > 0].sort_values('risk_score', ascending=False)

                priorities = []
                for _, row in df.iterrows():
                    score = row['risk_score']
                    # Include all ML-relevant features
                    priority_data = {
                        'fips': row.get('fips', ''),
                        'county': row.get('county_name', ''),
                        'state': row.get('state_abbr', ''),
                        'risk_score': round(score, 2),
                        'diabetes': row['diabetes_prev'],
                        'obesity': row['obesity_prev'],
                        'heart_disease': row['heart_prev'],
                        'priority': 'Critical' if score > 20 else 'High' if score > 18 else 'Medium',
                        # ML features - Food environment
                        'grocery_stores_per_1000': row.get('grocery_stores_per_1000', 0),
                        'fast_food_restaurants_per_1000': row.get('fast_food_restaurants_per_1000', 0),
                        'food_environment_index': row.get('food_environment_index', 0),
                        'food_insecurity_rate': row.get('food_insecurity_rate', 0),
                        'pct_limited_food_access': row.get('pct_limited_food_access', 0),
                        # ML features - Healthcare
                        'pcp_rate': row.get('pcp_rate', 0),
                        'mental_health_provider_rate': row.get('mental_health_provider_rate', 0),
                        'pct_uninsured': row.get('pct_uninsured', 0),
                        'preventable_hospitalizations': row.get('preventable_hospitalizations', 0),
                        # ML features - Socioeconomic
                        'median_household_income': row.get('median_household_income', 0),
                        'child_poverty_rate': row.get('child_poverty_rate', 0),
                        'income_inequality_ratio': row.get('income_inequality_ratio', 0),
                        'high_school_graduation_rate': row.get('high_school_graduation_rate', 0),
                        'pct_some_college': row.get('pct_some_college', 0),
                        # ML features - Behavioral
                        'physical_inactivity_prevalence': row.get('physical_inactivity_prevalence', 0),
                        'excessive_drinking_prevalence': row.get('excessive_drinking_prevalence', 0),
                        'smoking_prevalence': row.get('smoking_prevalence', 0),
                        'pct_insufficient_sleep': row.get('pct_insufficient_sleep', 0),
                        # ML features - Demographics
                        'pct_rural': row.get('pct_rural', 0),
                        # Additional for prioritizer
                        'chronic_disease_burden_score': row.get('chronic_disease_burden_score', 0),
                        'food_environment_score': row.get('food_environment_score', 50),
                        'high_bp_prevalence': row.get('high_bp_prevalence', 0),
                    }
                    priorities.append(priority_data)
                cls._cache['priorities'] = priorities
        return cls._cache['priorities'][:limit]

    @classmethod
    def get_states(cls):
        """Get list of valid US states/territories (cached)"""
        if 'states' not in cls._cache:
            df = cls._get_county_health_df()
            if df.empty:
                cls._cache['states'] = []
            else:
                state_col = None
                for col in ['state_abbr', 'state', 'State']:
                    if col in df.columns:
                        state_col = col
                        break
                if state_col:
                    states = df[state_col].dropna().unique()
                    # Filter to only valid US states/territories (50 states + DC + territories)
                    cls._cache['states'] = sorted([s for s in states if str(s).upper() in VALID_US_STATES])
                else:
                    cls._cache['states'] = []
        return cls._cache['states']

    @classmethod
    def get_stats(cls):
        """Get summary statistics (cached)"""
        if 'stats' not in cls._cache:
            df = cls._get_county_health_df()
            priorities = cls.get_intervention_priorities(limit=5000)

            diabetes_vals = pd.to_numeric(df.get('diabetes_prevalence', pd.Series()), errors='coerce').dropna()
            obesity_vals = pd.to_numeric(df.get('obesity_prevalence', pd.Series()), errors='coerce').dropna()
            heart_vals = pd.to_numeric(df.get('heart_disease_prevalence', pd.Series()), errors='coerce').dropna()

            critical_count = len([p for p in priorities if p.get('priority') == 'Critical'])
            high_count = len([p for p in priorities if p.get('priority') == 'High'])

            cls._cache['stats'] = {
                'total_counties': len(df),
                'avg_diabetes': round(diabetes_vals.mean(), 1) if len(diabetes_vals) > 0 else 0,
                'avg_obesity': round(obesity_vals.mean(), 1) if len(obesity_vals) > 0 else 0,
                'avg_heart_disease': round(heart_vals.mean(), 1) if len(heart_vals) > 0 else 0,
                'critical_counties': critical_count,
                'high_priority_counties': high_count,
                'states_covered': len(cls.get_states())
            }
        return cls._cache['stats']

    @classmethod
    def get_national_trends(cls):
        """Get national health trends"""
        stats = cls.get_stats()
        return {
            'diabetes_rate': stats['avg_diabetes'],
            'obesity_rate': stats['avg_obesity'],
            'trend': 'increasing',
            'year': 2024
        }

    @classmethod
    def get_state_statistics(cls):
        """Get state-by-state statistics (cached)"""
        if 'state_stats' not in cls._cache:
            df = cls._get_county_health_df()
            if df.empty:
                cls._cache['state_stats'] = {}
            else:
                state_col = None
                for col in ['state_abbr', 'state', 'State']:
                    if col in df.columns:
                        state_col = col
                        break

                if not state_col:
                    cls._cache['state_stats'] = {}
                else:
                    state_stats = {}
                    for state in df[state_col].dropna().unique():
                        # Only include valid US states/territories
                        if str(state).upper() not in VALID_US_STATES:
                            continue

                        state_df = df[df[state_col] == state]
                        diabetes_vals = pd.to_numeric(state_df.get('diabetes_prevalence', pd.Series()), errors='coerce').dropna()
                        obesity_vals = pd.to_numeric(state_df.get('obesity_prevalence', pd.Series()), errors='coerce').dropna()
                        heart_vals = pd.to_numeric(state_df.get('heart_disease_prevalence', pd.Series()), errors='coerce').dropna()

                        # Calculate risk scores for counties in this state
                        critical = 0
                        high = 0
                        medium = 0
                        for _, row in state_df.iterrows():
                            d = float(row.get('diabetes_prevalence', 0) or 0)
                            o = float(row.get('obesity_prevalence', 0) or 0)
                            h = float(row.get('heart_disease_prevalence', 0) or 0)
                            score = d * 0.4 + o * 0.35 + h * 0.25
                            if score > 20:
                                critical += 1
                            elif score > 18:
                                high += 1
                            else:
                                medium += 1

                        state_stats[state] = {
                            'total_counties': len(state_df),
                            'avg_diabetes': round(diabetes_vals.mean(), 1) if len(diabetes_vals) > 0 else 0,
                            'avg_obesity': round(obesity_vals.mean(), 1) if len(obesity_vals) > 0 else 0,
                            'avg_heart_disease': round(heart_vals.mean(), 1) if len(heart_vals) > 0 else 0,
                            'critical_counties': critical,
                            'high_counties': high,
                            'medium_counties': medium
                        }

                    cls._cache['state_stats'] = dict(sorted(state_stats.items()))
        return cls._cache['state_stats']
