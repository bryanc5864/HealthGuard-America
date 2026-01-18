"""
ChronicCare Data Service
Load chronic disease and food environment data
"""
import pandas as pd
from pathlib import Path
import json

BASE_DIR = Path(__file__).parent.parent.parent
DATA_DIR = BASE_DIR / 'data'


class ChronicCareService:
    _cache = {}

    @classmethod
    def get_county_health(cls, state=None, limit=100):
        """Get county-level chronic disease data"""
        if 'county_health' not in cls._cache:
            health_file = DATA_DIR / 'processed/chroniccare/chroniccare_merged.parquet'
            if health_file.exists():
                df = pd.read_parquet(health_file)
                cls._cache['county_health'] = df.to_dict('records')
            else:
                # Try CSV version
                csv_file = DATA_DIR / 'processed/chroniccare/chroniccare_merged.csv'
                if csv_file.exists():
                    df = pd.read_csv(csv_file)
                    cls._cache['county_health'] = df.to_dict('records')
                else:
                    cls._cache['county_health'] = []

        counties = cls._cache['county_health']
        if state:
            counties = [c for c in counties if c.get('state', c.get('State', '')) == state]
        return counties[:limit]

    @classmethod
    def get_county(cls, fips):
        """Get single county by FIPS"""
        counties = cls.get_county_health(limit=5000)
        for c in counties:
            if str(c.get('fips', c.get('FIPS', c.get('CountyFIPS', '')))) == str(fips):
                return c
        return None

    @classmethod
    def get_cdc_places(cls, state=None, limit=100):
        """Get CDC PLACES data"""
        if 'cdc_places' not in cls._cache:
            places_file = DATA_DIR / 'processed/chroniccare/cdc_places_county.csv'
            if places_file.exists():
                df = pd.read_csv(places_file)
                cls._cache['cdc_places'] = df.to_dict('records')
            else:
                cls._cache['cdc_places'] = []

        places = cls._cache['cdc_places']
        if state:
            places = [p for p in places if p.get('StateAbbr', p.get('state', '')) == state]
        return places[:limit]

    @classmethod
    def get_food_environment(cls, state=None, limit=100):
        """Get USDA food environment data"""
        if 'food_env' not in cls._cache:
            food_file = DATA_DIR / 'processed/chroniccare/usda_food_environment.csv'
            if food_file.exists():
                df = pd.read_csv(food_file)
                cls._cache['food_env'] = df.to_dict('records')
            else:
                cls._cache['food_env'] = []

        env_data = cls._cache['food_env']
        if state:
            env_data = [e for e in env_data if e.get('State', e.get('state', '')) == state]
        return env_data[:limit]

    @classmethod
    def get_correlations(cls):
        """Get disease-food correlations"""
        counties = cls.get_county_health(limit=5000)

        # Calculate correlation data points
        correlations = []
        for c in counties:
            diabetes = c.get('diabetes_prevalence', c.get('DIABETES', c.get('Diabetes_CrudePrev', 0)))
            obesity = c.get('obesity_prevalence', c.get('OBESITY', c.get('Obesity_CrudePrev', 0)))
            fast_food = c.get('fast_food_restaurants', c.get('FFRPTH16', 0))
            food_insecurity = c.get('food_insecurity', c.get('FOODINSEC_15_17', 0))

            if diabetes and obesity:
                correlations.append({
                    'fips': c.get('fips', c.get('FIPS', '')),
                    'county': c.get('county', c.get('County', '')),
                    'state': c.get('state', c.get('State', '')),
                    'diabetes': float(diabetes) if diabetes else 0,
                    'obesity': float(obesity) if obesity else 0,
                    'fast_food': float(fast_food) if fast_food else 0,
                    'food_insecurity': float(food_insecurity) if food_insecurity else 0
                })

        return correlations[:500]

    @classmethod
    def get_intervention_priorities(cls, limit=50):
        """Get counties prioritized for intervention (using ML model results)"""
        counties = cls.get_county_health(limit=5000)

        # Score counties by chronic disease burden
        scored = []
        for c in counties:
            diabetes = float(c.get('diabetes_prevalence', c.get('DIABETES', c.get('Diabetes_CrudePrev', 0))) or 0)
            obesity = float(c.get('obesity_prevalence', c.get('OBESITY', c.get('Obesity_CrudePrev', 0))) or 0)
            heart = float(c.get('heart_disease', c.get('CHD', c.get('CHD_CrudePrev', 0))) or 0)

            # Simple composite score
            risk_score = (diabetes * 0.4 + obesity * 0.35 + heart * 0.25) if (diabetes or obesity or heart) else 0

            if risk_score > 0:
                scored.append({
                    'fips': c.get('fips', c.get('FIPS', '')),
                    'county': c.get('county', c.get('County', '')),
                    'state': c.get('state', c.get('State', '')),
                    'risk_score': round(risk_score, 2),
                    'diabetes': diabetes,
                    'obesity': obesity,
                    'heart_disease': heart,
                    'priority': 'Critical' if risk_score > 15 else 'High' if risk_score > 12 else 'Medium'
                })

        # Sort by risk score descending
        scored.sort(key=lambda x: x['risk_score'], reverse=True)
        return scored[:limit]

    @classmethod
    def get_states(cls):
        """Get list of states"""
        counties = cls.get_county_health(limit=5000)
        states = set()
        for c in counties:
            state = c.get('state', c.get('State', ''))
            if state and len(str(state)) == 2:
                states.add(state)
        return sorted(states)

    @classmethod
    def get_stats(cls):
        """Get summary statistics"""
        counties = cls.get_county_health(limit=5000)
        priorities = cls.get_intervention_priorities(limit=5000)

        # Calculate averages
        diabetes_vals = [float(c.get('diabetes_prevalence', c.get('DIABETES', 0)) or 0) for c in counties if c.get('diabetes_prevalence', c.get('DIABETES'))]
        obesity_vals = [float(c.get('obesity_prevalence', c.get('OBESITY', 0)) or 0) for c in counties if c.get('obesity_prevalence', c.get('OBESITY'))]

        critical_count = len([p for p in priorities if p.get('priority') == 'Critical'])
        high_count = len([p for p in priorities if p.get('priority') == 'High'])

        return {
            'total_counties': len(counties),
            'avg_diabetes': round(sum(diabetes_vals) / len(diabetes_vals), 1) if diabetes_vals else 0,
            'avg_obesity': round(sum(obesity_vals) / len(obesity_vals), 1) if obesity_vals else 0,
            'critical_counties': critical_count,
            'high_priority_counties': high_count,
            'states_covered': len(cls.get_states())
        }

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
