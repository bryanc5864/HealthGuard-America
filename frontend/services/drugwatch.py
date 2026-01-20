"""
DrugWatch Data Service
Load drug pricing data (US and international) - OPTIMIZED
"""
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent
DATA_DIR = BASE_DIR / 'data'


class DrugWatchService:
    _cache = {}
    _df_cache = {}

    @classmethod
    def _get_us_drugs_df(cls):
        """Get US drugs DataFrame (cached)"""
        if 'us_drugs_df' not in cls._df_cache:
            # Try multiple file locations
            possible_files = [
                DATA_DIR / 'processed/drugwatch/us_drugs.csv',
                DATA_DIR / 'processed/drugwatch/medicare_part_d_spending.csv',
                DATA_DIR / 'processed/drugwatch/us_drugs.parquet',
            ]
            for f in possible_files:
                if f.exists():
                    if f.suffix == '.parquet':
                        cls._df_cache['us_drugs_df'] = pd.read_parquet(f)
                    else:
                        cls._df_cache['us_drugs_df'] = pd.read_csv(f)
                    break
            else:
                cls._df_cache['us_drugs_df'] = pd.DataFrame()
        return cls._df_cache['us_drugs_df']

    @classmethod
    def get_us_drugs(cls, limit=100, search=None):
        """Get US drug list"""
        df = cls._get_us_drugs_df()
        if df.empty:
            return []

        if search:
            search_lower = search.lower()
            mask = (
                df['brand_name'].fillna('').str.lower().str.contains(search_lower, regex=False) |
                df['generic_name'].fillna('').str.lower().str.contains(search_lower, regex=False)
            )
            df = df[mask]

        return df.head(limit).to_dict('records')

    @classmethod
    def get_drug(cls, drug_id):
        """Get single drug by ID or name"""
        # Guard for None or empty input
        if not drug_id or str(drug_id).strip() == '':
            return None

        df = cls._get_us_drugs_df()
        if df.empty:
            return None

        drug_id_lower = str(drug_id).strip().lower()

        # Exact match first
        exact = df[df['brand_name'].fillna('').str.lower() == drug_id_lower]
        if not exact.empty:
            return exact.iloc[0].to_dict()

        exact = df[df['generic_name'].fillna('').str.lower() == drug_id_lower]
        if not exact.empty:
            return exact.iloc[0].to_dict()

        # Partial match
        partial = df[df['brand_name'].fillna('').str.lower().str.contains(drug_id_lower, regex=False)]
        if not partial.empty:
            return partial.iloc[0].to_dict()

        return None

    @classmethod
    def get_international_prices(cls, country=None):
        """Get international drug prices (cached)"""
        cache_key = f'intl_{country}' if country else 'intl_all'
        if cache_key not in cls._cache:
            prices = []

            if not country or country == 'australia':
                aus_file = DATA_DIR / 'processed/drugwatch/australia_drugs.parquet'
                if aus_file.exists():
                    df = pd.read_parquet(aus_file)
                    df['country'] = 'Australia'
                    prices.extend(df.to_dict('records'))

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
        if 'nadac_df' not in cls._df_cache:
            nadac_file = DATA_DIR / 'processed/drugwatch/nadac_prices.parquet'
            if nadac_file.exists():
                cls._df_cache['nadac_df'] = pd.read_parquet(nadac_file)
            else:
                cls._df_cache['nadac_df'] = pd.DataFrame()

        df = cls._df_cache['nadac_df']
        if df.empty:
            return []

        if search:
            search_lower = search.lower()
            # Use drug_name column (ndc_description doesn't exist in this dataset)
            search_col = 'drug_name' if 'drug_name' in df.columns else 'ndc_description'
            df = df[df[search_col].fillna('').str.lower().str.contains(search_lower, regex=False)]

        return df.head(limit).to_dict('records')

    @classmethod
    def compare_prices(cls, drug_name):
        """Compare US vs international prices for a drug"""
        if not drug_name:
            return {'us': None, 'international': []}
        us_drug = cls.get_drug(drug_name)
        intl_prices = cls.get_international_prices()

        drug_name_lower = drug_name.lower()

        comparisons = []
        for p in intl_prices:
            drug_match = str(p.get('drug_name', p.get('name', p.get('brand_name', '')))).lower()
            generic_match = str(p.get('generic_name', '')).lower()
            if drug_name_lower in drug_match or drug_name_lower in generic_match:
                normalized = dict(p)
                if 'price_per_unit_usd' in p:
                    normalized['price'] = p['price_per_unit_usd']
                elif 'price_usd' in p:
                    normalized['price'] = p['price_usd']
                comparisons.append(normalized)

        return {
            'us': us_drug,
            'international': comparisons[:10]
        }

    @classmethod
    def get_stats(cls):
        """Get summary statistics (cached)"""
        if 'stats' not in cls._cache:
            df = cls._get_us_drugs_df()
            intl = cls.get_international_prices()
            cls._cache['stats'] = {
                'total_us_drugs': len(df),
                'countries': ['USA', 'Canada', 'Australia', 'UK'],
                'total_comparisons': len(intl)
            }
        return cls._cache['stats']

    @classmethod
    def get_top_expensive(cls, limit=20):
        """Get top expensive drugs by total spending"""
        df = cls._get_us_drugs_df()
        if df.empty:
            return []

        df_sorted = df.dropna(subset=['total_spending_2023']).sort_values(
            'total_spending_2023', ascending=False
        )
        return df_sorted.head(limit).to_dict('records')
