# Data Download Instructions

> **⚠️ WORK IN PROGRESS**: The `download_data.py` script is currently unfinished. PriceVision MRF data (1,084 hospital files, 30M+ records) is not yet available for automatic download. Check back for updates or contact the repository owner for data access.

This folder contains scripts to download the raw data needed for HealthGuard America.

## Quick Start

```bash
# Install dependencies
pip install requests tqdm pandas

# Download all data
python datadownload/download_data.py --all
```

## Data Sources

### DrugWatch
| Source | URL | Size |
|--------|-----|------|
| US Medicare Part D | [CMS Data](https://data.cms.gov/summary-statistics-on-use-and-payments/medicare-medicaid-spending-by-drug) | ~50MB |
| Australia PBS | [PBS Downloads](https://www.pbs.gov.au/info/browse/download) | ~20MB |
| Canada DPD | [Health Canada](https://health-products.canada.ca/api/drug/) | ~10MB |

### FoodScore
| Source | URL | Size |
|--------|-----|------|
| OpenFoodFacts | [OFF Data](https://world.openfoodfacts.org/data) | ~6GB compressed |
| Additive Database | Generated locally | ~5KB |

### RuralAccess
| Source | URL | Size |
|--------|-----|------|
| HRSA HPSA | [HRSA Data](https://data.hrsa.gov/topics/health-workforce/shortage-areas) | ~50MB |
| Census Population | [Census API](https://www.census.gov/data/developers.html) | ~5MB |

### PriceVision (Special Handling Required)
Hospital MRF files are decentralized. Options:

1. **DoltHub** (Recommended):
   ```bash
   pip install dolt
   dolt clone dolthub/hospital-price-transparency
   ```

2. **Turquoise Health**: https://turquoise.health/

3. **Manual Download**: Visit individual hospital websites

## Usage

```bash
# Download specific modules
python datadownload/download_data.py --drugwatch
python datadownload/download_data.py --foodscore
python datadownload/download_data.py --ruralaccess
python datadownload/download_data.py --pricevision

# Download everything
python datadownload/download_data.py --all
```

## After Downloading

Process the raw data:
```bash
python scripts/process_data.py --all
```

## Directory Structure After Download

```
data/
├── raw/
│   ├── pricevision/
│   │   ├── mrfs/           # Hospital MRF files
│   │   └── hospital_general_info.csv
│   ├── drugwatch/
│   │   ├── us/part_d/      # Medicare Part D
│   │   ├── australia/pbs/  # PBS data
│   │   └── canada/         # Health Canada
│   ├── foodscore/
│   │   ├── openfoodfacts_us.csv.gz
│   │   └── additive_risks.csv
│   └── ruralaccess/
│       ├── hrsa_hpsa.csv
│       └── county_population.json
└── processed/              # Generated after processing
```

## Troubleshooting

**Download fails**: Some government APIs have rate limits. Wait and retry.

**Large file timeout**: For OpenFoodFacts (~6GB), use a download manager or:
```bash
wget https://static.openfoodfacts.org/data/en.openfoodfacts.org.products.csv.gz
```

**MRF files missing**: See PriceVision section above for data sources.
