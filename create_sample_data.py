#!/usr/bin/env python3
"""Create sample data files for HealthGuard America demo"""
import pandas as pd
import numpy as np
from pathlib import Path
import random

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / 'data'

# Create sample price data
def create_price_data():
    """Generate sample hospital price data"""
    hospitals = list(range(100001, 100021))
    procedures = [
        ('70553', 'MRI Brain with and without Contrast'),
        ('70551', 'MRI Brain without Contrast'),
        ('71046', 'Chest X-Ray 2 Views'),
        ('71250', 'CT Chest without Contrast'),
        ('71260', 'CT Chest with Contrast'),
        ('72148', 'MRI Lumbar Spine without Contrast'),
        ('74177', 'CT Abdomen/Pelvis with Contrast'),
        ('45378', 'Colonoscopy Diagnostic'),
        ('45380', 'Colonoscopy with Biopsy'),
        ('27447', 'Total Knee Replacement'),
        ('27130', 'Total Hip Replacement'),
        ('93306', 'Echocardiogram Complete'),
        ('99213', 'Office Visit Established Level 3'),
        ('99214', 'Office Visit Established Level 4'),
    ]

    base_prices = {
        '70553': 1200, '70551': 900, '71046': 150, '71250': 800, '71260': 1100,
        '72148': 1100, '74177': 1400, '45378': 2500, '45380': 3200,
        '27447': 45000, '27130': 42000, '93306': 950, '99213': 180, '99214': 280
    }

    records = []
    for hosp_id in hospitals:
        for proc_code, proc_desc in procedures:
            base = base_prices[proc_code]
            # Add random variance
            variance = random.uniform(0.6, 1.8)
            cash_price = round(base * variance, 2)
            gross_charge = round(cash_price * random.uniform(2.0, 4.5), 2)

            records.append({
                'hospital_npi': str(hosp_id),
                'procedure_code': proc_code,
                'description': proc_desc,
                'cash_price': cash_price,
                'gross_charge': gross_charge,
                'min_price': round(cash_price * 0.8, 2),
                'max_price': round(cash_price * 1.2, 2),
                'payer_name': 'Cash/Self-Pay'
            })

    df = pd.DataFrame(records)
    output_file = DATA_DIR / 'processed/pricevision/all_prices_normalized.parquet'
    df.to_parquet(output_file, index=False)
    print(f"Created {output_file} with {len(df)} records")
    return df

# Create DrugWatch sample data
def create_drug_data():
    """Generate sample drug pricing data"""
    drugs = [
        ('Eliquis', 'apixaban', 550.00, 6500000, 23500000000),
        ('Ozempic', 'semaglutide', 935.00, 3200000, 12800000000),
        ('Humira', 'adalimumab', 6922.00, 920000, 8500000000),
        ('Jardiance', 'empagliflozin', 598.00, 4100000, 7200000000),
        ('Trulicity', 'dulaglutide', 886.00, 2800000, 6100000000),
        ('Xarelto', 'rivaroxaban', 525.00, 5200000, 5800000000),
        ('Keytruda', 'pembrolizumab', 10897.00, 450000, 5200000000),
        ('Revlimid', 'lenalidomide', 16053.00, 85000, 4900000000),
        ('Opdivo', 'nivolumab', 6348.00, 380000, 4500000000),
        ('Enbrel', 'etanercept', 5862.00, 520000, 4200000000),
        ('Metformin', 'metformin', 12.00, 35000000, 1200000000),
        ('Lisinopril', 'lisinopril', 8.00, 42000000, 980000000),
        ('Atorvastatin', 'atorvastatin', 15.00, 28000000, 850000000),
        ('Amlodipine', 'amlodipine', 10.00, 32000000, 720000000),
        ('Omeprazole', 'omeprazole', 18.00, 25000000, 680000000),
    ]

    records = []
    for brand, generic, us_price, beneficiaries, spending in drugs:
        records.append({
            'brand_name': brand,
            'generic_name': generic,
            'us_price': us_price,
            'au_price': round(us_price * random.uniform(0.25, 0.45), 2),
            'ca_price': round(us_price * random.uniform(0.30, 0.55), 2),
            'total_beneficiaries_2023': beneficiaries,
            'total_spending_2023': spending,
            'avg_cost_per_claim': round(spending / (beneficiaries * 4), 2)
        })

    df = pd.DataFrame(records)
    output_file = DATA_DIR / 'processed/drugwatch/medicare_part_d_spending.csv'
    df.to_csv(output_file, index=False)
    print(f"Created {output_file} with {len(df)} records")

    # Australia prices
    au_records = []
    for brand, generic, us_price, _, _ in drugs:
        au_records.append({
            'drug_name': brand,
            'generic_name': generic,
            'price_aud': round(us_price * random.uniform(0.20, 0.40), 2),
            'pbs_subsidy': 'Yes' if random.random() > 0.3 else 'No'
        })
    au_df = pd.DataFrame(au_records)
    au_df.to_csv(DATA_DIR / 'processed/drugwatch/australia_pbs.csv', index=False)

    # Canada prices
    ca_records = []
    for brand, generic, us_price, _, _ in drugs:
        ca_records.append({
            'drug_name': brand,
            'generic_name': generic,
            'price_cad': round(us_price * random.uniform(0.25, 0.50), 2),
        })
    ca_df = pd.DataFrame(ca_records)
    ca_df.to_csv(DATA_DIR / 'processed/drugwatch/canada_prices.csv', index=False)

    return df

# Create FoodScore sample data
def create_food_data():
    """Generate sample food product data"""
    products = [
        ('0012345678901', 'Organic Apple Juice', "Nature's Best", 1, 85, 'Beverages'),
        ('0012345678902', 'Whole Wheat Bread', 'Healthy Harvest', 3, 72, 'Bread'),
        ('0012345678903', 'Greek Yogurt Plain', 'Dairy Pure', 1, 88, 'Dairy'),
        ('0012345678904', 'Coca-Cola Classic', 'Coca-Cola', 4, 22, 'Beverages'),
        ('0012345678905', 'Doritos Nacho Cheese', 'Frito-Lay', 4, 18, 'Snacks'),
        ('0012345678906', 'Fresh Salmon Fillet', "Fisherman's Catch", 1, 95, 'Seafood'),
        ('0012345678907', 'Instant Ramen Noodles', 'Quick Meal', 4, 15, 'Prepared Foods'),
        ('0012345678908', 'Extra Virgin Olive Oil', 'Mediterranean Gold', 2, 90, 'Oils'),
        ('0012345678909', 'Frosted Flakes Cereal', "Kellogg's", 4, 28, 'Cereals'),
        ('0012345678910', 'Baby Spinach Organic', 'Farm Fresh', 1, 98, 'Vegetables'),
        ('0012345678911', 'Hot Dogs Beef', 'Oscar Mayer', 4, 25, 'Meat'),
        ('0012345678912', 'Almond Butter Natural', 'Nutty Goodness', 3, 78, 'Spreads'),
        ('0012345678913', 'Diet Coke', 'Coca-Cola', 4, 35, 'Beverages'),
        ('0012345678914', 'Brown Rice Organic', 'Whole Grains Co', 1, 92, 'Grains'),
        ('0012345678915', 'Potato Chips Classic', "Lay's", 4, 20, 'Snacks'),
    ]

    records = []
    for code, name, brand, nova, maha, category in products:
        additives = random.randint(0, 8) if nova == 4 else random.randint(0, 2)
        records.append({
            'code': code,
            'product_name': name,
            'brands': brand,
            'nova_group': nova,
            'maha_score': maha,
            'categories': category,
            'additives_count': additives,
            'nutriscore_grade': random.choice(['a', 'b', 'c', 'd', 'e']) if nova > 2 else random.choice(['a', 'b']),
        })

    df = pd.DataFrame(records)
    output_file = DATA_DIR / 'processed/foodscore/products_scored.csv'
    df.to_csv(output_file, index=False)
    print(f"Created {output_file} with {len(df)} records")

    # Additives database
    additives = [
        ('E100', 'Curcumin', 1, 'Color', 'Safe'),
        ('E150a', 'Caramel Color', 3, 'Color', 'Moderate Risk'),
        ('E211', 'Sodium Benzoate', 4, 'Preservative', 'Caution'),
        ('E250', 'Sodium Nitrite', 5, 'Preservative', 'High Risk'),
        ('E320', 'BHA', 4, 'Antioxidant', 'Caution'),
        ('E321', 'BHT', 4, 'Antioxidant', 'Caution'),
        ('E330', 'Citric Acid', 1, 'Acidity Regulator', 'Safe'),
        ('E412', 'Guar Gum', 2, 'Thickener', 'Safe'),
        ('E420', 'Sorbitol', 2, 'Sweetener', 'Safe'),
        ('E621', 'MSG', 3, 'Flavor Enhancer', 'Moderate Risk'),
        ('E951', 'Aspartame', 4, 'Sweetener', 'Caution'),
        ('E955', 'Sucralose', 3, 'Sweetener', 'Moderate Risk'),
    ]

    additive_records = []
    for code, name, risk, category, status in additives:
        additive_records.append({
            'additive_code': code,
            'additive_name': name,
            'risk_score': risk,
            'category': category,
            'status': status,
        })

    add_df = pd.DataFrame(additive_records)
    add_df.to_csv(DATA_DIR / 'processed/foodscore/additives_database.csv', index=False)

    return df

# Create ChronicCare sample data
def create_chroniccare_data():
    """Generate sample chronic disease data"""
    counties = [
        ('06037', 'Los Angeles', 'CA', 14.2, 32.5, 10.8, 22.3, 8.5),
        ('17031', 'Cook', 'IL', 12.8, 29.8, 9.2, 20.1, 7.8),
        ('48201', 'Harris', 'TX', 13.5, 31.2, 10.1, 21.5, 8.2),
        ('04013', 'Maricopa', 'AZ', 11.9, 28.5, 8.8, 19.2, 7.2),
        ('06073', 'San Diego', 'CA', 10.2, 26.1, 7.5, 17.8, 6.5),
        ('48113', 'Dallas', 'TX', 12.1, 30.5, 9.5, 20.8, 7.9),
        ('06059', 'Orange', 'CA', 9.8, 24.8, 7.1, 16.5, 6.1),
        ('12086', 'Miami-Dade', 'FL', 11.5, 28.2, 8.9, 19.8, 7.5),
        ('36047', 'Kings', 'NY', 13.2, 30.1, 9.8, 21.2, 8.1),
        ('48029', 'Bexar', 'TX', 12.8, 32.8, 10.5, 22.5, 8.8),
    ]

    records = []
    for fips, name, state, diabetes, obesity, copd, heart, kidney in counties:
        maha_index = 100 - (diabetes + obesity/2 + copd + heart + kidney) / 5 * 8
        records.append({
            'fips': fips,
            'county_name': name,
            'state': state,
            'diabetes_prevalence': diabetes,
            'obesity_prevalence': obesity,
            'copd_prevalence': copd,
            'heart_disease_prevalence': heart,
            'kidney_disease_prevalence': kidney,
            'maha_index': round(maha_index, 1),
            'priority_level': 'High' if maha_index < 65 else 'Medium' if maha_index < 75 else 'Low'
        })

    df = pd.DataFrame(records)
    output_file = DATA_DIR / 'processed/chroniccare/county_health_metrics.csv'
    df.to_csv(output_file, index=False)
    print(f"Created {output_file} with {len(df)} records")
    return df

# Create RuralAccess sample data
def create_ruralaccess_data():
    """Generate sample HPSA data"""
    hpsas = [
        ('1234567890', 'Rural Montana Primary Care', 'MT', 'Primary Care', 18, 'High', 'Geographic'),
        ('1234567891', 'West Texas Medical', 'TX', 'Primary Care', 22, 'High', 'Geographic'),
        ('1234567892', 'Eastern Kentucky Health', 'KY', 'Primary Care', 20, 'High', 'Population'),
        ('1234567893', 'South Dakota Rural', 'SD', 'Dental Health', 16, 'High', 'Geographic'),
        ('1234567894', 'Alaska Remote Communities', 'AK', 'Mental Health', 25, 'High', 'Geographic'),
        ('1234567895', 'Mississippi Delta Health', 'MS', 'Primary Care', 21, 'High', 'Population'),
        ('1234567896', 'New Mexico Frontier', 'NM', 'Primary Care', 19, 'High', 'Geographic'),
        ('1234567897', 'Arkansas Rural Counties', 'AR', 'Dental Health', 17, 'Medium', 'Geographic'),
        ('1234567898', 'West Virginia Appalachian', 'WV', 'Mental Health', 23, 'High', 'Population'),
        ('1234567899', 'Oklahoma Rural Areas', 'OK', 'Primary Care', 18, 'Medium', 'Geographic'),
    ]

    records = []
    for hpsa_id, name, state, discipline, score, need, hpsa_type in hpsas:
        records.append({
            'hpsa_id': hpsa_id,
            'hpsa_name': name,
            'state': state,
            'discipline': discipline,
            'hpsa_score': score,
            'shortage_level': need,
            'designation_type': hpsa_type,
            'population_served': random.randint(5000, 50000),
            'providers_needed': random.randint(2, 15)
        })

    df = pd.DataFrame(records)
    output_file = DATA_DIR / 'processed/ruralaccess/hpsa_designations.csv'
    df.to_csv(output_file, index=False)
    print(f"Created {output_file} with {len(df)} records")
    return df

if __name__ == '__main__':
    print("Creating sample data for HealthGuard America demo...")
    print("="*60)

    create_price_data()
    create_drug_data()
    create_food_data()
    create_chroniccare_data()
    create_ruralaccess_data()

    print("="*60)
    print("Sample data created successfully!")
