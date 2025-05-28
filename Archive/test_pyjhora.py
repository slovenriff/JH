# test_pyjhora.py

import datetime
import traceback
import os
import json
from dataclasses import dataclass
# Keep this if jhora_vimsottari_std is the correct module for the vimsottari_mahadasa function.
# If not, and if Horoscope object (h) has its own vimsottari methods, we might not need this specific import.
from jhora.horoscope.dhasa.graha import vimsottari as jhora_vimsottari_std

# --- PyJHora Core Imports ---
try:
    from jhora.horoscope.main import Horoscope
    from jhora.panchanga import drik
    from jhora import const
    from jhora.horoscope.chart import charts as jhora_charts
    from jhora import utils as jhora_utils
except ImportError as e:
    print(f"FATAL ERROR: Could not import PyJHora modules: {e}")
    exit()

# --- Configuration ---
DEFAULT_AYANAMSA_MODE = "LAHIRI"
OUTPUT_BASE_PATH = Path("./Kundali")  # Using Path object for consistency


# --- BirthData Dataclass ---
@dataclass
class BirthData:
    name: str
    date_of_birth: datetime.date
    time_of_birth: datetime.time
    latitude: float
    longitude: float
    timezone_offset: float
    gender: str = "neutral"

    @property
    def tob_str(self) -> str:
        return self.time_of_birth.strftime("%H:%M:%S")

    @property
    def dob_str(self) -> str:
        return self.date_of_birth.strftime("%Y-%m-%d")


# --- Hardcoded Birth Data Function ---
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


# --- VIMSHOTTARI DASHA EXTRACTION FUNCTION ---
def extract_standard_vimsottari_dasha(
        h_obj: Horoscope,
        # d1_chart_positions: list, # Not directly used by jhora_vimsottari_std.vimsottari_mahadasa
        birth_datetime_date: datetime.date  # Added type hint
):
    all_periods_md_ad_pd = []
    all_periods_filtered = []

    # Get Julian Day at birth and Place object from the Horoscope object
    jd_at_birth = h_obj.julian_day
    place_obj = h_obj.Place  # Corrected: h_obj.Place is a tuple, but Panchanga functions expect a drik.Place object

    # Create a drik.Place object for jhora library compatibility if needed.
    # Many jhora functions construct this internally if given lat/long/tz.
    # Let's assume jhora_vimsottari_std.vimsottari_mahadasa can handle the tuple h_obj.Place provides
    # or that Place object in Horoscope is already suitable.
    # If not, it might be: place_drik = drik.Place(str(place_obj[0]),str(place_obj[1]), str(place_obj[2]), place_obj[3], place_obj[4])

    total_years_to_calculate = 80

    today_date_filter = datetime.date.today()
    # Ensure correct timedelta usage if it was datetime.timedelta before
    filter_start_date_obj_filter = today_date_filter - timedelta(days=365)
    filter_end_date_obj_filter = today_date_filter + timedelta(days=(3 * 365))

    print(
        f"Vimshottari: Calculating for {total_years_to_calculate} years (MD/AD/PD) from {birth_datetime_date.strftime('%Y-%m-%d')}")
    print(
        f"Filter window for Vimshottari: {filter_start_date_obj_filter.strftime('%Y-%m-%d')} to {filter_end_date_obj_filter.strftime('%Y-%m-%d')}")

    try:
        # The vimsottari_mahadasa function in jhora usually requires:
        # 1. Julian day of birth.
        # 2. Place (often a drik.Place object, but sometimes tuple might work for simpler calcs).
        # 3. dhasa_starting_planet (from moon nakshatra lord usually).
        # 4. star_position_from_moon (moon's longitude within its nakshatra).
        # The h_obj.moon_nakshatra_position gives (nakshatra_number, star_longitude_within_nakshatra, star_pada)
        # The h_obj.moon_nakshatra_lord_from_nakshatra(nakshatra_number) gives starting planet

        moon_nak_num, moon_star_pos, _ = h_obj.moon_nakshatra_position  # _ is for pada, not used by vimsottari start
        dhasa_start_planet_idx = const.NAKSHATRA_LORDS[moon_nak_num - 1]  # Nakshatras 1-27, list 0-26

        print(
            f"  Debug Vim: Moon Nakshatra Num: {moon_nak_num}, Dhasa Start Planet Idx: {dhasa_start_planet_idx}, Moon Star Pos: {moon_star_pos}")

        mahadasas = jhora_vimsottari_std.vimsottari_mahadasa(
            jd_at_birth,
            place_obj,  # Assuming this is compatible or that the func handles it
            dhasa_starting_planet=dhasa_start_planet_idx,  # Correct starting planet
            star_position_from_moon=moon_star_pos  # Moon's position within its nakshatra
        )
    except Exception as e:
        print(f"Error in vimsottari_mahadasa call: {e}")
        traceback.print_exc()
        return None, None

    if not mahadasas:
        print("ERROR: vimsottari_mahadasa returned no data.")
        return None, None

    elapsed_total_dasha_span_years = 0.0

    for md_lord_idx, md_start_jd in mahadasas.items():
        if elapsed_total_dasha_span_years >= total_years_to_calculate:
            break

        md_full_duration_years = jhora_vimsottari_std.vimsottari_dict[md_lord_idx]
        # Note: jhora._vimsottari_bhukti might take planet index and start_jd of MD.
        # Let's assume the internal function uses md_lord_idx directly
        antardashas = jhora_vimsottari_std._vimsottari_bhukti(md_lord_idx, md_start_jd)

        for ad_lord_idx, ad_start_jd in antardashas.items():
            if ad_start_jd > jd_at_birth + (total_years_to_calculate * const.sidereal_year):
                break

            ad_full_duration_years = (jhora_vimsottari_std.vimsottari_dict[
                                          ad_lord_idx] * md_full_duration_years) / const.human_life_span_for_vimsottari_dhasa

            # Note: jhora._vimsottari_antara might take MD lord, AD lord, and AD start_jd.
            pratyantardashas = jhora_vimsottari_std._vimsottari_antara(md_lord_idx, ad_lord_idx, ad_start_jd)

            for pd_lord_idx, pd_start_jd in pratyantardashas.items():
                if pd_start_jd > jd_at_birth + (total_years_to_calculate * const.sidereal_year):
                    break

                pd_full_duration_years = (jhora_vimsottari_std.vimsottari_dict[
                                              pd_lord_idx] * ad_full_duration_years) / const.human_life_span_for_vimsottari_dhasa
                pd_end_jd = pd_start_jd + (pd_full_duration_years * const.sidereal_year)

                if pd_start_jd < jd_at_birth + (total_years_to_calculate * const.sidereal_year):
                    pd_start_tuple = jhora_utils.jd_to_gregorian(pd_start_jd)
                    pd_end_tuple = jhora_utils.jd_to_gregorian(pd_end_jd)
                    pd_start_date_str = f"{pd_start_tuple[0]:04d}-{pd_start_tuple[1]:02d}-{pd_start_tuple[2]:02d}"
                    pd_end_date_str = f"{pd_end_tuple[0]:04d}-{pd_end_tuple[1]:02d}-{pd_end_tuple[2]:02d}"

                    period_data = {
                        "md_lord": const.PLANET_NAMES_EN[md_lord_idx],
                        "ad_lord": const.PLANET_NAMES_EN[ad_lord_idx],
                        "pd_lord": const.PLANET_NAMES_EN[pd_lord_idx],
                        "start_date": pd_start_date_str,
                        "end_date": pd_end_date_str
                    }
                    all_periods_md_ad_pd.append(period_data)

                    pd_start_date_obj = datetime.date(pd_start_tuple[0], pd_start_tuple[1], pd_start_tuple[2])
                    pd_end_date_obj = datetime.date(pd_end_tuple[0], pd_end_tuple[1], pd_end_tuple[2])
                    if max(pd_start_date_obj, filter_start_date_obj_filter) < min(pd_end_date_obj,
                                                                                  filter_end_date_obj_filter):
                        all_periods_filtered.append(period_data)

        elapsed_total_dasha_span_years += md_full_duration_years
    return all_periods_md_ad_pd, all_periods_filtered


# --- K.N. Rao Chara Dasha Extraction Function ---
def extract_kn_rao_chara_dasha_detailed(
        h_obj: Horoscope,
        d1_chart_positions: list,
        birth_datetime_date: datetime.date
):
    # ... (This function remains as it was in your script, assuming it's working)
    all_periods_md_ad = []
    all_periods_filtered_to_sd_level = []

    current_jd = h_obj.julian_day
    one_year_in_days = const.sidereal_year
    total_years_to_calculate = 80  # Total span of MDs to calculate from birth

    today_date = datetime.date.today()
    # For filtering PD/SD to a window around today
    filter_start_date_obj = today_date - timedelta(days=365)  # Use timedelta directly
    filter_end_date_obj = today_date + timedelta(days=(3 * 365))

    print(
        f"K.N. Rao Chara Dasha: Calculating for {total_years_to_calculate} years (MD/AD) from {birth_datetime_date.strftime('%Y-%m-%d')}")
    print(
        f"Filter window for Sookshmadashas (MD/AD/PD/SD): {filter_start_date_obj.strftime('%Y-%m-%d')} to {filter_end_date_obj.strftime('%Y-%m-%d')}")

    md_progression_rasis = jhora_chara_dhasa._dhasa_progression_knrao_method(d1_chart_positions)
    elapsed_total_years_for_mds = 0.0
    max_md_cycles_to_consider = (total_years_to_calculate // 5) + 3  # Heuristic to ensure enough cycles

    md_start_jd_current_md = current_jd  # Start from birth JD for the first MD

    for cycle_num in range(max_md_cycles_to_consider):
        if elapsed_total_years_for_mds >= total_years_to_calculate:
            break
        for md_rasi_index in md_progression_rasis:
            if elapsed_total_years_for_mds >= total_years_to_calculate:
                break

            md_start_jd_this_period = md_start_jd_current_md  # JD when this MD iteration starts

            md_total_duration_years_full = jhora_chara_dhasa._dhasa_duration_knrao_method(d1_chart_positions,
                                                                                          md_rasi_index)
            if md_total_duration_years_full <= 0:
                md_total_duration_years_full = 1.0  # Default to 1 year if duration is invalid

            # How much of this MD's full duration can we actually run within the 80-year target?
            remaining_calc_span = total_years_to_calculate - elapsed_total_years_for_mds
            actual_md_run_duration_this_iteration = min(md_total_duration_years_full, remaining_calc_span)

            md_end_jd_this_period = md_start_jd_this_period + (actual_md_run_duration_this_iteration * one_year_in_days)

            # --- Process Antardashas for this MD iteration ---
            ad_proportional_duration_years = md_total_duration_years_full / 12.0  # AD duration is proportional to full MD length
            if ad_proportional_duration_years <= 0:
                # If AD duration is zero, no sub-periods, just advance current_jd and elapsed time by MD
                elapsed_total_years_for_mds += actual_md_run_duration_this_iteration
                md_start_jd_current_md = md_end_jd_this_period
                continue

            current_ad_start_jd = md_start_jd_this_period
            try:
                ad_start_progression_index = md_progression_rasis.index(md_rasi_index)
            except ValueError:
                elapsed_total_years_for_mds += actual_md_run_duration_this_iteration
                md_start_jd_current_md = md_end_jd_this_period
                continue

            for i in range(12):  # AD Loop
                if current_ad_start_jd >= md_end_jd_this_period: break

                ad_rasi_index = md_progression_rasis[(ad_start_progression_index + i) % 12]
                ad_end_jd_this_ad = min(current_ad_start_jd + (ad_proportional_duration_years * one_year_in_days),
                                        md_end_jd_this_period)

                ad_start_tuple = jhora_utils.jd_to_gregorian(current_ad_start_jd)
                ad_end_tuple = jhora_utils.jd_to_gregorian(ad_end_jd_this_ad)
                ad_start_date_str = f"{ad_start_tuple[0]:04d}-{ad_start_tuple[1]:02d}-{ad_start_tuple[2]:02d}"
                ad_end_date_str = f"{ad_end_tuple[0]:04d}-{ad_end_tuple[1]:02d}-{ad_end_tuple[2]:02d}"

                all_periods_md_ad.append({
                    "md_rasi": const.rasi_names_en[md_rasi_index],
                    "ad_rasi": const.rasi_names_en[ad_rasi_index],
                    "start_date": ad_start_date_str,
                    "end_date": ad_end_date_str,
                })

                # Check if this AD falls within the -1 to +3 year filter window for PD/SD calculation
                ad_start_date_obj_check = datetime.date(ad_start_tuple[0], ad_start_tuple[1], ad_start_tuple[2])
                ad_end_date_obj_check = datetime.date(ad_end_tuple[0], ad_end_tuple[1], ad_end_tuple[2])

                if max(ad_start_date_obj_check, filter_start_date_obj) < min(ad_end_date_obj_check,
                                                                             filter_end_date_obj):
                    pd_proportional_duration_years = ad_proportional_duration_years / 12.0
                    if pd_proportional_duration_years > 0:
                        current_pd_start_jd = current_ad_start_jd  # Start PDs from the start of this AD
                        try:
                            pd_start_progression_index = md_progression_rasis.index(ad_rasi_index)
                        except ValueError:
                            continue  # Should not happen if AD rasi is from progression

                        for j in range(12):  # PD Loop
                            if current_pd_start_jd >= ad_end_jd_this_ad: break
                            pd_rasi_index = md_progression_rasis[(pd_start_progression_index + j) % 12]
                            pd_end_jd_this_pd = min(
                                current_pd_start_jd + (pd_proportional_duration_years * one_year_in_days),
                                ad_end_jd_this_ad)

                            pd_start_tuple_check = jhora_utils.jd_to_gregorian(current_pd_start_jd)
                            pd_end_tuple_check = jhora_utils.jd_to_gregorian(pd_end_jd_this_pd)
                            pd_start_date_obj_check = datetime.date(pd_start_tuple_check[0], pd_start_tuple_check[1],
                                                                    pd_start_tuple_check[2])
                            pd_end_date_obj_check = datetime.date(pd_end_tuple_check[0], pd_end_tuple_check[1],
                                                                  pd_end_tuple_check[2])

                            if max(pd_start_date_obj_check, filter_start_date_obj) < min(pd_end_date_obj_check,
                                                                                         filter_end_date_obj):
                                sd_proportional_duration_years = pd_proportional_duration_years / 12.0
                                if sd_proportional_duration_years > 0:
                                    current_sd_start_jd = current_pd_start_jd  # Start SDs from start of this PD
                                    try:
                                        sd_start_progression_index = md_progression_rasis.index(pd_rasi_index)
                                    except ValueError:
                                        continue

                                    for k in range(12):  # SD Loop
                                        if current_sd_start_jd >= pd_end_jd_this_pd: break
                                        sd_rasi_index = md_progression_rasis[(sd_start_progression_index + k) % 12]
                                        sd_end_jd_this_sd = min(
                                            current_sd_start_jd + (sd_proportional_duration_years * one_year_in_days),
                                            pd_end_jd_this_pd)

                                        sd_start_tuple_check = jhora_utils.jd_to_gregorian(current_sd_start_jd)
                                        sd_end_tuple_check = jhora_utils.jd_to_gregorian(sd_end_jd_this_sd)

                                        all_periods_filtered_to_sd_level.append({
                                            "md_rasi": const.rasi_names_en[md_rasi_index],
                                            "ad_rasi": const.rasi_names_en[ad_rasi_index],
                                            "pd_rasi": const.rasi_names_en[pd_rasi_index],
                                            "sd_rasi": const.rasi_names_en[sd_rasi_index],
                                            "start_date": f"{sd_start_tuple_check[0]:04d}-{sd_start_tuple_check[1]:02d}-{sd_start_tuple_check[2]:02d}",
                                            "end_date": f"{sd_end_tuple_check[0]:04d}-{sd_end_tuple_check[1]:02d}-{sd_end_tuple_check[2]:02d}",
                                        })
                                        current_sd_start_jd = sd_end_jd_this_sd
                            current_pd_start_jd = pd_end_jd_this_pd
                current_ad_start_jd = ad_end_jd_this_ad

            elapsed_total_years_for_mds += actual_md_run_duration_this_iteration
            md_start_jd_current_md = md_end_jd_this_period  # Set start for the *next* MD in the cycle
    return all_periods_md_ad, all_periods_filtered_to_sd_level


# --- Main Execution Logic ---
def main():
    print("--- PyJHora Data Extractor ---")
    # Get birth data
    current_birth_data = get_abhijeet_birth_data()  # Using your function
    print(f"Processing for: {current_birth_data.name}")
    print(f"DOB: {current_birth_data.dob_str}, TOB: {current_birth_data.tob_str}")

    # Initialize Horoscope object - THIS WAS MISSING IN THE PROVIDED MAIN BEFORE VIMSOTTARI
    h: Horoscope | None = None
    d1_planet_positions: list | None = None

    try:
        # Assuming drik.Date can take int arguments directly
        drik_birth_date_obj = drik.Date(
            year=current_birth_data.date_of_birth.year,
            month=current_birth_data.date_of_birth.month,
            day=current_birth_data.date_of_birth.day
        )
        h = Horoscope(
            date_in=drik_birth_date_obj,
            birth_time=current_birth_data.tob_str,
            latitude=current_birth_data.latitude,
            longitude=current_birth_data.longitude,
            timezone_offset=current_birth_data.timezone_offset,
            ayanamsa_mode=DEFAULT_AYANAMSA_MODE
        )
        print("Successfully instantiated Horoscope object (h).")
    except Exception as e:
        print(f"ERROR during Horoscope setup: {e}")
        traceback.print_exc()
        return

    if not h: return  # Exit if horoscope object creation failed

    # Get D1 Rasi Chart positions - THIS WAS MISSING
    try:
        # Using h.julian_day and h.Place and h.ayanamsa_mode
        d1_planet_positions = jhora_charts.rasi_chart(
            jd_at_dob=h.julian_day,
            place_as_tuple=h.Place,  # Ensure h.Place is the (lat, long, tz) tuple
            ayanamsa_mode=h.ayanamsa_mode
        )
        if d1_planet_positions:
            print("Successfully fetched D1 Rasi Chart positions.")
        else:
            print("ERROR: D1 Rasi chart positions came back empty.")
            return  # Cannot proceed without D1 chart for some Dashas
    except Exception as e:
        print(f"ERROR: Could not get D1 Rasi chart: {e}")
        traceback.print_exc()
        return

    # Prepare output directory and file prefix - THIS WAS MISSING
    # Ensure OUTPUT_BASE_PATH is a Path object
    OUTPUT_BASE_PATH.mkdir(parents=True, exist_ok=True)

    slug_name = current_birth_data.name.lower().replace(" ", "_").replace("-", "_")
    time_suffix = current_birth_data.time_of_birth.strftime("%H%M")
    person_dir_name = f"{slug_name}_{time_suffix}"

    # Use OUTPUT_BASE_PATH here
    full_output_path = OUTPUT_BASE_PATH / person_dir_name
    try:
        full_output_path.mkdir(parents=True, exist_ok=True)
        print(f"\nOutput directory created/ensured: {full_output_path}")
    except OSError as oe:
        print(f"ERROR: Could not create output directory {full_output_path}: {oe}")
        return

    # file_prefix should be a Path object to join with filename string
    file_prefix = full_output_path / f"{slug_name}_{time_suffix}"

    # --- K.N. Rao Chara Dasha Calculation and Saving ---
    # This part from your original script looks fine assuming h and d1_planet_positions are set
    if h and d1_planet_positions:
        print("\nCalculating K.N. Rao Chara Dasha (MD/AD for 80yrs, MD/AD/PD/SD for filtered window)...")
        try:
            knr_md_ad_80yrs, knr_filtered_to_sd = extract_kn_rao_chara_dasha_detailed(
                h, d1_planet_positions, current_birth_data.date_of_birth
            )

            # Use f-string with file_prefix as Path
            filepath_knr_md_ad = Path(f"{str(file_prefix)}_dasha_KN_Rao_Chara_MD_AD_80yrs.json")
            with open(filepath_knr_md_ad, 'w', encoding='utf-8') as f:
                json.dump(knr_md_ad_80yrs, f, indent=2, ensure_ascii=False)
            print(f"Successfully saved K.N. Rao Chara Dasha (MD/AD 80yrs) to: {filepath_knr_md_ad}")

            filepath_knr_filtered_sd = Path(f"{str(file_prefix)}_dasha_KN_Rao_Chara_MD_AD_PD_SD_filtered.json")
            with open(filepath_knr_filtered_sd, 'w', encoding='utf-8') as f:
                json.dump(knr_filtered_to_sd, f, indent=2, ensure_ascii=False)
            print(f"Successfully saved K.N. Rao Chara Dasha (Filtered to SD level) to: {filepath_knr_filtered_sd}")

        except Exception as e:
            print(f"ERROR calculating or saving K.N. Rao Chara Dasha: {e}")
            traceback.print_exc()
    else:
        print("Skipping K.N. Rao Chara Dasha (Horoscope object 'h' or 'd1_planet_positions' not available).")

    # --- VIMSHOTTARI DASHA BLOCK ---
    if h and d1_planet_positions:
        print("\nCalculating Standard Vimshottari Dasha (MD/AD/PD for 80yrs and filtered window)...")
        try:
            vims_all_80yrs, vims_filtered = extract_standard_vimsottari_dasha(
                h,
                # d1_planet_positions, # This argument was removed from the function signature as it was unused there
                current_birth_data.date_of_birth
            )

            if vims_all_80yrs:
                # Use f-string with file_prefix as Path
                filepath_vims_full = Path(f"{str(file_prefix)}_dasha_vimshottari.json")
                with open(filepath_vims_full, 'w', encoding='utf-8') as f:
                    json.dump(vims_all_80yrs, f, indent=2, ensure_ascii=False)
                print(f"Successfully saved Vimshottari Dasha (Full 80yrs MD/AD/PD) to: {filepath_vims_full}")
            else:
                print("No Vimshottari Dasha (Full 80yrs) data generated.")

            if vims_filtered:
                filepath_vims_filtered = Path(f"{str(file_prefix)}_dasha_vimshottari_filtered.json")
                with open(filepath_vims_filtered, 'w', encoding='utf-8') as f:
                    json.dump(vims_filtered, f, indent=2, ensure_ascii=False)
                print(f"Successfully saved Vimshottari Dasha (Filtered MD/AD/PD) to: {filepath_vims_filtered}")
            else:
                print("No Vimshottari Dasha (Filtered) data generated.")

        except Exception as e:
            print(f"ERROR calculating or saving Vimshottari Dasha: {e}")
            traceback.print_exc()
    else:
        print("Skipping Vimshottari Dasha (Horoscope object 'h' or 'd1_planet_positions' not available).")
    # --- END OF VIMSHOTTARI DASHA BLOCK ---


if __name__ == "__main__":
    # Added timedelta import for Vimshottari function's filter dates
    from datetime import timedelta

    main()