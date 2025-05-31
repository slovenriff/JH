ExcellentExcellent idea. Creating a clear technical document will serve as our blueprint, keep us aligned, and ensure we cover idea! A clear technical document will serve as our blueprint and help us both stay precisely all requirements systematically.

Here's a draft of the technical document based on our discussions. We can refine this further if on track. This will detail the agreed-upon architecture, script responsibilities, data flows, and formats.

Let needed.

Technical Design Document: PyJHora Astrological Data Extraction and Processing Pipeline

**Version's draft this technical document now.

Technical Design Document: PyJHora Astrological Data Pipeline:** 1.0
Date: May 27, 2024

**1. Introduction

Version: 1.0
Date: May 27, 2024
Author & Goals

This document outlines the architecture and design for a Python-based pipeline to extract astrological data using the PyJHora library,/Lead:** (Your Name/Project Lead), AI Assistant

1. Introduction and Goals

Purpose: process it, and save it in various structured JSON formats. The primary goals are:

Automate the extraction of multiple To design and implement an automated Python-based pipeline for extracting comprehensive astrological data using the PyJHora library, processing this astrological data points for multiple individuals.

Ensure data accuracy by using reliable geocoding and timezone determination.

Produce comprehensive data, and generating various structured output files (primarily JSON) for individual birth charts.

Key Goals:
1 "master" datasets in a nested JSON format for each Dasha system and other astrological calculations.

Allow for flexible. Process birth data for multiple individuals from a single input text file (Jatak.txt).
2. En generation of various filtered and flattened "presentation" JSON files from these master datasets.

Maintain a modular and robustrich birth data with accurate geocoded coordinates (latitude, longitude) and timezone information.
3. Generate codebase that is easy to understand, test, and extend.

Provide diagnostic information for geocoding and data comprehensive, unfiltered "master" Dasha data in a deeply nested JSON format for each supported Dasha system (initially V processing steps.

2. System Architecture

The system will be composed of (at least) two main Pythonimsottari and K.N. Rao Chara Dasha).
4. Extract other astrological data points from scripts orchestrated by a master script:

Jatak_Input_Parser.py (or integrated into Master PyJHora: D1/D9 chart positions, Chara Karakas, Ashtakavarga, Planetary Strengths ( Script):

Responsible for reading and parsing the Jatak.txt file.

Handles the geocodingShadbala), Yogas, and Tajika (annual chart) information, saving each as a distinct, well-structured JSON file. of place names to latitude/longitude and the lookup of timezone offsets.

Creates a list of enriched BirthData objects.

Provide diagnostic information regarding the geocoding and timezone lookup process.

Separate

Pyjhora_Dasha_Extractor.py (Core Data Extractor):

Takes the data extraction process from the final formatting/filtering process using a modular, two-script (or multi-script) architecture a single BirthData object as input (or iterates through a list if called directly for batch processing from Jatak_Input_Parser.py).

Interacts with the PyJHora library to calculate various astrological data.

Outputs.

Ensure outputs are organized logically in a per-person directory structure.

Design "master" nested JSON files for each Dasha system and other detailed astrological data sets.

Outputs diagnostic for maintainability, testability, and future extensibility to include more Dasha systems or astrological data points.

**2. System files (e.g., Geo/Timezone info).

Dasha_Formatter.py (Presentation Architecture Overview

The system will consist of at least two primary Python scripts, orchestrated by a master script:

` Layer - Future Script):

Takes the "master" nested JSON files (produced by Pyjhora_DDasha_Pipeline_Manager.py (Master Orchestrator - Future Implementation):**

Theasha_Extractor.py`) as input.

Applies specific filtering and formatting rules.

Outputs main entry point for the user.

Reads Jatak.txt to obtain a list of individuals various flat/filtered JSON files as required for end-user consumption or specific analyses.

**`Dasha_Pipeline_Manager.

For each individual, sequentially invokes Pyjhora_Dasha_Extractor.py and.py` (Master Orchestrator - Future Script):**

Main entry point for the user.

Calls J thenData_Formatter.py`.

Handles high-level logging and pipeline flow control.

**Pyjhora_atak_Input_Parser.py (or its logic).

For each processed BirthData object, calls Pyjhora_Dasha_Extractor.py (or its main processing function).

AfterDasha_Extractor.py` (Core Data Extraction Engine):**

Input: BirthData object for master files are generated, calls Dasha_Formatter.py (or its logic) to create final outputs.

Manages file a single individual (passed by the orchestrator after parsing Jatak.txt and performing geo-enrichment, organization (e.g., moving master files to a DataSet/ subfolder).

3. Detailed Design or handles this internally).
* Processing:
* Instantiates PyJHora Horoscope object.: Pyjhora_Dasha_Extractor.py

This script is the primary focus for current development
* Calls specific PyJHora functions to calculate various astrological data points.
* For Dasha systems.

3.1. Configuration:

DEFAULT_AYANAMSA_MODE: e.g., "LAHIRI"
(Vimsottari, K.N. Rao Chara): Generates an intermediate hierarchical text representation and then parses* OUTPUT_BASE_PATH: Root for all output (e.g., "./Kundali")

JATAK_FILE_PATH: Path to input birth data (e.g., "./Jatak.txt")

GEOCODER_USER_AGENT this text into a comprehensive, deeply nested "master" JSON structure spanning a long duration (e.g., 80-: For Nominatim API calls.

Constants for Dasha calculation spans (e.g., 80 years120 years) without date-based filtering of sub-periods.
* For other data types (Chara Karakas, Asht for K.N. Rao, 120+ for Vimsottari).

**3.2. Dataakavarga, etc.): Directly processes PyJHora output into structured JSON.
* Output (for each Structures:

BirthData Dataclass:

name: str

date_of_birth: datetime.date

time_of_birth: datetime. person, placed inKundali/[PersonName_HHMM]/`):**

[PersonName]_time

latitude: float

longitude: float

timezone_offset: float (hours from UTC)

city_name: Optional[str]GeoTimeZone_Info.txt` (diagnostic for geocoding).

Within a DataSet/ sub (determined/parsed city)

country_name: Optional[str] (determined/parsed country)

folder: *[PersonName]_D1_Chart_Positions.json*[PersonName]_D9_Chart_Positions.json*[PersonName]_CharaKarakas.raw_place_string: Optional[str](original string fromJatak.txt`)

ianajson
* [PersonName]_Ashtakavarga.json
* [PersonName]_PlanetaryStrengths.json (containing Shadbala, etc.)
* [PersonName]_Yogas__timezone_name: Optional[str] (e.g., "Asia/Kolkata")

geocoding_success: bool

gender: str (default "neutral")

3.3. CoreDetected.json*[PersonName]Tajika_Varshaphal[YYYY].json(or similar for Tajika, scope TBD) *[PersonName]_Predictive_Indicators.jsonModules/Functions (withinPyjhora_Dasha_Extractor.py`):

Input Processing (scope TBD)
* [DashaSystemName]_PyJHora_RawText.txt (for each Module (integrated or called):

parse_jatak_txt(file_path: Path) -> List[ Dasha system, e.g.,VimsottariDasa_PyJHora_RawText.txtDict[str, str]]`:

Reads Jatak.txt, splits records by blank lines.

Parses each line into key-value pairs. Returns list of raw dicts.

geocode)
* [DashaSystemName]-Master_Nested.json (for each Dasha system, e_and_enrich_place(place_str: str, dob: datetime.date, tob: datetime.time) -> Tuple[Optional[float], Optional[float], Optional[float], Optional[str], Optional[str], Optional[str]].g., VimsottariDasa-Master_Nested.json, including birth_parameters_used)

Data_Formatter.py (Filtering and Final Output Generation - Future Implementation):

**`:

Uses geopy.Nominatim for lat/lon from place string.

UsesInput:** Path to a person's DataSet/ directory (containing the master nested JSONs and other raw data JSON timezonefinder.TimezoneFinder for IANA timezone name from lat/lon.

Uses pytz tos).

Processing: Reads the master/raw data files and applies specific filtering rules and formatting logic get UTC offset for the birth datetime using the IANA timezone.

Includes error handling and rate limiting (`.

**Output (for each person, placed in Kundali/[PersonName_HHMM]/,time.sleep(1.1)` for Nominatim).

Returns: (lat, lon, tz_offset_float, city, country, iana_tz_name).

process_raw_entries_to_birthdata(raw_entries: List[Dict[str, str]]) -> List[BirthData sibling toDataSet/`):**

Specific flat/filtered Dasha JSON files as previously defined (e.g., ]:

Converts list of raw dicts to list of BirthData objects.

Calls*_Vimsottari_MD_AD_80yrs.json,*KNRaoChara geocode_and_enrich_place.

Handles errors and skipping of records if crucial geo/tzMD_AD_PD_SD_filtered.json`, etc.).

Potentially other formatted/summarized outputs data is missing.

Utility Functions:

`_format_datetime_from_jd derived from Ashtakavarga, Yogas, etc.

3. Detailed Design: Pyjhora_Dasha_(jd_val: float) -> str: Converts JD to "YYYY-MM-DD HH:MM:SS". HandlesExtractor.py`

Input File (Jatak.txt):

Located fractional hour output from PyJHora's jd_to_gregorian.

_parse_datetime_universal(date_str_with_time: str) -> str: Converts "YYYY-MM-DD HH:MM at JATAK_FILE_PATH (configurable).

Format: Records separated by blank lines. Each:SS" to ISO8601.

_expand_name_universal(name_short: record uses "Key: Value" pairs for "Name", "Date" (Month Day, Year), "Time" (HH:MM:SS), str, dasha_system_name: str) -> str: Uses ZODIAC_MAP_UNIVERSAL to expand short Rasi/Planet names.

ZODIAC_MAP_UNIVERSAL and `PLAN "Place" (City, Country or City, Region, Country).

Parsed by parse_jatak_txt().

BirthData Dataclass:

Fields: name, date_of_birth,ET_FULL/SHORT_NAMES_LIST population logic.

Dasha Text Generation Module:

time_of_birth, latitude, longitude, timezone_offset, city_name, country_name, gender, raw_place_string, geocoding_success, iana_timezone_name.

Geocoding and Timezone Enrichment (geocode_and_enrich_placegenerate_vimsottari_text_for_universal_parser(h_obj: Horoscope) -> str:
* Calculates full Vimsottari (MD, AD, PD, SD) for 120+ years using PyJHora.
* Formats into a hierarchical text string.
* Output uses short planet names (()`):

Uses geopy.geocoders.Nominatim for coordinate lookup. Requirese.g., "Su", "Mo") for period lines.

generate_knrao_chara_text_for_universal_parser(h_obj: Horoscope, d1_chart_positions: list, total_years_to_calculate: int) -> str:

Calculates full K.N. Rao Ch GEOCODER_USER_AGENT and implements a delay (time.sleep(1.1)) to respect APIara Dasha (MD, AD, PD, SD) for total_years_to_calculate using PyJHora.

Formats into a hierarchical text string.

Output uses short Rasi names (e. limits.

Uses timezonefinder.TimezoneFinder for IANA timezone name from coordinates.

Uses pytz to get the historically accurate UTC offset for the birth datetime in the determined IANA timezone.

Handlesg., "Ar", "Ta") for period lines.

Nested JSON Parser Module:

`parse_dasha_text_content(text_content: str, person_name: str, dasha_system_ errors gracefully (timeouts, service unavailable, lookup failures).

Provides a fallback to default Indian timezone (+5.5,source_id: str, birth_params: Optional[Dict] = None) -> dict`:

Takes hierarchical text and birth_params.

Parses it into the standard nested dictionary structure:

"Asia/Kolkata (Assumed)") if geocoding determines country as India but TZ lookup fails. Records{
  "person_name": "...",
  "birth_parameters_used": { /* from birth_params */ },
  "dasha_system_name": "...",
  "source_file": "...",
  " without sufficient geo/TZ info will be skipped.


Output Folder Structure:

Base: `OUTPUTdasas": [ /* list of MD objects */ ]
}
```

MD/AD/PD/_BASE_PATH(e.g.,./Kundali/`)

Per Person: [PersonName_HHSD objects will havelevel,period_type,name(expanded),start_datetime(ISO),MM]/ (e.g., Priyanka_Verma_1600/)

[end_datetime(ISO),sub_periods`.

Master Nested JSON Generation and Saving Functions:

PersonName]_GeoTimeZone_Info.txt

DataSet/

All master nested Dgenerate_and_save_vimsottari_master_nested(h: Horoscope, birth_data: Birthasha JSONs.

All other PyJHora raw data extractions (Chara Karakas, DData, birth_params_for_json: Dict, output_folder: Path)`:

Calls `generate_vimsottari1, D9, Ashtakavarga, etc.).

Intermediate Dasha text dumps.

*_text_for_universal_parser. * Saves the raw text to.../DataSet/VimsottariD Core Astrological Calculations & Data Structure for Outputs:
* Horoscope Object: Instantiate Horasa_PyJHora_RawText.txt.
* Calls parse_dasha_text_content.oscopefromBirthData. * **birth_parameters_usedBlock:** All master nested Dasha JSONs * Saves the nested dict to.../DataSet/VimsottariDasa-Master_Nested.json. will include a top-level dictionary keybirth_parameters_usedcontaining a serialized version of theBirthDataobject (*generate_and_save_knrao_chara_master_nested(h: Horoscope, d1_positions: list, birth_data: BirthData, birth_params_for_json: Dict, output_folder: Path): * Callsgenerate_knrao_chara_text_for_universal_parser. * Saves the raw text to.../DataSet/KNRaoCharaDasa_PyJHora_RawTextor its key fields like DOB, TOB, Lat, Lon, TZ Offset, Ayanamsa Mode, Raw Place String,.txt. * Callsparse_dasha_text_content. * Saves the nested dict to.../DataSet/KNRaoCharaDasa-Master_Nested.json`.

IANA TZ) to ensure traceability of inputs.

**Dasha Text Generation (`generate_[DashaSystem]_ Other Astrological Data Extraction and Saving Functions (Stubs for now, to be implemented):

text_for_universal_parser()):**

These functions take h_obj (and extract_and_save_d1_chart(h_obj, birth_data, dataset_folder_path)

extractd1_positions if needed).

Calculate all levels (MD, AD, PD, SD) for the D_and_save_d9_chart(h_obj, birth_data, dataset_folder_path)`

extract_and_save_chara_karakas(h_obj, d1_positionsasha system for its full natural cycle or a defined long span (e.g., Vimsottari 120+ years, K.N, birth_data, dataset_folder_path)

`extract_and_save_ashtakavarga(h_. Rao Chara 80 years).

Output a hierarchical text string.

Use shortobj, birth_data, dataset_folder_path)`

extract_and_save_planetary_strengths(h_obj, birth_data, dataset_folder_path)

`extract_and_save_yogas(h_obj, birth planet/Rasi names (Su, Mo, Ar, Ta) for detailed period lines.

Format_data, dataset_folder_path)`

extract_and_save_tajika_details(h_obj, birth_data, dataset_folder_path, for_year=None)

dates/times using_format_datetime_from_jd()`.

Include "Maha Dasas:" summaryextract_and_save_predictive_indicators(h_obj, birth_data, dataset_folder_path)`

Each of these will call relevant PyJHora functions and save the output to a distinctly named JSON file in the block (with full planet/Rasi names).

Include context lines and section headers for sub-periods.

** DataSet/ subfolder. They should include birth_parameters_used where appropriate.

main() Function:
Nested JSON Parsing (parse_dasha_text_content()):**
* Takes the generated text, person * Parses Jatak.txt to get all_birth_data.

Loops through all_birth_data.

For each current_birth_data:

Creates name, source ID, andbirth_params_for_json`.

Produces the standard nested dictionary structure:

{
  "person_name": "...",
  "birth_parameters_used": {Kundali/PersonName_HHMM/` folder.
IGNORE_WHEN_COPYING_START
content_copy
download
Use code with caution.
Json
IGNORE_WHEN_COPYING_END

Creates Kundali/PersonName_HHMM/DataSet/ subfolder.

Saves GeoTimeZone_Info.txt in Kundali/PersonName_HH ... }, "dasha_system_name": "...", "source_file": "...", "dasas": [ { "level": 1, "period_type": "Mahadasha", "name": "...", "start_datetime": "...", "end_datetime": "...", "sub_periods": [ MM/.

Instantiates Horoscope.

Calls the relevant extract_and_save_... or generate_and_save_... functions, passing h_obj, birth_data, birth_params_for_json dictionary, and dataset_folder_path.

Error { "level": 2, "period_type": "Antardasha", ..., "sub_periods": [
{ "level": 3, "period_type": "Pratyantardasha", ..., "sub_periods": [
{ "level": 4, "period_type": "Sookshma-antardasha", ..., "sub_periods": [] }
]}
]}
]}
]
}
``` handling for Horoscope instantiation and individual extractions.

3.4. Output File Structure (for Pyjhora_Dasha_Extractor.py):
Kundali/ └── PersonName_HHMM/ # Folder * **Specific Extraction Functions (New Modular Approach):** * `extract_and_save_d1_ named with person's name and TOB (HourMinute) ├── PersonName_GeoTimeZone_Info.txt chart()`: Saves `[Planet, [RasiIndex, LongitudeInRasi]]` list. * `extract └── DataSet/ # Subfolder for all master/raw data ├── PersonName_D1_Chart_Positions.json ├── PersonName_D9_Chart_Positions.json ├── PersonName_CharaKarakas_and_save_d9_chart()`: Similar format to D1. * `extract_and_save_chara_.json ├── VimsottariDasa_PyJHora_RawText.txt ├── VimsottariDasa-Master_Nested.json ├── KNRaoCharaDasa_PyJHora_RawText.txt karakas()`: Saves a list or dictionary mapping Karaka name (e.g., "Atma Karaka") to planet ├── KNRaoCharaDasa-Master_Nested.json ├── PersonName_Ashtakavarga.json ├── PersonName_PlanetaryStrengths.json ├── PersonName_Yogas_Detected.json ├── PersonName index/name. Input `d1_planet_positions`. Output `{karaka_name: planet_name,_Tajika_Details.json └── PersonName_Predictive_Indicators.json
( ...}. *extract_and_save_ashtakavarga(): Saves BAV (Filenames for master nested Dashas will likely be prefixed withPersonName_as well for consistency withinDataSet/`)

48x12 matrix or dict), SAV (1x12 list or dict), PAV (8x8x12 or. Future: dasha_formatter.py
* Will read JSON files from the DataSet/ directory.
dict). Output e.g. {"bav": {...}, "sav": {...}}.
* extract* Will contain functions to transform/filter data from master nested JSONs into the specific flat JSON formats previously generated by_and_save_planetary_strengths(): Saves Shadbala components and total scores. Output e.g. {"shad the oldPyjhora_Dasha_Extractor - Hardcoded.pyscript (e.g., K.N. Rao MD/AD 80yrs, Vimsottari MD/AD/PD filtered, etc.). * Will savebala": {planet: {sthana:x, dig:y, ... total:z}}, "ishta_ph its output to the parent directory (Kundali/PersonName_HHMM/`).

This technical document provides a clear roadmapala": ...}. *extract_and_save_yogas(): Saves a list of detected yoga. The immediate focus is to implement the **K.N. Rao Chara Dasha master nested JSON generation** withinPyjhora_ names and possibly forming planets. Output [{"yoga_name": "...", "planets_involved": [...]}, ...].Dasha_Extractor.pyby creating the necessary text generator and ensuring the main loop calls it correctly. We also *extract_and_save_tajika_details(): (Scope for current year's Varshaphal initially) Save Var need to ensure all master Dasha JSONs include thebirth_parameters_used`.

Does this align with yourshaphal D1 positions, Muntha, Year Lord, Sahams. Structure TBD.
* `extract vision and provide enough clarity to proceed with coding the K.N. Rao nested output next?