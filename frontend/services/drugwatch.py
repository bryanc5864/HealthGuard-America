"""
DrugWatch Data Service
Load drug pricing data (US and international)
"""
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent
DATA_DIR = BASE_DIR / 'data'


class DrugWatchService:
    _cache = {}

    @classmethod
    def get_us_drugs(cls, limit=100, search=None):
        """Get US drug list"""
        if 'us_drugs' not in cls._cache:
            # Try CSV first (more reliable)
            csv_file = DATA_DIR / 'processed/drugwatch/us_drugs.csv'
            if csv_file.exists():
                df = pd.read_csv(csv_file)
                cls._cache['us_drugs'] = df.to_dict('records')
            else:
                drug_file = DATA_DIR / 'processed/drugwatch/us_drugs.parquet'
                if drug_file.exists():
                    df = pd.read_parquet(drug_file)
                    cls._cache['us_drugs'] = df.to_dict('records')
                else:
                    cls._cache['us_drugs'] = []

        drugs = cls._cache['us_drugs']
        if search:
            search = search.lower()
            drugs = [d for d in drugs if search in str(d.get('brand_name', '')).lower()
                    or search in str(d.get('generic_name', '')).lower()]
        return drugs[:limit]

    @classmethod
    def get_drug(cls, drug_id):
        """Get single drug by ID or name"""
        drugs = cls.get_us_drugs(limit=10000)
        drug_id_lower = str(drug_id).lower()
        for d in drugs:
            if d.get('brand_name', '').lower() == drug_id_lower:
                return d
            if d.get('generic_name', '').lower() == drug_id_lower:
                return d
        # Partial match
        for d in drugs:
            if drug_id_lower in d.get('brand_name', '').lower():
                return d
        return None

    @classmethod
    def get_international_prices(cls, country=None):
        """Get international drug prices"""
        cache_key = f'intl_{country}' if country else 'intl_all'
        if cache_key not in cls._cache:
            prices = []

            # Australia
            if not country or country == 'australia':
                aus_file = DATA_DIR / 'processed/drugwatch/australia_drugs.parquet'
                if aus_file.exists():
                    df = pd.read_parquet(aus_file)
                    df['country'] = 'Australia'
                    prices.extend(df.to_dict('records'))

            # Canada
            if not country or country == 'canada':
                can_file = DATA_DIR / 'processed/drugwatch/canada_drugs.parquet'
                if can_file.exists():
                    df = pd.read_parquet(can_file)
                    df['country'] = 'Canada'
                    prices.extend(df.to_dict('records'))

            cls._cache[cache_key] = prices

        return cls._cache[cache_key]

    @classmethod
    def get_nadac_prices(cls, limit=100, search=None):
        """Get NADAC pricing data"""
        if 'nadac' not in cls._cache:
            nadac_file = DATA_DIR / 'processed/drugwatch/nadac_prices.parquet'
            if nadac_file.exists():
                df = pd.read_parquet(nadac_file)
                cls._cache['nadac'] = df.to_dict('records')
            else:
                cls._cache['nadac'] = []

        prices = cls._cache['nadac']
        if search:
            search = search.lower()
            prices = [p for p in prices if search in str(p.get('ndc_description', '')).lower()]
        return prices[:limit]

    @classmethod
    def compare_prices(cls, drug_name):
        """Compare US vs international prices for a drug"""
        us_drugs = cls.get_us_drugs(limit=10000)
        intl_prices = cls.get_international_prices()

        drug_name_lower = drug_name.lower()

        us_price = None
        for d in us_drugs:
            if drug_name_lower in str(d.get('brand_name', '')).lower():
                us_price = d
                break

        comparisons = []
        for p in intl_prices:
            drug_match = str(p.get('drug_name', p.get('name', p.get('brand_name', '')))).lower()
            generic_match = str(p.get('generic_name', '')).lower()
            if drug_name_lower in drug_match or drug_name_lower in generic_match:
                # Normalize price field - Australia uses price_per_unit_usd, Canada has no price
                normalized = dict(p)
                if 'price_per_unit_usd' in p:
                    normalized['price'] = p['price_per_unit_usd']
                elif 'price_usd' in p:
                    normalized['price'] = p['price_usd']
                comparisons.append(normalized)

        return {
            'us': us_price,
            'international': comparisons[:10]
        }

    @classmethod
    def get_stats(cls):
        """Get summary statistics"""
        us_drugs = cls.get_us_drugs(limit=10000)
        return {
            'total_us_drugs': len(us_drugs),
            'countries': ['USA', 'Canada', 'Australia', 'UK'],
            'total_comparisons': len(cls.get_international_prices())
        }

    @classmethod
    def get_top_expensive(cls, limit=20):
        """Get top expensive drugs by total spending"""
        drugs = cls.get_us_drugs(limit=10000)
        # Sort by total_spending_2023 column
        sorted_drugs = sorted(drugs, key=lambda x: float(x.get('total_spending_2023', 0) or 0), reverse=True)
        return sorted_drugs[:limit]
