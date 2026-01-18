"""
RuralAccess Data Service
Load healthcare access and shortage data
"""
import pandas as pd
from pathlib import Path
import json

BASE_DIR = Path(__file__).parent.parent.parent
DATA_DIR = BASE_DIR / 'data'


class RuralAccessService:
    _cache = {}

    @classmethod
    def get_hpsa_designations(cls, state=None, discipline=None, limit=100):
        """Get Health Professional Shortage Areas"""
        if 'hpsa' not in cls._cache:
            hpsa_file = DATA_DIR / 'processed/ruralaccess/hpsa_designations.parquet'
            if hpsa_file.exists():
                df = pd.read_parquet(hpsa_file)
                cls._cache['hpsa'] = df.to_dict('records')
            else:
                # Try raw CSV
                raw_file = DATA_DIR / 'raw/ruralaccess/hrsa_hpsa.csv'
                if raw_file.exists():
                    df = pd.read_csv(raw_file, low_memory=False, nrows=10000)
                    cls._cache['hpsa'] = df.to_dict('records')
                else:
                    cls._cache['hpsa'] = []

        hpsas = cls._cache['hpsa']
        if state:
            hpsas = [h for h in hpsas if h.get('state', h.get('Common State Name', '')) == state]
        if discipline:
            hpsas = [h for h in hpsas if discipline.lower() in str(h.get('discipline', h.get('HPSA Discipline Class', ''))).lower()]
        return hpsas[:limit]

    @classmethod
    def get_hpsa(cls, hpsa_id):
        """Get single HPSA by ID"""
        hpsas = cls.get_hpsa_designations(limit=50000)
        for h in hpsas:
            if str(h.get('hpsa_id', h.get('HPSA ID', ''))) == str(hpsa_id):
                return h
        return None

    @classmethod
    def get_counties(cls, state=None, limit=100):
        """Get county-level data"""
        if 'counties' not in cls._cache:
            county_file = DATA_DIR / 'processed/ruralaccess/county_shortage_summary.parquet'
            if county_file.exists():
                df = pd.read_parquet(county_file)
                cls._cache['counties'] = df.to_dict('records')
            else:
                # Try population file
                pop_file = DATA_DIR / 'processed/ruralaccess/county_population.parquet'
                if pop_file.exists():
                    df = pd.read_parquet(pop_file)
                    cls._cache['counties'] = df.to_dict('records')
                else:
                    cls._cache['counties'] = []

        counties = cls._cache['counties']
        if state:
            counties = [c for c in counties if c.get('state', c.get('state_name', '')) == state]
        return counties[:limit]

    @classmethod
    def get_county(cls, fips):
        """Get single county by FIPS code"""
        counties = cls.get_counties(limit=5000)
        for c in counties:
            if str(c.get('fips', c.get('county_fips', ''))) == str(fips):
                return c
        return None

    @classmethod
    def get_fqhc_locations(cls, state=None, limit=100):
        """Get Federally Qualified Health Centers"""
        if 'fqhc' not in cls._cache:
            fqhc_file = DATA_DIR / 'processed/ruralaccess/fqhc_locations.parquet'
            if fqhc_file.exists():
                df = pd.read_parquet(fqhc_file)
                cls._cache['fqhc'] = df.to_dict('records')
            else:
                cls._cache['fqhc'] = []

        fqhcs = cls._cache['fqhc']
        if state:
            fqhcs = [f for f in fqhcs if f.get('state', '') == state]
        return fqhcs[:limit]

    @classmethod
    def get_hospital_closures(cls, limit=100):
        """Get rural hospital closures"""
        if 'closures' not in cls._cache:
            closure_file = DATA_DIR / 'processed/ruralaccess/rural_hospital_closures.parquet'
            if closure_file.exists():
                df = pd.read_parquet(closure_file)
                cls._cache['closures'] = df.to_dict('records')
            else:
                cls._cache['closures'] = []

        return cls._cache['closures'][:limit]

    @classmethod
    def get_states(cls):
        """Get list of states"""
        hpsas = cls.get_hpsa_designations(limit=50000)
        states = set()
        for h in hpsas:
            state = h.get('state', h.get('Common State Name', ''))
            if state and len(state) == 2:
                states.add(state)
        return sorted(states)

    @classmethod
    def get_stats(cls):
        """Get summary statistics"""
        hpsas = cls.get_hpsa_designations(limit=50000)
        counties = cls.get_counties(limit=5000)
        fqhcs = cls.get_fqhc_locations(limit=50000)
        closures = cls.get_hospital_closures(limit=1000)

        # Count by discipline
        disciplines = {}
        for h in hpsas:
            disc = h.get('discipline', h.get('HPSA Discipline Class', 'Unknown'))
            disciplines[disc] = disciplines.get(disc, 0) + 1

        return {
            'total_hpsas': len(hpsas),
            'total_counties': len(counties),
            'total_fqhcs': len(fqhcs),
            'hospital_closures': len(closures),
            'states_covered': len(cls.get_states()),
            'by_discipline': disciplines
        }

    @classmethod
    def get_shortage_map_data(cls):
        """Get data formatted for map visualization"""
        counties = cls.get_counties(limit=5000)
        map_data = []
        for c in counties:
            if c.get('latitude') and c.get('longitude'):
                map_data.append({
                    'fips': c.get('fips', c.get('county_fips')),
                    'name': c.get('county_name', c.get('name')),
                    'state': c.get('state'),
                    'lat': c.get('latitude'),
                    'lng': c.get('longitude'),
                    'shortage_score': c.get('shortage_score', c.get('hpsa_score', 0)),
                    'population': c.get('population', 0)
                })
        return map_data
