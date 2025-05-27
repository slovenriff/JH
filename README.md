
## Prerequisites

*   Python 3.x
*   Ensure all custom scripts (`JyotishaMitra.py`, `DataParser.py`) and the Jhora processing scripts are functional and produce their expected outputs in the `Processed/` directory for the main pipeline, or that `Jhora/` is populated with `*-JHora.txt` for direct `jhora_pipeline.py` execution.

## Running the Full Pipeline

1.  **Prepare Inputs for Initial Scripts:**
    *   If `JyotishaMitra.py` or `DataParser.py` require specific input files, ensure they are correctly placed.
    *   These initial scripts are expected to generate data (including `*-JHora.txt` for each person and various `[Name]_[HHMM]_*.json` files) and place them into subfolders within a directory named `Processed/` (e.g., `Processed/PersonName_HHMM/personname_hhmm_additional.json`, `Processed/PersonName_HHMM/personname-JHora.txt`).

2.  **Navigate to Project Directory:**
    Open your terminal and change to your main project directory:
    ```bash
    cd /path/to/YourProjectFolder
    ```

3.  **Run the Master Script:**
    ```bash
    python3 run_kundaliextraction_mac.py
    ```
    This will execute `JyotishaMitra.py`, `DataParser.py`, prepare files for `jhora_pipeline.py`, run `jhora_pipeline.py` (which includes its own internal organization), and then clean up intermediate folders.

## Running Only the `jhora_pipeline.py`

If you have manually populated the `Jhora/` folder with the necessary `*-JHora.txt` files and potentially placed relevant `[Name]_[HHMM]_*.json` files into `Kundali/[Name]_[HHMM]/` already (or are okay with `jhora_pipeline.py` only organizing what it generates), you can run it directly:

1.  **Navigate to Project Directory.**
2.  **Run:**
    ```bash
    python3 jhora_pipeline.py
    ```

## Running the `universal_dasha_parser.py` (Manual)

This script is for parsing text files containing detailed hierarchical Dasha information (like Chara K.N. Rao, or multi-level Vimsottari not handled by `jhora_pipeline.py`'s sub-scripts).

1.  **Prepare Input:** Place your Dasha `.txt` files into the `DashaInput/` folder (create this folder in your project root if it doesn't exist).
2.  **Navigate to Project Directory.**
3.  **Run:**
    ```bash
    python3 universal_dasha_parser.py
    ```
4.  **Output:** Nested JSON files will be saved in the `Processed/` folder.

## Notes

*   The file organization logic in `jhora_pipeline.py` is designed to be run once after all Jhora processing scripts have completed. Re-running it on already organized folders should ideally not cause issues but might result in "no files moved" messages.
*   The `universal_dasha_parser.py` assumes a specific, albeit flexible, textual structure for Dasha hierarchies. If your input files deviate significantly, the parser's regexes might need adjustments.
*   The `extract_person_name_from_filename` function in `universal_dasha_parser.py` uses a list of known suffixes to clean up person names. This list may need updates if new Dasha filename conventions are introduced.

---