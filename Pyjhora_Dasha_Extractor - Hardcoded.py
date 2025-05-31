# dasha_extractor_and_parser.py

import datetime
import traceback
import os
import json
from dataclasses import dataclass
from pathlib import Path
import re

# from datetime import timedelta # Already imported via import datetime

# --- PyJHora Core Imports ---
try:
    from jhora.horoscope.main import Horoscope
    from jhora.panchanga import drik
    from jhora import const
    from jhora.horoscope.chart import charts as jhora_charts
    from jhora.horoscope.dhasa.raasi import chara as jhora_chara_dhasa
    from jhora.horoscope.dhasa.graha import vimsottari as jhora_vimsottari_std
    from jhora import utils as jhora_utils

except ImportError as e:
    print(f"FATAL ERROR: Could not import PyJHora modules: {e}")
    exit()

# --- Configuration ---
DEFAULT_AYANAMSA_MODE = "LAHIRI"
OUTPUT_BASE_PATH = Path("./Kundali")

ZODIAC_MAP_UNIVERSAL = {
    "Ar": "Aries", "Ta": "Taurus", "Ge": "Gemini", "Cn": "Cancer",
    "Le": "Leo", "Vi": "Virgo", "Li": "Libra", "Sc": "Scorpio",
    "Sg": "Sagittarius", "Cp": "Capricorn", "Aq": "Aquarius", "Pi": "Pisces",
    "Sun": "Sun", "Moon": "Moon", "Mars": "Mars", "Merc": "Mercury", "Mer": "Mercury",
    "Jup": "Jupiter", "Ven": "Venus", "Sat": "Saturn",
    "Rah": "Rahu", "Ket": "Ketu"
}

PLANET_FULL_NAMES_LIST = None
PLANET_SHORT_NAMES_LIST = None

if hasattr(jhora_utils, 'PLANET_NAMES'):
    PLANET_FULL_NAMES_LIST = jhora_utils.PLANET_NAMES
elif hasattr(const, 'PLANET_NAMES'):
    PLANET_FULL_NAMES_LIST = const.PLANET_NAMES
elif hasattr(const, 'planet_names'):
    PLANET_FULL_NAMES_LIST = const.planet_names

if hasattr(jhora_utils, 'PLANET_SHORT_NAMES'):
    PLANET_SHORT_NAMES_LIST = jhora_utils.PLANET_SHORT_NAMES
elif hasattr(const, 'PLANET_SHORT_NAMES'):
    PLANET_SHORT_NAMES_LIST = const.PLANET_SHORT_NAMES
elif hasattr(const, 'planet_short_names'):
    PLANET_SHORT_NAMES_LIST = const.planet_short_names

if PLANET_FULL_NAMES_LIST and PLANET_SHORT_NAMES_LIST and \
        isinstance(PLANET_FULL_NAMES_LIST, list) and isinstance(PLANET_SHORT_NAMES_LIST, list) and \
        len(PLANET_FULL_NAMES_LIST) >= 9 and len(PLANET_SHORT_NAMES_LIST) >= 9:
    common_len = min(len(PLANET_FULL_NAMES_LIST), len(PLANET_SHORT_NAMES_LIST))
    common_len = min(common_len, 9)
    for i in range(common_len):
        short_name = PLANET_SHORT_NAMES_LIST[i]
        full_name = PLANET_FULL_NAMES_LIST[i]
        if isinstance(full_name, str):
            full_name = full_name.capitalize()
        if short_name not in ZODIAC_MAP_UNIVERSAL:
            ZODIAC_MAP_UNIVERSAL[short_name] = full_name
else:
    print(
        "WARNING: Could not reliably find PyJHora's planet name lists. Universal name expansion might be limited.")
    if not PLANET_FULL_NAMES_LIST or not (
            isinstance(PLANET_FULL_NAMES_LIST, list) and len(PLANET_FULL_NAMES_LIST) >= 9):
        PLANET_FULL_NAMES_LIST = ['Sun', 'Moon', 'Mars', 'Mercury', 'Jupiter', 'Venus', 'Saturn', 'Rahu', 'Ketu']
    if not PLANET_SHORT_NAMES_LIST or not (
            isinstance(PLANET_SHORT_NAMES_LIST, list) and len(PLANET_SHORT_NAMES_LIST) >= 9):
        PLANET_SHORT_NAMES_LIST = ["Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa", "Ra", "Ke"]
    print("INFO: Using fallback planet names for ZODIAC_MAP_UNIVERSAL population.")
    common_len_fallback = min(len(PLANET_FULL_NAMES_LIST), len(PLANET_SHORT_NAMES_LIST))
    common_len_fallback = min(common_len_fallback, 9)
    for i in range(common_len_fallback):
        short_name = PLANET_SHORT_NAMES_LIST[i]
        full_name = PLANET_FULL_NAMES_LIST[i]
        if isinstance(full_name, str):
            full_name = full_name.capitalize()
        if short_name not in ZODIAC_MAP_UNIVERSAL:
            ZODIAC_MAP_UNIVERSAL[short_name] = full_name


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
    def tob_str(self) -> str: return self.time_of_birth.strftime("%H:%M:%S")

    @property
    def dob_str(self) -> str: return self.date_of_birth.strftime("%Y-%m-%d")


# --- Hardcoded Birth Data ---
def get_abhijeet_birth_data() -> BirthData:
    return BirthData(name="Abhijeet Singh Chauhan", date_of_birth=datetime.date(1976, 9, 6),
                     time_of_birth=datetime.time(11, 20, 0), latitude=28.621111, longitude=77.080278,
                     timezone_offset=5.5, gender="male")


# --- Helper function for formatting datetime from JD ---
def _format_datetime_from_jd(jd_val: float) -> str:
    greg_date_tuple = jhora_utils.jd_to_gregorian(jd_val)
    if not isinstance(greg_date_tuple, (list, tuple)) or len(greg_date_tuple) < 4:
        print(
            f"ERROR (_format_datetime_from_jd): jd_to_gregorian({jd_val}) returned unexpected value: {greg_date_tuple}")
        return "0000-00-00 00:00:00"
    year, month, day = int(greg_date_tuple[0]), int(greg_date_tuple[1]), int(greg_date_tuple[2])
    fractional_hour = greg_date_tuple[3]
    hour = int(fractional_hour)
    minute_fraction = (fractional_hour - hour) * 60;
    minute = int(minute_fraction)
    second_fraction = (minute_fraction - minute) * 60;
    second = int(round(second_fraction))
    if second >= 60: second = 0; minute += 1
    if minute >= 60: minute = 0; hour += 1
    if hour >= 24: hour = 0
    return f"{year:04d}-{month:02d}-{day:02d} {hour:02d}:{minute:02d}:{second:02d}"


def _format_date_from_iso_str(iso_date_str: str) -> str:
    """Converts an ISO datetime string to 'YYYY-MM-DD'."""
    try:
        return datetime.datetime.fromisoformat(iso_date_str).strftime("%Y-%m-%d")
    except ValueError:
        print(f"Warning: Could not parse ISO date string for flat file: {iso_date_str}")
        return "0000-00-00"


# --- K.N. Rao Chara Dasha Extraction ---
def extract_kn_rao_chara_dasha_detailed(
        h_obj: Horoscope, d1_chart_positions: list, birth_datetime_date: datetime.date
):  # (Content as before - condensed for brevity in this response)
    all_periods_md_ad = []
    all_periods_filtered_to_sd_level = []
    current_jd_for_mds = h_obj.julian_day
    one_year_in_days = const.sidereal_year
    total_years_to_calculate_md_ad = 80
    today_date = datetime.date.today()
    filter_start_date_obj = today_date - datetime.timedelta(days=365)
    filter_end_date_obj = today_date + datetime.timedelta(days=(3 * 365))
    md_progression_rasis = jhora_chara_dhasa._dhasa_progression_knrao_method(d1_chart_positions)
    elapsed_total_years_for_mds = 0.0
    max_md_cycles = (total_years_to_calculate_md_ad // 5) + 3
    for cycle_num in range(max_md_cycles):
        if elapsed_total_years_for_mds >= total_years_to_calculate_md_ad: break
        for md_rasi_index_current_cycle in md_progression_rasis:
            if elapsed_total_years_for_mds >= total_years_to_calculate_md_ad: break
            md_start_jd_current_md = current_jd_for_mds
            md_total_duration_years_full = jhora_chara_dhasa._dhasa_duration_knrao_method(d1_chart_positions,
                                                                                          md_rasi_index_current_cycle)
            if md_total_duration_years_full <= 0: md_total_duration_years_full = 1.0
            remaining_years_for_target = total_years_to_calculate_md_ad - elapsed_total_years_for_mds
            actual_md_run_duration_this_iteration = min(md_total_duration_years_full, remaining_years_for_target)
            if actual_md_run_duration_this_iteration <= 0 and total_years_to_calculate_md_ad > elapsed_total_years_for_mds:
                actual_md_run_duration_this_iteration = md_total_duration_years_full
            if actual_md_run_duration_this_iteration <= 0: continue
            md_end_jd_current_md = md_start_jd_current_md + (actual_md_run_duration_this_iteration * one_year_in_days)
            ad_proportional_duration_years = md_total_duration_years_full / 12.0
            if ad_proportional_duration_years <= 0:
                current_jd_for_mds = md_end_jd_current_md
                elapsed_total_years_for_mds += actual_md_run_duration_this_iteration
                continue
            current_ad_start_jd = md_start_jd_current_md
            try:
                ad_start_progression_index = md_progression_rasis.index(md_rasi_index_current_cycle)
            except ValueError:
                current_jd_for_mds = md_end_jd_current_md
                elapsed_total_years_for_mds += actual_md_run_duration_this_iteration
                continue
            for i in range(12):
                if current_ad_start_jd >= md_end_jd_current_md: break
                ad_rasi_index = md_progression_rasis[(ad_start_progression_index + i) % 12]
                ad_start_jd_this_ad = current_ad_start_jd
                ad_end_jd_this_ad = min(ad_start_jd_this_ad + (ad_proportional_duration_years * one_year_in_days),
                                        md_end_jd_current_md)
                if ad_end_jd_this_ad < ad_start_jd_this_ad: ad_end_jd_this_ad = ad_start_jd_this_ad
                ad_start_tuple_raw = jhora_utils.jd_to_gregorian(ad_start_jd_this_ad)
                ad_end_tuple_raw = jhora_utils.jd_to_gregorian(ad_end_jd_this_ad)
                all_periods_md_ad.append({
                    "md_rasi": const.rasi_names_en[md_rasi_index_current_cycle],
                    "ad_rasi": const.rasi_names_en[ad_rasi_index],
                    "start_date": f"{int(ad_start_tuple_raw[0]):04d}-{int(ad_start_tuple_raw[1]):02d}-{int(ad_start_tuple_raw[2]):02d}",
                    "end_date": f"{int(ad_end_tuple_raw[0]):04d}-{int(ad_end_tuple_raw[1]):02d}-{int(ad_end_tuple_raw[2]):02d}",
                })
                ad_start_date_obj = datetime.date(int(ad_start_tuple_raw[0]), int(ad_start_tuple_raw[1]),
                                                  int(ad_start_tuple_raw[2]))
                ad_end_date_obj = datetime.date(int(ad_end_tuple_raw[0]), int(ad_end_tuple_raw[1]),
                                                int(ad_end_tuple_raw[2]))
                if max(ad_start_date_obj, filter_start_date_obj) < min(ad_end_date_obj, filter_end_date_obj):
                    pd_proportional_duration_years = ad_proportional_duration_years / 12.0
                    if pd_proportional_duration_years <= 0:
                        current_ad_start_jd = ad_end_jd_this_ad;
                        continue
                    current_pd_start_jd = ad_start_jd_this_ad
                    try:
                        pd_start_progression_index = md_progression_rasis.index(ad_rasi_index)
                    except ValueError:
                        current_ad_start_jd = ad_end_jd_this_ad;
                        continue
                    for j in range(12):
                        if current_pd_start_jd >= ad_end_jd_this_ad: break
                        pd_rasi_index = md_progression_rasis[(pd_start_progression_index + j) % 12]
                        pd_start_jd_this_pd = current_pd_start_jd
                        pd_end_jd_this_pd = min(
                            pd_start_jd_this_pd + (pd_proportional_duration_years * one_year_in_days),
                            ad_end_jd_this_ad)
                        if pd_end_jd_this_pd < pd_start_jd_this_pd: pd_end_jd_this_pd = pd_start_jd_this_pd
                        pd_start_tuple_raw = jhora_utils.jd_to_gregorian(pd_start_jd_this_pd)
                        pd_end_tuple_raw = jhora_utils.jd_to_gregorian(pd_end_jd_this_pd)
                        pd_start_date_obj = datetime.date(int(pd_start_tuple_raw[0]), int(pd_start_tuple_raw[1]),
                                                          int(pd_start_tuple_raw[2]))
                        pd_end_date_obj = datetime.date(int(pd_end_tuple_raw[0]), int(pd_end_tuple_raw[1]),
                                                        int(pd_end_tuple_raw[2]))
                        if max(pd_start_date_obj, filter_start_date_obj) < min(pd_end_date_obj, filter_end_date_obj):
                            sd_proportional_duration_years = pd_proportional_duration_years / 12.0
                            if sd_proportional_duration_years <= 0:
                                current_pd_start_jd = pd_end_jd_this_pd;
                                continue
                            current_sd_start_jd = pd_start_jd_this_pd
                            try:
                                sd_start_progression_index = md_progression_rasis.index(pd_rasi_index)
                            except ValueError:
                                current_pd_start_jd = pd_end_jd_this_pd;
                                continue
                            for k in range(12):
                                if current_sd_start_jd >= pd_end_jd_this_pd: break
                                sd_rasi_index = md_progression_rasis[(sd_start_progression_index + k) % 12]
                                sd_start_jd_this_sd = current_sd_start_jd
                                sd_end_jd_this_sd = min(
                                    sd_start_jd_this_sd + (sd_proportional_duration_years * one_year_in_days),
                                    pd_end_jd_this_pd)
                                if sd_end_jd_this_sd < sd_start_jd_this_sd: sd_end_jd_this_sd = sd_start_jd_this_sd
                                sd_start_tuple_raw = jhora_utils.jd_to_gregorian(sd_start_jd_this_sd)
                                sd_end_tuple_raw = jhora_utils.jd_to_gregorian(sd_end_jd_this_sd)
                                sd_start_date_obj = datetime.date(int(sd_start_tuple_raw[0]),
                                                                  int(sd_start_tuple_raw[1]),
                                                                  int(sd_start_tuple_raw[2]))
                                sd_end_date_obj = datetime.date(int(sd_end_tuple_raw[0]), int(sd_end_tuple_raw[1]),
                                                                int(sd_end_tuple_raw[2]))
                                if max(sd_start_date_obj, filter_start_date_obj) < min(sd_end_date_obj,
                                                                                       filter_end_date_obj):
                                    all_periods_filtered_to_sd_level.append({
                                        "md_rasi": const.rasi_names_en[md_rasi_index_current_cycle],
                                        "ad_rasi": const.rasi_names_en[ad_rasi_index],
                                        "pd_rasi": const.rasi_names_en[pd_rasi_index],
                                        "sd_rasi": const.rasi_names_en[sd_rasi_index],
                                        "start_date": f"{int(sd_start_tuple_raw[0]):04d}-{int(sd_start_tuple_raw[1]):02d}-{int(sd_start_tuple_raw[2]):02d}",
                                        "end_date": f"{int(sd_end_tuple_raw[0]):04d}-{int(sd_end_tuple_raw[1]):02d}-{int(sd_end_tuple_raw[2]):02d}",
                                    })
                                current_sd_start_jd = sd_end_jd_this_sd
                        current_pd_start_jd = pd_end_jd_this_pd
                current_ad_start_jd = ad_end_jd_this_ad
            current_jd_for_mds = md_end_jd_current_md
            elapsed_total_years_for_mds += actual_md_run_duration_this_iteration
            if elapsed_total_years_for_mds >= total_years_to_calculate_md_ad: break
    return all_periods_md_ad, all_periods_filtered_to_sd_level


# --- Vimsottari Dasha Text Generation (for Nested JSON) ---
def generate_vimsottari_text_for_universal_parser(h_obj: Horoscope) -> str:  # (Content as before - condensed)
    text_lines = [];
    dasha_system_name = "Vimsottari Dasa";
    text_lines.append(f"{dasha_system_name}:");
    text_lines.append("Maha Dasas:")
    jd_dob = h_obj.julian_day
    mahadashas_dict = jhora_vimsottari_std.vimsottari_mahadasa(jd=jd_dob, place=h_obj.Place, dhasa_starting_planet=1)
    md_summary_lines = [];
    md_detailed_blocks = []
    sorted_md_lords = sorted(mahadashas_dict.keys(), key=lambda lord: mahadashas_dict[lord])
    for md_idx_loop, md_lord_idx in enumerate(sorted_md_lords):
        md_start_jd_val = mahadashas_dict[md_lord_idx]
        md_lord_name_full = PLANET_FULL_NAMES_LIST[md_lord_idx].capitalize()
        md_lord_name_short = PLANET_SHORT_NAMES_LIST[md_lord_idx]
        md_dur_years = jhora_vimsottari_std.vimsottari_dict[md_lord_idx]
        md_end_jd_val = md_start_jd_val + (md_dur_years * const.sidereal_year)
        md_start_str = _format_datetime_from_jd(md_start_jd_val);
        md_end_str = _format_datetime_from_jd(md_end_jd_val)
        md_summary_lines.append(f"  {md_lord_name_full}: {md_start_str} - {md_end_str}")
        current_md_block = [];
        current_md_block.append(f"{md_lord_name_short} MD: {md_start_str} - {md_end_str}");
        current_md_block.append(f"Antardasas in this MD:")
        antardashas_dict = jhora_vimsottari_std._vimsottari_bhukti(md_lord_idx, md_start_jd_val)
        sorted_ad_lords = sorted(antardashas_dict.keys(), key=lambda lord: antardashas_dict[lord])
        for ad_lord_idx in sorted_ad_lords:
            ad_start_jd_val = antardashas_dict[ad_lord_idx];
            ad_lord_name_short = PLANET_SHORT_NAMES_LIST[ad_lord_idx]
            ad_dur_prop_md = jhora_vimsottari_std.vimsottari_dict[ad_lord_idx]
            ad_dur_years = (ad_dur_prop_md * md_dur_years) / const.human_life_span_for_vimsottari_dhasa
            ad_end_jd_val = ad_start_jd_val + (ad_dur_years * const.sidereal_year)
            if md_idx_loop + 1 < len(sorted_md_lords):
                next_md_start_jd = mahadashas_dict[sorted_md_lords[md_idx_loop + 1]]; ad_end_jd_val = min(ad_end_jd_val,
                                                                                                          next_md_start_jd)
            else:
                ad_end_jd_val = min(ad_end_jd_val, md_end_jd_val)
            if ad_start_jd_val >= ad_end_jd_val: continue
            ad_start_str = _format_datetime_from_jd(ad_start_jd_val);
            ad_end_str = _format_datetime_from_jd(ad_end_jd_val)
            current_md_block.append(f"    {ad_lord_name_short} AD: {ad_start_str} - {ad_end_str}");
            current_md_block.append(f"    {ad_lord_name_short} AD: {ad_start_str} - {ad_end_str}");
            current_md_block.append(f"    Pratyantardasas in this AD:")
            pratyantardashas_dict = jhora_vimsottari_std._vimsottari_antara(md_lord_idx, ad_lord_idx, ad_start_jd_val)
            sorted_pd_lords = sorted(pratyantardashas_dict.keys(), key=lambda lord: pratyantardashas_dict[lord])
            for pd_lord_idx in sorted_pd_lords:
                pd_start_jd_val = pratyantardashas_dict[pd_lord_idx];
                pd_lord_name_short = PLANET_SHORT_NAMES_LIST[pd_lord_idx]
                pd_dur_prop_ad = jhora_vimsottari_std.vimsottari_dict[pd_lord_idx]
                pd_dur_years = (pd_dur_prop_ad * ad_dur_years) / const.human_life_span_for_vimsottari_dhasa
                pd_end_jd_val = pd_start_jd_val + (pd_dur_years * const.sidereal_year);
                pd_end_jd_val = min(pd_end_jd_val, ad_end_jd_val)
                if pd_start_jd_val >= pd_end_jd_val: continue
                pd_start_str = _format_datetime_from_jd(pd_start_jd_val);
                pd_end_str = _format_datetime_from_jd(pd_end_jd_val)
                current_md_block.append(f"        {pd_lord_name_short} PD: {pd_start_str} - {pd_end_str}");
                current_md_block.append(f"        {pd_lord_name_short} PD: {pd_start_str} - {pd_end_str}");
                current_md_block.append(f"        Sookshma-antardasas in this PD:")
                sookshmadashas_dict = {};
                current_sd_start_jd_val = pd_start_jd_val;
                sd_lord_iter = pd_lord_idx
                for _ in range(9):
                    sookshmadashas_dict[sd_lord_iter] = current_sd_start_jd_val
                    sd_dur_prop_pd = jhora_vimsottari_std.vimsottari_dict[sd_lord_iter]
                    sd_dur_years_iter = (sd_dur_prop_pd * pd_dur_years) / const.human_life_span_for_vimsottari_dhasa
                    current_sd_start_jd_val += (sd_dur_years_iter * const.sidereal_year);
                    sd_lord_iter = jhora_vimsottari_std.vimsottari_next_adhipati(sd_lord_iter)
                sorted_sd_lords = sorted(sookshmadashas_dict.keys(), key=lambda lord: sookshmadashas_dict[lord])
                for sd_lord_idx_val in sorted_sd_lords:
                    sd_start_jd_val_iter = sookshmadashas_dict[sd_lord_idx_val];
                    sd_lord_name_short_iter = PLANET_SHORT_NAMES_LIST[sd_lord_idx_val]
                    sd_dur_prop_pd_iter = jhora_vimsottari_std.vimsottari_dict[sd_lord_idx_val]
                    sd_dur_years_final = (
                                                     sd_dur_prop_pd_iter * pd_dur_years) / const.human_life_span_for_vimsottari_dhasa
                    sd_end_jd_val_iter = sd_start_jd_val_iter + (sd_dur_years_final * const.sidereal_year);
                    sd_end_jd_val_iter = min(sd_end_jd_val_iter, pd_end_jd_val)
                    if sd_start_jd_val_iter >= sd_end_jd_val_iter: continue
                    sd_start_str_iter = _format_datetime_from_jd(sd_start_jd_val_iter);
                    sd_end_str_iter = _format_datetime_from_jd(sd_end_jd_val_iter)
                    current_md_block.append(
                        f"            {sd_lord_name_short_iter} SD: {sd_start_str_iter} - {sd_end_str_iter}")
                current_md_block.append("")
            current_md_block.append("")
        md_detailed_blocks.extend(current_md_block);
        md_detailed_blocks.append("")
    text_lines.extend(md_summary_lines);
    text_lines.append("");
    text_lines.extend(md_detailed_blocks)
    return "\n".join(text_lines)


# --- Vimsottari Dasha Flat Outputs Generation ---
def create_flat_vimsottari_from_nested_json(nested_data: dict, birth_date_obj: datetime.date):
    vimsottari_md_ad_80yrs = []
    vimsottari_md_ad_pd_filtered = []
    vimsottari_md_ad_pd_sd_filtered = []

    # Define date windows
    end_date_80yrs = birth_date_obj + datetime.timedelta(days=80 * 365.25)
    today = datetime.date.today()
    filter_pd_start = today - datetime.timedelta(days=365)
    filter_pd_end = today + datetime.timedelta(days=3 * 365)
    filter_sd_start = today - datetime.timedelta(days=90)
    filter_sd_end = today + datetime.timedelta(days=365)

    for md_period in nested_data.get("dasas", []):
        md_lord = md_period.get("name")
        md_start_iso = md_period.get("start_datetime")
        md_end_iso = md_period.get("end_datetime")

        if not (md_lord and md_start_iso and md_end_iso): continue

        md_start_date_obj = datetime.datetime.fromisoformat(md_start_iso).date()
        md_end_date_obj = datetime.datetime.fromisoformat(md_end_iso).date()

        # Optimization for 80yr MD/AD
        if md_start_date_obj > end_date_80yrs and md_start_date_obj > filter_pd_end and md_start_date_obj > filter_sd_end: continue
        if md_end_date_obj < birth_date_obj and md_end_date_obj < filter_pd_start and md_end_date_obj < filter_sd_start: continue

        for ad_period in md_period.get("sub_periods", []):
            ad_lord = ad_period.get("name")
            ad_start_iso = ad_period.get("start_datetime")
            ad_end_iso = ad_period.get("end_datetime")

            if not (ad_lord and ad_start_iso and ad_end_iso): continue

            ad_start_date_obj = datetime.datetime.fromisoformat(ad_start_iso).date()
            ad_end_date_obj = datetime.datetime.fromisoformat(ad_end_iso).date()

            # File 1: MD/AD for 80 years
            if max(ad_start_date_obj, birth_date_obj) < min(ad_end_date_obj, end_date_80yrs):
                vimsottari_md_ad_80yrs.append({
                    "md_lord": md_lord,
                    "ad_lord": ad_lord,
                    "start_date": _format_date_from_iso_str(ad_start_iso),
                    "end_date": _format_date_from_iso_str(ad_end_iso),
                })

            # Optimization for PD/SD based on AD window
            if ad_end_date_obj < filter_pd_start and ad_end_date_obj < filter_sd_start: continue
            if ad_start_date_obj > filter_pd_end and ad_start_date_obj > filter_sd_end: continue

            for pd_period in ad_period.get("sub_periods", []):
                pd_lord = pd_period.get("name")
                pd_start_iso = pd_period.get("start_datetime")
                pd_end_iso = pd_period.get("end_datetime")

                if not (pd_lord and pd_start_iso and pd_end_iso): continue

                pd_start_date_obj = datetime.datetime.fromisoformat(pd_start_iso).date()
                pd_end_date_obj = datetime.datetime.fromisoformat(pd_end_iso).date()

                # File 2: MD/AD/PD for 1yr past, 3yrs future
                if max(pd_start_date_obj, filter_pd_start) < min(pd_end_date_obj, filter_pd_end):
                    vimsottari_md_ad_pd_filtered.append({
                        "md_lord": md_lord,
                        "ad_lord": ad_lord,
                        "pd_lord": pd_lord,
                        "start_date": _format_date_from_iso_str(pd_start_iso),
                        "end_date": _format_date_from_iso_str(pd_end_iso),
                    })

                # Optimization for SD based on PD window
                if pd_end_date_obj < filter_sd_start: continue
                if pd_start_date_obj > filter_sd_end: continue

                for sd_period in pd_period.get("sub_periods", []):
                    sd_lord = sd_period.get("name")
                    sd_start_iso = sd_period.get("start_datetime")
                    sd_end_iso = sd_period.get("end_datetime")

                    if not (sd_lord and sd_start_iso and sd_end_iso): continue

                    sd_start_date_obj = datetime.datetime.fromisoformat(sd_start_iso).date()
                    sd_end_date_obj = datetime.datetime.fromisoformat(sd_end_iso).date()

                    # File 3: MD/AD/PD/SD for 3mo past, 1yr future
                    if max(sd_start_date_obj, filter_sd_start) < min(sd_end_date_obj, filter_sd_end):
                        vimsottari_md_ad_pd_sd_filtered.append({
                            "md_lord": md_lord,
                            "ad_lord": ad_lord,
                            "pd_lord": pd_lord,
                            "sd_lord": sd_lord,
                            "start_date": _format_date_from_iso_str(sd_start_iso),
                            "end_date": _format_date_from_iso_str(sd_end_iso),
                        })

    return vimsottari_md_ad_80yrs, vimsottari_md_ad_pd_filtered, vimsottari_md_ad_pd_sd_filtered


# --- Universal Dasha Parser Logic ---
def _parse_datetime_universal(date_str_with_time: str) -> str:  # (Content as before - condensed)
    try:
        dt = datetime.datetime.strptime(date_str_with_time, "%Y-%m-%d %H:%M:%S"); return dt.isoformat()
    except ValueError:
        try:
            dt = datetime.datetime.strptime(date_str_with_time, "%Y-%m-%d"); return dt.isoformat()
        except ValueError:
            return date_str_with_time


def _expand_name_universal(name_short: str, dasha_system_name: str) -> str:  # (Content as before)
    return ZODIAC_MAP_UNIVERSAL.get(name_short.strip(), name_short.strip())


def parse_dasha_text_content(text_content: str, person_name: str,
                             dasha_system_source_id: str) -> dict:  # (Content as before - condensed)
    lines = text_content.splitlines();
    parsed_data = {"person_name": person_name, "dasha_system_name": "", "source_file": dasha_system_source_id,
                   "dasas": []}
    dasha_system_header_pattern = re.compile(r"^\s*([A-Za-z0-9\s\(\)\-\._':]+? Dasa(?: \([^)]+\))?):")
    period_line_regex = re.compile(
        r"^(?P<indent>\s*)(?P<name>[A-Za-z0-9\s]+?)\s*(?P<type>MD|AD|PD|SD)?:\s*(?P<start_date>\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2})\s*-\s*(?P<end_date>\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2})")
    summary_period_line_regex = re.compile(
        r"^\s*(?P<name>[A-Za-z0-9\s]+?):\s*(?P<start_date>\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2})\s*-\s*(?P<end_date>\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2})")
    sub_period_section_headers = {"Antardasas in this MD:": ("Antardasha", 2),
                                  "Pratyantardasas in this AD:": ("Pratyantardasha", 3),
                                  "Sookshma-antardasas in this PD:": ("Sookshma-antardasha", 4)}
    context_stack = [];
    current_dasha_system_name = "Unknown Dasa"
    for line in lines:
        match_ds_header = dasha_system_header_pattern.match(line.strip())
        if match_ds_header: current_dasha_system_name = match_ds_header.group(1).strip(); parsed_data[
            "dasha_system_name"] = current_dasha_system_name; break
    is_in_summary_block = False
    for line_num, line_content in enumerate(lines):
        stripped_line = line_content.strip()
        if not stripped_line: continue
        if stripped_line == "Maha Dasas:": is_in_summary_block = True; continue
        if stripped_line in sub_period_section_headers: is_in_summary_block = False; continue
        match = period_line_regex.match(line_content)
        if match:
            is_in_summary_block = False;
            data = match.groupdict();
            name_short = data['name'].strip();
            period_type_from_line = data['type']
            level = 0;
            period_type_str = ""
            if period_type_from_line == "MD":
                level = 1; period_type_str = "Mahadasha"
            elif period_type_from_line == "AD":
                level = 2; period_type_str = "Antardasha"
            elif period_type_from_line == "PD":
                level = 3; period_type_str = "Pratyantardasha"
            elif period_type_from_line == "SD":
                level = 4; period_type_str = "Sookshma-antardasha"
            else:
                continue
            period_obj = {"level": level, "period_type": period_type_str,
                          "name": _expand_name_universal(name_short, current_dasha_system_name),
                          "start_datetime": _parse_datetime_universal(data['start_date']),
                          "end_datetime": _parse_datetime_universal(data['end_date']), "sub_periods": []}
            while context_stack and level <= context_stack[-1]['level']: context_stack.pop()
            if not context_stack:
                if level == 1: parsed_data["dasas"].append(period_obj); context_stack.append(period_obj)
            else:
                parent_period = context_stack[-1]
                if level == parent_period['level'] + 1: parent_period["sub_periods"].append(
                    period_obj); context_stack.append(period_obj)
            continue
        if is_in_summary_block:
            match_summary = summary_period_line_regex.match(stripped_line)
            if match_summary: pass
            continue
    return parsed_data


# --- Main Execution Logic ---
def main():
    print("--- PyJHora Data Extractor (Nested Dasha Parser Mode) ---")
    current_birth_data = get_abhijeet_birth_data()
    h: Horoscope | None = None
    d1_planet_positions: list | None = None
    try:
        drik_birth_date_obj = drik.Date(year=current_birth_data.date_of_birth.year,
                                        month=current_birth_data.date_of_birth.month,
                                        day=current_birth_data.date_of_birth.day)
        h = Horoscope(date_in=drik_birth_date_obj, birth_time=current_birth_data.tob_str,
                      latitude=current_birth_data.latitude, longitude=current_birth_data.longitude,
                      timezone_offset=current_birth_data.timezone_offset, ayanamsa_mode=DEFAULT_AYANAMSA_MODE)
    except Exception as e:
        print(f"ERROR during Horoscope setup: {e}"); traceback.print_exc(); return
    if not h: return

    person_dir_name_safe = current_birth_data.name.replace(" ", "_")
    time_suffix = current_birth_data.time_of_birth.strftime("%H%M")
    person_folder_name = f"{person_dir_name_safe}_{time_suffix}"
    full_output_path = OUTPUT_BASE_PATH / person_folder_name
    try:
        full_output_path.mkdir(parents=True, exist_ok=True)
    except OSError as oe:
        print(f"ERROR: Could not create output directory {full_output_path}: {oe}"); return

    original_slug_name = current_birth_data.name.lower().replace(" ", "_").replace("-", "_")
    file_prefix_knrao = full_output_path / f"{original_slug_name}_{time_suffix}"
    file_prefix_vimsottari = full_output_path / f"{current_birth_data.name.replace(' ', '_')}"

    # --- K.N. Rao Chara Dasha Calculation (Flat JSONs) ---
    try:
        d1_planet_positions = jhora_charts.rasi_chart(jd_at_dob=h.julian_day, place_as_tuple=h.Place,
                                                      ayanamsa_mode=h.ayanamsa_mode)
    except Exception as e:
        print(f"ERROR: Could not get D1 Rasi chart: {e}")

    if h and d1_planet_positions:
        try:
            knr_md_ad_80yrs, knr_filtered_to_sd = extract_kn_rao_chara_dasha_detailed(h, d1_planet_positions,
                                                                                      current_birth_data.date_of_birth)
            filepath_knr_md_ad = file_prefix_knrao.with_name(
                f"{file_prefix_knrao.name}_dasha_KN_Rao_Chara_MD_AD_80yrs.json")
            with open(filepath_knr_md_ad, 'w', encoding='utf-8') as f:
                json.dump(knr_md_ad_80yrs, f, indent=2, ensure_ascii=False)
            filepath_knr_filtered_sd = file_prefix_knrao.with_name(
                f"{file_prefix_knrao.name}_dasha_KN_Rao_Chara_MD_AD_PD_SD_filtered.json")
            with open(filepath_knr_filtered_sd, 'w', encoding='utf-8') as f:
                json.dump(knr_filtered_to_sd, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"ERROR K.N. Rao Chara Dasha (flat): {e}"); traceback.print_exc()

    # --- Vimsottari Dasha ---
    if h:
        # 1. Nested JSON (existing logic)
        print("\nGenerating Vimsottari Dasha text for universal parser (Nested JSON)...")
        vimsottari_text_generated = generate_vimsottari_text_for_universal_parser(h)
        debug_text_filepath = file_prefix_vimsottari.with_name(
            f"{file_prefix_vimsottari.name}-Vimsottari_GeneratedText.txt")
        try:
            with open(debug_text_filepath, 'w', encoding='utf-8') as f:
                f.write(vimsottari_text_generated)
            print(f"Saved Vimsottari generated text to: {debug_text_filepath}")
        except Exception as e:
            print(f"Warning: Could not save debug Vimsottari text: {e}")

        nested_vimsottari_json_data = None
        if "Error during generation." not in vimsottari_text_generated:
            print("Parsing Vimsottari Dasha text into nested JSON...")
            nested_vimsottari_json_data = parse_dasha_text_content(vimsottari_text_generated, current_birth_data.name,
                                                                   "Vimsottari Dasa (Generated from PyJHora)")
            filepath_vimsottari_nested = file_prefix_vimsottari.with_name(
                f"{file_prefix_vimsottari.name}-VimsottariDasa_Nested.json")
            try:
                with open(filepath_vimsottari_nested, 'w', encoding='utf-8') as f:
                    json.dump(nested_vimsottari_json_data, f, indent=2, ensure_ascii=False)
                print(f"Saved Vimsottari Dasha (Nested JSON) to: {filepath_vimsottari_nested}")
            except Exception as e:
                print(f"ERROR saving Vimsottari Nested JSON: {e}"); traceback.print_exc()
        else:
            print("Skipping Vimsottari Nested JSON due to generation error.")

        # 2. Custom Flat JSON Outputs (from the nested data if available)
        if nested_vimsottari_json_data and nested_vimsottari_json_data.get("dasas"):
            print("\nGenerating Vimsottari Dasha custom flat outputs from nested data...")
            try:
                vim_md_ad_80, vim_md_ad_pd_filt, vim_md_ad_pd_sd_filt = \
                    create_flat_vimsottari_from_nested_json(nested_vimsottari_json_data,
                                                            current_birth_data.date_of_birth)

                filepath_vim_md_ad = file_prefix_vimsottari.with_name(
                    f"{file_prefix_vimsottari.name}-Vimsottari_MD_AD_80yrs.json")
                with open(filepath_vim_md_ad, 'w', encoding='utf-8') as f:
                    json.dump(vim_md_ad_80, f, indent=2, ensure_ascii=False)
                print(f"Saved Vimsottari (MD/AD 80yrs) to: {filepath_vim_md_ad}")

                filepath_vim_md_ad_pd = file_prefix_vimsottari.with_name(
                    f"{file_prefix_vimsottari.name}-Vimsottari_MD_AD_PD_filtered.json")
                with open(filepath_vim_md_ad_pd, 'w', encoding='utf-8') as f:
                    json.dump(vim_md_ad_pd_filt, f, indent=2, ensure_ascii=False)
                print(f"Saved Vimsottari (MD/AD/PD Filtered) to: {filepath_vim_md_ad_pd}")

                filepath_vim_md_ad_pd_sd = file_prefix_vimsottari.with_name(
                    f"{file_prefix_vimsottari.name}-Vimsottari_MD_AD_PD_SD_filtered.json")
                with open(filepath_vim_md_ad_pd_sd, 'w', encoding='utf-8') as f:
                    json.dump(vim_md_ad_pd_sd_filt, f, indent=2, ensure_ascii=False)
                print(f"Saved Vimsottari (MD/AD/PD/SD Filtered) to: {filepath_vim_md_ad_pd_sd}")

            except Exception as e:
                print(f"ERROR Vimsottari custom flat outputs: {e}"); traceback.print_exc()
        else:
            print("Skipping Vimsottari custom flat outputs as nested data was not available/generated.")

    print("\n--- Processing Complete ---")


if __name__ == "__main__":
    main()