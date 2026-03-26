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
    def _ensure_barcode_index(cls):
        """Build barcode index for O(1) product lookup"""
        if 'barcode_index' not in cls._cache:
            df = cls._get_products_df()
            if not df.empty and 'code' in df.columns:
                cls._cache['barcode_index'] = {
                    str(code): idx for idx, code in enumerate(df['code'].values)
                }
            else:
                cls._cache['barcode_index'] = {}

    @classmethod
    def get_product(cls, barcode):
        """Get single product by barcode - O(1) indexed lookup"""
        df = cls._get_products_df()
        if df.empty:
            return None

        cls._ensure_barcode_index()
        barcode_str = str(barcode)
        idx = cls._cache['barcode_index'].get(barcode_str)
        if idx is not None:
            record = df.iloc[idx].to_dict()
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
    def _ensure_additive_index(cls):
        """Build additive index for O(1) lookup by e_number or name"""
        if 'additive_index' not in cls._cache:
            additives = cls.get_additives(limit=1000)
            index = {}
            for a in additives:
                e_num = str(a.get('e_number', ''))
                name = a.get('name', a.get('additive_name', ''))
                if e_num:
                    index[e_num] = a
                if name:
                    index[name] = a
            cls._cache['additive_index'] = index

    @classmethod
    def get_additive(cls, additive_id):
        """Get single additive by E-number or name - O(1) indexed lookup"""
        cls._ensure_additive_index()
        return cls._cache['additive_index'].get(str(additive_id))

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
        """Get products with lowest MAHA scores (highest risk) - cached"""
        cache_key = f'high_risk_{limit}'
        if cache_key not in cls._cache:
            df = cls._get_products_df()
            if df.empty:
                cls._cache[cache_key] = []
            else:
                df = df[df['product_name'].notna() & (df['product_name'] != '')]
                df_sorted = df.dropna(subset=['maha_score']).sort_values('maha_score', ascending=True)
                cls._cache[cache_key] = clean_nan_records(df_sorted.head(limit).to_dict('records'))
        return cls._cache[cache_key]

    @classmethod
    def get_products_by_nova(cls, nova_group, limit=20):
        """Get top products for a specific NOVA group - cached"""
        cache_key = f'nova_products_{nova_group}'
        if cache_key not in cls._cache:
            df = cls._get_products_df()
            if df.empty:
                cls._cache[cache_key] = []
            else:
                df = df[df['product_name'].notna() & (df['product_name'] != '')]
                if 'nova_group' in df.columns:
                    nova_df = df[df['nova_group'].astype(str).str.replace('en:', '').str.strip() == str(nova_group)]
                    cls._cache[cache_key] = clean_nan_records(nova_df.head(limit).to_dict('records'))
                else:
                    cls._cache[cache_key] = []
        return cls._cache[cache_key]

    @classmethod
    def get_category_stats(cls):
        """Get product counts by category - cached"""
        if 'category_stats' not in cls._cache:
            df = cls._get_products_df()
            if df.empty:
                cls._cache['category_stats'] = {}
            else:
                cat_col = 'categories_en' if 'categories_en' in df.columns else 'categories'
                cat_counts = {}
                for cats in df[cat_col].dropna().head(10000):
                    for c in str(cats).split(','):
                        c = c.strip()
                        if c and len(c) > 2:
                            cat_counts[c] = cat_counts.get(c, 0) + 1
                cls._cache['category_stats'] = dict(sorted(cat_counts.items(), key=lambda x: -x[1])[:50])
        return cls._cache['category_stats']

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
