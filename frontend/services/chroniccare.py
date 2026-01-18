"""
ChronicCare Data Service
Load chronic disease and food environment data - OPTIMIZED
"""
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent
DATA_DIR = BASE_DIR / 'data'


class ChronicCareService:
    _cache = {}
    _df_cache = {}

    @classmethod
    def _get_county_health_df(cls):
        """Get county health DataFrame (cached)"""
        if 'county_health_df' not in cls._df_cache:
            health_file = DATA_DIR / 'processed/chroniccare/chroniccare_merged.parquet'
            if health_file.exists():
                cls._df_cache['county_health_df'] = pd.read_parquet(health_file)
            else:
                csv_file = DATA_DIR / 'processed/chroniccare/chroniccare_merged.csv'
                if csv_file.exists():
                    cls._df_cache['county_health_df'] = pd.read_csv(csv_file)
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
            state_col = 'StateAbbr' if 'StateAbbr' in df.columns else 'state'
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
            state_col = 'State' if 'State' in df.columns else 'state'
            df = df[df[state_col] == state]

        return df.head(limit).to_dict('records')

    @classmethod
    def get_correlations(cls):
        """Get disease-food correlations (cached)"""
        if 'correlations' not in cls._cache:
            df = cls._get_county_health_df()
            if df.empty:
                cls._cache['correlations'] = []
            else:
                correlations = []
                for _, row in df.head(500).iterrows():
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
        """Get counties prioritized for intervention (cached)"""
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
                    priorities.append({
                        'fips': row.get('fips', ''),
                        'county': row.get('county_name', ''),
                        'state': row.get('state_abbr', ''),
                        'risk_score': round(score, 2),
                        'diabetes': row['diabetes_prev'],
                        'obesity': row['obesity_prev'],
                        'heart_disease': row['heart_prev'],
                        'priority': 'Critical' if score > 20 else 'High' if score > 18 else 'Medium'
                    })
                cls._cache['priorities'] = priorities
        return cls._cache['priorities'][:limit]

    @classmethod
    def get_states(cls):
        """Get list of states (cached)"""
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
                    cls._cache['states'] = sorted([s for s in states if len(str(s)) == 2])
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
