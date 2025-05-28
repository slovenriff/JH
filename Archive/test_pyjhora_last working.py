# test_pyjhora.py

# ---- STANDARD LIBRARY IMPORTS ----
import datetime
import json  # For potentially printing the final extracted_data dictionary
import traceback  # For detailed error messages

# ---- THIRD-PARTY IMPORTS (PyJHora and its dependencies) ----
# These will be resolved from your activated virtual environment (or global site-packages)
try:
    from jhora.horoscope.main import Horoscope
    from jhora.panchanga import drik
    from jhora import const
    from jhora.horoscope.chart import charts as jhora_charts
    from jhora.horoscope.dhasa.raasi import chara as jhora_chara_dhasa  # For Chara Dasha
    from jhora import utils
except ImportError as e:
    print(f"FATAL: Could not import core PyJHora modules. Ensure PyJHora is installed correctly.")
    print(f"Error details: {e}")
    print("Please check your Python environment and PyJHora installation.")
    print("Make sure ephemeris files are in jhora/data/ephe/ within your site-packages.")
    exit()

# ---- INITIALIZE DATA STORE ----
extracted_data = {}

# ---- BIRTH DATA CONFIGURATION ----
# Replace with your actual test case
birth_name = "PVR Narasimha Rao"  # Example from JHora/PVR's book
birth_date_str = "1969-07-09"  # YYYY-MM-DD
birth_time_str = "19:52:00"  # HH:MM:SS (24-hour format)
# city_with_country = "Machilipatnam, IN"
# Manual override for precision or if geocoding issues
latitude_manual = 16.1997  # Machilipatnam
longitude_manual = 81.1330  # Machilipatnam
timezone_offset_manual = 5.5  # IST for India

# ayanamsa_mode_to_use = "LAHIRI" # As per PVR's book/JHora software default
ayanamsa_mode_to_use = const._DEFAULT_AYANAMSA_MODE  # Use the package default


# ---- SCRIPT EXECUTION ----
def main():
    print("--- Starting PyJHora Data Extraction Script ---")

    # --- 1. Prepare Birth Date and Time Objects ---
    try:
        year, month, day = map(int, birth_date_str.split('-'))
        # For drik.Date, time components are needed but can be 0 if only date part is primary
        # However, Horoscope class takes separate date_in (drik.Date) and birth_time (str)
        drik_birth_date_for_horo_obj = drik.Date(year, month, day)
        datetime_birth_date_for_dasha = datetime.date(year, month, day)  # For Dasha functions
    except ValueError:
        print(f"FATAL: Could not parse birth_date_str: {birth_date_str}")
        return

    # --- 2. Instantiate Horoscope Object ---
    try:
        print(f"\nInstantiating Horoscope object for: {birth_name}")
        print(f"  Date: {birth_date_str}, Time: {birth_time_str}")
        print(f"  Lat: {latitude_manual}, Lon: {longitude_manual}, TZ: {timezone_offset_manual}")
        print(f"  Ayanamsa: {ayanamsa_mode_to_use}")

        h = Horoscope(
            # place_with_country_code=city_with_country, # Can use this if confident in geocoding
            latitude=latitude_manual,
            longitude=longitude_manual,
            timezone_offset=timezone_offset_manual,
            date_in=drik_birth_date_for_horo_obj,
            birth_time=birth_time_str,
            ayanamsa_mode=ayanamsa_mode_to_use,
            language='en'
        )
        extracted_data['birth_name'] = birth_name
        extracted_data['input_dob_str'] = birth_date_str
        extracted_data['input_tob_str'] = birth_time_str
        extracted_data['place_info'] = h.Place
        extracted_data['julian_day'] = h.julian_day
        extracted_data['ayanamsa_mode_used'] = h.ayanamsa_mode
        extracted_data['ayanamsa_value_calculated'] = h.ayanamsa_value
        extracted_data['calendar_info'] = h.calendar_info  # Basic panchanga
        extracted_data['chara_karakas_from_horoscope_obj'] = h.chara_karakas_list

        print("  Horoscope object created successfully.")
        print(f"  Julian Day: {h.julian_day}")
        print(f"  Ayanamsa Value: {h.ayanamsa_value}")
        print(f"  Chara Karakas: {h.chara_karakas_list}")

    except Exception as e:
        print(f"FATAL: Error creating Horoscope object: {e}")
        traceback.print_exc()
        return

    # --- 3. Get D1 Rasi Chart (Structured Planet Positions) ---
    # This is crucial for many subsequent calculations, especially Dashas
    try:
        print("\nFetching D1 Rasi Chart (structured planet positions)...")
        # Use the direct jhora_charts.rasi_chart for explicit control
        structured_d1_planet_positions = jhora_charts.rasi_chart(
            jd_at_dob=h.julian_day,
            place_as_tuple=h.Place,
            ayanamsa_mode=h.ayanamsa_mode
        )
        extracted_data['d1_rasi_chart_structured'] = structured_d1_planet_positions

        # Also get D1 details from the Horoscope object's helper method
        d1_details_dict, d1_placements_list, d1_asc_house_idx = h.get_horoscope_information_for_chart(chart_index=0)
        extracted_data['d1_rasi_chart_details_from_horo_obj'] = d1_details_dict
        # extracted_data['d1_rasi_chart_placements_list_from_horo_obj'] = d1_placements_list # Often verbose
        extracted_data['d1_asc_house_idx_from_horo_obj'] = d1_asc_house_idx

        print(f"  D1 Rasi Chart (Structured): {structured_d1_planet_positions}")
        print(f"  D1 Ascendant House Index (0=Aries): {d1_asc_house_idx}")

    except Exception as e:
        print(f"ERROR: Could not get D1 Rasi chart: {e}")
        traceback.print_exc()
        # Decide if this is fatal. For Dashas, it often is.
        # return

    # --- 4. Calculate Chara Dasha (K.N. Rao Style - Custom Implementation) ---
    # This uses the internal functions from jhora.horoscope.dhasa.raasi.chara
    # to ensure K.N. Rao's progression and duration rules are applied.
    extracted_data['chara_dasha_kn_rao_custom'] = "Not calculated yet"
    try:
        print("\nCalculating Chara Dasha (K.N. Rao Style - Custom)...")

        # Inputs for Dasha calculation
        # datetime_birth_date_for_dasha (datetime.date)
        # birth_time_str (string 'HH:MM:SS')
        # h.Place (tuple lat, lon, tz)
        # h.ayanamsa_mode (string)

        jd_at_dob_for_dasha_calc = h.julian_day  # Use the one from Horoscope obj

        # D1 planet positions are needed by the _dhasa_progression and _dhasa_duration functions.
        # These functions expect the output format of jhora_charts.divisional_chart.
        # 'structured_d1_planet_positions' should already be in this format.
        planet_positions_for_d1_dasha = structured_d1_planet_positions

        # If for some reason structured_d1_planet_positions was not calculated or is in wrong format,
        # you could recalculate it here:
        # planet_positions_for_d1_dasha = jhora_charts.divisional_chart(
        #     jd_at_dob_for_dasha_calc,
        #     h.Place,
        #     divisional_chart_factor=1, # D1
        #     ayanamsa_mode=h.ayanamsa_mode
        # )

        # Get K.N. Rao Dasha Progression (sequence of Mahadasha Rasis)
        dasha_progression_knrao = jhora_chara_dhasa._dhasa_progression_knrao_method(
            planet_positions_for_d1_dasha
        )

        kn_rao_periods_list = []
        current_jd_for_dasha = jd_at_dob_for_dasha_calc
        one_year_in_days = const.sidereal_year  # PyJHora uses sidereal year for many dashas

        for md_rasi_index in dasha_progression_knrao:
            md_duration_years = jhora_chara_dhasa._dhasa_duration_knrao_method(
                planet_positions_for_d1_dasha, md_rasi_index
            )

            # Antardasha (AD) sequence for K.N. Rao Chara Dasha:
            # Starts from the Mahadasha Rasi and follows the same progression.
            start_index_ad = dasha_progression_knrao.index(md_rasi_index)
            ad_rasi_sequence_for_this_md = [
                dasha_progression_knrao[(start_index_ad + i) % 12] for i in range(12)
            ]

            ad_duration_years_each = md_duration_years / 12.0

            for ad_rasi_index in ad_rasi_sequence_for_this_md:
                greg_date_start_tuple = utils.jd_to_gregorian_tuple(current_jd_for_dasha)
                start_date_str_formatted = (
                    f"{greg_date_start_tuple[0]:04d}-"
                    f"{greg_date_start_tuple[1]:02d}-"
                    f"{greg_date_start_tuple[2]:02d}"
                    # f" {utils.to_dms(greg_date_start_tuple[3], as_string=True)}" # Optional time
                )

                end_jd_for_this_ad = current_jd_for_dasha + (ad_duration_years_each * one_year_in_days)
                greg_date_end_tuple = utils.jd_to_gregorian_tuple(end_jd_for_this_ad)
                end_date_str_formatted = (
                    f"{greg_date_end_tuple[0]:04d}-"
                    f"{greg_date_end_tuple[1]:02d}-"
                    f"{greg_date_end_tuple[2]:02d}"
                    # f" {utils.to_dms(greg_date_end_tuple[3], as_string=True)}" # Optional time
                )

                kn_rao_periods_list.append({
                    "md_rasi_idx": md_rasi_index,
                    "md_rasi_name": const.rasi_names_en[md_rasi_index],
                    "ad_rasi_idx": ad_rasi_index,
                    "ad_rasi_name": const.rasi_names_en[ad_rasi_index],
                    "start_date": start_date_str_formatted,
                    "end_date": end_date_str_formatted,
                    "ad_duration_years": round(ad_duration_years_each, 3)
                })
                current_jd_for_dasha = end_jd_for_this_ad  # Move to start of next AD

        extracted_data['chara_dasha_kn_rao_custom'] = kn_rao_periods_list
        print(f"  Chara Dasha (K.N. Rao Custom) calculated with {len(kn_rao_periods_list)} AD periods.")
        # Print first few periods for verification
        for i, period in enumerate(kn_rao_periods_list):
            if i < 12:  # Print first MD
                print(f"    MD: {period['md_rasi_name']}, AD: {period['ad_rasi_name']}, "
                      f"Start: {period['start_date']}, End: {period['end_date']}")
            else:
                if i == 12: print("    ...")
                break
    except AttributeError as e:
        print(
            f"ERROR calculating Chara Dasha (K.N. Rao Custom): Likely an issue with accessing an internal function from jhora_chara_dhasa. {e}")
        traceback.print_exc()
        extracted_data['chara_dasha_kn_rao_custom'] = f"Error: {e}"
    except Exception as e:
        print(f"ERROR calculating Chara Dasha (K.N. Rao Custom): {e}")
        traceback.print_exc()
        extracted_data['chara_dasha_kn_rao_custom'] = f"Error: {e}"

    # --- X. Add more data extraction sections here ---
    # Example: Vimsottari Dasha
    # try:
    #     print("\nCalculating Vimsottari Dasha...")
    #     from jhora.horoscope.dhasa.graha import vimsottari
    #     # Ensure vimsottari.get_dhasa_antardhasa signature is checked
    #     # It usually needs: dob, tob, place, planet_positions (D1), ayanamsa_mode, moon_nakshatra_pada etc.
    #     # This might require getting moon_nakshatra_pada from h.calendar_info or drik module.
    #     # moon_longitude = # get moon longitude from structured_d1_planet_positions
    #     # moon_nakshatra, moon_pada, _, _ = drik.nakshatra_pada(h.julian_day, h.Place, moon_longitude)

    #     # vimsottari_periods = vimsottari.get_dhasa_antardhasa(
    #     #     dob=datetime_birth_date_for_dasha,
    #     #     tob=birth_time_str,
    #     #     place=h.Place,
    #     #     planet_positions=structured_d1_planet_positions, # D1 positions
    #     #     ayanamsa_mode=h.ayanamsa_mode,
    #     #     birth_star_number=moon_nakshatra -1, # often 0-indexed
    #     #     years_to_calculate=120,
    #     #     include_antardhasa=True,
    #     #     include_pratyantardhasa=False
    #     # )
    #     # extracted_data['vimsottari_dasha'] = "Vimsottari placeholder - needs correct params" # vimsottari_periods
    #     # print("  Vimsottari Dasha calculation placeholder.")
    # except Exception as e:
    #     print(f"ERROR calculating Vimsottari Dasha: {e}")
    #     traceback.print_exc()

    print("\n--- PyJHora Data Extraction Complete ---")

    # --- 5. Optionally print all extracted data ---
    # print("\n\n--- FINAL EXTRACTED DATA (JSON) ---")
    # try:
    #     print(json.dumps(extracted_data, indent=2))
    # except TypeError as e:
    #     print(f"Could not serialize extracted_data to JSON: {e}")
    #     print("Printing keys and simple values instead:")
    #     for key, value in extracted_data.items():
    #         if isinstance(value, (list, dict)) and len(value) > 5:
    #             print(f"{key}: [Object with {len(value)} items/keys, type: {type(value).__name__}]")
    #         elif isinstance(value, (list, dict)):
    #             print(f"{key}: {value}")
    #         else:
    #             print(f"{key}: {value}")


if __name__ == "__main__":
    main()