"""
FoodScore Data Service
Load food product and additive data - OPTIMIZED
"""
import pandas as pd
import numpy as np
from pathlib import Path
import json

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


class FoodScoreService:
    _cache = {}
    _df_cache = {}  # Cache DataFrames for efficient filtering

    @classmethod
    def _get_products_df(cls):
        """Get products DataFrame (cached)"""
        if 'products_df' not in cls._df_cache:
            # Try multiple file locations
            possible_files = [
                DATA_DIR / 'processed/foodscore/us_products_scored.parquet',
                DATA_DIR / 'processed/foodscore/products_scored.csv',
                DATA_DIR / 'processed/foodscore/products_scored.parquet',
            ]
            for f in possible_files:
                if f.exists():
                    if f.suffix == '.parquet':
                        cls._df_cache['products_df'] = pd.read_parquet(f)
                    else:
                        cls._df_cache['products_df'] = pd.read_csv(f)
                    break
            else:
                cls._df_cache['products_df'] = pd.DataFrame()
        return cls._df_cache['products_df']

    @classmethod
    def get_products(cls, limit=100, search=None, category=None):
        """Get food products with health scores"""
        df = cls._get_products_df()
        if df.empty:
            return []

        # Filter out products with null names
        df = df[df['product_name'].notna() & (df['product_name'] != '')]

        # Apply filters using pandas (more efficient than list comprehension)
        if search:
            search_lower = search.lower()
            mask = (
                df['product_name'].fillna('').str.lower().str.contains(search_lower, regex=False) |
                df['brands'].fillna('').str.lower().str.contains(search_lower, regex=False)
            )
            df = df[mask]

        if category:
            cat_lower = category.lower()
            cat_col = 'categories_en' if 'categories_en' in df.columns else 'categories'
            df = df[df[cat_col].fillna('').str.lower().str.contains(cat_lower, regex=False)]

        return clean_nan_records(df.head(limit).to_dict('records'))

    @classmethod
    def get_product(cls, barcode):
        """Get single product by barcode"""
        df = cls._get_products_df()
        if df.empty:
            return None

        # Direct lookup is faster
        barcode_str = str(barcode)
        matches = df[df['code'].astype(str) == barcode_str]
        if not matches.empty:
            record = matches.iloc[0].to_dict()
            # Clean NaN values
            for key, value in record.items():
                if pd.isna(value):
                    record[key] = None
            return record
        return None

    @classmethod
    def get_additives(cls, limit=100, search=None):
        """Get food additives with risk scores"""
        if 'additives' not in cls._cache:
            # Try multiple file locations
            possible_files = [
                DATA_DIR / 'raw/foodscore/additive_risks_expanded.csv',
                DATA_DIR / 'processed/foodscore/additives_database.csv',
                DATA_DIR / 'raw/foodscore/additive_risks.json',
            ]
            for f in possible_files:
                if f.exists():
                    if f.suffix == '.csv':
                        df = pd.read_csv(f)
                        cls._cache['additives'] = clean_nan_records(df.to_dict('records'))
                    else:
                        with open(f) as fh:
                            cls._cache['additives'] = json.load(fh)
                    break
            else:
                cls._cache['additives'] = []

        additives = cls._cache['additives']
        if search:
            search = search.lower()
            additives = [a for a in additives if search in str(a.get('name', a.get('additive_name', ''))).lower()
                        or search in str(a.get('e_number', '')).lower()]
        return additives[:limit]

    @classmethod
    def get_additive(cls, additive_id):
        """Get single additive by E-number or name"""
        additives = cls.get_additives(limit=1000)
        for a in additives:
            if str(a.get('e_number', '')) == str(additive_id):
                return a
            if a.get('name', a.get('additive_name', '')) == additive_id:
                return a
        return None

    @classmethod
    def get_categories(cls):
        """Get product categories (cached)"""
        if 'categories' not in cls._cache:
            df = cls._get_products_df()
            if df.empty:
                cls._cache['categories'] = []
            else:
                categories = set()
                cat_col = 'categories_en' if 'categories_en' in df.columns else 'categories'
                for cats in df[cat_col].dropna().head(10000):
                    for c in str(cats).split(','):
                        c = c.strip()
                        if c and len(c) > 2:
                            categories.add(c)
                cls._cache['categories'] = sorted(list(categories))[:50]
        return cls._cache['categories']

    @classmethod
    def get_nova_distribution(cls):
        """Get NOVA classification distribution (cached)"""
        if 'nova_dist' not in cls._cache:
            df = cls._get_products_df()
            if df.empty:
                cls._cache['nova_dist'] = {1: 0, 2: 0, 3: 0, 4: 0}
            else:
                nova_counts = {1: 0, 2: 0, 3: 0, 4: 0}
                for nova in df['nova_group'].dropna():
                    try:
                        nova_int = int(str(nova).replace('en:', '').strip())
                        if nova_int in nova_counts:
                            nova_counts[nova_int] += 1
                    except:
                        pass
                cls._cache['nova_dist'] = nova_counts
        return cls._cache['nova_dist']

    @classmethod
    def get_high_risk_products(cls, limit=20):
        """Get products with lowest MAHA scores (highest risk)"""
        df = cls._get_products_df()
        if df.empty:
            return []

        # Filter out products with null names and sort by MAHA score ascending (lower = worse)
        df = df[df['product_name'].notna() & (df['product_name'] != '')]
        df_sorted = df.dropna(subset=['maha_score']).sort_values('maha_score', ascending=True)
        return clean_nan_records(df_sorted.head(limit).to_dict('records'))

    @classmethod
    def get_stats(cls):
        """Get summary statistics (cached)"""
        if 'stats' not in cls._cache:
            df = cls._get_products_df()
            additives = cls.get_additives(limit=1000)
            nova = cls.get_nova_distribution()
            categories = cls.get_categories()

            cls._cache['stats'] = {
                'total_products': len(df),
                'total_additives': len(additives),
                'nova_distribution': nova,
                'categories': len(categories)
            }
        return cls._cache['stats']
