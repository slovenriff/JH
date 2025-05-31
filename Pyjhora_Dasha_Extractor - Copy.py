# Pyjhora_Dasha_Extractor.py

import datetime
import traceback
import os
import json
from dataclasses import dataclass, asdict
from pathlib import Path
import re
from typing import List, Dict, Tuple, Optional
import time

# --- External Libraries ---
try:
    from geopy.geocoders import Nominatim
    from geopy.exc import GeocoderTimedOut, GeocoderUnavailable, GeocoderServiceError
    from timezonefinder import TimezoneFinder
    import pytz
except ImportError:
    print("ERROR: Install geopy, timezonefinder, pytz");
    exit()

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
    print(f"FATAL ERROR: PyJHora import failed: {e}");
    exit()

# --- Configuration ---
DEFAULT_AYANAMSA_MODE = "LAHIRI"
OUTPUT_BASE_PATH = Path("./Kundali")
JATAK_FILE_PATH = Path("./Jatak.txt")
GEOCODER_USER_AGENT = "PyjhoraDashaExtractor/1.1"  # Increment version

ZODIAC_MAP_UNIVERSAL = {  # ... (as before) ...
    "Ar": "Aries", "Ta": "Taurus", "Ge": "Gemini", "Cn": "Cancer",
    "Le": "Leo", "Vi": "Virgo", "Li": "Libra", "Sc": "Scorpio",
    "Sg": "Sagittarius", "Cp": "Capricorn", "Aq": "Aquarius", "Pi": "Pisces",
    "Sun": "Sun", "Moon": "Moon", "Mars": "Mars", "Merc": "Mercury", "Mer": "Mercury",
    "Jup": "Jupiter", "Ven": "Venus", "Sat": "Saturn",
    "Rah": "Rahu", "Ket": "Ketu"
}
PLANET_FULL_NAMES_LIST, PLANET_SHORT_NAMES_LIST = None, None
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
if not (PLANET_FULL_NAMES_LIST and PLANET_SHORT_NAMES_LIST and isinstance(PLANET_FULL_NAMES_LIST, list) and len(
        PLANET_FULL_NAMES_LIST) >= 9 and isinstance(PLANET_SHORT_NAMES_LIST, list) and len(
        PLANET_SHORT_NAMES_LIST) >= 9):
    print("WARNING: PyJHora planet name lists not found or incomplete. Using fallback.")
    PLANET_FULL_NAMES_LIST = ['Sun', 'Moon', 'Mars', 'Mercury', 'Jupiter', 'Venus', 'Saturn', 'Rahu', 'Ketu']
    PLANET_SHORT_NAMES_LIST = ["Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa", "Ra", "Ke"]
print("INFO: Using planet name lists for ZODIAC_MAP_UNIVERSAL population.")  # Moved print outside if/else
common_len_names = min(len(PLANET_FULL_NAMES_LIST or []), len(PLANET_SHORT_NAMES_LIST or []))  # Handle None
common_len_names = min(common_len_names, 9)
for i in range(common_len_names):
    short, full = PLANET_SHORT_NAMES_LIST[i], PLANET_FULL_NAMES_LIST[i]
    if isinstance(full, str): full = full.capitalize()
    if short not in ZODIAC_MAP_UNIVERSAL: ZODIAC_MAP_UNIVERSAL[short] = full


# --- BirthData Dataclass ---
@dataclass
class BirthData:
    name: str
    date_of_birth: datetime.date
    time_of_birth: datetime.time
    latitude: float
    longitude: float
    timezone_offset: float
    city_name: Optional[str] = None
    country_name: Optional[str] = None
    gender: str = "neutral"
    raw_place_string: Optional[str] = None
    geocoding_success: bool = False
    iana_timezone_name: Optional[str] = None  # Added to store IANA timezone

    @property
    def tob_str(self) -> str: return self.time_of_birth.strftime("%H:%M:%S")

    @property
    def dob_str(self) -> str: return self.date_of_birth.strftime("%Y-%m-%d")


# --- Helper functions ---
def _format_datetime_from_jd(jd_val: float) -> str:
    # This is the corrected version that handles fractional hours from jd_to_gregorian
    greg_date_tuple = jhora_utils.jd_to_gregorian(jd_val)
    if not isinstance(greg_date_tuple, (list, tuple)) or len(greg_date_tuple) < 4:
        print(
            f"ERROR (_format_datetime_from_jd): jd_to_gregorian({jd_val}) returned unexpected value: {greg_date_tuple}")
        return "0000-00-00 00:00:00"
    year, month, day = int(greg_date_tuple[0]), int(greg_date_tuple[1]), int(greg_date_tuple[2])
    fractional_hour = greg_date_tuple[3]
    hour = int(fractional_hour)
    minute_fraction = (fractional_hour - hour) * 60
    minute = int(minute_fraction)
    second_fraction = (minute_fraction - minute) * 60
    second = int(round(second_fraction))
    if second >= 60: second = 0; minute += 1
    if minute >= 60: minute = 0; hour += 1
    if hour >= 24: hour = 0  # Or handle day increment if PyJHora guarantees JD always refers to a specific Gregorian day start
    return f"{year:04d}-{month:02d}-{day:02d} {hour:02d}:{minute:02d}:{second:02d}"


def _parse_datetime_universal(date_str_with_time: str) -> str:
    # (Full function as previously provided)
    try:
        dt = datetime.datetime.strptime(date_str_with_time, "%Y-%m-%d %H:%M:%S"); return dt.isoformat()
    except ValueError:
        try:
            dt = datetime.datetime.strptime(date_str_with_time, "%Y-%m-%d"); return dt.isoformat()
        except ValueError:
            return date_str_with_time


def _expand_name_universal(name_short: str, dasha_system_name: str) -> str:
    # (Full function as previously provided)
    return ZODIAC_MAP_UNIVERSAL.get(name_short.strip(), name_short.strip())


# --- Jatak.txt Parsing and Geocoding (Full Functions) ---
def parse_jatak_txt(file_path: Path) -> List[Dict[str, str]]:
    # (Full function as previously provided)
    raw_records = []
    if not file_path.is_file():
        print(f"ERROR: Jatak.txt not found at {file_path}");
        return raw_records
    with open(file_path, 'r', encoding='utf-8') as f:
        current_record = {}
        for line_content in f:
            line = line_content.strip()
            if not line:
                if current_record: raw_records.append(current_record); current_record = {}
                continue
            parts = line.split(':', 1)
            if len(parts) == 2: key, value = parts[0].strip(), parts[1].strip(); current_record[key] = value
        if current_record: raw_records.append(current_record)
    return raw_records


def geocode_and_enrich_place(place_str: str, dob: datetime.date, tob: datetime.time) -> \
        Tuple[Optional[float], Optional[float], Optional[float], Optional[str], Optional[str], Optional[str]]:
    # (Full function as previously provided, modified to use dob/tob for historical TZ offset)
    if not place_str: return None, None, None, None, None, None
    geolocator = Nominatim(user_agent=GEOCODER_USER_AGENT, timeout=10)
    tf = TimezoneFinder()
    lat, lon, tz_offset, city, country, iana_tz_name = None, None, None, None, None, None
    try:
        print(f"      Geocoding '{place_str}'...")
        location = geolocator.geocode(place_str, language='en', addressdetails=True)
        time.sleep(1.1)
        if location and location.latitude is not None and location.longitude is not None:
            lat, lon = location.latitude, location.longitude
            raw_address = location.raw.get('address', {})
            city = raw_address.get('city', raw_address.get('town', raw_address.get('village', raw_address.get('county',
                                                                                                              place_str.split(
                                                                                                                  ',')[
                                                                                                                  0].strip()))))
            country = raw_address.get('country', "Unknown")
            iana_tz_name = tf.timezone_at(lng=lon, lat=lat)
            if iana_tz_name:
                try:
                    timezone_obj = pytz.timezone(iana_tz_name)
                    # Combine date and time for accurate historical offset
                    birth_dt_naive = datetime.datetime.combine(dob, tob)
                    birth_dt_aware = timezone_obj.localize(birth_dt_naive, is_dst=None)  # is_dst=None handles ambiguity
                    offset_timedelta = birth_dt_aware.utcoffset()
                    if offset_timedelta:
                        tz_offset = offset_timedelta.total_seconds() / 3600.0
                    else:
                        print(f"    WARNING: Could not get UTC offset for timezone '{iana_tz_name}'.")
                except pytz.exceptions.UnknownTimeZoneError:
                    print(f"    WARNING: pytz could not find '{iana_tz_name}'.")
                except Exception as e_pytz:
                    print(f"    ERROR getting TZ offset for {iana_tz_name}: {e_pytz}.")
            else:
                print(f"    WARNING: IANA Timezone not found for {place_str} (lat:{lat},lon:{lon}).")
        else:
            print(f"    WARNING: Geocoding failed for '{place_str}'.")
    except GeocoderTimedOut:
        print(f"    ERROR: Geocoding timed out for '{place_str}'.")
    except GeocoderUnavailable:
        print(f"    ERROR: Geocoding unavailable for '{place_str}'.")
    except GeocoderServiceError as e:
        print(f"    ERROR: Geocoding service error for '{place_str}': {e}")
    except Exception as e:
        print(f"    ERROR geocoding '{place_str}': {e}"); traceback.print_exc()
    if not city and place_str: city = place_str.split(',')[0].strip()
    if not country and place_str and len(place_str.split(',')) > 1: country = place_str.split(',')[-1].strip()
    return lat, lon, tz_offset, city, country, iana_tz_name


def process_raw_entries_to_birthdata(raw_entries: List[Dict[str, str]]) -> List[BirthData]:
    # (Full function as previously provided, calls the modified geocode_and_enrich_place)
    birth_data_list = []
    for i, entry in enumerate(raw_entries):
        print(f"\nProcessing Jatak Record {i + 1}/{len(raw_entries)}: {entry.get('Name', 'Unknown Name')}")
        name, date_str, time_str, place_str = entry.get("Name"), entry.get("Date"), entry.get("Time"), entry.get(
            "Place")
        if not (name and date_str and time_str and place_str):
            print(f"    WARNING: Skipping record for '{name or 'Unknown'}' due to missing essential fields.");
            continue
        try:
            dob = datetime.datetime.strptime(date_str, "%B %d, %Y").date()
            tob = datetime.datetime.strptime(time_str, "%H:%M:%S").time()
        except ValueError as e:
            print(f"    ERROR: Parse date/time for {name} ('{date_str}','{time_str}'): {e}. Skip.");
            continue
        lat, lon, tz_offset, city, country, iana_tz_name = geocode_and_enrich_place(place_str, dob, tob)
        if lat is None or lon is None or tz_offset is None:
            # Fallback for India as discussed
            if country and "india" in country.lower() and tz_offset is None:
                print("    INFO: Using default timezone +5.5 for India as a fallback for failed TZ lookup.")
                tz_offset = 5.5
                if not iana_tz_name: iana_tz_name = "Asia/Kolkata (Assumed)"
            else:
                print(f"    CRITICAL: Geocoding/TZ failed for {name} at '{place_str}'. Skipping.")
                continue

        bd = BirthData(name=name, date_of_birth=dob, time_of_birth=tob, latitude=lat, longitude=lon,
                       timezone_offset=tz_offset, city_name=city, country_name=country,
                       raw_place_string=place_str, geocoding_success=True,
                       iana_timezone_name=iana_tz_name)  # Store IANA TZ
        birth_data_list.append(bd)
        print(
            f"    Enriched: {name}, Lat:{lat:.4f},Lon:{lon:.4f},TZ Offset:{tz_offset},City:'{city}',Country:'{country}',IANA TZ:'{iana_tz_name}'")
    return birth_data_list


# --- K.N. Rao Chara Dasha: Placeholder for Master Nested JSON Generation ---
def generate_knrao_chara_master_nested_json(h_obj: Horoscope, d1_chart_positions: list, birth_data: BirthData, birth_params_for_json: Dict) -> Dict:
    # (Full function definition will be placed here later. For now, the STUB is fine)
    print(f"    NOTICE: K.N. Rao Chara Dasha to Master Nested JSON is a STUB/TODO for {birth_data.name}.")
    return {
        "person_name": birth_data.name,
        "birth_parameters_used": asdict(birth_data),  # Store entire enriched BirthData
        "dasha_system_name": "K.N. Rao Chara Dasa (Master - STUB)",
        "source_file": f"K.N. Rao Chara Dasa Master (PyJHora - {birth_data.name})",
        "dasas": []
    }


# --- Vimsottari Dasha Text Generation (for Nested JSON) (FULL VERSION) ---
def generate_vimsottari_text_for_universal_parser(h_obj: Horoscope) -> str:
    # (This is the FULL, working version of this function from our previous successful script)
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


# --- Universal Dasha Parser Logic (FULL VERSION) ---
def parse_dasha_text_content(text_content: str, person_name: str,
                             dasha_system_source_id: str,
                             birth_params: Optional[Dict] = None) -> dict:
    # (This is the FULL, working version of this function from our previous successful script)
    lines = [line.strip() for line in text_content.splitlines()]
    parsed_data = {"person_name": person_name,
                   "birth_parameters_used": birth_params or {},
                   "dasha_system_name": "Unknown Dasha System",
                   "source_file": dasha_system_source_id, "dasas": []}
    dasha_system_header_pattern = re.compile(r"^\s*([A-Za-z0-9\s\(\)\-\._':]+? Dasa(?: \([^)]+\))?):")
    period_line_regex = re.compile(
        r"^(?P<indent>\s*)(?P<name>[A-Za-z0-9\s]+?)\s*(?P<type>MD|AD|PD|SD)?:\s*(?P<start_date>\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2})\s*-\s*(?P<end_date>\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2})")
    summary_period_line_regex = re.compile(
        r"^\s*(?P<name>[A-Za-z0-9\s]+?):\s*(?P<start_date>\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2})\s*-\s*(?P<end_date>\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2})")
    sub_period_section_headers = {"Antardasas in this MD:": ("Antardasha", 2),
                                  "Pratyantardasas in this AD:": ("Pratyantardasha", 3),
                                  "Sookshma-antardasas in this PD:": ("Sookshma-antardasha", 4)}
    context_stack = [];
    current_dasha_system_name = "Unknown Dasa";
    first_dasha_system_header_found = False
    for line in lines:  # First pass for Dasha System Name
        if not first_dasha_system_header_found:
            match_ds_header = dasha_system_header_pattern.match(line)
            if match_ds_header: current_dasha_system_name = match_ds_header.group(1).strip(); parsed_data[
                "dasha_system_name"] = current_dasha_system_name; first_dasha_system_header_found = True; break
    if not first_dasha_system_header_found and "Vimsottari" in dasha_system_source_id: parsed_data[
        "dasha_system_name"] = "Vimsottari Dasa"  # Fallback for Vimsottari

    is_in_summary_block = False
    for line_num, line_content in enumerate(lines):
        stripped_line = line_content.strip()
        if not stripped_line: continue
        if not first_dasha_system_header_found and dasha_system_header_pattern.match(
            stripped_line): continue  # Skip if already processed
        if stripped_line == "Maha Dasas:": is_in_summary_block = True; context_stack = []; continue  # Reset stack for MD summary
        if stripped_line in sub_period_section_headers: is_in_summary_block = False; continue  # Header lines handled by context

        match = period_line_regex.match(line_content)  # For detailed lines "Planet TYPE: ..."
        match_summary = None
        if not match and is_in_summary_block:  # For summary lines "Planet: ..."
            match_summary = summary_period_line_regex.match(stripped_line)

        if match or match_summary:
            data = match.groupdict() if match else match_summary.groupdict()
            name_short = data['name'].strip()
            period_type_from_line = data.get('type')  # Will be None for summary_match
            level, period_type_str = 0, ""

            if period_type_from_line == "MD" or (is_in_summary_block and not period_type_from_line):
                level, period_type_str = 1, "Mahadasha"
            elif period_type_from_line == "AD":
                level, period_type_str = 2, "Antardasha"
            elif period_type_from_line == "PD":
                level, period_type_str = 3, "Pratyantardasha"
            elif period_type_from_line == "SD":
                level, period_type_str = 4, "Sookshma-antardasha"
            else:
                continue  # Should not happen with correct text or implies non-dasha line

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
            if level == 1: is_in_summary_block = False  # Exit summary block once first detailed MD (or MD item) is processed
            continue
    return parsed_data


# --- Main Execution Logic ---
def main():
    print("--- PyJHora Data Extractor (Multi-Jatak & Master Nested Dasha Focus) ---")
    raw_jatak_entries = parse_jatak_txt(JATAK_FILE_PATH)
    if not raw_jatak_entries: print("No records in Jatak.txt. Exiting."); return
    all_birth_data = process_raw_entries_to_birthdata(raw_jatak_entries)
    if not all_birth_data: print("No birth data processed after geocoding. Exiting."); return

    for current_birth_data in all_birth_data:
        print(f"\n\n--- Processing Dasha for: {current_birth_data.name} ---")
        h: Optional[Horoscope] = None

        birth_params_for_json = {
            "date_of_birth": current_birth_data.dob_str,
            "time_of_birth": current_birth_data.tob_str,
            "latitude": current_birth_data.latitude,
            "longitude": current_birth_data.longitude,
            "timezone_offset": current_birth_data.timezone_offset,
            "raw_place_string": current_birth_data.raw_place_string,
            "iana_timezone_name": current_birth_data.iana_timezone_name,
            "ayanamsa_mode": DEFAULT_AYANAMSA_MODE
        }
        try:
            drik_birth_date_obj = drik.Date(year=current_birth_data.date_of_birth.year,
                                            month=current_birth_data.date_of_birth.month,
                                            day=current_birth_data.date_of_birth.day)
            h = Horoscope(date_in=drik_birth_date_obj, birth_time=current_birth_data.tob_str,
                          latitude=current_birth_data.latitude, longitude=current_birth_data.longitude,
                          timezone_offset=current_birth_data.timezone_offset, ayanamsa_mode=DEFAULT_AYANAMSA_MODE)
            birth_params_for_json["ayanamsa_mode"] = h.ayanamsa_mode
        except Exception as e:
            print(f"    ERROR Horoscope setup for {current_birth_data.name}: {e}"); traceback.print_exc(); continue
        if not h: continue

        person_dir_name_safe = current_birth_data.name.replace(" ", "_").replace(".", "")
        time_suffix_folder = current_birth_data.time_of_birth.strftime("%H%M")  # HHMM for folder
        person_folder_name = f"{person_dir_name_safe}_{time_suffix_folder}"
        full_output_path = OUTPUT_BASE_PATH / person_folder_name
        try:
            full_output_path.mkdir(parents=True, exist_ok=True)
        except OSError as oe:
            print(f"    ERROR creating output directory {full_output_path}: {oe}"); continue

        geo_info_path = full_output_path / f"{person_dir_name_safe}_GeoTimeZone_Info.txt"
        try:
            with open(geo_info_path, 'w', encoding='utf-8') as f_geo:  # Write Geo Info
                f_geo.write(f"Geo and Timezone Information for: {current_birth_data.name}\n" + \
                            f"Raw Place String: {current_birth_data.raw_place_string}\n" + \
                            f"Determined City: {current_birth_data.city_name}\n" + \
                            f"Determined Country: {current_birth_data.country_name}\n" + \
                            f"Determined Latitude: {current_birth_data.latitude}\n" + \
                            f"Determined Longitude: {current_birth_data.longitude}\n" + \
                            f"Determined IANA Timezone: {current_birth_data.iana_timezone_name}\n" + \
                            f"Determined Timezone Offset (hours from UTC): {current_birth_data.timezone_offset}\n" + \
                            f"Geocoding Success: {current_birth_data.geocoding_success}\n")
            print(f"    Saved Geo/Timezone Info to: {geo_info_path}")
        except Exception as e:
            print(f"    ERROR saving Geo/Timezone Info for {current_birth_data.name}: {e}")

        # --- Master Nested K.N. Rao Chara Dasha ---
        print(f"    Generating Master Nested K.N. Rao Chara Dasha for {current_birth_data.name}...")
        d1_positions: Optional[List] = None
        try:
            d1_positions = jhora_charts.rasi_chart(jd_at_dob=h.julian_day, place_as_tuple=h.Place,
                                                   ayanamsa_mode=h.ayanamsa_mode)
        except Exception as e:
            print(f"    ERROR getting D1 chart for KNRao for {current_birth_data.name}: {e}")

        if d1_positions:
            master_knrao_nested_data = generate_knrao_chara_master_nested_json(h, d1_positions, current_birth_data,
                                                                               birth_params_for_json)
            master_knrao_filepath = full_output_path / f"{person_dir_name_safe}-KNRaoCharaDasa-Master_Nested.json"
            try:
                with open(master_knrao_filepath, 'w', encoding='utf-8') as f:
                    json.dump(master_knrao_nested_data, f, indent=2, ensure_ascii=False)
                print(f"    Saved Master Nested K.N. Rao Chara Dasha to: {master_knrao_filepath} (Currently STUB)")
            except Exception as e:
                print(f"    ERROR saving Master KNRao JSON for {current_birth_data.name}: {e}")
        else:
            print(f"    Skipping K.N. Rao Chara Dasha for {current_birth_data.name} (D1 chart error).")

        # --- Master Nested Vimsottari Dasha ---
        print(f"    Generating Master Nested Vimsottari Dasha for {current_birth_data.name}...")
        vimsottari_text_generated = generate_vimsottari_text_for_universal_parser(h)
        if "Error during generation." not in vimsottari_text_generated:
            master_vimsottari_nested_data = parse_dasha_text_content(
                vimsottari_text_generated, current_birth_data.name,
                f"Vimsottari Dasa Master (PyJHora - {current_birth_data.name})",
                birth_params=birth_params_for_json
            )
            master_vimsottari_filepath = full_output_path / f"{person_dir_name_safe}-VimsottariDasa-Master_Nested.json"
            try:
                with open(master_vimsottari_filepath, 'w', encoding='utf-8') as f:
                    json.dump(master_vimsottari_nested_data, f, indent=2, ensure_ascii=False)
                print(f"    Saved Master Nested Vimsottari Dasha to: {master_vimsottari_filepath}")
            except Exception as e:
                print(f"    ERROR saving Master Vimsottari JSON for {current_birth_data.name}: {e}")
        else:
            print(f"    Skipping Master Nested Vimsottari for {current_birth_data.name} due to generation error.")
    print("\n--- Master Nested Dasha Generation Complete ---")


if __name__ == "__main__":
    main()