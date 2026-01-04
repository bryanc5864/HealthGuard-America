#!/usr/bin/env python3
"""
HealthGuard America - Data Processing Pipeline
Processes raw data from all four modules into standardized formats.

Usage:
    python process_data.py --all           # Process all modules
    python process_data.py --pricevision   # Process only PriceVision
    python process_data.py --drugwatch     # Process only DrugWatch
    python process_data.py --foodscore     # Process only FoodScore
    python process_data.py --ruralaccess   # Process only RuralAccess
"""

import os
import sys
import json
import gzip
import logging
import argparse
import zipfile
import tempfile
import io
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
import re

import pandas as pd
import numpy as np

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('data_processing.log')
    ]
)
logger = logging.getLogger(__name__)

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_RAW = PROJECT_ROOT / "data" / "raw"
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"

# Ensure processed directories exist
for module in ["pricevision", "drugwatch", "foodscore", "ruralaccess"]:
    (DATA_PROCESSED / module).mkdir(parents=True, exist_ok=True)


# =============================================================================
# PRICEVISION PROCESSING
# =============================================================================

class PriceVisionProcessor:
    """Process hospital MRF files into standardized price data."""

    # Extended column mapping for ALL known hospital formats
    COLUMN_MAPPING = {
        # Description columns (includes XPath-style, CMS, and simple formats)
        'description': [
            'description', 'procedure_description', 'service_description',
            'item_description', 'charge_description', 'procedure', 'descr',
            '/facility/charge/item/descr', 'service description',
        ],
        # Procedure codes (CMS format uses code|1, some use procedurecode)
        'procedure_code': [
            'code|1', 'cpt_code', 'hcpcs_code', 'procedure_code', 'procedurecode',
            'billing_code', 'cpt', 'hcpcs', 'code', 'service id',
            '/facility/charge/item/@code', '/facility/charge/item/code',
        ],
        'code_type': [
            'code|1|type', 'code_type', 'billing_code_type',
            '/facility/charge/@type',
        ],
        'revenue_code': [
            'code|2', 'revenue_code', 'rev_code', 'rc', 'revenue code',
            '/facility/charge/item/revenuecode',
        ],
        # Gross charges (many naming variants)
        'gross_charge': [
            'standard_charge|gross', 'gross_charge', 'gross', 'grosscharge',
            'standard_charge', 'charge', 'list_price', 'chargemaster_price',
            '/facility/charge/item/grosscharge', 'gross charge',
            'inpatientgrosscharge', 'outpatientgrosscharge',
            'msdrgaveragegrosscharge',
        ],
        # Cash/self-pay prices
        'cash_price': [
            'standard_charge|discounted_cash', 'discounted_cash', 'cash_price',
            'self_pay', 'cash', 'discount_cash_price', 'self_pay_price',
            '/facility/charge/item/discountcashcharge', 'discounted cash price',
            'discountedcashpriceinpatient', 'discountedcashpriceoutpatient',
        ],
        # Min/max negotiated
        'min_price': [
            'standard_charge|min', 'min', 'minimum', 'min_negotiated',
            '/facility/charge/item/minnegotiatedcharge', 'minimumnegotiatedcharge',
        ],
        'max_price': [
            'standard_charge|max', 'max', 'maximum', 'max_negotiated',
            '/facility/charge/item/maxnegotiatedcharge', 'maximumnegotiatedcharge',
        ],
        # Payer info
        'payer_name': [
            'payer_name', 'payer', 'insurance_name', 'insurance',
            '/facility/charge/item/contracts/contract/@payer',
        ],
        'plan_name': [
            'plan_name', 'plan', 'insurance_plan',
        ],
        'negotiated_rate': [
            'standard_charge|negotiated_dollar', 'negotiated_dollar',
            'negotiated_rate', 'payer_rate', 'contracted_rate',
            '/facility/charge/item/contracts/contract/@charge',
        ],
        # Setting/location
        'setting': [
            'setting', 'service_setting', 'patient_type',
        ],
    }

    # Encodings to try in order (most common first)
    ENCODINGS = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252', 'iso-8859-1', 'windows-1252']

    def __init__(self):
        self.raw_dir = DATA_RAW / "pricevision" / "mrfs"
        self.processed_dir = DATA_PROCESSED / "pricevision"
        self.hospital_info = self._load_hospital_info()

    def _load_hospital_info(self) -> pd.DataFrame:
        """Load hospital general information for enrichment."""
        info_path = DATA_RAW / "pricevision" / "hospital_general_info.csv"
        if info_path.exists():
            return pd.read_csv(info_path, dtype=str)
        return pd.DataFrame()

    def _detect_file_type(self, filepath: Path) -> str:
        """Detect actual file type by reading magic bytes and content."""
        try:
            with open(filepath, 'rb') as f:
                header = f.read(512)

            # Check for ZIP magic bytes (PK\x03\x04) - could be XLSX or ZIP containing CSV
            if header[:4] == b'PK\x03\x04':
                # Check if it's an XLSX (contains [Content_Types].xml)
                if b'[Content_Types].xml' in header or b'xl/' in header:
                    return 'xlsx'
                # Otherwise it's a ZIP containing something else (like CSV)
                return 'zip'

            # Check for OLE Compound Document (old .xls format)
            # Magic bytes: D0 CF 11 E0 A1 B1 1A E1
            if header[:8] == b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1':
                return 'xls'

            # Check for gzip magic bytes
            if header[:2] == b'\x1f\x8b':
                return 'gzip'

            # Decode for text analysis
            try:
                text = header.decode('utf-8', errors='ignore').strip()
            except:
                text = header.decode('latin-1', errors='ignore').strip()

            # Check if it's JSON (starts with { or [)
            text_stripped = text.lstrip('\ufeff')  # Remove BOM if present
            if text_stripped.startswith('{') or text_stripped.startswith('['):
                return 'json'

            # Check if it's XML
            if text_stripped.startswith('<'):
                return 'xml'

            # Check if it looks like CSV (has commas and typical headers)
            if ',' in text or '\t' in text:
                return 'csv'

            return 'unknown'
        except Exception:
            return 'unknown'

    def _extract_from_zip(self, filepath: Path) -> Optional[Path]:
        """Extract CSV/JSON from ZIP file, return temp file path."""
        try:
            with zipfile.ZipFile(filepath, 'r') as zf:
                # Look for CSV or JSON files inside
                for name in zf.namelist():
                    if name.lower().endswith(('.csv', '.json', '.txt')):
                        # Extract to temp directory
                        temp_dir = tempfile.mkdtemp()
                        extracted = zf.extract(name, temp_dir)
                        return Path(extracted)
            return None
        except Exception as e:
            logger.debug(f"Failed to extract ZIP {filepath.name}: {e}")
            return None

    def _normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize column names to standard schema."""
        if df.empty:
            return df

        # Clean column names: lowercase, strip whitespace, normalize special chars
        clean_cols = []
        for c in df.columns:
            c_clean = str(c).lower().strip()
            # Remove leading slashes for XPath-style columns
            if c_clean.startswith('/'):
                c_clean = c_clean.split('/')[-1].replace('@', '').replace('#', '')
            clean_cols.append(c_clean)
        df.columns = clean_cols

        # Map to standard names
        rename_map = {}
        used_std_names = set()  # Track which standard names we've already assigned

        for std_name, variants in self.COLUMN_MAPPING.items():
            if std_name in used_std_names:
                continue  # Skip if we already assigned this standard name

            for variant in variants:
                variant_clean = variant.lower().replace('/', '').replace('@', '').replace('#', '')
                for col in df.columns:
                    if col in rename_map:  # Skip if this column already mapped
                        continue
                    if col == variant.lower() or col == variant_clean or variant.lower() in col:
                        rename_map[col] = std_name
                        used_std_names.add(std_name)
                        break
                if std_name in used_std_names:
                    break  # Found a match for this standard name

        # Apply rename
        df = df.rename(columns=rename_map)

        # Handle any remaining duplicate column names by keeping first occurrence
        if df.columns.duplicated().any():
            df = df.loc[:, ~df.columns.duplicated(keep='first')]

        return df

    def _detect_csv_format(self, filepath: Path, encoding: str = 'utf-8') -> Tuple[str, int]:
        """
        Detect CSV format type and header row number.
        Returns: (format_type, header_row)
        Format types: 'cms', 'xpath', 'simple', 'banner', 'metadata', 'xml', 'unknown'
        """
        try:
            with open(filepath, 'r', encoding=encoding, errors='replace') as f:
                lines = []
                for i, line in enumerate(f):
                    if i >= 20:
                        break
                    lines.append(line.strip())

            if not lines:
                return ('unknown', 0)

            # Check for XML format
            if lines[0].startswith('<') and ('StandardCharges' in lines[0] or 'Facility' in lines[0]):
                return ('xml', 0)

            # Check each line to find the header row
            for i, line in enumerate(lines):
                line_lower = line.lower()
                comma_count = line.count(',')

                # CMS v2.0/v3.0 format: headers have "description,code|1"
                if 'description,code|1' in line_lower:
                    return ('cms', i)

                # XPath format: headers have "/facility/"
                if '/facility/' in line_lower and comma_count >= 5:
                    return ('xpath', i)

                # Simple format: first row with typical column names
                if i == 0 and comma_count >= 3:
                    if any(x in line_lower for x in ['cdm', 'charge description', 'service description',
                                                       'gross charge', 'revenue code', 'charge type']):
                        return ('simple', 0)

                # Metadata format: row 0 is metadata, row 1 is header
                # (single metadata line followed by headers)
                if i == 1 and comma_count >= 3:
                    # Check if this looks like a header row
                    header_indicators = ['description', 'charge', 'code', 'price', 'procedure', 'gross']
                    matches = sum(1 for x in header_indicators if x in line_lower)
                    if matches >= 2:
                        # Check if row 0 looks like metadata (few commas, contains 'date' or 'update')
                        row0_lower = lines[0].lower()
                        row0_commas = lines[0].count(',')
                        is_metadata = row0_commas <= 2 or any(m in row0_lower for m in ['update', 'date', 'last', 'version'])
                        if is_metadata:
                            return ('metadata', i)

                # Banner/metadata format: look for header row after multiple metadata rows
                if i >= 2 and comma_count >= 3:
                    # Check if this looks like a header (has typical column names)
                    header_indicators = ['description', 'charge', 'code', 'price', 'procedure', 'gross']
                    matches = sum(1 for x in header_indicators if x in line_lower)
                    if matches >= 2:
                        # Make sure previous rows look like metadata
                        prev_looks_like_metadata = all(
                            lines[j].count(',') < comma_count or
                            any(m in lines[j].lower() for m in ['update', 'date', 'file', 'note', 'last', 'machine', 'comprehensive'])
                            for j in range(i)
                        )
                        if prev_looks_like_metadata:
                            return ('banner', i)

            # Default: try row 0 as header
            return ('unknown', 0)

        except Exception:
            return ('unknown', 0)

    def _parse_csv_mrf(self, filepath: Path) -> Optional[pd.DataFrame]:
        """Parse a CSV format MRF file with robust encoding and format handling."""

        # Try each encoding
        for encoding in self.ENCODINGS:
            try:
                # Detect format and header row
                format_type, header_row = self._detect_csv_format(filepath, encoding)

                # Skip XML files - they need special parsing
                if format_type == 'xml':
                    return self._parse_xml_as_csv(filepath)

                # Try parsing with python engine (more flexible but no low_memory option)
                try:
                    df = pd.read_csv(
                        filepath,
                        skiprows=header_row,
                        encoding=encoding,
                        on_bad_lines='skip',
                        dtype=str,
                        engine='python',
                        quotechar='"',
                        skipinitialspace=True,
                    )

                    # Validate we got meaningful data
                    if df is not None and len(df) > 0 and len(df.columns) >= 3:
                        # Clean up empty rows and columns
                        df = df.dropna(how='all').dropna(axis=1, how='all')

                        if len(df) > 0 and len(df.columns) >= 3:
                            # Check for expected column patterns
                            cols_lower = ' '.join([str(c).lower() for c in df.columns])
                            has_content = any(x in cols_lower for x in [
                                'desc', 'charge', 'code', 'price', 'gross', 'procedure',
                                'service', 'payer', 'hcpcs', 'cpt', 'revenue', 'facility'
                            ])

                            if has_content:
                                return self._normalize_columns(df)
                except Exception:
                    pass

            except Exception:
                continue

        # Fallback: try with C engine (faster, supports low_memory)
        for encoding in ['latin-1', 'cp1252', 'utf-8']:
            try:
                df = pd.read_csv(
                    filepath,
                    encoding=encoding,
                    on_bad_lines='skip',
                    low_memory=False,
                    dtype=str,
                    engine='c',
                )
                if df is not None and len(df) > 0 and len(df.columns) >= 3:
                    return self._normalize_columns(df)
            except Exception:
                continue

        logger.debug(f"Could not parse CSV: {filepath.name}")
        return None

    def _parse_xml_as_csv(self, filepath: Path) -> Optional[pd.DataFrame]:
        """Parse XML-formatted MRF files."""
        try:
            import xml.etree.ElementTree as ET

            # Read file content
            with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()

            # Parse XML
            root = ET.fromstring(content)

            # Extract charge items
            records = []
            for facility in root.findall('.//Facility') or [root]:
                facility_name = facility.get('Name', '')
                for charge in facility.findall('.//Charge'):
                    for item in charge.findall('.//Item'):
                        record = {
                            'hospital_name': facility_name,
                            'description': item.findtext('Descr', ''),
                            'procedure_code': item.get('Code', ''),
                            'gross_charge': item.findtext('GrossCharge', ''),
                            'cash_price': item.findtext('DiscountCashCharge', ''),
                            'min_price': item.findtext('MinNegotiatedCharge', ''),
                            'max_price': item.findtext('MaxNegotiatedCharge', ''),
                        }
                        # Get payer contracts
                        for contract in item.findall('.//Contract'):
                            record['payer_name'] = contract.get('Payer', '')
                            record['negotiated_rate'] = contract.get('Charge', '')
                            records.append(record.copy())

                        if not item.findall('.//Contract'):
                            records.append(record)

            if records:
                return pd.DataFrame(records)

        except Exception as e:
            logger.debug(f"XML parse failed for {filepath.name}: {e}")

        return None

    def _parse_json_mrf(self, filepath: Path) -> Optional[pd.DataFrame]:
        """Parse a JSON format MRF file with robust handling."""
        try:
            # Read with BOM handling
            with open(filepath, 'r', encoding='utf-8-sig', errors='ignore') as f:
                content = f.read().strip()

            if not content:
                return None

            # Check if it's actually CSV mislabeled as JSON
            first_char = content.lstrip('\ufeff')[0] if content.lstrip('\ufeff') else ''
            if first_char not in ('{', '[', '"'):
                # Looks like CSV, not JSON
                return self._parse_csv_content(content, filepath.name)

            # Try to parse as JSON
            try:
                data = json.loads(content)
            except json.JSONDecodeError:
                # Maybe NDJSON (newline-delimited JSON)?
                try:
                    records = []
                    for line in content.split('\n'):
                        line = line.strip()
                        if line:
                            records.append(json.loads(line))
                    data = records
                except:
                    # Last resort: try as CSV
                    return self._parse_csv_content(content, filepath.name)

            # Convert JSON to DataFrame
            if isinstance(data, list):
                if len(data) == 0:
                    return None
                df = pd.DataFrame(data)
            elif isinstance(data, dict):
                # CMS format with nested structure
                if 'standard_charge_information' in data:
                    df = pd.DataFrame(data['standard_charge_information'])
                elif 'data' in data:
                    df = pd.DataFrame(data['data'])
                elif 'charges' in data:
                    df = pd.DataFrame(data['charges'])
                else:
                    # Try to flatten nested structure
                    try:
                        df = pd.json_normalize(data, max_level=2)
                    except:
                        return None
            else:
                return None

            return self._normalize_columns(df)

        except Exception as e:
            logger.warning(f"Failed to parse JSON {filepath.name}: {e}")
            return None

    def _parse_xlsx_mrf(self, filepath: Path) -> Optional[pd.DataFrame]:
        """Parse an XLSX (Excel 2007+) format MRF file."""
        try:
            # Try openpyxl for .xlsx files
            df = pd.read_excel(filepath, dtype=str, engine='openpyxl')
            if df is not None and len(df) > 0:
                # Clean up empty rows/columns
                df = df.dropna(how='all').dropna(axis=1, how='all')
                if len(df) > 0:
                    return self._normalize_columns(df)
        except Exception as e:
            logger.debug(f"openpyxl failed for {filepath.name}: {e}")

        # Try calamine as fallback (faster, handles more formats)
        try:
            df = pd.read_excel(filepath, dtype=str, engine='calamine')
            if df is not None and len(df) > 0:
                df = df.dropna(how='all').dropna(axis=1, how='all')
                if len(df) > 0:
                    return self._normalize_columns(df)
        except Exception:
            pass

        return None

    def _parse_xls_mrf(self, filepath: Path) -> Optional[pd.DataFrame]:
        """Parse an XLS (Excel 97-2003, OLE format) MRF file."""
        try:
            # Try xlrd for old .xls files
            df = pd.read_excel(filepath, dtype=str, engine='xlrd')
            if df is not None and len(df) > 0:
                df = df.dropna(how='all').dropna(axis=1, how='all')
                if len(df) > 0:
                    return self._normalize_columns(df)
        except Exception as e:
            logger.debug(f"xlrd failed for {filepath.name}: {e}")

        # Try calamine as fallback
        try:
            df = pd.read_excel(filepath, dtype=str, engine='calamine')
            if df is not None and len(df) > 0:
                df = df.dropna(how='all').dropna(axis=1, how='all')
                if len(df) > 0:
                    return self._normalize_columns(df)
        except Exception:
            pass

        # Try openpyxl as last resort (sometimes works)
        try:
            df = pd.read_excel(filepath, dtype=str, engine='openpyxl')
            if df is not None and len(df) > 0:
                df = df.dropna(how='all').dropna(axis=1, how='all')
                if len(df) > 0:
                    return self._normalize_columns(df)
        except Exception:
            pass

        return None

    def _extract_hospital_id(self, filename: str) -> str:
        """Extract hospital NPI from filename."""
        # Format: {npi}_{hash}.{ext}
        match = re.match(r'^(\d+)_', filename)
        return match.group(1) if match else ""

    def _clean_price(self, value: Any) -> Optional[float]:
        """Convert price value to float."""
        # Handle None and empty cases
        if value is None:
            return None

        # Handle pandas Series (can happen with duplicate columns)
        if isinstance(value, pd.Series):
            value = value.iloc[0] if len(value) > 0 else None

        # Check for NaN
        try:
            if pd.isna(value):
                return None
        except (ValueError, TypeError):
            pass

        if value == '':
            return None

        try:
            # Handle various formats
            if isinstance(value, str):
                value = value.strip()
                # Skip N/A values
                if value.upper() in ('N/A', 'NA', 'NULL', '-', '', '*SEE NARRATIVE'):
                    return None
                # Remove currency symbols, commas, and spaces
                value = re.sub(r'[$,\s]', '', value)
            return float(value)
        except (ValueError, TypeError):
            return None

    def process_single_file(self, filepath: Path, original_filename: str = None) -> Optional[pd.DataFrame]:
        """Process a single MRF file with smart format detection."""
        temp_file = None
        orig_filepath = filepath  # Keep track of original path
        original_filename = original_filename or filepath.name

        try:
            # Detect actual file type (don't trust extension)
            file_type = self._detect_file_type(filepath)

            # Handle ZIP files (some CSVs are actually ZIPs)
            if file_type == 'zip':
                temp_file = self._extract_from_zip(filepath)
                if temp_file is None:
                    logger.debug(f"Could not extract from ZIP: {filepath.name}")
                    return None
                # Detect the extracted file's type
                file_type = self._detect_file_type(temp_file)
                filepath = temp_file

            # Parse based on detected content type
            df = None
            if file_type == 'json':
                df = self._parse_json_mrf(filepath)
            elif file_type == 'csv':
                df = self._parse_csv_mrf(filepath)
            elif file_type == 'xlsx':
                df = self._parse_xlsx_mrf(filepath)
            elif file_type == 'xls':
                df = self._parse_xls_mrf(filepath)
            elif file_type == 'xml':
                df = self._parse_xml_as_csv(filepath)
            else:
                # Fallback: try based on extension, then try all parsers
                ext = filepath.suffix.lower()
                if ext in ['.xlsx']:
                    df = self._parse_xlsx_mrf(filepath)
                elif ext in ['.xls']:
                    df = self._parse_xls_mrf(filepath)
                elif ext == '.json':
                    df = self._parse_json_mrf(filepath)
                else:
                    df = self._parse_csv_mrf(filepath)

            if df is None or df.empty:
                return None

            # Add hospital ID from original filename (not extracted temp name)
            hospital_id = self._extract_hospital_id(original_filename)
            df['hospital_npi'] = hospital_id
            df['source_file'] = original_filename

            # Clean price columns
            for col in ['gross_charge', 'cash_price', 'min_price', 'max_price', 'negotiated_rate']:
                if col in df.columns:
                    df[col] = df[col].apply(self._clean_price)

            return df

        except Exception as e:
            logger.debug(f"Error processing {original_filename}: {e}")
            return None

        finally:
            # Clean up temp file if we created one
            if temp_file is not None:
                try:
                    temp_file.unlink()
                    temp_file.parent.rmdir()
                except:
                    pass

    def process_all(self, limit: Optional[int] = None) -> pd.DataFrame:
        """Process all MRF files incrementally to avoid memory issues."""
        all_files = list(self.raw_dir.glob('*.*'))
        all_files = [f for f in all_files if f.suffix.lower() in ['.csv', '.json', '.xlsx', '.xls']]

        if limit:
            all_files = all_files[:limit]

        logger.info(f"Processing {len(all_files)} MRF files...")

        # Key columns to keep (reduce memory usage)
        key_columns = ['description', 'procedure_code', 'code_type', 'revenue_code',
                      'gross_charge', 'cash_price', 'min_price', 'max_price',
                      'payer_name', 'plan_name', 'negotiated_rate', 'setting',
                      'hospital_npi', 'source_file']

        output_path = self.processed_dir / "all_prices_normalized.parquet"
        temp_files = []
        success_count = 0
        total_records = 0

        for i, filepath in enumerate(all_files):
            if (i + 1) % 10 == 0 or i == 0:
                logger.info(f"Progress: {i + 1}/{len(all_files)} files processed")
                sys.stdout.flush()

            print(f"[{i+1}/{len(all_files)}] {filepath.name}...", end=" ", flush=True)
            df = self.process_single_file(filepath)
            if df is not None and not df.empty:
                print(f"OK ({len(df):,} rows)")
            else:
                print("FAILED")
            if df is not None and not df.empty:
                # Keep only key columns that exist
                available_cols = [c for c in key_columns if c in df.columns]
                df = df[available_cols].copy()

                # Limit rows per file to prevent memory explosion (keep first 50k rows per hospital)
                if len(df) > 50000:
                    df = df.head(50000)

                # Write to temp parquet file
                temp_path = self.processed_dir / f"temp_{i}.parquet"
                df.to_parquet(temp_path, index=False)
                temp_files.append(temp_path)
                success_count += 1
                total_records += len(df)

        logger.info(f"Successfully processed {success_count}/{len(all_files)} files")
        logger.info(f"Total records: {total_records:,}")

        if not temp_files:
            return pd.DataFrame()

        # Combine temp files in batches
        logger.info("Combining processed files...")
        batch_size = 20
        combined_dfs = []

        for batch_start in range(0, len(temp_files), batch_size):
            batch_files = temp_files[batch_start:batch_start + batch_size]
            batch_dfs = [pd.read_parquet(f) for f in batch_files]
            combined_dfs.append(pd.concat(batch_dfs, ignore_index=True))

        # Final combination
        if len(combined_dfs) > 1:
            result = pd.concat(combined_dfs, ignore_index=True)
        else:
            result = combined_dfs[0] if combined_dfs else pd.DataFrame()

        # Clean up temp files
        for temp_path in temp_files:
            try:
                temp_path.unlink()
            except:
                pass

        return result

    def run(self, limit: Optional[int] = None):
        """Run the complete PriceVision processing pipeline."""
        logger.info("=" * 60)
        logger.info("PRICEVISION PROCESSING")
        logger.info("=" * 60)

        # Process all MRF files
        df = self.process_all(limit=limit)

        if df.empty:
            logger.warning("No data processed!")
            return

        logger.info(f"Total records: {len(df):,}")
        logger.info(f"Unique hospitals: {df['hospital_npi'].nunique():,}")

        # Convert all object columns to string to avoid parquet type issues
        for col in df.columns:
            if df[col].dtype == 'object':
                df[col] = df[col].astype(str).replace('nan', '')

        # Save processed data
        output_path = self.processed_dir / "all_prices_normalized.parquet"
        df.to_parquet(output_path, index=False)
        logger.info(f"Saved to {output_path}")

        # Generate summary statistics
        summary = {
            'total_records': len(df),
            'unique_hospitals': df['hospital_npi'].nunique(),
            'columns': list(df.columns),
            'processed_at': datetime.now().isoformat()
        }

        with open(self.processed_dir / "processing_summary.json", 'w') as f:
            json.dump(summary, f, indent=2)

        return df


# =============================================================================
# DRUGWATCH PROCESSING
# =============================================================================

class DrugWatchProcessor:
    """Process drug pricing data from US and international sources."""

    # Exchange rates (USD)
    EXCHANGE_RATES = {
        'AUD': 0.65,  # Australian Dollar
        'CAD': 0.74,  # Canadian Dollar
        'GBP': 1.27,  # British Pound
    }

    def __init__(self):
        self.raw_dir = DATA_RAW / "drugwatch"
        self.processed_dir = DATA_PROCESSED / "drugwatch"

    def process_us_part_d(self) -> pd.DataFrame:
        """Process Medicare Part D spending data."""
        logger.info("Processing US Medicare Part D data...")

        part_d_dir = self.raw_dir / "us" / "part_d"

        # Find the main Part D file
        csv_files = list(part_d_dir.rglob("*.csv"))
        if not csv_files:
            logger.warning("No Part D CSV files found")
            return pd.DataFrame()

        # Use the most recent file (by name pattern)
        main_file = sorted(csv_files, key=lambda x: x.name, reverse=True)[0]
        logger.info(f"Using Part D file: {main_file.name}")

        df = pd.read_csv(main_file, dtype=str, low_memory=False)

        # Select and rename columns
        cols_2023 = {
            'Brnd_Name': 'brand_name',
            'Gnrc_Name': 'generic_name',
            'Mftr_Name': 'manufacturer',
            'Tot_Spndng_2023': 'total_spending_2023',
            'Tot_Dsg_Unts_2023': 'total_units_2023',
            'Tot_Clms_2023': 'total_claims_2023',
            'Tot_Benes_2023': 'total_beneficiaries_2023',
            'Avg_Spnd_Per_Dsg_Unt_Wghtd_2023': 'avg_price_per_unit_2023',
        }

        available_cols = {k: v for k, v in cols_2023.items() if k in df.columns}
        df = df[list(available_cols.keys())].rename(columns=available_cols)

        # Convert numeric columns
        numeric_cols = ['total_spending_2023', 'total_units_2023', 'total_claims_2023',
                       'total_beneficiaries_2023', 'avg_price_per_unit_2023']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        # Filter to Overall manufacturer rows (aggregate)
        if 'manufacturer' in df.columns:
            df = df[df['manufacturer'] == 'Overall'].copy()

        df['country'] = 'US'
        df['source'] = 'Medicare Part D'

        logger.info(f"Processed {len(df)} US drugs")
        return df

    def process_australia_pbs(self) -> pd.DataFrame:
        """Process Australian PBS drug data."""
        logger.info("Processing Australia PBS data...")

        pbs_dir = self.raw_dir / "australia" / "pbs" / "tables_as_csv"
        items_file = pbs_dir / "items.csv"

        if not items_file.exists():
            logger.warning("Australia PBS items.csv not found")
            return pd.DataFrame()

        df = pd.read_csv(items_file, dtype=str, low_memory=False)

        # Select key columns
        cols = {
            'drug_name': 'generic_name',
            'brand_name': 'brand_name',
            'li_form': 'formulation',
            'determined_price': 'price_aud',
            'pack_size': 'pack_size',
            'pbs_code': 'pbs_code',
        }

        available_cols = {k: v for k, v in cols.items() if k in df.columns}
        df = df[list(available_cols.keys())].rename(columns=available_cols)

        # Convert price to USD
        if 'price_aud' in df.columns:
            df['price_aud'] = pd.to_numeric(df['price_aud'], errors='coerce')
            df['price_usd'] = df['price_aud'] * self.EXCHANGE_RATES['AUD']

        # Calculate price per unit
        if 'pack_size' in df.columns and 'price_usd' in df.columns:
            df['pack_size'] = pd.to_numeric(df['pack_size'], errors='coerce')
            df['price_per_unit_usd'] = df['price_usd'] / df['pack_size']

        df['country'] = 'Australia'
        df['source'] = 'PBS'

        logger.info(f"Processed {len(df)} Australian drugs")
        return df

    def process_canada(self) -> pd.DataFrame:
        """Process Canadian drug data."""
        logger.info("Processing Canada drug data...")

        canada_file = self.raw_dir / "canada" / "drug_products.json"

        if not canada_file.exists():
            logger.warning("Canada drug_products.json not found")
            return pd.DataFrame()

        with open(canada_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if isinstance(data, dict) and 'data' in data:
            records = data['data']
        elif isinstance(data, list):
            records = data
        else:
            logger.warning("Unexpected Canada data format")
            return pd.DataFrame()

        df = pd.DataFrame(records)
        df['country'] = 'Canada'
        df['source'] = 'Health Canada'

        logger.info(f"Processed {len(df)} Canadian drug records")
        return df

    def run(self):
        """Run the complete DrugWatch processing pipeline."""
        logger.info("=" * 60)
        logger.info("DRUGWATCH PROCESSING")
        logger.info("=" * 60)

        # Process each country
        us_df = self.process_us_part_d()
        aus_df = self.process_australia_pbs()
        can_df = self.process_canada()

        # Save individual country files
        if not us_df.empty:
            us_df.to_parquet(self.processed_dir / "us_drugs.parquet", index=False)
            us_df.to_csv(self.processed_dir / "us_drugs.csv", index=False)
            logger.info(f"Saved US drugs: {len(us_df)} records")

        if not aus_df.empty:
            aus_df.to_parquet(self.processed_dir / "australia_drugs.parquet", index=False)
            logger.info(f"Saved Australia drugs: {len(aus_df)} records")

        if not can_df.empty:
            can_df.to_parquet(self.processed_dir / "canada_drugs.parquet", index=False)
            logger.info(f"Saved Canada drugs: {len(can_df)} records")

        # Generate summary
        summary = {
            'us_drugs': len(us_df),
            'australia_drugs': len(aus_df),
            'canada_drugs': len(can_df),
            'processed_at': datetime.now().isoformat()
        }

        with open(self.processed_dir / "processing_summary.json", 'w') as f:
            json.dump(summary, f, indent=2)

        return us_df, aus_df, can_df


# =============================================================================
# FOODSCORE PROCESSING
# =============================================================================

class FoodScoreProcessor:
    """Process OpenFoodFacts and additive data for MAHA scoring."""

    def __init__(self):
        self.raw_dir = DATA_RAW / "foodscore"
        self.processed_dir = DATA_PROCESSED / "foodscore"
        self.additive_risks = self._load_additive_risks()

    def _load_additive_risks(self) -> Dict[str, dict]:
        """Load additive risk database."""
        risk_file = self.raw_dir / "additive_risks.csv"
        if not risk_file.exists():
            return {}

        df = pd.read_csv(risk_file)
        risks = {}

        for _, row in df.iterrows():
            name = row['name'].lower()
            risks[name] = {
                'risk_score': row['risk_score'],
                'type': row['type'],
                'fda_status': row['fda_status'],
                'eu_status': row['eu_status'],
                'is_artificial': row['is_artificial'],
            }

            # Also index by aliases
            if pd.notna(row.get('aliases')):
                for alias in str(row['aliases']).split('|'):
                    risks[alias.lower().strip()] = risks[name]

        return risks

    def _parse_ingredients(self, ingredients_text: str) -> List[str]:
        """Parse ingredients text into list of individual ingredients."""
        if pd.isna(ingredients_text) or not ingredients_text:
            return []

        # Basic parsing: split on commas, clean up
        ingredients = []
        for item in str(ingredients_text).split(','):
            # Remove parenthetical content for now
            item = re.sub(r'\([^)]*\)', '', item)
            item = item.strip().lower()
            if item:
                ingredients.append(item)

        return ingredients

    def _identify_additives(self, ingredients: List[str]) -> List[dict]:
        """Identify additives in ingredient list."""
        found_additives = []

        for ingredient in ingredients:
            # Check exact match
            if ingredient in self.additive_risks:
                found_additives.append({
                    'name': ingredient,
                    **self.additive_risks[ingredient]
                })
            else:
                # Check partial match
                for additive_name, additive_info in self.additive_risks.items():
                    if additive_name in ingredient or ingredient in additive_name:
                        found_additives.append({
                            'name': additive_name,
                            **additive_info
                        })
                        break

        return found_additives

    def _calculate_maha_score(self, row: pd.Series, additives: List[dict]) -> Tuple[float, int]:
        """Calculate MAHA score for a product (0-100, higher is healthier).
        Returns (score, additive_count)."""
        score = 100.0
        additive_count = 0

        # Deduct for NOVA level
        nova_group = row.get('nova_group')
        if pd.notna(nova_group):
            try:
                nova = int(float(nova_group))
                deductions = {1: 0, 2: 5, 3: 15, 4: 25}
                score -= deductions.get(nova, 0)
            except (ValueError, TypeError):
                pass

        # Check additives_n from OpenFoodFacts (if available)
        additives_n = row.get('additives_n')
        if pd.notna(additives_n):
            try:
                additive_count = int(float(additives_n))
                # Deduct based on number of additives
                score -= min(additive_count * 2, 20)
            except (ValueError, TypeError):
                pass

        # Also check for high-risk additives from our list
        for additive in additives:
            risk = additive.get('risk_score', 0)
            # Scale risk score to deduction (max 5 points per additive)
            score -= min(risk / 20, 5)
            additive_count += 1

        # Deduct for sugar (if available)
        sugars = row.get('sugars_100g')
        if pd.notna(sugars):
            try:
                sugar_g = float(sugars)
                # More than 15g sugar per 100g is concerning
                if sugar_g > 15:
                    score -= min((sugar_g - 15) * 0.5, 10)
            except (ValueError, TypeError):
                pass

        # Deduct for sodium (if available)
        sodium = row.get('sodium_100g')
        if pd.notna(sodium):
            try:
                sodium_mg = float(sodium) * 1000  # Convert to mg
                # More than 500mg per 100g is concerning
                if sodium_mg > 500:
                    score -= min((sodium_mg - 500) / 100, 10)
            except (ValueError, TypeError):
                pass

        return max(0, min(100, score)), additive_count

    def process_openfoodfacts(self, sample_size: Optional[int] = None) -> pd.DataFrame:
        """Process OpenFoodFacts data."""
        logger.info("Processing OpenFoodFacts data...")

        off_file = self.raw_dir / "openfoodfacts_us.csv.gz"

        if not off_file.exists():
            logger.warning("OpenFoodFacts file not found")
            return pd.DataFrame()

        # Read in chunks due to large file size
        chunks = []
        chunk_size = 50000

        # Key columns to keep (matching actual OpenFoodFacts column names)
        usecols = [
            'code', 'product_name', 'brands', 'categories_en',
            'ingredients_text', 'allergens', 'nova_group',
            'nutriscore_grade', 'sugars_100g', 'sodium_100g',
            'energy-kcal_100g', 'fat_100g', 'saturated-fat_100g',
            'countries_tags', 'additives_n', 'additives_tags'
        ]

        try:
            reader = pd.read_csv(off_file, compression='gzip',
                                chunksize=chunk_size,
                                dtype=str,
                                sep='\t',  # OpenFoodFacts uses TAB delimiter
                                usecols=lambda x: x in usecols,
                                low_memory=False,
                                on_bad_lines='skip')

            total_rows = 0
            for chunk in reader:
                # Filter to US products
                if 'countries_tags' in chunk.columns:
                    us_mask = chunk['countries_tags'].str.contains('united-states', na=False, case=False)
                    chunk = chunk[us_mask]

                chunks.append(chunk)
                total_rows += len(chunk)

                if sample_size and total_rows >= sample_size:
                    break

                if len(chunks) % 10 == 0:
                    logger.info(f"Processed {total_rows:,} US products...")

        except Exception as e:
            logger.error(f"Error reading OpenFoodFacts: {e}")
            return pd.DataFrame()

        if not chunks:
            return pd.DataFrame()

        df = pd.concat(chunks, ignore_index=True)

        if sample_size:
            df = df.head(sample_size)

        logger.info(f"Loaded {len(df):,} US products")

        # Process each product
        logger.info("Calculating MAHA scores...")

        maha_scores = []
        additive_counts = []

        for idx, row in df.iterrows():
            if idx % 10000 == 0:
                logger.info(f"Scoring product {idx:,}/{len(df):,}")

            ingredients = self._parse_ingredients(row.get('ingredients_text', ''))
            additives = self._identify_additives(ingredients)
            maha_score, additive_count = self._calculate_maha_score(row, additives)

            maha_scores.append(maha_score)
            additive_counts.append(additive_count)

        df['maha_score'] = maha_scores
        df['flagged_additive_count'] = additive_counts

        logger.info(f"Average MAHA score: {df['maha_score'].mean():.1f}")

        return df

    def run(self, sample_size: Optional[int] = 50000):
        """Run the complete FoodScore processing pipeline."""
        logger.info("=" * 60)
        logger.info("FOODSCORE PROCESSING")
        logger.info("=" * 60)

        # Process additive database
        logger.info(f"Loaded {len(self.additive_risks)} additives with risk scores")

        # Save additive lookup
        additive_df = pd.DataFrame([
            {'name': k, **v} for k, v in self.additive_risks.items()
        ])
        if not additive_df.empty:
            additive_df.to_parquet(self.processed_dir / "additive_lookup.parquet", index=False)

        # Process OpenFoodFacts
        products_df = self.process_openfoodfacts(sample_size=sample_size)

        if not products_df.empty:
            products_df.to_parquet(self.processed_dir / "us_products_scored.parquet", index=False)
            logger.info(f"Saved {len(products_df):,} scored products")

            # Generate statistics
            stats = {
                'total_products': len(products_df),
                'avg_maha_score': float(products_df['maha_score'].mean()),
                'products_with_additives': int((products_df['flagged_additive_count'] > 0).sum()),
                'nova_distribution': products_df['nova_group'].value_counts().to_dict() if 'nova_group' in products_df.columns else {},
                'processed_at': datetime.now().isoformat()
            }

            with open(self.processed_dir / "processing_summary.json", 'w') as f:
                json.dump(stats, f, indent=2)

        return products_df


# =============================================================================
# RURALACCESS PROCESSING
# =============================================================================

class RuralAccessProcessor:
    """Process healthcare access and shortage data."""

    def __init__(self):
        self.raw_dir = DATA_RAW / "ruralaccess"
        self.processed_dir = DATA_PROCESSED / "ruralaccess"

    def process_hpsa(self) -> pd.DataFrame:
        """Process HRSA HPSA (Health Professional Shortage Area) data."""
        logger.info("Processing HRSA HPSA data...")

        hpsa_file = self.raw_dir / "hrsa_hpsa.csv"

        if not hpsa_file.exists():
            logger.warning("HPSA file not found")
            return pd.DataFrame()

        df = pd.read_csv(hpsa_file, dtype=str, low_memory=False)

        # Filter to active designations only
        if 'HPSA Status' in df.columns:
            df = df[df['HPSA Status'] == 'Designated'].copy()

        # Select key columns
        key_cols = [
            'HPSA Name', 'HPSA ID', 'Designation Type', 'HPSA Discipline Class',
            'HPSA Score', 'Primary State Abbreviation', 'HPSA Status',
            'Longitude', 'Latitude', 'Common County Name', 'Common State County FIPS Code',
            'HPSA Designation Population', '% of Population Below 100% Poverty',
            'Rural Status'
        ]

        available_cols = [c for c in key_cols if c in df.columns]
        df = df[available_cols].copy()

        # Rename columns
        rename_map = {
            'HPSA Name': 'hpsa_name',
            'HPSA ID': 'hpsa_id',
            'Designation Type': 'designation_type',
            'HPSA Discipline Class': 'discipline',
            'HPSA Score': 'hpsa_score',
            'Primary State Abbreviation': 'state',
            'HPSA Status': 'status',
            'Longitude': 'longitude',
            'Latitude': 'latitude',
            'Common County Name': 'county',
            'Common State County FIPS Code': 'county_fips',
            'HPSA Designation Population': 'population',
            '% of Population Below 100% Poverty': 'poverty_rate',
            'Rural Status': 'rural_status'
        }

        df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

        # Convert numeric columns
        for col in ['hpsa_score', 'longitude', 'latitude', 'population', 'poverty_rate']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        logger.info(f"Processed {len(df)} HPSA designations")
        return df

    def process_county_population(self) -> pd.DataFrame:
        """Process county population data."""
        logger.info("Processing county population data...")

        pop_file = self.raw_dir / "county_population.json"

        if not pop_file.exists():
            logger.warning("County population file not found")
            return pd.DataFrame()

        with open(pop_file, 'r') as f:
            data = json.load(f)

        if isinstance(data, list):
            df = pd.DataFrame(data)
        elif isinstance(data, dict):
            df = pd.DataFrame(list(data.items()), columns=['county_fips', 'population'])
        else:
            return pd.DataFrame()

        logger.info(f"Processed {len(df)} county population records")
        return df

    def aggregate_by_county(self, hpsa_df: pd.DataFrame) -> pd.DataFrame:
        """Aggregate HPSA data by county."""
        if hpsa_df.empty:
            return pd.DataFrame()

        # Count shortages by type per county
        county_agg = hpsa_df.groupby(['county_fips', 'state']).agg({
            'hpsa_id': 'count',
            'hpsa_score': 'mean',
            'population': 'sum'
        }).reset_index()

        county_agg = county_agg.rename(columns={
            'hpsa_id': 'shortage_count',
            'hpsa_score': 'avg_shortage_score',
            'population': 'affected_population'
        })

        return county_agg

    def run(self):
        """Run the complete RuralAccess processing pipeline."""
        logger.info("=" * 60)
        logger.info("RURALACCESS PROCESSING")
        logger.info("=" * 60)

        # Process HPSA data
        hpsa_df = self.process_hpsa()

        if not hpsa_df.empty:
            hpsa_df.to_parquet(self.processed_dir / "hpsa_designations.parquet", index=False)
            logger.info(f"Saved {len(hpsa_df)} HPSA designations")

        # Process county population
        pop_df = self.process_county_population()
        if not pop_df.empty:
            pop_df.to_parquet(self.processed_dir / "county_population.parquet", index=False)

        # Aggregate by county
        county_df = self.aggregate_by_county(hpsa_df)
        if not county_df.empty:
            county_df.to_parquet(self.processed_dir / "county_shortage_summary.parquet", index=False)
            logger.info(f"Saved county-level summary: {len(county_df)} counties")

        # Generate statistics
        stats = {
            'total_hpsa_designations': len(hpsa_df),
            'unique_counties_with_shortages': hpsa_df['county_fips'].nunique() if 'county_fips' in hpsa_df.columns else 0,
            'by_discipline': hpsa_df['discipline'].value_counts().to_dict() if 'discipline' in hpsa_df.columns else {},
            'by_state': hpsa_df['state'].value_counts().head(10).to_dict() if 'state' in hpsa_df.columns else {},
            'processed_at': datetime.now().isoformat()
        }

        with open(self.processed_dir / "processing_summary.json", 'w') as f:
            json.dump(stats, f, indent=2)

        return hpsa_df


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description='HealthGuard Data Processing Pipeline')
    parser.add_argument('--all', action='store_true', help='Process all modules')
    parser.add_argument('--pricevision', action='store_true', help='Process PriceVision only')
    parser.add_argument('--drugwatch', action='store_true', help='Process DrugWatch only')
    parser.add_argument('--foodscore', action='store_true', help='Process FoodScore only')
    parser.add_argument('--ruralaccess', action='store_true', help='Process RuralAccess only')
    parser.add_argument('--limit', type=int, help='Limit records for testing')
    parser.add_argument('--sample', type=int, default=50000, help='Sample size for large datasets')

    args = parser.parse_args()

    # Default to all if no specific module selected
    if not any([args.all, args.pricevision, args.drugwatch, args.foodscore, args.ruralaccess]):
        args.all = True

    start_time = datetime.now()
    logger.info(f"Starting data processing at {start_time}")
    logger.info(f"Project root: {PROJECT_ROOT}")

    try:
        if args.all or args.drugwatch:
            processor = DrugWatchProcessor()
            processor.run()

        if args.all or args.foodscore:
            processor = FoodScoreProcessor()
            processor.run(sample_size=args.sample)

        if args.all or args.ruralaccess:
            processor = RuralAccessProcessor()
            processor.run()

        if args.all or args.pricevision:
            processor = PriceVisionProcessor()
            processor.run(limit=args.limit)

    except Exception as e:
        logger.error(f"Processing failed: {e}")
        raise

    end_time = datetime.now()
    duration = end_time - start_time
    logger.info(f"Processing completed in {duration}")


if __name__ == '__main__':
    main()
