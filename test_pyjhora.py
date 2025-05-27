# test_pyjhora.py (Chara Karakas extraction removed)

import datetime
import traceback
import os
import json
from dataclasses import dataclass
from jhora.horoscope.dhasa.graha import vimsottari as jhora_vimsottari_std

# --- PyJHora Core Imports ---
try:
    from jhora.horoscope.main import Horoscope
    from jhora.panchanga import drik
    from jhora import const
    from jhora.horoscope.chart import charts as jhora_charts
    # from jhora.horoscope.chart import house as jhora_house # Removed as Chara Karakas are removed
    from jhora.horoscope.dhasa.raasi import chara as jhora_chara_dhasa
    from jhora import utils as jhora_utils
except ImportError as e:
    print(f"FATAL ERROR: Could not import PyJHora modules: {e}")
    exit()

# --- Configuration ---
DEFAULT_AYANAMSA_MODE = "LAHIRI"
OUTPUT_BASE_PATH = "./Kundali"


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
# PASTE THE NEW FUNCTION HERE:
def extract_standard_vimsottari_dasha(
        h_obj: Horoscope,
        d1_chart_positions: list,
        birth_datetime_date: datetime.date
):
    all_periods_md_ad_pd = []
    all_periods_filtered = []

    jd_at_birth = h_obj.julian_day
    place_obj = h_obj.Place

    total_years_to_calculate = 80

    today_date_filter = datetime.date.today()
    filter_start_date_obj_filter = today_date_filter - datetime.timedelta(days=365)
    filter_end_date_obj_filter = today_date_filter + datetime.timedelta(days=(3 * 365))

    print(
        f"Vimshottari: Calculating for {total_years_to_calculate} years (MD/AD/PD) from {birth_datetime_date.strftime('%Y-%m-%d')}")
    print(
        f"Filter window for Vimshottari: {filter_start_date_obj_filter.strftime('%Y-%m-%d')} to {filter_end_date_obj_filter.strftime('%Y-%m-%d')}")

    try:
        mahadasas = jhora_vimsottari_std.vimsottari_mahadasa(
            jd_at_birth,
            place_obj,
            dhasa_starting_planet=1,
            star_position_from_moon=1
        )
    except Exception as e:
        print(f"Error in vimsottari_mahadasa call: {e}")
        traceback.print_exc()
        return None, None

    if not mahadasas:
        print("ERROR: vimsottari_mahadasa returned no data.")
        return None, None

    # For debugging, print the first MD lord and start date
    # first_md_lord_debug = list(mahadasas.keys())[0]
    # first_md_start_jd_debug = mahadasas[first_md_lord_debug]
    # print(f"Debug: First MD lord: {const.PLANET_NAMES_EN[first_md_lord_debug]}, Start JD: {first_md_start_jd_debug}")
    # birth_jd_check = h_obj.julian_day
    # if first_md_start_jd_debug > birth_jd_check:
    #     print(f"Warning: First MD start JD {first_md_start_jd_debug} is after birth JD {birth_jd_check}")
    # else:
    #     print(f"Balance of first Dasha already accounted for in MD start JD. Days into Dasha: {birth_jd_check - first_md_start_jd_debug}")

    elapsed_total_dasha_span_years = 0.0  # Tracks the span covered by full MDs

    for md_lord_idx, md_start_jd in mahadasas.items():
        if elapsed_total_dasha_span_years >= total_years_to_calculate:
            # print(f"Reached {total_years_to_calculate} years of MD span, stopping MD loop.")
            break

        md_full_duration_years = jhora_vimsottari_std.vimsottari_dict[md_lord_idx]

        antardashas = jhora_vimsottari_std._vimsottari_bhukti(md_lord_idx, md_start_jd)

        for ad_lord_idx, ad_start_jd in antardashas.items():
            # Check if this AD starts beyond the 80-year calculation limit from birth
            if ad_start_jd > jd_at_birth + (total_years_to_calculate * const.sidereal_year):
                # print(f"  AD of {const.PLANET_NAMES_EN[ad_lord_idx]} starts beyond 80yr limit. Skipping further ADs for this MD.")
                break  # Break from AD loop for this MD

            ad_full_duration_years = (jhora_vimsottari_std.vimsottari_dict[
                                          ad_lord_idx] * md_full_duration_years) / const.human_life_span_for_vimsottari_dhasa

            pratyantardashas = jhora_vimsottari_std._vimsottari_antara(md_lord_idx, ad_lord_idx, ad_start_jd)

            for pd_lord_idx, pd_start_jd in pratyantardashas.items():
                # Check if this PD starts beyond the 80-year calculation limit from birth
                if pd_start_jd > jd_at_birth + (total_years_to_calculate * const.sidereal_year):
                    # print(f"    PD of {const.PLANET_NAMES_EN[pd_lord_idx]} starts beyond 80yr limit. Skipping further PDs for this AD.")
                    break  # Break from PD loop for this AD

                pd_full_duration_years = (jhora_vimsottari_std.vimsottari_dict[
                                              pd_lord_idx] * ad_full_duration_years) / const.human_life_span_for_vimsottari_dhasa
                pd_end_jd = pd_start_jd + (pd_full_duration_years * const.sidereal_year)

                # Only add to the 80-year list if the PD *starts* within the 80-year window from birth
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

                    # Filtering logic for the -1 to +3 year window
                    pd_start_date_obj = datetime.date(pd_start_tuple[0], pd_start_tuple[1], pd_start_tuple[2])
                    pd_end_date_obj = datetime.date(pd_end_tuple[0], pd_end_tuple[1], pd_end_tuple[2])
                    if max(pd_start_date_obj, filter_start_date_obj_filter) < min(pd_end_date_obj,
                                                                                  filter_end_date_obj_filter):
                        all_periods_filtered.append(period_data)  # Already formatted

        elapsed_total_dasha_span_years += md_full_duration_years
        # print(f"MD {const.PLANET_NAMES_EN[md_lord_idx]} ({md_full_duration_years} yrs) processed. Total elapsed: {elapsed_total_dasha_span_years:.2f} yrs")

    return all_periods_md_ad_pd, all_periods_filtered


def main():
    # ... (your existing main function code up to the point of K.N. Rao Dasha saving) ...
    # (This includes current_birth_data, h, d1_planet_positions, slug_name, time_suffix, full_output_path, file_prefix)

    # --- ADD THIS BLOCK FOR VIMSHOTTARI DASHA ---
    if h and d1_planet_positions:  # Ensure we have h and D1 chart
        print("\nCalculating Standard Vimshottari Dasha (MD/AD/PD for 80yrs and filtered window)...")
        try:
            vims_all_80yrs, vims_filtered = extract_standard_vimsottari_dasha(
                h,
                d1_planet_positions,
                current_birth_data.date_of_birth
            )

            if vims_all_80yrs:
                filepath_vims_full = f"{file_prefix}_dasha_vimshottari.json"
                with open(filepath_vims_full, 'w', encoding='utf-8') as f:
                    json.dump(vims_all_80yrs, f, indent=2, ensure_ascii=False)
                print(f"Successfully saved Vimshottari Dasha (Full 80yrs MD/AD/PD) to: {filepath_vims_full}")
            else:
                print("No Vimshottari Dasha (Full 80yrs) data generated.")

            if vims_filtered:
                filepath_vims_filtered = f"{file_prefix}_dasha_vimshottari_filtered.json"
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
    main()

# --- K.N. Rao Chara Dasha Extraction Function (with Sookshmadasha for filtered output) ---
def extract_kn_rao_chara_dasha_detailed(
        h_obj: Horoscope,
        d1_chart_positions: list,
        birth_datetime_date: datetime.date
):
    all_periods_md_ad = []
    all_periods_filtered_to_sd_level = []

    current_jd = h_obj.julian_day
    one_year_in_days = const.sidereal_year
    total_years_to_calculate = 80

    today_date = datetime.date.today()
    filter_start_date_obj = today_date - datetime.timedelta(days=365)
    filter_end_date_obj = today_date + datetime.timedelta(days=(3 * 365))

    print(
        f"K.N. Rao Chara Dasha: Calculating for {total_years_to_calculate} years (MD/AD) from {birth_datetime_date.strftime('%Y-%m-%d')}")
    print(
        f"Filter window for Sookshmadashas (MD/AD/PD/SD): {filter_start_date_obj.strftime('%Y-%m-%d')} to {filter_end_date_obj.strftime('%Y-%m-%d')}")

    md_progression_rasis = jhora_chara_dhasa._dhasa_progression_knrao_method(d1_chart_positions)
    elapsed_total_years = 0.0
    max_md_cycles = (total_years_to_calculate // 5) + 3

    for cycle_num in range(max_md_cycles):
        if elapsed_total_years >= total_years_to_calculate:
            break
        for md_rasi_index in md_progression_rasis:
            if elapsed_total_years >= total_years_to_calculate:
                break

            md_start_jd = current_jd
            md_total_duration_years_full = jhora_chara_dhasa._dhasa_duration_knrao_method(d1_chart_positions,
                                                                                          md_rasi_index)

            if md_total_duration_years_full <= 0:
                print(
                    f"Warning: MD Rasi {const.rasi_names_en[md_rasi_index]} has 0 or negative full duration ({md_total_duration_years_full}). Defaulting to 1 year.")
                md_total_duration_years_full = 1.0

            remaining_years_for_80yr_target = total_years_to_calculate - elapsed_total_years
            actual_md_run_duration = min(md_total_duration_years_full, remaining_years_for_80yr_target)
            md_end_jd = md_start_jd + (actual_md_run_duration * one_year_in_days)

            ad_proportional_duration_years = md_total_duration_years_full / 12.0
            if ad_proportional_duration_years <= 0: continue

            current_ad_start_jd = md_start_jd
            try:
                ad_start_progression_index = md_progression_rasis.index(md_rasi_index)
            except ValueError:
                print(f"Error: MD Rasi {md_rasi_index} not found in progression {md_progression_rasis}. Skipping MD.")
                continue

            for i in range(12):  # AD Loop
                if current_ad_start_jd >= md_end_jd: break

                ad_rasi_index = md_progression_rasis[(ad_start_progression_index + i) % 12]
                ad_start_jd_this_ad = current_ad_start_jd
                ad_end_jd_this_ad = min(ad_start_jd_this_ad + (ad_proportional_duration_years * one_year_in_days),
                                        md_end_jd)

                ad_start_tuple = jhora_utils.jd_to_gregorian(ad_start_jd_this_ad)
                ad_end_tuple = jhora_utils.jd_to_gregorian(ad_end_jd_this_ad)

                all_periods_md_ad.append({
                    "md_rasi": const.rasi_names_en[md_rasi_index],
                    "ad_rasi": const.rasi_names_en[ad_rasi_index],
                    "start_date": f"{ad_start_tuple[0]:04d}-{ad_start_tuple[1]:02d}-{ad_start_tuple[2]:02d}",
                    "end_date": f"{ad_end_tuple[0]:04d}-{ad_end_tuple[1]:02d}-{ad_end_tuple[2]:02d}",
                })

                ad_start_date_obj = datetime.date(ad_start_tuple[0], ad_start_tuple[1], ad_start_tuple[2])
                ad_end_date_obj = datetime.date(ad_end_tuple[0], ad_end_tuple[1], ad_end_tuple[2])

                if max(ad_start_date_obj, filter_start_date_obj) < min(ad_end_date_obj, filter_end_date_obj):
                    pd_proportional_duration_years = ad_proportional_duration_years / 12.0
                    if pd_proportional_duration_years <= 0: continue
                    current_pd_start_jd = ad_start_jd_this_ad

                    try:
                        pd_start_progression_index = md_progression_rasis.index(ad_rasi_index)
                    except ValueError:
                        print(f"Error: AD Rasi {ad_rasi_index} not in progression. Skipping PDs.")
                        continue

                    for j in range(12):  # PD Loop
                        if current_pd_start_jd >= ad_end_jd_this_ad: break

                        pd_rasi_index = md_progression_rasis[(pd_start_progression_index + j) % 12]
                        pd_start_jd_this_pd = current_pd_start_jd
                        pd_end_jd_this_pd = min(
                            pd_start_jd_this_pd + (pd_proportional_duration_years * one_year_in_days),
                            ad_end_jd_this_ad)

                        pd_start_tuple = jhora_utils.jd_to_gregorian(pd_start_jd_this_pd)
                        pd_end_tuple = jhora_utils.jd_to_gregorian(pd_end_jd_this_pd)
                        pd_start_date_obj = datetime.date(pd_start_tuple[0], pd_start_tuple[1], pd_start_tuple[2])
                        pd_end_date_obj = datetime.date(pd_end_tuple[0], pd_end_tuple[1], pd_end_tuple[2])

                        if max(pd_start_date_obj, filter_start_date_obj) < min(pd_end_date_obj, filter_end_date_obj):
                            sd_proportional_duration_years = pd_proportional_duration_years / 12.0
                            if sd_proportional_duration_years <= 0: continue
                            current_sd_start_jd = pd_start_jd_this_pd

                            try:
                                sd_start_progression_index = md_progression_rasis.index(pd_rasi_index)
                            except ValueError:
                                print(f"Error: PD Rasi {pd_rasi_index} not in progression. Skipping SDs.")
                                continue

                            for k in range(12):  # SD Loop
                                if current_sd_start_jd >= pd_end_jd_this_pd: break

                                sd_rasi_index = md_progression_rasis[(sd_start_progression_index + k) % 12]
                                sd_start_jd_this_sd = current_sd_start_jd
                                sd_end_jd_this_sd = min(
                                    sd_start_jd_this_sd + (sd_proportional_duration_years * one_year_in_days),
                                    pd_end_jd_this_pd)

                                sd_start_tuple = jhora_utils.jd_to_gregorian(sd_start_jd_this_sd)
                                sd_end_tuple = jhora_utils.jd_to_gregorian(sd_end_jd_this_sd)
                                sd_start_date_obj = datetime.date(sd_start_tuple[0], sd_start_tuple[1],
                                                                  sd_start_tuple[2])
                                sd_end_date_obj = datetime.date(sd_end_tuple[0], sd_end_tuple[1], sd_end_tuple[2])

                                if max(sd_start_date_obj, filter_start_date_obj) < min(sd_end_date_obj,
                                                                                       filter_end_date_obj):
                                    all_periods_filtered_to_sd_level.append({
                                        "md_rasi": const.rasi_names_en[md_rasi_index],
                                        "ad_rasi": const.rasi_names_en[ad_rasi_index],
                                        "pd_rasi": const.rasi_names_en[pd_rasi_index],
                                        "sd_rasi": const.rasi_names_en[sd_rasi_index],
                                        "start_date": f"{sd_start_tuple[0]:04d}-{sd_start_tuple[1]:02d}-{sd_start_tuple[2]:02d}",
                                        "end_date": f"{sd_end_tuple[0]:04d}-{sd_end_tuple[1]:02d}-{sd_end_tuple[2]:02d}",
                                    })
                                current_sd_start_jd = sd_end_jd_this_sd
                        current_pd_start_jd = pd_end_jd_this_pd
                current_ad_start_jd = ad_end_jd_this_ad

            elapsed_total_years += actual_md_run_duration
            current_jd = md_end_jd

            if elapsed_total_years >= total_years_to_calculate:
                break

    return all_periods_md_ad, all_periods_filtered_to_sd_level


# --- Main Execution Logic ---
def main():
    print("--- PyJHora Data Extractor (Single Script Mode) ---")
    current_birth_data = get_abhijeet_birth_data()
    print(f"Processing for: {current_birth_data.name}")
    print(f"DOB: {current_birth_data.dob_str}, TOB: {current_birth_data.tob_str}")

    h: Horoscope | None = None
    d1_planet_positions: list | None = None

    try:
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
    if not h: return

    try:
        d1_planet_positions = jhora_charts.rasi_chart(
            jd_at_dob=h.julian_day,
            place_as_tuple=h.Place,
            ayanamsa_mode=h.ayanamsa_mode
        )
        print("Successfully fetched D1 Rasi Chart.")
    except Exception as e:
        print(f"ERROR: Could not get D1 Rasi chart: {e}")
        traceback.print_exc()
        d1_planet_positions = None

        # --- Chara Karakas calculation and saving is REMOVED ---

    slug_name = current_birth_data.name.lower().replace(" ", "_").replace("-", "_")
    time_suffix = current_birth_data.time_of_birth.strftime("%H%M")
    person_dir_name = f"{slug_name}_{time_suffix}"
    full_output_path = os.path.join(OUTPUT_BASE_PATH, person_dir_name)
    try:
        os.makedirs(full_output_path, exist_ok=True)
        print(f"\nOutput directory created/ensured: {full_output_path}")
    except OSError as oe:
        print(f"ERROR: Could not create output directory {full_output_path}: {oe}")
        return
    file_prefix = os.path.join(full_output_path, f"{slug_name}_{time_suffix}")

    # --- K.N. Rao Chara Dasha Calculation and Saving ---
    if h and d1_planet_positions:
        print("\nCalculating K.N. Rao Chara Dasha (MD/AD for 80yrs, MD/AD/PD/SD for filtered window)...")
        try:
            knr_md_ad_80yrs, knr_filtered_to_sd = extract_kn_rao_chara_dasha_detailed(
                h, d1_planet_positions, current_birth_data.date_of_birth
            )

            filepath_knr_md_ad = f"{file_prefix}_dasha_KN_Rao_Chara_MD_AD_80yrs.json"
            with open(filepath_knr_md_ad, 'w', encoding='utf-8') as f:
                json.dump(knr_md_ad_80yrs, f, indent=2, ensure_ascii=False)
            print(f"Successfully saved K.N. Rao Chara Dasha (MD/AD 80yrs) to: {filepath_knr_md_ad}")

            filepath_knr_filtered_sd = f"{file_prefix}_dasha_KN_Rao_Chara_MD_AD_PD_SD_filtered.json"
            with open(filepath_knr_filtered_sd, 'w', encoding='utf-8') as f:
                json.dump(knr_filtered_to_sd, f, indent=2, ensure_ascii=False)
            print(f"Successfully saved K.N. Rao Chara Dasha (Filtered to SD level) to: {filepath_knr_filtered_sd}")

        except Exception as e:
            print(f"ERROR calculating or saving K.N. Rao Chara Dasha: {e}")
            traceback.print_exc()
    else:
        print("Skipping K.N. Rao Chara Dasha (Horoscope object 'h' or 'd1_planet_positions' not available).")


if __name__ == "__main__":
    main()