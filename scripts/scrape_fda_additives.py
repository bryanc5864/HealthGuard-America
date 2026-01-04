"""
Scrape FDA Food Additive Status List
"""

import requests
from bs4 import BeautifulSoup
import csv
import json
from pathlib import Path

def scrape_fda_additives():
    """Scrape FDA Food Additive Status List from the FDA website."""

    # FDA EAFUS (Everything Added to Food in the US) can be accessed via this URL
    url = "https://www.cfsanappsexternal.fda.gov/scripts/fdcc/index.cfm?set=FoodSubstances&sort=Sortterm&order=ASC&startrow=1&type=basic&search="

    print("Attempting to fetch FDA food substances data...")

    # Alternative: Use the FDA GRAS substances API
    gras_url = "https://www.cfsanappsexternal.fda.gov/scripts/fdcc/index.cfm?set=SCOGS&sort=SortSCOG&order=ASC&startrow=1&type=basic&search="

    # Try to get the data
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    additives = []

    try:
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')

            # Look for table data
            tables = soup.find_all('table')
            if tables:
                print(f"Found {len(tables)} tables on page")
                for table in tables:
                    rows = table.find_all('tr')
                    for row in rows[1:]:  # Skip header
                        cols = row.find_all(['td', 'th'])
                        if cols:
                            additive = {
                                'name': cols[0].get_text(strip=True) if len(cols) > 0 else '',
                                'function': cols[1].get_text(strip=True) if len(cols) > 1 else '',
                                'status': cols[2].get_text(strip=True) if len(cols) > 2 else '',
                            }
                            if additive['name']:
                                additives.append(additive)
            else:
                print("No tables found, saving raw HTML for inspection")
                with open('fda_page.html', 'w', encoding='utf-8') as f:
                    f.write(response.text)
        else:
            print(f"HTTP {response.status_code} received")

    except Exception as e:
        print(f"Error fetching FDA data: {e}")

    return additives


def create_sample_additives():
    """Create a sample additives database based on common food additives."""

    # Common food additives with risk assessments
    additives = [
        # Artificial Dyes (High Risk)
        {"name": "Red 40", "aliases": ["Allura Red", "E129", "FD&C Red No. 40"], "type": "dye", "risk_score": 85, "fda_status": "approved", "eu_status": "restricted", "is_artificial": True, "is_petroleum_based": True, "notes": "Linked to hyperactivity in children, requires warning label in EU"},
        {"name": "Yellow 5", "aliases": ["Tartrazine", "E102", "FD&C Yellow No. 5"], "type": "dye", "risk_score": 80, "fda_status": "approved", "eu_status": "restricted", "is_artificial": True, "is_petroleum_based": True, "notes": "May cause allergic reactions, hyperactivity concerns"},
        {"name": "Yellow 6", "aliases": ["Sunset Yellow", "E110", "FD&C Yellow No. 6"], "type": "dye", "risk_score": 80, "fda_status": "approved", "eu_status": "restricted", "is_artificial": True, "is_petroleum_based": True, "notes": "Hyperactivity concerns, contamination with carcinogens"},
        {"name": "Blue 1", "aliases": ["Brilliant Blue", "E133", "FD&C Blue No. 1"], "type": "dye", "risk_score": 70, "fda_status": "approved", "eu_status": "approved", "is_artificial": True, "is_petroleum_based": True, "notes": "Generally considered safer than other dyes"},
        {"name": "Blue 2", "aliases": ["Indigo Carmine", "E132", "FD&C Blue No. 2"], "type": "dye", "risk_score": 75, "fda_status": "approved", "eu_status": "approved", "is_artificial": True, "is_petroleum_based": True, "notes": "May cause nausea and high blood pressure"},
        {"name": "Red 3", "aliases": ["Erythrosine", "E127", "FD&C Red No. 3"], "type": "dye", "risk_score": 90, "fda_status": "approved", "eu_status": "restricted", "is_artificial": True, "is_petroleum_based": False, "notes": "Thyroid carcinogen in animals, FDA proposed ban"},
        {"name": "Caramel Color", "aliases": ["E150", "Caramel Coloring"], "type": "dye", "risk_score": 60, "fda_status": "approved", "eu_status": "approved", "is_artificial": True, "is_petroleum_based": False, "notes": "4-MEI contaminant in some types is carcinogenic"},

        # Artificial Sweeteners (Moderate to High Risk)
        {"name": "Aspartame", "aliases": ["E951", "NutraSweet", "Equal"], "type": "sweetener", "risk_score": 65, "fda_status": "approved", "eu_status": "approved", "is_artificial": True, "is_petroleum_based": False, "notes": "WHO classified as possibly carcinogenic, headache reports"},
        {"name": "Sucralose", "aliases": ["E955", "Splenda"], "type": "sweetener", "risk_score": 50, "fda_status": "approved", "eu_status": "approved", "is_artificial": True, "is_petroleum_based": False, "notes": "May affect gut microbiome, stable at high heat"},
        {"name": "Saccharin", "aliases": ["E954", "Sweet'N Low"], "type": "sweetener", "risk_score": 55, "fda_status": "approved", "eu_status": "approved", "is_artificial": True, "is_petroleum_based": True, "notes": "Previously linked to cancer, warning removed in 2000"},
        {"name": "Acesulfame Potassium", "aliases": ["E950", "Ace-K", "Acesulfame K"], "type": "sweetener", "risk_score": 60, "fda_status": "approved", "eu_status": "approved", "is_artificial": True, "is_petroleum_based": False, "notes": "Inadequate testing, may affect metabolism"},
        {"name": "Stevia", "aliases": ["E960", "Steviol Glycosides", "Stevia Leaf Extract"], "type": "sweetener", "risk_score": 15, "fda_status": "approved", "eu_status": "approved", "is_artificial": False, "is_petroleum_based": False, "notes": "Natural origin, generally considered safe"},

        # Preservatives (Variable Risk)
        {"name": "Sodium Nitrite", "aliases": ["E250", "Nitrite"], "type": "preservative", "risk_score": 75, "fda_status": "approved", "eu_status": "approved", "is_artificial": True, "is_petroleum_based": False, "notes": "Forms carcinogenic nitrosamines when heated with protein"},
        {"name": "Sodium Nitrate", "aliases": ["E251", "Nitrate"], "type": "preservative", "risk_score": 70, "fda_status": "approved", "eu_status": "approved", "is_artificial": True, "is_petroleum_based": False, "notes": "Converts to nitrite, same concerns"},
        {"name": "BHA", "aliases": ["E320", "Butylated Hydroxyanisole"], "type": "preservative", "risk_score": 80, "fda_status": "approved", "eu_status": "restricted", "is_artificial": True, "is_petroleum_based": True, "notes": "Reasonably anticipated carcinogen, endocrine disruptor"},
        {"name": "BHT", "aliases": ["E321", "Butylated Hydroxytoluene"], "type": "preservative", "risk_score": 75, "fda_status": "approved", "eu_status": "approved", "is_artificial": True, "is_petroleum_based": True, "notes": "Possible carcinogen, may affect hormones"},
        {"name": "TBHQ", "aliases": ["E319", "Tertiary Butylhydroquinone"], "type": "preservative", "risk_score": 70, "fda_status": "approved", "eu_status": "approved", "is_artificial": True, "is_petroleum_based": True, "notes": "May weaken immune system at high doses"},
        {"name": "Sodium Benzoate", "aliases": ["E211", "Benzoate of Soda"], "type": "preservative", "risk_score": 55, "fda_status": "approved", "eu_status": "approved", "is_artificial": True, "is_petroleum_based": False, "notes": "Forms benzene with vitamin C, hyperactivity concerns"},
        {"name": "Potassium Sorbate", "aliases": ["E202"], "type": "preservative", "risk_score": 20, "fda_status": "approved", "eu_status": "approved", "is_artificial": True, "is_petroleum_based": False, "notes": "Generally considered safe"},
        {"name": "Citric Acid", "aliases": ["E330"], "type": "preservative", "risk_score": 5, "fda_status": "approved", "eu_status": "approved", "is_artificial": False, "is_petroleum_based": False, "notes": "Naturally occurring, very safe"},
        {"name": "Ascorbic Acid", "aliases": ["E300", "Vitamin C"], "type": "preservative", "risk_score": 5, "fda_status": "approved", "eu_status": "approved", "is_artificial": False, "is_petroleum_based": False, "notes": "Vitamin C, beneficial"},

        # Emulsifiers (Variable Risk)
        {"name": "Carrageenan", "aliases": ["E407"], "type": "emulsifier", "risk_score": 55, "fda_status": "approved", "eu_status": "approved", "is_artificial": False, "is_petroleum_based": False, "notes": "May cause inflammation and digestive issues"},
        {"name": "Polysorbate 80", "aliases": ["E433", "Tween 80"], "type": "emulsifier", "risk_score": 50, "fda_status": "approved", "eu_status": "approved", "is_artificial": True, "is_petroleum_based": False, "notes": "May affect gut barrier, inflammation concerns"},
        {"name": "Soy Lecithin", "aliases": ["E322", "Lecithin"], "type": "emulsifier", "risk_score": 15, "fda_status": "approved", "eu_status": "approved", "is_artificial": False, "is_petroleum_based": False, "notes": "Natural, generally safe, allergen for some"},
        {"name": "Mono and Diglycerides", "aliases": ["E471"], "type": "emulsifier", "risk_score": 25, "fda_status": "approved", "eu_status": "approved", "is_artificial": True, "is_petroleum_based": False, "notes": "May contain trans fats"},
        {"name": "Xanthan Gum", "aliases": ["E415"], "type": "emulsifier", "risk_score": 10, "fda_status": "approved", "eu_status": "approved", "is_artificial": False, "is_petroleum_based": False, "notes": "Generally safe, natural fermentation product"},
        {"name": "Guar Gum", "aliases": ["E412"], "type": "emulsifier", "risk_score": 10, "fda_status": "approved", "eu_status": "approved", "is_artificial": False, "is_petroleum_based": False, "notes": "Natural, may cause digestive issues in large amounts"},

        # Flavor Enhancers
        {"name": "MSG", "aliases": ["E621", "Monosodium Glutamate", "Glutamic Acid"], "type": "flavor", "risk_score": 35, "fda_status": "approved", "eu_status": "approved", "is_artificial": True, "is_petroleum_based": False, "notes": "Controversial, may cause reactions in sensitive people"},
        {"name": "Disodium Inosinate", "aliases": ["E631"], "type": "flavor", "risk_score": 30, "fda_status": "approved", "eu_status": "approved", "is_artificial": True, "is_petroleum_based": False, "notes": "Often used with MSG, similar concerns"},
        {"name": "Disodium Guanylate", "aliases": ["E627"], "type": "flavor", "risk_score": 30, "fda_status": "approved", "eu_status": "approved", "is_artificial": True, "is_petroleum_based": False, "notes": "Often used with MSG, similar concerns"},
        {"name": "Natural Flavors", "aliases": ["Natural Flavoring"], "type": "flavor", "risk_score": 25, "fda_status": "approved", "eu_status": "approved", "is_artificial": False, "is_petroleum_based": False, "notes": "Vague term, can include many substances"},
        {"name": "Artificial Flavors", "aliases": ["Artificial Flavoring"], "type": "flavor", "risk_score": 45, "fda_status": "approved", "eu_status": "approved", "is_artificial": True, "is_petroleum_based": False, "notes": "Synthetic chemicals, safety varies"},

        # High Fructose Corn Syrup and Sugars
        {"name": "High Fructose Corn Syrup", "aliases": ["HFCS", "Corn Syrup", "Glucose-Fructose Syrup"], "type": "sweetener", "risk_score": 70, "fda_status": "approved", "eu_status": "approved", "is_artificial": True, "is_petroleum_based": False, "notes": "Linked to obesity, diabetes, metabolic syndrome"},
        {"name": "Maltodextrin", "aliases": ["E1400"], "type": "other", "risk_score": 45, "fda_status": "approved", "eu_status": "approved", "is_artificial": True, "is_petroleum_based": False, "notes": "High glycemic index, may affect gut bacteria"},
        {"name": "Dextrose", "aliases": ["Glucose", "D-Glucose"], "type": "sweetener", "risk_score": 40, "fda_status": "approved", "eu_status": "approved", "is_artificial": False, "is_petroleum_based": False, "notes": "Simple sugar, high glycemic impact"},

        # Trans Fats and Oils
        {"name": "Partially Hydrogenated Oil", "aliases": ["PHO", "Trans Fat"], "type": "other", "risk_score": 100, "fda_status": "banned", "eu_status": "banned", "is_artificial": True, "is_petroleum_based": False, "notes": "Banned by FDA, causes heart disease"},
        {"name": "Interesterified Fat", "aliases": ["Interesterified Oil"], "type": "other", "risk_score": 60, "fda_status": "approved", "eu_status": "approved", "is_artificial": True, "is_petroleum_based": False, "notes": "Trans fat replacement, safety uncertain"},

        # Other Additives
        {"name": "Titanium Dioxide", "aliases": ["E171", "TiO2"], "type": "dye", "risk_score": 75, "fda_status": "approved", "eu_status": "banned", "is_artificial": True, "is_petroleum_based": False, "notes": "Banned in EU 2022, possible carcinogen"},
        {"name": "Potassium Bromate", "aliases": ["E924", "Bromated Flour"], "type": "other", "risk_score": 95, "fda_status": "approved", "eu_status": "banned", "is_artificial": True, "is_petroleum_based": False, "notes": "Carcinogen, banned in EU/UK/Canada/Brazil"},
        {"name": "Azodicarbonamide", "aliases": ["E927a", "ADA"], "type": "other", "risk_score": 80, "fda_status": "approved", "eu_status": "banned", "is_artificial": True, "is_petroleum_based": False, "notes": "Banned in EU/Australia, respiratory sensitizer"},
        {"name": "Propyl Paraben", "aliases": ["E217", "Propylparaben"], "type": "preservative", "risk_score": 70, "fda_status": "banned", "eu_status": "approved", "is_artificial": True, "is_petroleum_based": False, "notes": "Endocrine disruptor, FDA banned in food 2024"},
        {"name": "Brominated Vegetable Oil", "aliases": ["BVO", "E443"], "type": "other", "risk_score": 85, "fda_status": "banned", "eu_status": "banned", "is_artificial": True, "is_petroleum_based": False, "notes": "FDA revoked approval 2024, bioaccumulates"},
    ]

    return additives


def main():
    output_dir = Path("C:/Users/BCheng/.vscode/projects/HealthGuard/data/raw/foodscore")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Create curated additives database
    print("Creating curated additives database...")
    additives = create_sample_additives()

    # Save as CSV
    csv_path = output_dir / "additive_risks.csv"
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['name', 'aliases', 'type', 'risk_score', 'fda_status', 'eu_status', 'is_artificial', 'is_petroleum_based', 'notes']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for additive in additives:
            row = additive.copy()
            row['aliases'] = '|'.join(row['aliases'])  # Convert list to pipe-separated string
            writer.writerow(row)

    # Save as JSON
    json_path = output_dir / "additive_risks.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(additives, f, indent=2)

    print(f"Saved {len(additives)} additives to:")
    print(f"  - {csv_path}")
    print(f"  - {json_path}")

    # Also try scraping FDA data
    print("\nAttempting to scrape FDA additive list...")
    fda_additives = scrape_fda_additives()
    if fda_additives:
        fda_path = output_dir / "fda_additives_scraped.csv"
        with open(fda_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['name', 'function', 'status'])
            writer.writeheader()
            writer.writerows(fda_additives)
        print(f"Saved {len(fda_additives)} FDA additives to {fda_path}")


if __name__ == "__main__":
    main()
