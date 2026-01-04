#!/usr/bin/env python3
"""Analyze processed data for data brief."""

import pandas as pd
import numpy as np
import warnings
import json
warnings.filterwarnings('ignore')

DATA_DIR = "data/processed"

def analyze_pricevision():
    """Analyze PriceVision hospital pricing data."""
    print("=" * 60)
    print("PRICEVISION ANALYSIS")
    print("=" * 60)

    df = pd.read_parquet(f"{DATA_DIR}/pricevision/all_prices_normalized.parquet")

    stats = {
        "total_records": len(df),
        "unique_hospitals": df["hospital_npi"].nunique(),
        "columns": list(df.columns),
    }

    # Price statistics (filter out extreme outliers for meaningful stats)
    price_stats = {}
    for col in ['gross_charge', 'cash_price', 'min_price', 'max_price', 'negotiated_rate']:
        if col in df.columns:
            numeric = pd.to_numeric(df[col], errors='coerce')
            # Filter reasonable range (0 to 10 million)
            valid = numeric[(numeric >= 0) & (numeric <= 10000000)].dropna()
            if len(valid) > 0:
                price_stats[col] = {
                    "count": int(len(valid)),
                    "mean": float(valid.mean()),
                    "median": float(valid.median()),
                    "std": float(valid.std()),
                    "min": float(valid.min()),
                    "max": float(valid.max()),
                    "p25": float(valid.quantile(0.25)),
                    "p75": float(valid.quantile(0.75)),
                    "p95": float(valid.quantile(0.95)),
                }
    stats["price_statistics"] = price_stats

    # Code types
    if 'code_type' in df.columns:
        code_counts = df['code_type'].value_counts().head(10).to_dict()
        stats["code_types"] = {str(k): int(v) for k, v in code_counts.items()}

    # Settings
    if 'setting' in df.columns:
        setting_counts = df['setting'].value_counts().to_dict()
        stats["settings"] = {str(k): int(v) for k, v in setting_counts.items()}

    # Payers
    if 'payer_name' in df.columns:
        # Filter out empty payers
        payer_df = df[df['payer_name'].notna() & (df['payer_name'] != '') & (df['payer_name'] != 'None')]
        payer_counts = payer_df['payer_name'].value_counts().head(20).to_dict()
        stats["top_payers"] = {str(k): int(v) for k, v in payer_counts.items()}

    return stats


def analyze_drugwatch():
    """Analyze DrugWatch drug pricing data."""
    print("\n" + "=" * 60)
    print("DRUGWATCH ANALYSIS")
    print("=" * 60)

    stats = {}

    # US Medicare Part D
    us = pd.read_parquet(f"{DATA_DIR}/drugwatch/us_drugs.parquet")
    us_stats = {"total_drugs": len(us)}

    if 'total_spending_2023' in us.columns:
        us['total_spending_2023'] = pd.to_numeric(us['total_spending_2023'], errors='coerce')
        us_stats["total_spending_2023"] = float(us['total_spending_2023'].sum())

        # Top drugs by spending
        top = us.nlargest(10, 'total_spending_2023')[['brand_name', 'generic_name', 'total_spending_2023']]
        us_stats["top_drugs_by_spending"] = [
            {"brand": row['brand_name'], "generic": row['generic_name'], "spending": float(row['total_spending_2023'])}
            for _, row in top.iterrows()
        ]

    if 'avg_price_per_unit_2023' in us.columns:
        us['avg_price_per_unit_2023'] = pd.to_numeric(us['avg_price_per_unit_2023'], errors='coerce')
        valid = us['avg_price_per_unit_2023'].dropna()
        us_stats["price_per_unit"] = {
            "mean": float(valid.mean()),
            "median": float(valid.median()),
            "max": float(valid.max()),
            "min": float(valid.min()),
        }

        # Most expensive drugs per unit
        top_price = us.nlargest(10, 'avg_price_per_unit_2023')[['brand_name', 'generic_name', 'avg_price_per_unit_2023']]
        us_stats["most_expensive_drugs"] = [
            {"brand": row['brand_name'], "generic": row['generic_name'], "price_per_unit": float(row['avg_price_per_unit_2023'])}
            for _, row in top_price.iterrows()
        ]

    if 'total_beneficiaries_2023' in us.columns:
        us['total_beneficiaries_2023'] = pd.to_numeric(us['total_beneficiaries_2023'], errors='coerce')
        us_stats["total_beneficiaries"] = int(us['total_beneficiaries_2023'].sum())

    stats["us_medicare_part_d"] = us_stats

    # Australia PBS
    aus = pd.read_parquet(f"{DATA_DIR}/drugwatch/australia_drugs.parquet")
    aus_stats = {"total_drugs": len(aus)}

    if 'price_usd' in aus.columns:
        aus['price_usd'] = pd.to_numeric(aus['price_usd'], errors='coerce')
        valid = aus['price_usd'].dropna()
        aus_stats["price_usd"] = {
            "mean": float(valid.mean()),
            "median": float(valid.median()),
            "max": float(valid.max()),
        }

    stats["australia_pbs"] = aus_stats

    # Canada
    can = pd.read_parquet(f"{DATA_DIR}/drugwatch/canada_drugs.parquet")
    stats["canada"] = {
        "total_drug_records": len(can),
        "columns": list(can.columns)[:10],
    }

    return stats


def analyze_foodscore():
    """Analyze FoodScore product data."""
    print("\n" + "=" * 60)
    print("FOODSCORE ANALYSIS")
    print("=" * 60)

    df = pd.read_parquet(f"{DATA_DIR}/foodscore/us_products_scored.parquet")

    stats = {
        "total_products": len(df),
    }

    # MAHA Score analysis
    if 'maha_score' in df.columns:
        df['maha_score'] = pd.to_numeric(df['maha_score'], errors='coerce')
        valid = df['maha_score'].dropna()
        stats["maha_score"] = {
            "mean": float(valid.mean()),
            "median": float(valid.median()),
            "std": float(valid.std()),
            "min": float(valid.min()),
            "max": float(valid.max()),
        }

        # Distribution buckets
        stats["maha_distribution"] = {
            "excellent_90_100": int((valid >= 90).sum()),
            "good_75_90": int(((valid >= 75) & (valid < 90)).sum()),
            "moderate_50_75": int(((valid >= 50) & (valid < 75)).sum()),
            "poor_25_50": int(((valid >= 25) & (valid < 50)).sum()),
            "very_poor_0_25": int((valid < 25).sum()),
        }

    # NOVA groups
    if 'nova_group' in df.columns:
        nova_counts = df['nova_group'].value_counts().to_dict()
        stats["nova_distribution"] = {str(k): int(v) for k, v in nova_counts.items()}

        # Calculate percentages
        total = sum(nova_counts.values())
        stats["nova_percentages"] = {
            str(k): round(v / total * 100, 1) for k, v in nova_counts.items()
        }

    # Nutriscore
    if 'nutriscore_grade' in df.columns:
        nutri_counts = df['nutriscore_grade'].value_counts().to_dict()
        stats["nutriscore_distribution"] = {str(k): int(v) for k, v in nutri_counts.items()}

    # Additives
    if 'flagged_additive_count' in df.columns:
        df['flagged_additive_count'] = pd.to_numeric(df['flagged_additive_count'], errors='coerce')
        stats["products_with_additives"] = int((df['flagged_additive_count'] > 0).sum())
        stats["avg_additives_per_product"] = float(df['flagged_additive_count'].mean())

    # Top categories
    if 'categories_en' in df.columns:
        cat_counts = df['categories_en'].value_counts().head(15).to_dict()
        stats["top_categories"] = {str(k): int(v) for k, v in cat_counts.items()}

    # Top brands
    if 'brands' in df.columns:
        brand_counts = df['brands'].value_counts().head(15).to_dict()
        stats["top_brands"] = {str(k): int(v) for k, v in brand_counts.items()}

    # Nutritional averages
    nutrition_cols = ['sugars_100g', 'sodium_100g', 'fat_100g', 'energy-kcal_100g']
    nutrition_stats = {}
    for col in nutrition_cols:
        if col in df.columns:
            numeric = pd.to_numeric(df[col], errors='coerce')
            valid = numeric.dropna()
            if len(valid) > 0:
                nutrition_stats[col] = {
                    "mean": float(valid.mean()),
                    "median": float(valid.median()),
                }
    stats["nutrition_averages"] = nutrition_stats

    return stats


def analyze_ruralaccess():
    """Analyze RuralAccess healthcare shortage data."""
    print("\n" + "=" * 60)
    print("RURALACCESS ANALYSIS")
    print("=" * 60)

    df = pd.read_parquet(f"{DATA_DIR}/ruralaccess/hpsa_designations.parquet")

    stats = {
        "total_hpsa_designations": len(df),
    }

    # By state
    if 'state' in df.columns:
        state_counts = df['state'].value_counts().to_dict()
        stats["by_state"] = {str(k): int(v) for k, v in state_counts.items()}
        stats["states_with_shortages"] = len(state_counts)

    # By discipline
    if 'discipline' in df.columns:
        disc_counts = df['discipline'].value_counts().to_dict()
        stats["by_discipline"] = {str(k): int(v) for k, v in disc_counts.items()}

    # Rural status
    if 'rural_status' in df.columns:
        rural_counts = df['rural_status'].value_counts().to_dict()
        stats["rural_status"] = {str(k): int(v) for k, v in rural_counts.items()}

    # HPSA scores
    if 'hpsa_score' in df.columns:
        df['hpsa_score'] = pd.to_numeric(df['hpsa_score'], errors='coerce')
        valid = df['hpsa_score'].dropna()
        if len(valid) > 0:
            stats["hpsa_score"] = {
                "mean": float(valid.mean()),
                "median": float(valid.median()),
                "max": float(valid.max()),
                "min": float(valid.min()),
            }

    # Population affected
    if 'population' in df.columns:
        df['population'] = pd.to_numeric(df['population'], errors='coerce')
        valid = df['population'].dropna()
        if len(valid) > 0:
            stats["population_affected"] = {
                "total": int(valid.sum()),
                "mean_per_hpsa": int(valid.mean()),
            }

    # Poverty rate
    if 'poverty_rate' in df.columns:
        df['poverty_rate'] = pd.to_numeric(df['poverty_rate'], errors='coerce')
        valid = df['poverty_rate'].dropna()
        if len(valid) > 0:
            stats["poverty_rate"] = {
                "mean": float(valid.mean()),
                "median": float(valid.median()),
            }

    # County summary
    county_df = pd.read_parquet(f"{DATA_DIR}/ruralaccess/county_shortage_summary.parquet")
    stats["unique_counties"] = len(county_df)

    return stats


def main():
    """Run all analyses and save results."""
    all_stats = {
        "generated_at": pd.Timestamp.now().isoformat(),
        "pricevision": analyze_pricevision(),
        "drugwatch": analyze_drugwatch(),
        "foodscore": analyze_foodscore(),
        "ruralaccess": analyze_ruralaccess(),
    }

    # Save to JSON
    with open("data/processed/data_analysis.json", "w") as f:
        json.dump(all_stats, f, indent=2, default=str)

    print("\n" + "=" * 60)
    print("Analysis complete! Saved to data/processed/data_analysis.json")
    print("=" * 60)

    return all_stats


if __name__ == "__main__":
    main()
