"""
FoodScore Data Service
Load food product and additive data
"""
import pandas as pd
from pathlib import Path
import json

BASE_DIR = Path(__file__).parent.parent.parent
DATA_DIR = BASE_DIR / 'data'


class FoodScoreService:
    _cache = {}

    @classmethod
    def get_products(cls, limit=100, search=None, category=None):
        """Get food products with health scores"""
        if 'products' not in cls._cache:
            prod_file = DATA_DIR / 'processed/foodscore/us_products_scored.parquet'
            if prod_file.exists():
                df = pd.read_parquet(prod_file)
                cls._cache['products'] = df.to_dict('records')
            else:
                cls._cache['products'] = []

        products = cls._cache['products']
        if search:
            search = search.lower()
            products = [p for p in products if search in str(p.get('product_name', '')).lower()
                       or search in str(p.get('brands', '')).lower()]
        if category:
            products = [p for p in products if category.lower() in str(p.get('categories_en', p.get('categories', ''))).lower()]
        return products[:limit]

    @classmethod
    def get_product(cls, barcode):
        """Get single product by barcode"""
        products = cls.get_products(limit=100000)
        for p in products:
            if str(p.get('code', p.get('barcode', ''))) == str(barcode):
                return p
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
                # Try JSON version
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
        """Get product categories"""
        products = cls.get_products(limit=10000)
        categories = set()
        for p in products:
            cats = str(p.get('categories_en', p.get('categories', ''))).split(',')
            for c in cats:
                c = c.strip()
                if c and len(c) > 2:
                    categories.add(c)
        return sorted(list(categories))[:50]

    @classmethod
    def get_nova_distribution(cls):
        """Get NOVA classification distribution"""
        products = cls.get_products(limit=100000)
        nova_counts = {1: 0, 2: 0, 3: 0, 4: 0}
        for p in products:
            nova = p.get('nova_group', p.get('nova_groups_tags', 0))
            try:
                nova = int(str(nova).replace('en:', '').strip()) if nova else 0
                if nova in nova_counts:
                    nova_counts[nova] += 1
            except:
                pass
        return nova_counts

    @classmethod
    def get_high_risk_products(cls, limit=20):
        """Get products with highest additive risk"""
        products = cls.get_products(limit=10000)
        # Sort by MAHA score (lower is worse)
        sorted_prods = sorted(products, key=lambda x: float(x.get('maha_score', x.get('health_score', 100)) or 100))
        return sorted_prods[:limit]

    @classmethod
    def get_stats(cls):
        """Get summary statistics"""
        products = cls.get_products(limit=100000)
        additives = cls.get_additives(limit=1000)
        nova = cls.get_nova_distribution()
        return {
            'total_products': len(products),
            'total_additives': len(additives),
            'nova_distribution': nova,
            'categories': len(cls.get_categories())
        }
