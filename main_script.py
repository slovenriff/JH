# main_script.py
import datetime
import traceback
import os  # For directory creation later

# Import from our project structure
from configs import settings
from utils.birthdata_handler import BirthData

# We will create core_jhora_interaction.py next and import from it

# --- PyJHora Core Imports ---
try:
    from jhora.horoscope.main import Horoscope
    from jhora.panchanga import drik  # This is where drik.Date is defined
    from jhora import const  # For constants like ayanamsa modes if needed
except ImportError as e:
    print(f"FATAL ERROR: Could not import PyJHora modules: {e}")
    print("Please ensure PyJHora is installed correctly in your environment and ephemeris files are set up.")
    exit()


# --- Hardcoded Birth Data for Abhijeet Singh Chauhan (Task 1.1a) ---
def get_abhijeet_birth_data() -> BirthData:
    return BirthData(
        name="Abhijeet Singh Chauhan",
        date_of_birth=datetime.date(1976, 9, 6),
        time_of_birth=datetime.time(11, 20, 0),
        latitude=28.621111,
        longitude=77.080278,
        timezone_offset=5.5,
        gender="male"
    )


def main():
    print("--- PyJHora Data Extractor ---")

    # Get birth data
    current_birth_data = get_abhijeet_birth_data()
    print(f"Processing for: {current_birth_data.name}")
    print(f"DOB: {current_birth_data.dob_str}, TOB: {current_birth_data.tob_str}")

    # --- Task 0.1: Resolve drik.Date & Instantiate Horoscope Object ---
    h = None  # Initialize h
    try:
        # Correct instantiation of jhora.panchanga.drik.Date
        # It takes 3 arguments: year, month, day
        drik_birth_date_obj = drik.Date(
            year=current_birth_data.date_of_birth.year,
            month=current_birth_data.date_of_birth.month,
            day=current_birth_data.date_of_birth.day
        )
        print(f"Successfully created drik.Date object: {drik_birth_date_obj}")

        # Now instantiate the Horoscope object
        h = Horoscope(
            date_in=drik_birth_date_obj,
            birth_time=current_birth_data.tob_str,  # tob_str property gives "HH:MM:SS"
            latitude=current_birth_data.latitude,
            longitude=current_birth_data.longitude,
            timezone_offset=current_birth_data.timezone_offset,
            ayanamsa_mode=settings.DEFAULT_AYANAMSA_MODE
            # language='en' # Default is 'en', can be specified
        )
        print("Successfully instantiated Horoscope object (h).")
        print(f"  Julian Day: {h.julian_day}")
        print(f"  Place Info: {h.Place}")
        print(f"  Ayanamsa ({h.ayanamsa_mode}): {h.ayanamsa_value}")
        print(f"  Chara Karakas from h: {h.chara_karakas_list}")

    except TypeError as te:
        print(f"FATAL TYPE ERROR during drik.Date or Horoscope instantiation: {te}")
        traceback.print_exc()
        return  # Exit main if this critical step fails
    except Exception as e:
        print(f"FATAL UNEXPECTED ERROR during Horoscope instantiation: {e}")
        traceback.print_exc()
        return  # Exit main

    if not h:
        print("Failed to create Horoscope object. Exiting.")
        return

    # If we reach here, h is created. We can proceed to next tasks.
    # ... (Code for Task 1.1b - D1 Rasi Chart will go here next) ...
    # ... (Code for Task 1.3 - File/Dir Utilities will be called here) ...
    # ... (Code for Task 2.1 - Chara Karakas Extractor will be called here) ...


if __name__ == "__main__":
    # Create empty __init__.py files if they don't exist to make directories importable
    for dir_name in ["configs", "utils", "extractors",
                     "core_jhora_interaction_module"]:  # Added a placeholder for core module
        # A bit of a hack for __init__.py, normally you'd create these files manually
        # For 'extractors' and 'core_jhora_interaction_module' we'll create them properly soon
        if dir_name in ["configs", "utils"]:
            os.makedirs(dir_name, exist_ok=True)
            init_py_path = os.path.join(dir_name, "__init__.py")
            if not os.path.exists(init_py_path):
                with open(init_py_path, "w") as f:
                    pass  # Create empty __init__.py

    main()