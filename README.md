# geoindex-data

Index-agnostic space weather and solar data collection pipeline for downloading, validating, and registering observations into PostgreSQL.

## Features

- **Solar Image Data**: Download and manage FITS images from LASCO (SOHO), SDO (AIA/HMI), and SECCHI (STEREO)
- **Space Weather Indices**: Ingest OMNI solar wind data (hourly, 1-min, 5-min resolution) and HPo geomagnetic indices (Hp30/Hp60)
- **GOES Data**: Download and register GOES XRS (X-ray flux), MAG (magnetometer), and proton flux netCDF products from NOAA NCEI/NGDC, covering both legacy (GOES-13/14/15) and GOES-R (16+) satellites with unified per-instrument schemas
- **Aggregation**: Build 30-minute aggregated solar wind tables and extract per-event CSV/Parquet datasets for downstream modeling
- **FITS Validation**: Automated quality checks on solar image metadata and pixel data
- **Database Management**: PostgreSQL-based storage with composite primary keys, upsert support, and orphan cleanup
- **Unified CLI**: Single `swdb` command wrapping all download, register, build, extract, and database operations

## Requirements

- Python 3
- PostgreSQL

### Python Dependencies

Install everything with:

```bash
pip install -r requirements.txt
```

`requirements.txt` pins:

```
pandas
numpy
astropy
drms
sunpy
requests
urllib3
pyyaml
pyarrow
xarray
netCDF4
egghouse[database] @ git+https://github.com/eunsu-park/egghouse.git
```

## Setup

### 1. Environment Variables

Set database connection parameters:

```bash
export DB_HOST=localhost
export DB_USER=your_user
export DB_PASSWORD=your_password
```

### 2. Initialize Databases

```bash
swdb db init            # or: python scripts/create_all_tables.py
```

This creates two PostgreSQL databases:
- `solar_images` - tables: `lasco`, `sdo`, `secchi`
- `space_weather` - tables: `omni_low_resolution`, `omni_high_resolution`, `omni_high_resolution_5min`, `hpo_hp30`, `hpo_hp60`, `goes_xrs`, `goes_mag`, `goes_proton`, `sw_30min`

## Usage

The primary interface is the unified `swdb` command (an executable launcher that
dispatches to `core.main`). Run `swdb --help` or `swdb <command> --help` for the
full flag list. Every operation is also available as a standalone `scripts/*.py`
script if you prefer to invoke them directly.

```
swdb download omni|hpo|sdo|goes ...   # fetch raw data
swdb register sdo|goes ...            # register archived files into the DB
swdb build sw-30min ...               # build the 30-min aggregated table
swdb extract events ...               # extract per-event CSV datasets
swdb db init|status                   # initialize tables / show DB status
```

### Download OMNI Solar Wind Data

```bash
# All resolutions
swdb download omni --all --start 2020 --end 2024

# Specific resolution
swdb download omni --lowres --start 2020 --end 2024
swdb download omni --highres --highres-5min --start 2024 --end 2024
```

> At least one resolution flag (`--lowres`, `--highres`, `--highres-5min`, or `--all`) is required.

### Download HPo Geomagnetic Indices

```bash
# Year-based download (default)
swdb download hpo --all --start 2020 --end 2024
swdb download hpo --hp30 --start 1985 --end 2024

# Last 30 days (incremental update)
swdb download hpo --all --nowcast
```

### Download and Register GOES Data

GOES XRS / MAG / proton products are downloaded as daily netCDF files from NOAA
NCEI/NGDC, then registered into the `goes_xrs`, `goes_mag`, and `goes_proton`
tables (keyed on `satellite`, `datetime`). Use `--instrument all` to process all
three at once, and pass one or more satellite numbers (legacy 13/14/15 and
GOES-R 16+ are both supported).

```bash
# Download XRS for GOES-16/17/18 over a date range
swdb download goes --instrument xrs --satellites 16 17 18 \
    --start-date 2024-01-01 --end-date 2024-01-31 --init-db

# Download all instruments for a single satellite
swdb download goes --instrument all --satellites 16 \
    --start-date 2024-01-01 --end-date 2024-01-31 --parallel 4

# Register archived netCDF files into the database
swdb register goes --instrument all --satellites 16 17 18 --verbose
```

### Download Solar Images

```bash
# SDO (AIA + HMI)
swdb download sdo --telescope aia --start-date 2024-01-01 --end-date 2024-01-31 --init-db
swdb download sdo --telescope hmi --start-date 2024-01-01 --end-date 2024-01-31 --overwrite --parallel 4

# LASCO / SECCHI (script-level; not yet wrapped by swdb)
python scripts/download_lasco.py --start-date 2024-01-01 --end-date 2024-01-31
python scripts/download_secchi.py --start-date 2024-01-01 --end-date 2024-01-31
```

### Register Existing FITS Files

```bash
swdb register sdo /path/to/fits/files --parallel 4
python scripts/register_lasco.py /path/to/fits/files
python scripts/register_secchi.py /path/to/fits/files
```

### Build Aggregated Tables and Extract Events

```bash
# Build the 30-min aggregated solar wind table
swdb build sw-30min --start-year 2020 --end-year 2024

# Extract per-event CSV datasets (T-window around an event)
swdb extract events -s "2024-05-10 00:00:00" -e "2024-05-12 00:00:00" -o ./events/
```

### Inspect Database Status

```bash
swdb db status
```

### Query Data / Download from a URL List

```bash
python scripts/query_sdo.py --help
python scripts/download_from_urls.py --help
```

## Project Structure

```
geoindex-data/
├── swdb                            # Executable launcher for the unified CLI (→ core.main)
├── requirements.txt
├── configs/
│   ├── solar_images_config.yaml    # LASCO, SDO, SECCHI schema and download settings
│   └── space_weather_config.yaml   # OMNI, HPo, GOES, sw_30min schema and download settings
├── core/
│   ├── __init__.py                 # Package exports
│   ├── main.py                     # Unified `swdb` CLI dispatcher
│   ├── cli.py                      # Shared CLI argument utilities
│   ├── database.py                 # DB creation, table management, insert/upsert
│   ├── download.py                 # HTTP download with retry and parallel support
│   ├── aggregate.py                # 30-min solar wind aggregation + event extraction
│   ├── parse.py                    # OMNI/HPo data parsing, FITS datetime parsing
│   ├── query.py                    # DB query functions (best match, time range)
│   ├── result.py                   # Result/status value objects
│   ├── fits_handler.py             # FITS reading, validation, and I/O helpers
│   ├── goes.py                     # GOES XRS/MAG/proton netCDF listing and parsing
│   ├── lasco.py                    # LASCO-specific query, download, metadata
│   ├── sdo.py                      # SDO/JSOC query, FITS validation, TAI-UTC conversion
│   ├── secchi.py                   # SECCHI metadata extraction
│   └── utils.py                    # YAML config loader with env var substitution
├── scripts/
│   ├── create_all_tables.py        # Initialize all databases and tables
│   ├── create_sw_index.py          # Create/refresh space-weather indexes
│   ├── download_omni.py            # Download OMNI solar wind data
│   ├── download_hpo.py             # Download HPo geomagnetic indices (Hp30/Hp60)
│   ├── download_goes.py            # Download GOES XRS/MAG/proton netCDF from NOAA NCEI
│   ├── download_sdo.py             # Download SDO images via JSOC
│   ├── download_lasco.py           # Download LASCO images via VSO
│   ├── download_secchi.py          # Download SECCHI images
│   ├── download_from_urls.py       # Generic URL-based file downloader
│   ├── register_goes.py            # Parse and register GOES netCDF files
│   ├── register_sdo.py             # Validate and register SDO FITS files
│   ├── register_lasco.py           # Validate and register LASCO FITS files
│   ├── register_secchi.py          # Validate and register SECCHI FITS files
│   ├── build_sw_30min.py           # Build the sw_30min aggregated table
│   ├── extract_sw_events.py        # Extract per-event solar wind CSV datasets
│   ├── export_sw_data.py           # Export sw_30min to a single Parquet file
│   ├── export_tables_to_csv.py     # Export database tables to CSV
│   └── query_sdo.py                # Query SDO images from database
└── LICENSE
```

## Data Sources

| Source | Provider | Access Method |
|--------|----------|---------------|
| SDO/AIA, SDO/HMI | JSOC (Stanford) | `drms` client |
| LASCO | VSO / NRL Archive | `sunpy` Fido / HTTP |
| SECCHI | NASA SECCHI Archive | HTTP directory listing |
| OMNI | NASA SPDF | HTTP download |
| HPo (Hp30/Hp60) | GFZ Potsdam | HTTP download |
| GOES XRS / MAG / Proton | NOAA NCEI / NGDC | HTTP directory listing (netCDF) |

## License

MIT License. See [LICENSE](LICENSE).
