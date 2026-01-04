"""
Create sample procedure name variations for training the BioClinicalBERT encoder.
Based on real CPT code variations seen in hospital price transparency files.
"""

import csv
import json
from pathlib import Path

# Sample procedure variations mapped to CPT codes
# These represent the kind of naming inconsistencies we need to handle
PROCEDURE_VARIATIONS = [
    # MRI Brain variations (CPT 70551)
    {"cpt_code": "70551", "canonical_name": "MRI Brain without Contrast", "variations": [
        "MRI BRAIN W/O CONTRAST",
        "Magnetic Resonance Imaging, Brain, Without Dye",
        "MR HEAD WO",
        "713 MRI BRAIN PLAIN",
        "MRI HEAD NO CONTRAST",
        "BRAIN MRI WO CONTRAST MATERIAL",
        "MR BRAIN WITHOUT IV CONTRAST",
        "Magnetic Resonance Brain Scan",
        "MRI BRN W/O",
    ]},
    # MRI Brain with Contrast (CPT 70552)
    {"cpt_code": "70552", "canonical_name": "MRI Brain with Contrast", "variations": [
        "MRI BRAIN W/ CONTRAST",
        "Magnetic Resonance Imaging, Brain, With Dye",
        "MR HEAD W CONTRAST",
        "714 MRI BRAIN W/CONTRAST",
        "MRI HEAD WITH CONTRAST",
        "BRAIN MRI WITH CONTRAST MATERIAL",
        "MR BRAIN WITH IV CONTRAST",
        "MRI BRN W/",
    ]},
    # CT Head (CPT 70450)
    {"cpt_code": "70450", "canonical_name": "CT Head without Contrast", "variations": [
        "CT HEAD W/O CONTRAST",
        "Computed Tomography, Head, Without Dye",
        "HEAD CT NO CONTRAST",
        "CT SCAN HEAD PLAIN",
        "CAT SCAN HEAD W/O",
        "CT HEAD WO IV CONTRAST",
        "COMPUTED TOMOGRAPHY HEAD",
    ]},
    # Knee Replacement (CPT 27447)
    {"cpt_code": "27447", "canonical_name": "Total Knee Arthroplasty", "variations": [
        "TOTAL KNEE REPLACEMENT",
        "TKA",
        "Total Knee Arthroplasty",
        "KNEE REPLACEMENT TOTAL",
        "ARTHROPLASTY KNEE TOTAL",
        "Complete Knee Replacement Surgery",
        "Knee Joint Replacement",
        "TOTAL KNEE",
    ]},
    # Hip Replacement (CPT 27130)
    {"cpt_code": "27130", "canonical_name": "Total Hip Arthroplasty", "variations": [
        "TOTAL HIP REPLACEMENT",
        "THA",
        "Total Hip Arthroplasty",
        "HIP REPLACEMENT TOTAL",
        "ARTHROPLASTY HIP TOTAL",
        "Complete Hip Replacement Surgery",
        "Hip Joint Replacement",
        "TOTAL HIP",
    ]},
    # Colonoscopy (CPT 45378)
    {"cpt_code": "45378", "canonical_name": "Colonoscopy Diagnostic", "variations": [
        "COLONOSCOPY",
        "DIAGNOSTIC COLONOSCOPY",
        "Colonoscopy, flexible",
        "COLONOSCOPY FLEXIBLE",
        "GI COLONOSCOPY",
        "Colonoscopy Procedure",
        "COLON SCOPE",
    ]},
    # Chest X-Ray (CPT 71046)
    {"cpt_code": "71046", "canonical_name": "Chest X-Ray 2 Views", "variations": [
        "CHEST XRAY 2V",
        "CXR 2 VIEWS",
        "Chest X-Ray, 2 Views",
        "CHEST RADIOGRAPH",
        "X-RAY CHEST 2 VIEW",
        "Chest Film 2 View",
        "PA AND LATERAL CHEST",
    ]},
    # Echocardiogram (CPT 93306)
    {"cpt_code": "93306", "canonical_name": "Echocardiogram Complete", "variations": [
        "ECHO COMPLETE",
        "ECHOCARDIOGRAM",
        "TTE COMPLETE",
        "Transthoracic Echocardiogram",
        "CARDIAC ECHO",
        "Heart Ultrasound Complete",
        "ECHO DOPPLER COMPLETE",
    ]},
    # C-Section (CPT 59510)
    {"cpt_code": "59510", "canonical_name": "Cesarean Delivery", "variations": [
        "C-SECTION",
        "CESAREAN SECTION",
        "CSECTION DELIVERY",
        "Cesarean Delivery",
        "C SECTION",
        "SURGICAL DELIVERY",
        "CESAREAN BIRTH",
    ]},
    # Vaginal Delivery (CPT 59400)
    {"cpt_code": "59400", "canonical_name": "Vaginal Delivery", "variations": [
        "VAGINAL DELIVERY",
        "NORMAL DELIVERY",
        "NSD",
        "Natural Childbirth",
        "VAGINAL BIRTH",
        "SPONTANEOUS VAGINAL DELIVERY",
    ]},
    # Blood Work (CPT 80053)
    {"cpt_code": "80053", "canonical_name": "Comprehensive Metabolic Panel", "variations": [
        "CMP",
        "COMPREHENSIVE METABOLIC PANEL",
        "CHEM 14",
        "Metabolic Panel Comprehensive",
        "COMPLETE METABOLIC",
        "BLOOD CHEM PANEL",
    ]},
    # CBC (CPT 85025)
    {"cpt_code": "85025", "canonical_name": "Complete Blood Count with Differential", "variations": [
        "CBC WITH DIFF",
        "COMPLETE BLOOD COUNT",
        "CBC W DIFFERENTIAL",
        "Blood Count Complete",
        "CBC AUTO DIFF",
        "HEMOGRAM WITH DIFF",
    ]},
    # Upper GI Endoscopy (CPT 43239)
    {"cpt_code": "43239", "canonical_name": "Upper GI Endoscopy with Biopsy", "variations": [
        "EGD WITH BIOPSY",
        "UPPER ENDOSCOPY",
        "ESOPHAGOGASTRODUODENOSCOPY",
        "Upper GI Scope",
        "GASTROSCOPY",
        "EGD DIAGNOSTIC",
    ]},
    # Mammogram (CPT 77067)
    {"cpt_code": "77067", "canonical_name": "Screening Mammogram Bilateral", "variations": [
        "MAMMO SCREENING",
        "SCREENING MAMMOGRAM",
        "BILATERAL MAMMOGRAM",
        "Mammography Screening",
        "MAMMO BILATERAL",
        "BREAST SCREENING",
    ]},
    # Cardiac Catheterization (CPT 93458)
    {"cpt_code": "93458", "canonical_name": "Left Heart Catheterization", "variations": [
        "LEFT HEART CATH",
        "CARDIAC CATH",
        "LHC",
        "Heart Catheterization",
        "CORONARY ANGIOGRAPHY",
        "CARDIAC CATHETERIZATION",
    ]},
]


def main():
    output_dir = Path("C:/Users/BCheng/.vscode/projects/HealthGuard/data/raw/pricevision")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Remove failed download
    failed_file = output_dir / "medicare_provider_util.csv"
    if failed_file.exists() and failed_file.stat().st_size < 100:
        failed_file.unlink()

    # Create training pairs CSV
    training_data = []
    for proc in PROCEDURE_VARIATIONS:
        for variation in proc['variations']:
            training_data.append({
                'cpt_code': proc['cpt_code'],
                'canonical_name': proc['canonical_name'],
                'procedure_name': variation,
            })

    csv_path = output_dir / "procedure_training_data.csv"
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['cpt_code', 'canonical_name', 'procedure_name'])
        writer.writeheader()
        writer.writerows(training_data)

    # Save full structure as JSON
    json_path = output_dir / "procedure_variations.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(PROCEDURE_VARIATIONS, f, indent=2)

    print(f"Created procedure training data:")
    print(f"  - {len(PROCEDURE_VARIATIONS)} CPT codes")
    print(f"  - {len(training_data)} procedure name variations")
    print(f"  - Saved to: {csv_path}")
    print(f"  - Saved to: {json_path}")


if __name__ == "__main__":
    main()
