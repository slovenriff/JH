JyotishaMitra Astrological Processing Pipeline

A modular system to process astrological data from JyotishaMitra, JHora, and related tools — designed for data transformation, structured parsing, and Dasha decoding.

================================================================================

QUICK SETUP (RECOMMENDED)

To quickly prepare your environment and avoid manual steps, run:

    python start_here.py

This script will:
- Prompt you to create a virtual environment (venv/)
- Automatically install all dependencies from requirements.txt
- Ensure your project is ready to run the full pipeline

If you’ve already run the setup once, the script will detect this and skip unnecessary steps.

================================================================================

PREREQUISITES

- Python 3.x
- Ensure all custom scripts (JyotishaMitra.py, DataParser.py) and the JHora processing scripts are functional and produce their expected outputs in the Processed/ directory for the main pipeline, or that Jhora/ is populated with *-JHora.txt for direct jhora_pipeline.py execution.

================================================================================

MANUAL SETUP (IF SKIPPING THE SCRIPT)

1. Create a Virtual Environment

    Mac/Linux:
        python3 -m venv venv
        source venv/bin/activate

    Windows:
        python -m venv venv
        venv\Scripts\activate

2. Install Dependencies

    pip install -r requirements.txt

3. (Optional) Install Developer Tools

    pip install -r requirements-dev.txt

================================================================================

RUNNING THE FULL PIPELINE

1. Prepare Inputs for Initial Scripts:
    - If JyotishaMitra.py or DataParser.py require specific input files, ensure they are correctly placed.
    - These initial scripts are expected to generate data (including *-JHora.txt for each person and various [Name]_[HHMM]_*.json files) and place them into subfolders within a directory named Processed/
      Example: Processed/PersonName_HHMM/personname_hhmm_additional.json

2. Navigate to Project Directory:

    cd /path/to/YourProjectFolder

3. Run the Master Script:

    python3 run_kundaliextraction_mac.py

    This will:
    - Execute JyotishaMitra.py, DataParser.py
    - Prepare files for jhora_pipeline.py
    - Run jhora_pipeline.py (includes internal organization)
    - Clean up intermediate folders

================================================================================

RUNNING ONLY THE jhora_pipeline.py

If you have manually populated the Jhora/ folder with the necessary *-JHora.txt files and potentially placed relevant [Name]_[HHMM]_*.json files into Kundali/[Name]_[HHMM]/ already (or are okay with jhora_pipeline.py only organizing what it generates), you can run it directly:

1. Navigate to Project Directory

2. Run:

    python3 jhora_pipeline.py

================================================================================

RUNNING THE universal_dasha_parser.py (MANUAL)

This script is for parsing text files containing detailed hierarchical Dasha information (like Chara K.N. Rao, or multi-level Vimsottari not handled by jhora_pipeline.py's sub-scripts).

1. Prepare Input: 
    Place your Dasha .txt files into the DashaInput/ folder (create this folder in your project root if it doesn't exist).

2. Navigate to Project Directory.

3. Run:

    python3 universal_dasha_parser.py

4. Output: 
    Nested JSON files will be saved in the Processed/ folder.

================================================================================

NOTES

- The file organization logic in jhora_pipeline.py is designed to be run once after all JHora processing scripts have completed. Re-running it on already organized folders should ideally not cause issues but might result in "no files moved" messages.
- The universal_dasha_parser.py assumes a specific, albeit flexible, textual structure for Dasha hierarchies. If your input files deviate significantly, the parser's regexes might need adjustments.
- The extract_person_name_from_filename function in universal_dasha_parser.py uses a list of known suffixes to clean up person names. This list may need updates if new Dasha filename conventions are introduced.

================================================================================

PROJECT STRUCTURE SUGGESTION

your-project/
├── start_here.py
├── JyotishaMitra.py
├── DataParser.py
├── jhora_pipeline.py
├── universal_dasha_parser.py
├── run_kundaliextraction_mac.py
├── requirements.txt
├── requirements-dev.txt
├── README.md
├── Processed/
├── Jhora/
└── DashaInput/

================================================================================

CONTRIBUTING

Contributions are welcome! Open an issue or submit a pull request to improve or extend the pipeline.

================================================================================

MAINTAINER

Made with care for astrological data enthusiasts.
