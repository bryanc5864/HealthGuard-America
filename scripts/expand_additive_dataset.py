"""
Expand Additive Dataset

Combines multiple sources to create comprehensive additive risk database:
1. Existing additive_lookup.parquet (125 additives)
2. OpenFoodFacts additives extracted from products
3. EWG/CSPI risk ratings for common additives

Output: Expanded additive dataset for ML training
"""

import pandas as pd
import numpy as np
from pathlib import Path
import re

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_RAW = PROJECT_ROOT / "data" / "raw" / "foodscore"
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed" / "foodscore"

# EWG/CSPI Risk Database - Common food additives with risk scores
# Source: EWG Food Scores, CSPI Chemical Cuisine
EWG_CSPI_ADDITIVES = {
    # HIGH RISK (70-100) - Avoid
    "potassium bromate": {"risk": 95, "type": "other", "fda": "approved", "eu": "banned"},
    "brominated vegetable oil": {"risk": 90, "type": "other", "fda": "approved", "eu": "banned"},
    "bha": {"risk": 85, "type": "preservative", "fda": "approved", "eu": "restricted"},
    "butylated hydroxyanisole": {"risk": 85, "type": "preservative", "fda": "approved", "eu": "restricted"},
    "bht": {"risk": 75, "type": "preservative", "fda": "approved", "eu": "approved"},
    "butylated hydroxytoluene": {"risk": 75, "type": "preservative", "fda": "approved", "eu": "approved"},
    "propyl gallate": {"risk": 75, "type": "preservative", "fda": "approved", "eu": "approved"},
    "sodium nitrite": {"risk": 80, "type": "preservative", "fda": "approved", "eu": "approved"},
    "sodium nitrate": {"risk": 75, "type": "preservative", "fda": "approved", "eu": "approved"},
    "azodicarbonamide": {"risk": 85, "type": "other", "fda": "approved", "eu": "banned"},
    "caramel color": {"risk": 70, "type": "dye", "fda": "approved", "eu": "approved"},
    "caramel coloring": {"risk": 70, "type": "dye", "fda": "approved", "eu": "approved"},

    # MODERATE RISK (40-69) - Caution
    "carrageenan": {"risk": 65, "type": "emulsifier", "fda": "approved", "eu": "approved"},
    "polysorbate 80": {"risk": 60, "type": "emulsifier", "fda": "approved", "eu": "approved"},
    "polysorbate 60": {"risk": 55, "type": "emulsifier", "fda": "approved", "eu": "approved"},
    "sodium benzoate": {"risk": 55, "type": "preservative", "fda": "approved", "eu": "approved"},
    "potassium sorbate": {"risk": 45, "type": "preservative", "fda": "approved", "eu": "approved"},
    "sorbic acid": {"risk": 40, "type": "preservative", "fda": "approved", "eu": "approved"},
    "phosphoric acid": {"risk": 50, "type": "other", "fda": "approved", "eu": "approved"},
    "sodium phosphate": {"risk": 50, "type": "emulsifier", "fda": "approved", "eu": "approved"},
    "monosodium glutamate": {"risk": 45, "type": "flavor", "fda": "approved", "eu": "approved"},
    "msg": {"risk": 45, "type": "flavor", "fda": "approved", "eu": "approved"},
    "high fructose corn syrup": {"risk": 60, "type": "sweetener", "fda": "approved", "eu": "approved"},
    "hfcs": {"risk": 60, "type": "sweetener", "fda": "approved", "eu": "approved"},
    "corn syrup": {"risk": 50, "type": "sweetener", "fda": "approved", "eu": "approved"},
    "partially hydrogenated": {"risk": 95, "type": "other", "fda": "banned", "eu": "banned"},
    "hydrogenated oil": {"risk": 70, "type": "other", "fda": "approved", "eu": "approved"},
    "interesterified oil": {"risk": 55, "type": "other", "fda": "approved", "eu": "approved"},
    "tbhq": {"risk": 65, "type": "preservative", "fda": "approved", "eu": "approved"},
    "sodium aluminum phosphate": {"risk": 55, "type": "other", "fda": "approved", "eu": "approved"},
    "sodium aluminum sulfate": {"risk": 55, "type": "other", "fda": "approved", "eu": "approved"},

    # LOW RISK (10-39) - Generally Safe
    "citric acid": {"risk": 10, "type": "preservative", "fda": "approved", "eu": "approved"},
    "ascorbic acid": {"risk": 5, "type": "preservative", "fda": "approved", "eu": "approved"},
    "vitamin c": {"risk": 5, "type": "other", "fda": "approved", "eu": "approved"},
    "tocopherols": {"risk": 10, "type": "preservative", "fda": "approved", "eu": "approved"},
    "vitamin e": {"risk": 10, "type": "other", "fda": "approved", "eu": "approved"},
    "lactic acid": {"risk": 10, "type": "preservative", "fda": "approved", "eu": "approved"},
    "malic acid": {"risk": 10, "type": "other", "fda": "approved", "eu": "approved"},
    "pectin": {"risk": 5, "type": "emulsifier", "fda": "approved", "eu": "approved"},
    "lecithin": {"risk": 10, "type": "emulsifier", "fda": "approved", "eu": "approved"},
    "soy lecithin": {"risk": 15, "type": "emulsifier", "fda": "approved", "eu": "approved"},
    "sunflower lecithin": {"risk": 10, "type": "emulsifier", "fda": "approved", "eu": "approved"},
    "xanthan gum": {"risk": 15, "type": "emulsifier", "fda": "approved", "eu": "approved"},
    "guar gum": {"risk": 15, "type": "emulsifier", "fda": "approved", "eu": "approved"},
    "locust bean gum": {"risk": 10, "type": "emulsifier", "fda": "approved", "eu": "approved"},
    "gellan gum": {"risk": 15, "type": "emulsifier", "fda": "approved", "eu": "approved"},
    "acacia gum": {"risk": 10, "type": "emulsifier", "fda": "approved", "eu": "approved"},
    "gum arabic": {"risk": 10, "type": "emulsifier", "fda": "approved", "eu": "approved"},
    "cellulose": {"risk": 10, "type": "other", "fda": "approved", "eu": "approved"},
    "cellulose gum": {"risk": 15, "type": "emulsifier", "fda": "approved", "eu": "approved"},
    "methylcellulose": {"risk": 15, "type": "emulsifier", "fda": "approved", "eu": "approved"},
    "beta carotene": {"risk": 5, "type": "dye", "fda": "approved", "eu": "approved"},
    "annatto": {"risk": 25, "type": "dye", "fda": "approved", "eu": "approved"},
    "paprika": {"risk": 5, "type": "dye", "fda": "approved", "eu": "approved"},
    "turmeric": {"risk": 5, "type": "dye", "fda": "approved", "eu": "approved"},
    "beet juice": {"risk": 5, "type": "dye", "fda": "approved", "eu": "approved"},
    "stevia": {"risk": 20, "type": "sweetener", "fda": "approved", "eu": "approved"},
    "monk fruit": {"risk": 15, "type": "sweetener", "fda": "approved", "eu": "approved"},
    "erythritol": {"risk": 25, "type": "sweetener", "fda": "approved", "eu": "approved"},
    "xylitol": {"risk": 25, "type": "sweetener", "fda": "approved", "eu": "approved"},
    "sorbitol": {"risk": 30, "type": "sweetener", "fda": "approved", "eu": "approved"},
    "maltitol": {"risk": 35, "type": "sweetener", "fda": "approved", "eu": "approved"},
    "mannitol": {"risk": 30, "type": "sweetener", "fda": "approved", "eu": "approved"},
    "inulin": {"risk": 15, "type": "other", "fda": "approved", "eu": "approved"},
    "natural flavor": {"risk": 30, "type": "flavor", "fda": "approved", "eu": "approved"},
    "natural flavors": {"risk": 30, "type": "flavor", "fda": "approved", "eu": "approved"},
    "artificial flavor": {"risk": 50, "type": "flavor", "fda": "approved", "eu": "approved"},
    "artificial flavors": {"risk": 50, "type": "flavor", "fda": "approved", "eu": "approved"},
}

# E-number to name/risk mapping (European additive codes)
E_NUMBER_MAP = {
    # Colors (E100-E199)
    "e100": {"name": "curcumin", "risk": 10, "type": "dye"},
    "e101": {"name": "riboflavin", "risk": 5, "type": "dye"},
    "e102": {"name": "tartrazine", "risk": 80, "type": "dye"},
    "e104": {"name": "quinoline yellow", "risk": 75, "type": "dye"},
    "e110": {"name": "sunset yellow", "risk": 80, "type": "dye"},
    "e120": {"name": "carmine", "risk": 40, "type": "dye"},
    "e122": {"name": "azorubine", "risk": 75, "type": "dye"},
    "e123": {"name": "amaranth", "risk": 90, "type": "dye"},
    "e124": {"name": "ponceau 4r", "risk": 75, "type": "dye"},
    "e127": {"name": "erythrosine", "risk": 70, "type": "dye"},
    "e129": {"name": "allura red", "risk": 85, "type": "dye"},
    "e131": {"name": "patent blue v", "risk": 65, "type": "dye"},
    "e132": {"name": "indigotine", "risk": 60, "type": "dye"},
    "e133": {"name": "brilliant blue", "risk": 70, "type": "dye"},
    "e140": {"name": "chlorophyll", "risk": 5, "type": "dye"},
    "e141": {"name": "copper chlorophyll", "risk": 15, "type": "dye"},
    "e150a": {"name": "caramel color", "risk": 50, "type": "dye"},
    "e150b": {"name": "caustic sulfite caramel", "risk": 60, "type": "dye"},
    "e150c": {"name": "ammonia caramel", "risk": 70, "type": "dye"},
    "e150d": {"name": "sulfite ammonia caramel", "risk": 75, "type": "dye"},
    "e151": {"name": "brilliant black", "risk": 70, "type": "dye"},
    "e153": {"name": "vegetable carbon", "risk": 20, "type": "dye"},
    "e160a": {"name": "beta carotene", "risk": 5, "type": "dye"},
    "e160b": {"name": "annatto", "risk": 25, "type": "dye"},
    "e160c": {"name": "paprika extract", "risk": 5, "type": "dye"},
    "e160d": {"name": "lycopene", "risk": 5, "type": "dye"},
    "e161b": {"name": "lutein", "risk": 5, "type": "dye"},
    "e162": {"name": "beetroot red", "risk": 5, "type": "dye"},
    "e163": {"name": "anthocyanins", "risk": 5, "type": "dye"},
    "e170": {"name": "calcium carbonate", "risk": 5, "type": "other"},
    "e171": {"name": "titanium dioxide", "risk": 70, "type": "dye"},
    "e172": {"name": "iron oxides", "risk": 20, "type": "dye"},

    # Preservatives (E200-E299)
    "e200": {"name": "sorbic acid", "risk": 40, "type": "preservative"},
    "e202": {"name": "potassium sorbate", "risk": 45, "type": "preservative"},
    "e210": {"name": "benzoic acid", "risk": 55, "type": "preservative"},
    "e211": {"name": "sodium benzoate", "risk": 55, "type": "preservative"},
    "e212": {"name": "potassium benzoate", "risk": 55, "type": "preservative"},
    "e220": {"name": "sulfur dioxide", "risk": 50, "type": "preservative"},
    "e221": {"name": "sodium sulfite", "risk": 50, "type": "preservative"},
    "e223": {"name": "sodium metabisulfite", "risk": 50, "type": "preservative"},
    "e224": {"name": "potassium metabisulfite", "risk": 50, "type": "preservative"},
    "e249": {"name": "potassium nitrite", "risk": 80, "type": "preservative"},
    "e250": {"name": "sodium nitrite", "risk": 80, "type": "preservative"},
    "e251": {"name": "sodium nitrate", "risk": 75, "type": "preservative"},
    "e252": {"name": "potassium nitrate", "risk": 75, "type": "preservative"},
    "e260": {"name": "acetic acid", "risk": 5, "type": "preservative"},
    "e270": {"name": "lactic acid", "risk": 10, "type": "preservative"},
    "e280": {"name": "propionic acid", "risk": 25, "type": "preservative"},
    "e281": {"name": "sodium propionate", "risk": 30, "type": "preservative"},
    "e282": {"name": "calcium propionate", "risk": 30, "type": "preservative"},
    "e296": {"name": "malic acid", "risk": 10, "type": "other"},
    "e297": {"name": "fumaric acid", "risk": 15, "type": "other"},

    # Antioxidants (E300-E399)
    "e300": {"name": "ascorbic acid", "risk": 5, "type": "preservative"},
    "e301": {"name": "sodium ascorbate", "risk": 5, "type": "preservative"},
    "e302": {"name": "calcium ascorbate", "risk": 5, "type": "preservative"},
    "e304": {"name": "ascorbyl palmitate", "risk": 10, "type": "preservative"},
    "e306": {"name": "tocopherols", "risk": 10, "type": "preservative"},
    "e307": {"name": "alpha tocopherol", "risk": 10, "type": "preservative"},
    "e310": {"name": "propyl gallate", "risk": 75, "type": "preservative"},
    "e315": {"name": "erythorbic acid", "risk": 10, "type": "preservative"},
    "e316": {"name": "sodium erythorbate", "risk": 10, "type": "preservative"},
    "e319": {"name": "tbhq", "risk": 65, "type": "preservative"},
    "e320": {"name": "bha", "risk": 85, "type": "preservative"},
    "e321": {"name": "bht", "risk": 75, "type": "preservative"},
    "e322": {"name": "lecithin", "risk": 10, "type": "emulsifier"},
    "e325": {"name": "sodium lactate", "risk": 10, "type": "other"},
    "e326": {"name": "potassium lactate", "risk": 10, "type": "other"},
    "e327": {"name": "calcium lactate", "risk": 10, "type": "other"},
    "e330": {"name": "citric acid", "risk": 10, "type": "preservative"},
    "e331": {"name": "sodium citrate", "risk": 10, "type": "other"},
    "e332": {"name": "potassium citrate", "risk": 10, "type": "other"},
    "e333": {"name": "calcium citrate", "risk": 10, "type": "other"},
    "e334": {"name": "tartaric acid", "risk": 10, "type": "other"},
    "e335": {"name": "sodium tartrate", "risk": 10, "type": "other"},
    "e336": {"name": "potassium tartrate", "risk": 10, "type": "other"},
    "e338": {"name": "phosphoric acid", "risk": 50, "type": "other"},
    "e339": {"name": "sodium phosphate", "risk": 50, "type": "emulsifier"},
    "e340": {"name": "potassium phosphate", "risk": 50, "type": "emulsifier"},
    "e341": {"name": "calcium phosphate", "risk": 40, "type": "emulsifier"},

    # Emulsifiers/Stabilizers (E400-E499)
    "e400": {"name": "alginic acid", "risk": 10, "type": "emulsifier"},
    "e401": {"name": "sodium alginate", "risk": 10, "type": "emulsifier"},
    "e402": {"name": "potassium alginate", "risk": 10, "type": "emulsifier"},
    "e406": {"name": "agar", "risk": 5, "type": "emulsifier"},
    "e407": {"name": "carrageenan", "risk": 65, "type": "emulsifier"},
    "e410": {"name": "locust bean gum", "risk": 10, "type": "emulsifier"},
    "e412": {"name": "guar gum", "risk": 15, "type": "emulsifier"},
    "e414": {"name": "gum arabic", "risk": 10, "type": "emulsifier"},
    "e415": {"name": "xanthan gum", "risk": 15, "type": "emulsifier"},
    "e417": {"name": "tara gum", "risk": 15, "type": "emulsifier"},
    "e418": {"name": "gellan gum", "risk": 15, "type": "emulsifier"},
    "e420": {"name": "sorbitol", "risk": 30, "type": "sweetener"},
    "e421": {"name": "mannitol", "risk": 30, "type": "sweetener"},
    "e422": {"name": "glycerol", "risk": 15, "type": "other"},
    "e432": {"name": "polysorbate 20", "risk": 55, "type": "emulsifier"},
    "e433": {"name": "polysorbate 80", "risk": 60, "type": "emulsifier"},
    "e435": {"name": "polysorbate 60", "risk": 55, "type": "emulsifier"},
    "e440": {"name": "pectin", "risk": 5, "type": "emulsifier"},
    "e450": {"name": "diphosphates", "risk": 50, "type": "emulsifier"},
    "e451": {"name": "triphosphates", "risk": 50, "type": "emulsifier"},
    "e452": {"name": "polyphosphates", "risk": 55, "type": "emulsifier"},
    "e460": {"name": "cellulose", "risk": 10, "type": "other"},
    "e461": {"name": "methylcellulose", "risk": 15, "type": "emulsifier"},
    "e463": {"name": "hydroxypropyl cellulose", "risk": 20, "type": "emulsifier"},
    "e464": {"name": "hydroxypropyl methylcellulose", "risk": 20, "type": "emulsifier"},
    "e466": {"name": "carboxymethyl cellulose", "risk": 25, "type": "emulsifier"},
    "e471": {"name": "mono and diglycerides", "risk": 35, "type": "emulsifier"},
    "e472e": {"name": "diacetyl tartaric acid esters", "risk": 30, "type": "emulsifier"},
    "e473": {"name": "sucrose esters", "risk": 30, "type": "emulsifier"},
    "e475": {"name": "polyglycerol esters", "risk": 30, "type": "emulsifier"},
    "e476": {"name": "polyglycerol polyricinoleate", "risk": 35, "type": "emulsifier"},
    "e481": {"name": "sodium stearoyl lactylate", "risk": 25, "type": "emulsifier"},
    "e491": {"name": "sorbitan monostearate", "risk": 30, "type": "emulsifier"},

    # Sweeteners (E900-E999)
    "e950": {"name": "acesulfame k", "risk": 55, "type": "sweetener"},
    "e951": {"name": "aspartame", "risk": 65, "type": "sweetener"},
    "e952": {"name": "cyclamate", "risk": 70, "type": "sweetener"},
    "e953": {"name": "isomalt", "risk": 25, "type": "sweetener"},
    "e954": {"name": "saccharin", "risk": 60, "type": "sweetener"},
    "e955": {"name": "sucralose", "risk": 50, "type": "sweetener"},
    "e957": {"name": "thaumatin", "risk": 15, "type": "sweetener"},
    "e960": {"name": "steviol glycosides", "risk": 20, "type": "sweetener"},
    "e961": {"name": "neotame", "risk": 55, "type": "sweetener"},
    "e962": {"name": "aspartame acesulfame salt", "risk": 60, "type": "sweetener"},
    "e965": {"name": "maltitol", "risk": 35, "type": "sweetener"},
    "e966": {"name": "lactitol", "risk": 30, "type": "sweetener"},
    "e967": {"name": "xylitol", "risk": 25, "type": "sweetener"},
    "e968": {"name": "erythritol", "risk": 25, "type": "sweetener"},
}


def extract_openfoodfacts_additives(sample_size: int = 100000) -> set:
    """Extract unique additives from OpenFoodFacts products."""
    off_path = DATA_RAW / "openfoodfacts_us.csv.gz"

    if not off_path.exists():
        print(f"OpenFoodFacts not found: {off_path}")
        return set()

    print(f"Reading OpenFoodFacts additives (sample={sample_size})...")
    df = pd.read_csv(off_path, sep='\t', usecols=['additives_tags'], nrows=sample_size, low_memory=False)

    additives = set()
    for tags in df['additives_tags'].dropna():
        if isinstance(tags, str):
            for tag in tags.split(','):
                tag = tag.strip().lower()
                if tag.startswith('en:'):
                    tag = tag[3:]
                if tag:
                    additives.add(tag)

    print(f"Found {len(additives)} unique additives in OpenFoodFacts")
    return additives


def build_expanded_dataset() -> pd.DataFrame:
    """Build expanded additive dataset from all sources."""

    # 1. Load existing processed data
    existing_df = pd.read_parquet(DATA_PROCESSED / "additive_lookup.parquet")
    existing_names = set(existing_df['name'].str.lower())
    print(f"Existing additives: {len(existing_df)}")

    # 2. Extract from OpenFoodFacts
    off_additives = extract_openfoodfacts_additives()

    # 3. Build new entries from EWG/CSPI database
    new_entries = []

    # Add EWG/CSPI additives
    for name, info in EWG_CSPI_ADDITIVES.items():
        if name.lower() not in existing_names:
            new_entries.append({
                'name': name.lower(),
                'risk_score': info['risk'],
                'type': info['type'],
                'fda_status': info['fda'],
                'eu_status': info['eu'],
                'is_artificial': info['type'] in ['dye', 'sweetener', 'preservative'],
            })
            existing_names.add(name.lower())

    # Add E-number additives
    for e_num, info in E_NUMBER_MAP.items():
        # Add E-number itself
        if e_num not in existing_names:
            new_entries.append({
                'name': e_num,
                'risk_score': info['risk'],
                'type': info['type'],
                'fda_status': 'approved',
                'eu_status': 'approved',
                'is_artificial': info['type'] in ['dye', 'sweetener', 'preservative'],
            })
            existing_names.add(e_num)

        # Add name if not already present
        if info['name'] not in existing_names:
            new_entries.append({
                'name': info['name'],
                'risk_score': info['risk'],
                'type': info['type'],
                'fda_status': 'approved',
                'eu_status': 'approved',
                'is_artificial': info['type'] in ['dye', 'sweetener', 'preservative'],
            })
            existing_names.add(info['name'])

    # Add common additives found in OpenFoodFacts that we have risk data for
    for additive in off_additives:
        additive_clean = additive.replace('-', ' ').replace('_', ' ').strip()

        # Check if it's an E-number
        e_match = re.match(r'e(\d+[a-z]?)', additive_clean)
        if e_match:
            e_code = e_match.group(0)
            if e_code in E_NUMBER_MAP and additive_clean not in existing_names:
                info = E_NUMBER_MAP[e_code]
                new_entries.append({
                    'name': additive_clean,
                    'risk_score': info['risk'],
                    'type': info['type'],
                    'fda_status': 'approved',
                    'eu_status': 'approved',
                    'is_artificial': info['type'] in ['dye', 'sweetener', 'preservative'],
                })
                existing_names.add(additive_clean)

        # Check if name matches EWG/CSPI
        if additive_clean in EWG_CSPI_ADDITIVES and additive_clean not in existing_names:
            info = EWG_CSPI_ADDITIVES[additive_clean]
            new_entries.append({
                'name': additive_clean,
                'risk_score': info['risk'],
                'type': info['type'],
                'fda_status': info['fda'],
                'eu_status': info['eu'],
                'is_artificial': info['type'] in ['dye', 'sweetener', 'preservative'],
            })
            existing_names.add(additive_clean)

    # Combine with existing
    if new_entries:
        new_df = pd.DataFrame(new_entries)
        expanded_df = pd.concat([existing_df, new_df], ignore_index=True)
    else:
        expanded_df = existing_df

    # Drop duplicates by name
    expanded_df = expanded_df.drop_duplicates(subset=['name'], keep='first')

    print(f"\nExpanded dataset: {len(expanded_df)} additives")
    print(f"  - From existing: {len(existing_df)}")
    print(f"  - New additions: {len(new_entries)}")

    # Print distribution
    print(f"\nType distribution:")
    for t, count in expanded_df['type'].value_counts().items():
        print(f"  {t}: {count}")

    print(f"\nRisk score distribution:")
    print(f"  Min: {expanded_df['risk_score'].min()}")
    print(f"  Max: {expanded_df['risk_score'].max()}")
    print(f"  Mean: {expanded_df['risk_score'].mean():.1f}")

    return expanded_df


def main():
    """Build and save expanded additive dataset."""
    print("=" * 60)
    print("EXPANDING ADDITIVE DATASET")
    print("=" * 60)

    expanded_df = build_expanded_dataset()

    # Save
    output_path = DATA_PROCESSED / "additive_lookup.parquet"
    expanded_df.to_parquet(output_path, index=False)
    print(f"\nSaved to: {output_path}")

    # Also save CSV for inspection
    csv_path = DATA_RAW / "additive_risks_expanded.csv"
    expanded_df.to_csv(csv_path, index=False)
    print(f"CSV backup: {csv_path}")

    print("\n" + "=" * 60)
    print("EXPANSION COMPLETE")
    print("=" * 60)

    return expanded_df


if __name__ == "__main__":
    main()
