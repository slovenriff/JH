# Kundali Data Processing Project

This project provides an automated pipeline for processing astrological data from various sources (Jhora software, JyotishaMitra, DataParser) into a structured and organized format. The primary output is a set of JSON files for each individual, neatly arranged in a per-person directory structure.

## Features

*   **Automated Workflow:** A master script (`run_kundaliextraction_mac.py`) orchestrates the entire process.
*   **Jhora Data Processing:** Converts raw Jhora text output into various structured text and JSON files for different Dasha systems and Chara Karakas via `jhora_pipeline.py`.
*   **Hierarchical Dasha Parsing:** Includes a powerful `universal_dasha_parser.py` script capable of parsing multi-level Dasha systems (MD, AD, PD, SD) from text dumps into nested JSON, suitable for LLM consumption or detailed analysis.
*   **File Organization:**
    *   Consolidates all files related to an individual into a `Kundali/[Name]_[HHMM]/` folder.
    *   Within each person's folder, files are further organized into subdirectories:
        *   `[Name]-Chara.json` and specific `[Name]_[HHMM]_*.json` reports (e.g., `_additional.json`, `_charts.json`) are kept in the root.
        *   `Dasha_JSON/`: Contains JSON files for standard Dasha systems processed by `jhora_pipeline.py`.
        *   `DataSet/`: Contains all input and intermediate `.txt` files from the `jhora_pipeline.py` process.
        *   `Charts/`: Contains other `[Name]_[HHMM]_*.json` files not kept in the root (e.g., `_health.json`, `_wealth.json`).
*   **Intermediate File Cleanup:** Automatically cleans up temporary processing directories.

## Directory Structure

Your project should be set up as follows:
YourProjectFolder/
├── run_kundaliextraction_mac.py # MASTER SCRIPT TO RUN EVERYTHING
├── jhora_pipeline.py # Core Jhora data processing
├── JyotishaMitra.py # Your custom script
├── DataParser.py # Your custom script
├── universal_dasha_parser.py # For manual parsing of complex Dasha TXT
│
├── Scripts/ # Helper scripts for jhora_pipeline.py
│ ├── add_jhora_heading.py
│ ├── split_dasha_sections.py
│ ├── Jhora_extract_chara.py
│ ├── chara_to_json.py
│ ├── mo_vi_asg_to_json.py
│ ├── kalachakra_dasha_to_json.py
│ └── sudasa_narayana_dasha_to_json.py
│
├── Jhora/ # INPUT for jhora_pipeline.py. Initially contains *-JHora.txt.
│ # Should be (mostly) empty after successful run.
│
├── DashaInput/ # INPUT for universal_dasha_parser.py (manual runs).
│ └── example-dasha-file.txt
│
├── Kundali/ # FINAL ORGANIZED OUTPUT
│ └── PersonName_HHMM/
│ ├── PersonName_HHMM_additional.json
│ ├── PersonName_HHMM_charts.json
│ ├── PersonName_HHMM_dasha_filtered.json
│ ├── PersonName_HHMM_dashas.json
│ ├── PersonName-Chara.json
│ ├── Charts/
│ ├── Dasha_JSON/
│ └── DataSet/
│
├── Processing/ # Temporary (created & deleted by run_kundaliextraction_mac.py)
└── Processed/ # Intermediate (created & deleted by run_kundaliextraction_mac.py)
# (Also the output dir for manual universal_dasha_parser.py runs)