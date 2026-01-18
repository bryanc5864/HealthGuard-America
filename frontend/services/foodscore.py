"""
FoodScore Data Service
Load food product and additive data - OPTIMIZED
"""
import pandas as pd
from pathlib import Path
import json

BASE_DIR = Path(__file__).parent.parent.parent
DATA_DIR = BASE_DIR / 'data'


class FoodScoreService:
    _cache = {}
    _df_cache = {}  # Cache DataFrames for efficient filtering

    @classmethod
    def _get_products_df(cls):
        """Get products DataFrame (cached)"""
        if 'products_df' not in cls._df_cache:
            prod_file = DATA_DIR / 'processed/foodscore/us_products_scored.parquet'
            if prod_file.exists():
                cls._df_cache['products_df'] = pd.read_parquet(prod_file)
            else:
                cls._df_cache['products_df'] = pd.DataFrame()
        return cls._df_cache['products_df']

    @classmethod
    def get_products(cls, limit=100, search=None, category=None):
        """Get food products with health scores"""
        df = cls._get_products_df()
        if df.empty:
            return []

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
            df = df[df['categories_en'].fillna('').str.lower().str.contains(cat_lower, regex=False)]

        return df.head(limit).to_dict('records')

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
            return matches.iloc[0].to_dict()
        return None

    @classmethod
    def get_additives(cls, limit=100, search=None):
        """Get food additives with risk scores"""
        if 'additives' not in cls._cache:
            add_file = DATA_DIR / 'raw/foodscore/additive_risks_expanded.csv'
            if add_file.exists():
                df = pd.read_csv(add_file)
                cls._cache['additives'] = df.to_dict('records')
            else:
                json_file = DATA_DIR / 'raw/foodscore/additive_risks.json'
                if json_file.exists():
                    with open(json_file) as f:
                        cls._cache['additives'] = json.load(f)
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
                for cats in df['categories_en'].dropna().head(10000):
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

        # Sort by MAHA score ascending (lower = worse)
        df_sorted = df.dropna(subset=['maha_score']).sort_values('maha_score', ascending=True)
        return df_sorted.head(limit).to_dict('records')

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
