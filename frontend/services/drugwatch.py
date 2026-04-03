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
    _drug_detail_cache = {}
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
    def _ensure_drug_index(cls):
        """Build drug name index for fast lookups"""
        if 'drug_index' not in cls._cache:
            df = cls._get_us_drugs_df()
            if df.empty:
                cls._cache['drug_index'] = {}
                return
            index = {}
            for idx, row in df.iterrows():
                brand = str(row.get('brand_name', '')).strip().lower()
                generic = str(row.get('generic_name', '')).strip().lower()
                if brand and brand != 'nan':
                    index[brand] = idx
                if generic and generic != 'nan':
                    index[generic] = idx
            cls._cache['drug_index'] = index

    @classmethod
    def get_drug(cls, drug_id):
        """Get single drug by ID or name - indexed lookup with caching"""
        if not drug_id or str(drug_id).strip() == '':
            return None

        drug_id_lower = str(drug_id).strip().lower()

        # Check drug detail cache first
        if drug_id_lower in cls._drug_detail_cache:
            return cls._drug_detail_cache[drug_id_lower]

        df = cls._get_us_drugs_df()
        if df.empty:
            return None

        cls._ensure_drug_index()

        result = None

        # O(1) indexed lookup
        idx = cls._cache['drug_index'].get(drug_id_lower)
        if idx is not None:
            result = df.iloc[idx].to_dict()
        else:
            # Fallback: partial match
            partial = df[df['brand_name'].fillna('').str.lower().str.contains(drug_id_lower, regex=False)]
            if not partial.empty:
                result = partial.iloc[0].to_dict()

        # Cache the result (limit to 300 entries)
        if result is not None:
            if len(cls._drug_detail_cache) >= 300:
                oldest_key = next(iter(cls._drug_detail_cache))
                del cls._drug_detail_cache[oldest_key]
            cls._drug_detail_cache[drug_id_lower] = result

        return result

    @classmethod
    def get_international_prices(cls, country=None):
        """Get international drug prices (cached).
        Only loads datasets that have actual pricing columns."""
        cache_key = f'intl_{country}' if country else 'intl_all'
        if cache_key not in cls._cache:
            prices = []

            if not country or country == 'australia':
                aus_file = DATA_DIR / 'processed/drugwatch/australia_drugs.parquet'
                if aus_file.exists():
                    df = pd.read_parquet(aus_file)
                    df['country'] = 'Australia'
                    prices.extend(df.to_dict('records'))

            # Canada data is a drug registry without pricing — skip for comparisons
            # but still allow loading metadata if explicitly requested
            if country == 'canada':
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

        # Also match by the US drug's generic name for better coverage
        search_terms = {drug_name_lower}
        if us_drug:
            generic = str(us_drug.get('generic_name', '')).strip().lower()
            if generic and generic != 'nan':
                search_terms.add(generic)

        comparisons = []
        seen_keys = set()
        for p in intl_prices:
            drug_match = str(p.get('drug_name', p.get('name', p.get('brand_name', '')))).lower()
            generic_match = str(p.get('generic_name', '')).lower()

            matched = any(
                term in drug_match or term in generic_match
                for term in search_terms
            )
            if not matched:
                continue

            # Skip entries without any price data
            has_price = any(p.get(col) for col in ['price_per_unit_usd', 'price_usd', 'price'])
            if not has_price:
                continue

            # Deduplicate by country + brand
            dedup_key = (p.get('country', ''), drug_match)
            if dedup_key in seen_keys:
                continue
            seen_keys.add(dedup_key)

            normalized = dict(p)
            if 'price_per_unit_usd' in p and p['price_per_unit_usd']:
                normalized['price'] = p['price_per_unit_usd']
            elif 'price_usd' in p and p['price_usd']:
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

    @classmethod
    def get_top_expensive_cached(cls, limit=20):
        """Get top expensive drugs with caching to avoid re-sorting every call"""
        cache_key = f'top_expensive_{limit}'
        if cache_key not in cls._cache:
            cls._cache[cache_key] = cls.get_top_expensive(limit=limit)
        return cls._cache[cache_key]

    @classmethod
    def get_cached_comparison(cls, drug_name):
        """Get cached comparison results for a drug"""
        if not drug_name:
            return {'us': None, 'international': []}
        drug_name_lower = drug_name.strip().lower()
        cache_key = f'comparison_{drug_name_lower}'
        if cache_key not in cls._cache:
            # Limit comparison cache to 200 entries
            comparison_keys = [k for k in cls._cache if k.startswith('comparison_')]
            if len(comparison_keys) >= 200:
                oldest_key = comparison_keys[0]
                del cls._cache[oldest_key]
            cls._cache[cache_key] = cls.compare_prices(drug_name)
        return cls._cache[cache_key]

    @classmethod
    def get_nadac_stats(cls):
        """Get NADAC price summary statistics (cached)"""
        if 'nadac_stats' not in cls._cache:
            if 'nadac_df' not in cls._df_cache:
                nadac_file = DATA_DIR / 'processed/drugwatch/nadac_prices.parquet'
                if nadac_file.exists():
                    cls._df_cache['nadac_df'] = pd.read_parquet(nadac_file)
                else:
                    cls._df_cache['nadac_df'] = pd.DataFrame()

            df = cls._df_cache['nadac_df']
            if df.empty:
                cls._cache['nadac_stats'] = {'count': 0, 'avg_price': 0.0}
            else:
                price_col = None
                for col in ['nadac_per_unit', 'price', 'price_per_unit', 'nadac_price']:
                    if col in df.columns:
                        price_col = col
                        break
                avg_price = float(df[price_col].mean()) if price_col else 0.0
                cls._cache['nadac_stats'] = {
                    'count': len(df),
                    'avg_price': round(avg_price, 4)
                }
        return cls._cache['nadac_stats']
