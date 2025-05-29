# Pyjhora_Dasha_Extractor.py

import datetime
import traceback
import os
import json
from dataclasses import dataclass, asdict
from pathlib import Path
import re
from typing import List, Dict, Tuple, Optional, Any
import time
import pprint  # For pretty printing raw data to text files

# --- External Libraries ---
try:
    from geopy.geocoders import Nominatim
    from geopy.exc import GeocoderTimedOut, GeocoderUnavailable, GeocoderServiceError
    from timezonefinder import TimezoneFinder
    import pytz
except ImportError:
    print("ERROR: Required libraries not found. Please install them: pip install geopy timezonefinder pytz")
    exit()

# --- PyJHora Core Imports ---
# Structure based on the provided JHora_Structure.txt
try:
    from jhora.horoscope.main import Horoscope
    from jhora.panchanga import drik
    from jhora import const
    from jhora import utils as jhora_utils

    # Chart related
    from jhora.horoscope.chart import charts as jhora_charts
    from jhora.horoscope.chart import house as jhora_house
    from jhora.horoscope.chart import arudhas as jhora_arudhas
    from jhora.horoscope.chart import ashtakavarga as jhora_ashtakavarga
    from jhora.horoscope.chart import strength as jhora_strength
    from jhora.horoscope.chart import yoga as jhora_yoga
    from jhora.horoscope.chart import sphuta as jhora_sphuta
    from jhora.horoscope.chart import dosha as jhora_dosha

    # Dasha related
    from jhora.horoscope.dhasa.graha import vimsottari as jhora_vimsottari_std
    from jhora.horoscope.dhasa.raasi import chara as jhora_chara_dhasa

    # Transit/Tajika related
    from jhora.horoscope.transit import tajaka as jhora_tajaka

    # Prediction related
    from jhora.horoscope.prediction import longevity as jhora_longevity
    from jhora.horoscope.prediction import general as jhora_general_prediction

except ImportError as e:
    print(f"FATAL ERROR: PyJHora import failed: {e}. Ensure PyJHora is correctly installed and accessible.")
    print("Please verify your Python environment and PyJHora installation path.")
    traceback.print_exc()
    exit()

# --- Configuration ---
DEFAULT_AYANAMSA_MODE = "LAHIRI"
OUTPUT_BASE_PATH = Path("./Kundali")
JATAK_FILE_PATH = Path("./Jatak.txt")
GEOCODER_USER_AGENT = "PyjhoraDashaExtractor/1.4"

VIMSOTTARI_FULL_CYCLE_YEARS = 120
KNRAO_CHARA_TOTAL_YEARS = 96

# Constants for mapping (populated by _initialize_global_constants)
ZODIAC_MAP_UNIVERSAL = {
    "Ar": "Aries", "Ta": "Taurus", "Ge": "Gemini", "Cn": "Cancer",
    "Le": "Leo", "Vi": "Virgo", "Li": "Libra", "Sc": "Scorpio",
    "Sg": "Sagittarius", "Cp": "Capricorn", "Aq": "Aquarius", "Pi": "Pisces",
    "Asc": "Ascendant", "L": "Ascendant",
}
PLANET_FULL_NAMES_LIST = []
PLANET_SHORT_NAMES_LIST = []
RASHI_NAMES_LIST = []
RASHI_SHORT_NAMES_LIST = []
CHARA_KARAKA_NAMES_LIST = []
SPHUTA_FUNCTION_MAP = {}  # To be populated in _initialize_global_constants


def _initialize_global_constants():
    """Populate global constants from PyJHora for mappings."""
    global PLANET_FULL_NAMES_LIST, PLANET_SHORT_NAMES_LIST, ZODIAC_MAP_UNIVERSAL
    global RASHI_NAMES_LIST, RASHI_SHORT_NAMES_LIST, CHARA_KARAKA_NAMES_LIST
    global SPHUTA_FUNCTION_MAP

    print("INFO: Initializing global constants from PyJHora modules...")

    # Planet Names
    default_planets_full = ['Sun', 'Moon', 'Mars', 'Mercury', 'Jupiter', 'Venus', 'Saturn', 'Rahu', 'Ketu']
    default_planets_short = ["Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa", "Ra", "Ke"]

    if hasattr(jhora_utils, 'PLANET_NAMES'):
        PLANET_FULL_NAMES_LIST = jhora_utils.PLANET_NAMES
    elif hasattr(const, 'PLANET_NAMES'):
        PLANET_FULL_NAMES_LIST = const.PLANET_NAMES
    elif hasattr(const, 'planet_names'):
        PLANET_FULL_NAMES_LIST = const.planet_names
    else:
        PLANET_FULL_NAMES_LIST = default_planets_full; print("  WARNING: Using fallback PLANET_NAMES.")

    if hasattr(jhora_utils, 'PLANET_SHORT_NAMES'):
        PLANET_SHORT_NAMES_LIST = jhora_utils.PLANET_SHORT_NAMES
    elif hasattr(const, 'PLANET_SHORT_NAMES'):
        PLANET_SHORT_NAMES_LIST = const.PLANET_SHORT_NAMES
    elif hasattr(const, 'planet_short_names'):
        PLANET_SHORT_NAMES_LIST = const.planet_short_names
    else:
        PLANET_SHORT_NAMES_LIST = default_planets_short; print("  WARNING: Using fallback PLANET_SHORT_NAMES.")

    # Ensure lists are actual lists and not None before proceeding
    PLANET_FULL_NAMES_LIST = PLANET_FULL_NAMES_LIST if isinstance(PLANET_FULL_NAMES_LIST,
                                                                  list) else default_planets_full
    PLANET_SHORT_NAMES_LIST = PLANET_SHORT_NAMES_LIST if isinstance(PLANET_SHORT_NAMES_LIST,
                                                                    list) else default_planets_short

    if PLANET_FULL_NAMES_LIST and PLANET_SHORT_NAMES_LIST:
        print(
            f"  Loaded {len(PLANET_FULL_NAMES_LIST)} planet full names and {len(PLANET_SHORT_NAMES_LIST)} short names.")
        min_len = min(len(PLANET_FULL_NAMES_LIST), len(PLANET_SHORT_NAMES_LIST), 9)
        for i in range(min_len):
            short, full = PLANET_SHORT_NAMES_LIST[i], PLANET_FULL_NAMES_LIST[i]
            full_cap = full.capitalize() if isinstance(full, str) else str(full)
            ZODIAC_MAP_UNIVERSAL[short] = full_cap
            ZODIAC_MAP_UNIVERSAL[str(i)] = full_cap
    else:
        print(
            "  CRITICAL WARNING: Planet name lists from PyJHora are empty or invalid after attempting to load. Using hardcoded fallbacks.")
        PLANET_FULL_NAMES_LIST = default_planets_full
        PLANET_SHORT_NAMES_LIST = default_planets_short
        for i in range(9):
            ZODIAC_MAP_UNIVERSAL[PLANET_SHORT_NAMES_LIST[i]] = PLANET_FULL_NAMES_LIST[i]
            ZODIAC_MAP_UNIVERSAL[str(i)] = PLANET_FULL_NAMES_LIST[i]

    # Rashi Names
    default_rashis_full = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius",
                           "Capricorn", "Aquarius", "Pisces"]
    default_rashis_short = ["Ar", "Ta", "Ge", "Cn", "Le", "Vi", "Li", "Sc", "Sg", "Cp", "Aq", "Pi"]

    if hasattr(const, 'RAASI_LIST'):
        RASHI_NAMES_LIST = const.RAASI_LIST
    elif hasattr(const, 'RASHI_NAMES'):
        RASHI_NAMES_LIST = const.RASHI_NAMES
    elif hasattr(const, 'rasi_names_en'):
        RASHI_NAMES_LIST = const.rasi_names_en
    else:
        RASHI_NAMES_LIST = default_rashis_full; print("  WARNING: Using fallback RASHI_NAMES_LIST.")

    if hasattr(const, 'RASHI_SHORT_NAMES'):
        RASHI_SHORT_NAMES_LIST = const.RASHI_SHORT_NAMES
    else:
        RASHI_SHORT_NAMES_LIST = default_rashis_short; print("  WARNING: Using fallback RASHI_SHORT_NAMES_LIST.")

    RASHI_NAMES_LIST = RASHI_NAMES_LIST if isinstance(RASHI_NAMES_LIST, list) and len(
        RASHI_NAMES_LIST) == 12 else default_rashis_full
    RASHI_SHORT_NAMES_LIST = RASHI_SHORT_NAMES_LIST if isinstance(RASHI_SHORT_NAMES_LIST, list) and len(
        RASHI_SHORT_NAMES_LIST) == 12 else default_rashis_short

    if RASHI_NAMES_LIST and RASHI_SHORT_NAMES_LIST and len(RASHI_NAMES_LIST) == 12 and len(
            RASHI_SHORT_NAMES_LIST) == 12:
        print(f"  Loaded {len(RASHI_NAMES_LIST)} Rashi names.")
        for i in range(12):
            ZODIAC_MAP_UNIVERSAL[RASHI_SHORT_NAMES_LIST[i]] = RASHI_NAMES_LIST[i]
    else:
        print(
            "  CRITICAL WARNING: Rashi name lists from PyJHora are invalid. Using hardcoded ZODIAC_MAP_UNIVERSAL for Rasis.")

    # Chara Karaka Names
    if hasattr(const, 'chara_karaka_names'):
        CHARA_KARAKA_NAMES_LIST = const.chara_karaka_names
    else:
        CHARA_KARAKA_NAMES_LIST = ['Atma Karaka', 'Amatya Karaka', 'Bhratri Karaka', 'Matri Karaka', 'Putra Karaka',
                                   'Gnati Karaka', 'Dara Karaka', 'Pitri Karaka']
    print(f"  Loaded {len(CHARA_KARAKA_NAMES_LIST)} Chara Karaka names.")

    # Sphuta Functions (map name to function for easier iteration)
    SPHUTA_FUNCTION_MAP = {
        "TriSphuta": jhora_sphuta.tri_sphuta,
        "BeejaSphuta": jhora_sphuta.beeja_sphuta,
        "KshetraSphuta": jhora_sphuta.kshetra_sphuta,
        "PranaSphuta": jhora_sphuta.prana_sphuta,
        "DehaSphuta": jhora_sphuta.deha_sphuta,
        "MrityuSphuta": jhora_sphuta.mrityu_sphuta,
        "SookshmaTriSphuta": jhora_sphuta.sookshma_tri_sphuta,
        "TithiSphuta": jhora_sphuta.tithi_sphuta,
        "YogaSphuta": jhora_sphuta.yoga_sphuta,  # Note: yoga_sphuta might take add_yogi_longitude
        "YogiSphuta": jhora_sphuta.yogi_sphuta,
        "AvayogiSphuta": jhora_sphuta.avayogi_sphuta,
        "RahuTithiSphuta": jhora_sphuta.rahu_tithi_sphuta
    }
    print(f"  Initialized Sphuta function map with {len(SPHUTA_FUNCTION_MAP)} entries.")
    print("INFO: Global constants initialization complete.")


# --- BirthData Dataclass --- (Identical to previous, so not repeated for brevity)
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
    iana_timezone_name: Optional[str] = None

    @property
    def tob_str(self) -> str: return self.time_of_birth.strftime("%H:%M:%S")

    @property
    def dob_str(self) -> str: return self.date_of_birth.strftime("%Y-%m-%d")


# --- Utility Functions --- (Identical to previous, not repeated)
def _format_longitude_dms(longitude: float) -> str:
    if longitude is None: return "N/A"
    degrees = int(longitude)
    minutes_float = (longitude - degrees) * 60
    minutes = int(minutes_float)
    seconds_float = (minutes_float - minutes) * 60
    seconds = int(round(seconds_float))
    if seconds >= 60: seconds = 59
    return f"{degrees}°{minutes:02d}'{seconds:02d}\""


def _format_datetime_from_jd(jd_val: float) -> str:
    if jd_val is None: return "0000-00-00 00:00:00"
    try:
        greg_date_tuple = jhora_utils.jd_to_gregorian(jd_val)
        if not isinstance(greg_date_tuple, (list, tuple)) or len(greg_date_tuple) < 4:
            print(
                f"    ERROR (_format_datetime_from_jd): jd_to_gregorian({jd_val}) returned unexpected: {greg_date_tuple}")
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
        if hour >= 24: hour = 0
        return f"{year:04d}-{month:02d}-{day:02d} {hour:02d}:{minute:02d}:{second:02d}"
    except Exception as e:
        print(f"    ERROR in _format_datetime_from_jd for JD {jd_val}: {e}")
        return "0000-00-00 00:00:00"


def _parse_datetime_universal(date_str_with_time: str) -> str:
    if not date_str_with_time or date_str_with_time == "0000-00-00 00:00:00": return ""
    try:
        dt = datetime.datetime.strptime(date_str_with_time, "%Y-%m-%d %H:%M:%S");
        return dt.isoformat()
    except ValueError:
        try:
            dt = datetime.datetime.strptime(date_str_with_time, "%Y-%m-%d");
            return dt.date().isoformat()
        except ValueError:
            print(f"    WARNING: Could not parse datetime string '{date_str_with_time}' to ISO format.")
            return date_str_with_time


def _expand_name_universal(name_short: str, dasha_system_name: Optional[str] = None) -> str:
    return ZODIAC_MAP_UNIVERSAL.get(name_short.strip(), name_short.strip())


def get_planet_name_from_id(planet_id: Any) -> str:
    if isinstance(planet_id, str) and planet_id.upper() in ['L', 'ASC']: return "Ascendant"
    try:
        idx = int(planet_id)
        if 0 <= idx < len(PLANET_FULL_NAMES_LIST):
            name = PLANET_FULL_NAMES_LIST[idx]
            return name.capitalize() if isinstance(name, str) else str(name)
        return f"UnknownPlanet({planet_id})"
    except (ValueError, TypeError):
        return str(planet_id)


def get_rasi_name_from_index(rasi_index: int) -> str:
    if 0 <= rasi_index < len(RASHI_NAMES_LIST): return RASHI_NAMES_LIST[rasi_index]
    return f"UnknownRasi({rasi_index})"


# --- File I/O Helper Functions --- (Identical to previous, not repeated)
def save_json_to_dataset(data_to_save: Dict, filename_prefix: str, filename_suffix: str,
                         dataset_path: Path, birth_params: Optional[Dict] = None,
                         add_birth_params_to_payload: bool = True):
    filepath = dataset_path / f"{filename_prefix}-{filename_suffix}.json"
    final_data = data_to_save
    if add_birth_params_to_payload and birth_params:
        final_data = {"birth_parameters_used": birth_params, **data_to_save}
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(final_data, f, indent=2, ensure_ascii=False)
        print(f"    SUCCESS: Saved JSON to: {filepath.name}")
    except Exception as e:
        print(f"    ERROR: Could not save JSON to {filepath.name}: {e}");
        traceback.print_exc()


def save_raw_text_to_dataset(raw_data: Any, filename_prefix: str, filename_suffix: str, dataset_path: Path):
    filepath = dataset_path / f"{filename_prefix}-{filename_suffix}_PyJHoraRaw.txt"
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            if isinstance(raw_data, (list, dict, tuple)):
                f.write(pprint.pformat(raw_data, indent=2, width=120, sort_dicts=False))
            else:
                f.write(str(raw_data))
        print(f"    SUCCESS: Saved RAW TXT to: {filepath.name}")
    except Exception as e:
        print(f"    ERROR: Could not save RAW TXT to {filepath.name}: {e}");
        traceback.print_exc()


# --- Jatak.txt Parsing and Geocoding --- (Identical to previous, not repeated)
def parse_jatak_txt(file_path: Path) -> List[Dict[str, str]]:
    print(f"\nINFO: Parsing Jatak file: {file_path}")
    raw_records = []
    if not file_path.is_file():
        print(f"  ERROR: Jatak.txt not found at {file_path}. Cannot proceed.");
        return raw_records
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            current_record = {};
            line_num = 0
            for line_content in f:
                line_num += 1;
                line = line_content.strip()
                if not line:
                    if current_record: raw_records.append(current_record); current_record = {}
                    continue
                parts = line.split(':', 1)
                if len(parts) == 2:
                    current_record[parts[0].strip()] = parts[1].strip()
                else:
                    print(f"  WARNING: Line {line_num} in Jatak.txt is not 'Key: Value' format: '{line}'")
            if current_record: raw_records.append(current_record)
        print(f"  SUCCESS: Parsed {len(raw_records)} raw records from Jatak.txt.")
    except Exception as e:
        print(f"  ERROR: Failed to parse Jatak.txt: {e}"); traceback.print_exc()
    return raw_records


def geocode_and_enrich_place(place_str: str, dob: datetime.date, tob: datetime.time) -> \
        Tuple[Optional[float], Optional[float], Optional[float], Optional[str], Optional[str], Optional[str]]:
    print(f"    GEOCODING: For '{place_str}' (DOB: {dob}, TOB: {tob})")
    if not place_str: print("      WARNING: Empty place string."); return None, None, None, None, None, None
    geolocator = Nominatim(user_agent=GEOCODER_USER_AGENT, timeout=15)
    tf = TimezoneFinder()
    lat, lon, tz_offset, city, country, iana_tz_name = None, None, None, None, None, None
    try:
        print(f"      Calling Nominatim for: '{place_str}'")
        location = geolocator.geocode(place_str, language='en', addressdetails=True, exactly_one=True)
        time.sleep(1.2)
        if location and location.latitude is not None and location.longitude is not None:
            lat, lon = location.latitude, location.longitude
            print(f"      Geocoded: Lat={lat:.4f}, Lon={lon:.4f}")
            raw_address = location.raw.get('address', {})
            city = raw_address.get('city',
                                   raw_address.get('town', raw_address.get('village', raw_address.get('county'))))
            country_code = raw_address.get('country_code', '').upper()
            country = raw_address.get('country', "Unknown")
            if not city: city = place_str.split(',')[0].strip()
            print(f"      Location Details: City='{city}', Country='{country}' (Code: '{country_code}')")
            iana_tz_name = tf.timezone_at(lng=lon, lat=lat)
            if iana_tz_name:
                print(f"      TimezoneFinder found IANA TZ: {iana_tz_name}")
                try:
                    tz_obj = pytz.timezone(iana_tz_name)
                    dt_naive = datetime.datetime.combine(dob, tob)
                    dt_aware = tz_obj.localize(dt_naive, is_dst=None)
                    offset_td = dt_aware.utcoffset()
                    if offset_td:
                        tz_offset = offset_td.total_seconds() / 3600.0; print(
                            f"      Calculated TZ Offset: {tz_offset} hrs for {dt_aware.tzname()}")
                    else:
                        print(f"      WARNING: pytz could not get offset for '{iana_tz_name}' at {dt_naive}.")
                except pytz.exceptions.UnknownTimeZoneError:
                    print(f"      WARNING: pytz unknown TZ '{iana_tz_name}'."); iana_tz_name = None
                except Exception as e_pytz:
                    print(f"      ERROR in pytz for {iana_tz_name}: {e_pytz}"); iana_tz_name = None
            else:
                print(f"      WARNING: IANA TZ not found by TimezoneFinder for Lat:{lat}, Lon:{lon}.")
        else:
            print(f"      WARNING: Geocoding failed for '{place_str}'.")
    except Exception as e_geo:
        print(f"      ERROR during geocoding/timezone for '{place_str}': {e_geo}"); traceback.print_exc()
    if country_code and country == country_code:
        try:
            country = pytz.country_names[country_code.lower()]
        except KeyError:
            pass
    print(
        f"    GEOCODING RESULT: Lat={lat}, Lon={lon}, TZ Offset={tz_offset}, City='{city}', Country='{country}', IANA_TZ='{iana_tz_name}'")
    return lat, lon, tz_offset, city, country, iana_tz_name


def process_raw_entries_to_birthdata(raw_entries: List[Dict[str, str]]) -> List[BirthData]:
    print("\nINFO: Processing raw Jatak entries into BirthData objects...")
    birth_data_list = []
    if not raw_entries: print("  No raw entries to process."); return birth_data_list
    for i, entry in enumerate(raw_entries):
        name = entry.get("Name", f"UnnamedRecord_{i + 1}")
        print(f"  Processing record {i + 1}/{len(raw_entries)} for: {name}")
        date_str, time_str, place_str = entry.get("Date"), entry.get("Time"), entry.get("Place")
        gender = entry.get("Gender", "neutral").lower()
        if not (name and date_str and time_str and place_str):
            print(f"    WARNING: Skipping '{name}' due to missing essential fields. Entry: {entry}");
            continue
        try:
            dob = datetime.datetime.strptime(date_str, "%B %d, %Y").date()
            tob = datetime.datetime.strptime(time_str, "%H:%M:%S").time()
            print(f"    Parsed DOB: {dob}, TOB: {tob}")
        except ValueError as e_dt:
            print(f"    ERROR: Parse Date/Time for {name}: {e_dt}. Skipping."); continue
        lat, lon, tz_offset, city, country, iana_tz_name = geocode_and_enrich_place(place_str, dob, tob)
        geocoding_ok = False
        if lat is not None and lon is not None and tz_offset is not None:
            geocoding_ok = True
        else:
            is_india_loc = country and (
                        "india" in country.lower() or (iana_tz_name and "asia/kolkata" in iana_tz_name.lower()))
            if is_india_loc and tz_offset is None and lat is not None and lon is not None:
                print(f"    INFO: {name} in India, TZ fail. Fallback +5.5.");
                tz_offset = 5.5
                if not iana_tz_name: iana_tz_name = "Asia/Kolkata (Assumed)"; geocoding_ok = True
            else:
                print(f"    CRITICAL: Geo/TZ incomplete for {name} at '{place_str}'. Skipping."); continue
        bd = BirthData(name, dob, tob, lat, lon, tz_offset, city, country, gender, place_str, geocoding_ok,
                       iana_tz_name)
        birth_data_list.append(bd)
        print(
            f"    SUCCESS: BirthData for {name}. Lat:{bd.latitude:.4f}, Lon:{bd.longitude:.4f}, TZ:{bd.timezone_offset}, IANA:{bd.iana_timezone_name}")
    print(f"INFO: Processed raw entries. {len(birth_data_list)} BirthData objects created.")
    return birth_data_list


# --- Dasha Text Generation & Parsing --- (Identical to previous, not repeated)
def generate_vimsottari_text_for_universal_parser(h_obj: Horoscope) -> str:
    print(f"    VIMSOTTARI_TEXT: Generating for {h_obj.name}...")
    text_lines = [];
    dasha_system_name = "Vimsottari Dasa";
    text_lines.append(f"{dasha_system_name}:");
    text_lines.append("Maha Dasas:")
    if not (PLANET_FULL_NAMES_LIST and PLANET_SHORT_NAMES_LIST and len(PLANET_FULL_NAMES_LIST) >= 9 and len(
            PLANET_SHORT_NAMES_LIST) >= 9):
        print("    ERROR (Vimsottari Text Gen): Planet names not initialized.");
        return "Error: Planet names missing."
    jd_dob = h_obj.julian_day
    try:
        mahadashas_dict = jhora_vimsottari_std.vimsottari_mahadasa(jd=jd_dob, place=h_obj.Place,
                                                                   dhasa_starting_planet=1)
    except Exception as e:
        print(f"    ERROR (Vimsottari Text Gen): Get Mahadashas: {e}"); return f"Error: {e}"
    md_summary_lines = [];
    md_detailed_blocks = [];
    sorted_md_lords = sorted(mahadashas_dict.keys(), key=lambda lord: mahadashas_dict[lord])
    for md_idx_loop, md_lord_idx in enumerate(sorted_md_lords):
        md_start_jd_val = mahadashas_dict[md_lord_idx];
        md_lord_name_full = PLANET_FULL_NAMES_LIST[md_lord_idx].capitalize();
        md_lord_name_short = PLANET_SHORT_NAMES_LIST[md_lord_idx]
        md_dur_years = jhora_vimsottari_std.vimsottari_dict[md_lord_idx];
        md_end_jd_val = md_start_jd_val + (md_dur_years * const.SIDEREAL_YEAR)
        md_start_str = _format_datetime_from_jd(md_start_jd_val);
        md_end_str = _format_datetime_from_jd(md_end_jd_val)
        md_summary_lines.append(f"  {md_lord_name_full}: {md_start_str} - {md_end_str}");
        current_md_block = [];
        current_md_block.append(f"{md_lord_name_short} MD: {md_start_str} - {md_end_str}");
        current_md_block.append(f"Antardasas in this MD:")
        try:
            antardashas_dict = jhora_vimsottari_std._vimsottari_bhukti(md_lord_idx, md_start_jd_val)
        except Exception as e:
            print(f"    ERROR (Vimsottari Text Gen): Get Bhuktis for MD {md_lord_name_short}: {e}"); continue
        sorted_ad_lords = sorted(antardashas_dict.keys(), key=lambda lord: antardashas_dict[lord])
        for ad_lord_idx in sorted_ad_lords:
            ad_start_jd_val = antardashas_dict[ad_lord_idx];
            ad_lord_name_short = PLANET_SHORT_NAMES_LIST[ad_lord_idx];
            ad_dur_prop_md = jhora_vimsottari_std.vimsottari_dict[ad_lord_idx]
            ad_dur_years = (ad_dur_prop_md * md_dur_years) / const.HUMAN_LIFE_SPAN_FOR_VIMSOTTARI_DHASA;
            ad_end_jd_val_calculated = ad_start_jd_val + (ad_dur_years * const.SIDEREAL_YEAR)
            ad_end_jd_val = ad_end_jd_val_calculated
            if md_idx_loop + 1 < len(sorted_md_lords): next_md_start_jd = mahadashas_dict[
                sorted_md_lords[md_idx_loop + 1]]; ad_end_jd_val = min(ad_end_jd_val, next_md_start_jd)
            ad_end_jd_val = min(ad_end_jd_val, md_end_jd_val)
            if ad_start_jd_val >= ad_end_jd_val: continue
            ad_start_str = _format_datetime_from_jd(ad_start_jd_val);
            ad_end_str = _format_datetime_from_jd(ad_end_jd_val);
            current_md_block.append(f"    {ad_lord_name_short} AD: {ad_start_str} - {ad_end_str}");
            current_md_block.append(f"    Pratyantardasas in this AD:")
            try:
                pratyantardashas_dict = jhora_vimsottari_std._vimsottari_antara(md_lord_idx, ad_lord_idx,
                                                                                ad_start_jd_val)
            except Exception as e:
                print(f"    ERROR (Vimsottari Text Gen): Get Antaras for AD {ad_lord_name_short}: {e}"); continue
            sorted_pd_lords = sorted(pratyantardashas_dict.keys(), key=lambda lord: pratyantardashas_dict[lord])
            for pd_lord_idx in sorted_pd_lords:
                pd_start_jd_val = pratyantardashas_dict[pd_lord_idx];
                pd_lord_name_short = PLANET_SHORT_NAMES_LIST[pd_lord_idx];
                pd_dur_prop_ad = jhora_vimsottari_std.vimsottari_dict[pd_lord_idx]
                pd_dur_years = (pd_dur_prop_ad * ad_dur_years) / const.HUMAN_LIFE_SPAN_FOR_VIMSOTTARI_DHASA;
                pd_end_jd_val_calculated = pd_start_jd_val + (pd_dur_years * const.SIDEREAL_YEAR);
                pd_end_jd_val = min(pd_end_jd_val_calculated, ad_end_jd_val)
                if pd_start_jd_val >= pd_end_jd_val: continue
                pd_start_str = _format_datetime_from_jd(pd_start_jd_val);
                pd_end_str = _format_datetime_from_jd(pd_end_jd_val);
                current_md_block.append(f"        {pd_lord_name_short} PD: {pd_start_str} - {pd_end_str}");
                current_md_block.append(f"        Sookshma-antardasas in this PD:")
                sookshmadashas_dict = {};
                current_sd_start_jd_val = pd_start_jd_val;
                sd_lord_iter_idx = pd_lord_idx
                for _sd_loop_idx in range(9):
                    sookshmadashas_dict[sd_lord_iter_idx] = current_sd_start_jd_val;
                    sd_dur_prop_pd = jhora_vimsottari_std.vimsottari_dict[sd_lord_iter_idx]
                    sd_dur_years_iter = (sd_dur_prop_pd * pd_dur_years) / const.HUMAN_LIFE_SPAN_FOR_VIMSOTTARI_DHASA;
                    current_sd_start_jd_val += (sd_dur_years_iter * const.SIDEREAL_YEAR)
                    sd_lord_iter_idx = jhora_vimsottari_std.vimsottari_next_adhipati(sd_lord_iter_idx)
                sorted_sd_lords = sorted(sookshmadashas_dict.keys(), key=lambda lord: sookshmadashas_dict[lord])
                for sd_lord_idx_val in sorted_sd_lords:
                    sd_start_jd_val_iter = sookshmadashas_dict[sd_lord_idx_val];
                    sd_lord_name_short_iter = PLANET_SHORT_NAMES_LIST[sd_lord_idx_val];
                    sd_dur_prop_pd_iter = jhora_vimsottari_std.vimsottari_dict[sd_lord_idx_val]
                    sd_dur_years_final = (
                                                     sd_dur_prop_pd_iter * pd_dur_years) / const.HUMAN_LIFE_SPAN_FOR_VIMSOTTARI_DHASA;
                    sd_end_jd_val_iter_calculated = sd_start_jd_val_iter + (sd_dur_years_final * const.SIDEREAL_YEAR);
                    sd_end_jd_val_iter = min(sd_end_jd_val_iter_calculated, pd_end_jd_val)
                    if sd_start_jd_val_iter >= sd_end_jd_val_iter: continue
                    sd_start_str_iter = _format_datetime_from_jd(sd_start_jd_val_iter);
                    sd_end_str_iter = _format_datetime_from_jd(sd_end_jd_val_iter);
                    current_md_block.append(
                        f"            {sd_lord_name_short_iter} SD: {sd_start_str_iter} - {sd_end_str_iter}")
                current_md_block.append("")
            current_md_block.append("")
        md_detailed_blocks.extend(current_md_block);
        md_detailed_blocks.append("")
    text_lines.extend(md_summary_lines);
    text_lines.append("");
    text_lines.extend(md_detailed_blocks)
    print(f"    VIMSOTTARI_TEXT: Generation complete for {h_obj.name}.")
    return "\n".join(text_lines)


def generate_knrao_chara_text_for_universal_parser(h_obj: Horoscope, d1_chart_positions: list,
                                                   total_years_to_calculate: int) -> str:
    print(f"    KNRAO_CHARA_TEXT: Generating for {h_obj.name} for {total_years_to_calculate} years...")
    text_lines = [];
    dasha_system_name = "K.N. Rao Chara Dasa";
    text_lines.append(f"{dasha_system_name}:");
    text_lines.append("Maha Dasas:")
    md_summary_lines = [];
    md_detailed_blocks = []
    if not (hasattr(const, 'RASHI_NAMES') and hasattr(const, 'RASHI_SHORT_NAMES') and len(
            const.RASHI_NAMES) == 12 and len(const.RASHI_SHORT_NAMES) == 12):
        print("    ERROR (KNRAO Text Gen): Rashi names missing.");
        return "Error: Missing Rashi constants."
    try:
        md_progression_rasis = jhora_chara_dhasa._dhasa_progression_knrao_method(d1_chart_positions)
    except Exception as e:
        print(f"    ERROR (KNRAO Text Gen): Get Dasha progression: {e}"); return f"Error: {e}"
    elapsed_total_years_for_mds = 0.0;
    current_jd_for_mds = h_obj.julian_day;
    one_year_in_days = const.SIDEREAL_YEAR
    max_md_cycles = (total_years_to_calculate // 1) + 3
    for cycle_num in range(max_md_cycles):
        if elapsed_total_years_for_mds >= total_years_to_calculate: break
        for md_rasi_index_current_cycle in md_progression_rasis:
            if elapsed_total_years_for_mds >= total_years_to_calculate: break
            md_start_jd_current_md = current_jd_for_mds
            try:
                md_total_duration_years_full = jhora_chara_dhasa._dhasa_duration_knrao_method(d1_chart_positions,
                                                                                              md_rasi_index_current_cycle)
            except Exception as e:
                print(
                    f"    ERROR (KNRAO Text Gen): Get MD duration for Rasi {md_rasi_index_current_cycle}: {e}"); continue
            if md_total_duration_years_full <= 0: md_total_duration_years_full = 1.0
            remaining_years_for_target = total_years_to_calculate - elapsed_total_years_for_mds;
            actual_md_run_duration_this_iteration = min(md_total_duration_years_full, remaining_years_for_target)
            if actual_md_run_duration_this_iteration <= 0: continue
            md_end_jd_current_md = md_start_jd_current_md + (actual_md_run_duration_this_iteration * one_year_in_days)
            md_rasi_name_full = const.RASHI_NAMES[md_rasi_index_current_cycle];
            md_rasi_name_short = const.RASHI_SHORT_NAMES[md_rasi_index_current_cycle]
            md_start_str = _format_datetime_from_jd(md_start_jd_current_md);
            md_end_str = _format_datetime_from_jd(md_end_jd_current_md)
            md_summary_lines.append(f"  {md_rasi_name_full}: {md_start_str} - {md_end_str}");
            current_md_block = [];
            current_md_block.append(f"{md_rasi_name_short} MD: {md_start_str} - {md_end_str}");
            current_md_block.append(f"Antardasas in this MD:")
            ad_proportional_duration_years = md_total_duration_years_full / 12.0
            if ad_proportional_duration_years > 0:
                current_ad_start_jd = md_start_jd_current_md
                try:
                    ad_start_progression_index = md_progression_rasis.index(md_rasi_index_current_cycle)
                except ValueError:
                    print(
                        f"    ERROR (KNRAO Text Gen): MD Rasi {md_rasi_name_short} not in progression. Skip ADs."); elapsed_total_years_for_mds += actual_md_run_duration_this_iteration; current_jd_for_mds = md_end_jd_current_md; continue
                for i in range(12):
                    if current_ad_start_jd >= md_end_jd_current_md: break
                    ad_rasi_index = md_progression_rasis[(ad_start_progression_index + i) % 12];
                    ad_rasi_name_short = const.RASHI_SHORT_NAMES[ad_rasi_index]
                    ad_start_jd_this_ad = current_ad_start_jd;
                    ad_end_jd_this_ad = min(ad_start_jd_this_ad + (ad_proportional_duration_years * one_year_in_days),
                                            md_end_jd_current_md)
                    if ad_end_jd_this_ad <= ad_start_jd_this_ad: current_ad_start_jd = ad_end_jd_this_ad; continue
                    ad_start_str = _format_datetime_from_jd(ad_start_jd_this_ad);
                    ad_end_str = _format_datetime_from_jd(ad_end_jd_this_ad);
                    current_md_block.append(f"    {ad_rasi_name_short} AD: {ad_start_str} - {ad_end_str}");
                    current_md_block.append(f"    Pratyantardasas in this AD:")
                    pd_proportional_duration_years = ad_proportional_duration_years / 12.0
                    if pd_proportional_duration_years > 0:
                        current_pd_start_jd = ad_start_jd_this_ad
                        try:
                            pd_start_progression_index = md_progression_rasis.index(ad_rasi_index)
                        except ValueError:
                            print(
                                f"    ERROR (KNRAO Text Gen): AD Rasi {ad_rasi_name_short} not in progression. Skip PDs."); current_ad_start_jd = ad_end_jd_this_ad; continue
                        for j in range(12):
                            if current_pd_start_jd >= ad_end_jd_this_ad: break
                            pd_rasi_index = md_progression_rasis[(pd_start_progression_index + j) % 12];
                            pd_rasi_name_short = const.RASHI_SHORT_NAMES[pd_rasi_index]
                            pd_start_jd_this_pd = current_pd_start_jd;
                            pd_end_jd_this_pd = min(
                                pd_start_jd_this_pd + (pd_proportional_duration_years * one_year_in_days),
                                ad_end_jd_this_ad)
                            if pd_end_jd_this_pd <= pd_start_jd_this_pd: current_pd_start_jd = pd_end_jd_this_pd; continue
                            pd_start_str = _format_datetime_from_jd(pd_start_jd_this_pd);
                            pd_end_str = _format_datetime_from_jd(pd_end_jd_this_pd);
                            current_md_block.append(f"        {pd_rasi_name_short} PD: {pd_start_str} - {pd_end_str}");
                            current_md_block.append(f"        Sookshma-antardasas in this PD:")
                            sd_proportional_duration_years = pd_proportional_duration_years / 12.0
                            if sd_proportional_duration_years > 0:
                                current_sd_start_jd = pd_start_jd_this_pd
                                try:
                                    sd_start_progression_index = md_progression_rasis.index(pd_rasi_index)
                                except ValueError:
                                    print(
                                        f"    ERROR (KNRAO Text Gen): PD Rasi {pd_rasi_name_short} not in progression. Skip SDs."); current_pd_start_jd = pd_end_jd_this_pd; continue
                                for k in range(12):
                                    if current_sd_start_jd >= pd_end_jd_this_pd: break
                                    sd_rasi_index = md_progression_rasis[(sd_start_progression_index + k) % 12];
                                    sd_rasi_name_short = const.RASHI_SHORT_NAMES[sd_rasi_index]
                                    sd_start_jd_this_sd = current_sd_start_jd;
                                    sd_end_jd_this_sd = min(
                                        sd_start_jd_this_sd + (sd_proportional_duration_years * one_year_in_days),
                                        pd_end_jd_this_pd)
                                    if sd_end_jd_this_sd <= sd_start_jd_this_sd: current_sd_start_jd = sd_end_jd_this_sd; continue
                                    sd_start_str = _format_datetime_from_jd(sd_start_jd_this_sd);
                                    sd_end_str = _format_datetime_from_jd(sd_end_jd_this_sd);
                                    current_md_block.append(
                                        f"            {sd_rasi_name_short} SD: {sd_start_str} - {sd_end_str}")
                                    current_sd_start_jd = sd_end_jd_this_sd
                                current_md_block.append("")
                            current_pd_start_jd = pd_end_jd_this_pd
                        current_md_block.append("")
                    current_ad_start_jd = ad_end_jd_this_ad
                current_md_block.append("")
            md_detailed_blocks.extend(current_md_block);
            md_detailed_blocks.append("")
            elapsed_total_years_for_mds += actual_md_run_duration_this_iteration;
            current_jd_for_mds = md_end_jd_current_md
    text_lines.extend(md_summary_lines);
    text_lines.append("");
    text_lines.extend(md_detailed_blocks)
    print(f"    KNRAO_CHARA_TEXT: Generation complete for {h_obj.name}.")
    return "\n".join(text_lines)


def parse_dasha_text_content(text_content: str, person_name: str,
                             dasha_system_source_id: str,
                             birth_params: Optional[Dict] = None) -> dict:
    print(f"    DASHA_PARSE: For '{dasha_system_source_id}' of {person_name}...")
    lines = [line for line in text_content.splitlines()];
    parsed_data = {"person_name": person_name, "birth_parameters_used": birth_params or {},
                   "dasha_system_name": "Unknown Dasha System", "source_file": dasha_system_source_id, "dasas": []}
    dasha_system_header_pattern = re.compile(r"^\s*([A-Za-z0-9\s\(\)\-\._':]+? Dasa(?: \([^)]+\))?):")
    period_line_regex = re.compile(
        r"^(?P<indent>\s*)(?P<name>[A-Za-z0-9\s]+?)\s*(?P<type>MD|AD|PD|SD)?:\s*(?P<start_date>\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2})\s*-\s*(?P<end_date>\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2})")
    summary_period_line_regex = re.compile(
        r"^\s*(?P<name>[A-Za-z0-9\s]+?):\s*(?P<start_date>\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2})\s*-\s*(?P<end_date>\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2})")
    context_stack = [];
    current_dasha_system_name = "Unknown Dasa";
    first_dasha_system_header_found = False
    for line_num, line_content in enumerate(lines):
        stripped_line = line_content.strip()
        if not first_dasha_system_header_found:
            match_ds_header = dasha_system_header_pattern.match(stripped_line)
            if match_ds_header: current_dasha_system_name = match_ds_header.group(1).strip(); parsed_data[
                "dasha_system_name"] = current_dasha_system_name; first_dasha_system_header_found = True; break
    if not first_dasha_system_header_found:
        if "Vimsottari" in dasha_system_source_id:
            parsed_data["dasha_system_name"] = "Vimsottari Dasa"
        elif "K.N. Rao Chara Dasa" in dasha_system_source_id:
            parsed_data["dasha_system_name"] = "K.N. Rao Chara Dasa"
        print(
            f"      WARNING (Dasha Parse): Dasha system name not found via regex in '{dasha_system_source_id}'. Using fallback: '{parsed_data['dasha_system_name']}'")
    is_in_summary_block = False;
    section_header_to_level = {"Maha Dasas:": 1, "Antardasas in this MD:": 2, "Pratyantardasas in this AD:": 3,
                               "Sookshma-antardasas in this PD:": 4}
    period_type_by_level = {1: "Mahadasha", 2: "Antardasha", 3: "Pratyantardasha", 4: "Sookshma-antardasha"}
    for line_num, line_content in enumerate(lines):
        stripped_line = line_content.strip();
        if not stripped_line: continue
        if dasha_system_header_pattern.match(stripped_line) and line_num < 5: continue
        is_section_header = False
        for header, _ in section_header_to_level.items():
            if stripped_line == header: is_in_summary_block = (header == "Maha Dasas:"); is_section_header = True; break
        if is_section_header: continue
        match = period_line_regex.match(line_content);
        level = 0;
        period_type_str = "";
        data_dict = None
        if match:
            data_dict = match.groupdict();
            period_type_shorthand = data_dict['type']
            if period_type_shorthand == "MD":
                level = 1
            elif period_type_shorthand == "AD":
                level = 2
            elif period_type_shorthand == "PD":
                level = 3
            elif period_type_shorthand == "SD":
                level = 4
            if level > 0: period_type_str = period_type_by_level[level]
            is_in_summary_block = False
        elif is_in_summary_block:
            match_summary = summary_period_line_regex.match(stripped_line)
            if match_summary: data_dict = match_summary.groupdict(); level = 1; period_type_str = period_type_by_level[
                level]
        if data_dict and level > 0:
            name_short = data_dict['name'].strip();
            period_obj = {"level": level, "period_type": period_type_str,
                          "name": _expand_name_universal(name_short, current_dasha_system_name),
                          "start_datetime": _parse_datetime_universal(data_dict['start_date']),
                          "end_datetime": _parse_datetime_universal(data_dict['end_date']), "sub_periods": []}
            while context_stack and level <= context_stack[-1]['level']: context_stack.pop()
            if not context_stack:
                if level == 1: parsed_data["dasas"].append(period_obj); context_stack.append(period_obj)
            else:
                parent_period = context_stack[-1]
                if level == parent_period['level'] + 1: parent_period["sub_periods"].append(
                    period_obj); context_stack.append(period_obj)
            if level == 1 and match: is_in_summary_block = False
    print(f"    DASHA_PARSE: Complete for {person_name}. Found {len(parsed_data['dasas'])} top Dasha periods.")
    return parsed_data


# --- Individual Data Extraction Functions --- (D1, D9, CharaKarakas, Ashtakavarga from previous response)
def extract_and_save_d1_chart(h_obj: Horoscope, birth_params_for_json: Dict,
                              dataset_folder_path: Path, person_dir_name_safe: str) -> Optional[List]:
    print(f"  EXTRACTING D1 Chart for {birth_params_for_json.get('name', 'Current Individual')}...")
    try:
        d1_positions_raw = jhora_charts.rasi_chart(jd_at_dob=h_obj.julian_day, place_as_tuple=h_obj.Place,
                                                   ayanamsa_mode=h_obj.ayanamsa_mode)
        print(f"    Raw D1 from PyJHora: {d1_positions_raw}")
        save_raw_text_to_dataset(d1_positions_raw, person_dir_name_safe, "D1_Chart_Positions", dataset_folder_path)
        processed_positions = [
            {"point": get_planet_name_from_id(pid), "rasi_index": r_idx, "rasi_name": get_rasi_name_from_index(r_idx),
             "longitude_in_rasi": round(long, 4), "longitude_dms": _format_longitude_dms(long)} for pid, (r_idx, long)
            in d1_positions_raw]
        json_output = {"chart_name": "D1 Rasi Chart", "positions": processed_positions}
        save_json_to_dataset(json_output, person_dir_name_safe, "D1_Chart_Positions", dataset_folder_path,
                             birth_params_for_json)
        return d1_positions_raw
    except Exception as e:
        print(f"    ERROR extracting D1: {e}"); traceback.print_exc(); return None


def extract_and_save_d9_chart(h_obj: Horoscope, d1_positions_raw: Optional[List], birth_params_for_json: Dict,
                              dataset_folder_path: Path, person_dir_name_safe: str):
    if not d1_positions_raw: print(f"  SKIPPING D9 for {h_obj.name} (D1 missing)."); return
    print(f"  EXTRACTING D9 Chart for {h_obj.name}...")
    try:
        d9_positions_raw = jhora_charts.divisional_chart(jd_at_dob=h_obj.julian_day, place_as_tuple=h_obj.Place,
                                                         ayanamsa_mode=h_obj.ayanamsa_mode, divisional_chart_factor=9,
                                                         chart_method=1)
        print(f"    Raw D9 from PyJHora: {d9_positions_raw}")
        save_raw_text_to_dataset(d9_positions_raw, person_dir_name_safe, "D9_Chart_Positions", dataset_folder_path)
        processed_positions = [
            {"point": get_planet_name_from_id(pid), "rasi_index": r_idx, "rasi_name": get_rasi_name_from_index(r_idx),
             "longitude_in_rasi": round(long, 4), "longitude_dms": _format_longitude_dms(long)} for pid, (r_idx, long)
            in d9_positions_raw]
        json_output = {"chart_name": "D9 Navamsa Chart", "positions": processed_positions}
        save_json_to_dataset(json_output, person_dir_name_safe, "D9_Chart_Positions", dataset_folder_path,
                             birth_params_for_json)
    except Exception as e:
        print(f"    ERROR extracting D9: {e}"); traceback.print_exc()


def extract_and_save_chara_karakas(d1_positions_raw: Optional[List], birth_params_for_json: Dict,
                                   dataset_folder_path: Path, person_dir_name_safe: str):
    if not d1_positions_raw: print(f"  SKIPPING Chara Karakas for {person_dir_name_safe} (D1 missing)."); return
    print(f"  EXTRACTING Chara Karakas for {person_dir_name_safe}...")
    try:
        raw_karaka_indices = jhora_house.chara_karakas(planet_positions=d1_positions_raw)
        print(f"    Raw Chara Karaka indices: {raw_karaka_indices}")
        save_raw_text_to_dataset(raw_karaka_indices, person_dir_name_safe, "CharaKarakas", dataset_folder_path)
        karakas_dict = {CHARA_KARAKA_NAMES_LIST[i]: get_planet_name_from_id(raw_karaka_indices[i]) for i in
                        range(min(len(raw_karaka_indices), len(CHARA_KARAKA_NAMES_LIST)))}
        if len(raw_karaka_indices) > len(CHARA_KARAKA_NAMES_LIST): print(
            f"    Warning: More karaka indices ({len(raw_karaka_indices)}) than names ({len(CHARA_KARAKA_NAMES_LIST)}). Some may not be named.")
        json_output = {"karakas": karakas_dict}
        save_json_to_dataset(json_output, person_dir_name_safe, "CharaKarakas", dataset_folder_path,
                             birth_params_for_json)
    except Exception as e:
        print(f"    ERROR extracting Chara Karakas: {e}"); traceback.print_exc()


def extract_and_save_ashtakavarga(h_obj: Horoscope, d1_positions_raw: Optional[List], birth_params_for_json: Dict,
                                  dataset_folder_path: Path, person_dir_name_safe: str):
    if not d1_positions_raw: print(f"  SKIPPING Ashtakavarga for {h_obj.name} (D1 missing)."); return
    print(f"  EXTRACTING Ashtakavarga for {h_obj.name}...")
    try:
        house_to_planet_list_for_av = [''] * 12
        for planet_id, (rasi_idx, _) in d1_positions_raw:
            planet_str = str(planet_id);
            current_val = house_to_planet_list_for_av[rasi_idx]
            house_to_planet_list_for_av[rasi_idx] = (current_val + '/' + planet_str) if current_val else planet_str
        print(f"    Input to get_ashtaka_varga (house_to_planet_list): {house_to_planet_list_for_av}")
        bav_raw, sav_raw, pav_raw = jhora_ashtakavarga.get_ashtaka_varga(house_to_planet_list_for_av)
        raw_av_output = {"BAV_raw": bav_raw, "SAV_raw": sav_raw, "PAV_raw": pav_raw}
        print(
            f"    Raw AV: BAV {len(bav_raw)}x{len(bav_raw[0]) if bav_raw else 0}, SAV {len(sav_raw)}, PAV {len(pav_raw)}x{len(pav_raw[0]) if pav_raw else 0}x{len(pav_raw[0][0]) if pav_raw and pav_raw[0] else 0}")
        save_raw_text_to_dataset(raw_av_output, person_dir_name_safe, "Ashtakavarga", dataset_folder_path)

        bav_planet_map = PLANET_FULL_NAMES_LIST[:7] + ["Ascendant"];
        bav_processed = {}
        for i, planet_bav_row in enumerate(bav_raw): bav_processed[bav_planet_map[i]] = {
            get_rasi_name_from_index(j): pts for j, pts in enumerate(planet_bav_row)}
        sav_processed = {get_rasi_name_from_index(i): pts for i, pts in enumerate(sav_raw)}

        pav_processed = {};
        pav_subject_planets = PLANET_FULL_NAMES_LIST[:7] + ["Ascendant"];
        pav_contributor_map = PLANET_FULL_NAMES_LIST[:7] + ["Ascendant"]
        # pav_raw structure: [subject_planet_idx][contributor_idx][rasi_idx]
        for subj_idx, subject_pav_data in enumerate(pav_raw):  # subject_pav_data is 8x12 list of lists
            subj_planet_name = pav_subject_planets[subj_idx];
            pav_processed[subj_planet_name] = {}
            for rasi_idx in range(12):
                rasi_name = get_rasi_name_from_index(rasi_idx);
                pav_processed[subj_planet_name][rasi_name] = {}
                total_for_rasi = 0
                for contrib_idx in range(len(subject_pav_data)):  # Should be 8 contributors
                    contrib_name = pav_contributor_map[contrib_idx]
                    # subject_pav_data[contrib_idx] is a list of 12 points for that contributor for the subject planet
                    points = subject_pav_data[contrib_idx][rasi_idx]
                    pav_processed[subj_planet_name][rasi_name][contrib_name] = points
                    total_for_rasi += points
                pav_processed[subj_planet_name][rasi_name]["Total"] = total_for_rasi

        json_output = {"BhinnaAshtakavarga": bav_processed, "SarvaAshtakavarga": sav_processed,
                       "PrashtaraAshtakavarga": pav_processed}
        save_json_to_dataset(json_output, person_dir_name_safe, "Ashtakavarga", dataset_folder_path,
                             birth_params_for_json)
    except Exception as e:
        print(f"    ERROR extracting Ashtakavarga: {e}"); traceback.print_exc()


# --- Placeholder for other extraction functions ---
# ... (Planetary Strengths, Yogas, Tajika, Arudhas, Sphutas, Doshas, Longevity) ...
# These will be added in subsequent iterations, following the same pattern.

def extract_and_save_planetary_strengths(h_obj: Horoscope, birth_params_for_json: Dict,
                                         dataset_folder_path: Path, person_dir_name_safe: str):
    print(f"  EXTRACTING Planetary Strengths for {h_obj.name}...")
    try:
        # Shadbala
        shadbala_raw = jhora_strength.shad_bala(jd=h_obj.julian_day, place=h_obj.Place,
                                                ayanamsa_mode=h_obj.ayanamsa_mode)
        # Output: [stb, kb, dgb, cb, nb, dkb, sb_sum, sb_rupa, sb_strength] each is list of 7 (Sun-Sat)
        print(f"    Raw Shadbala from PyJHora: (components: {len(shadbala_raw) - 3}, sum, rupa, strength)")

        # Ishta Phala
        ishta_phala_raw = jhora_strength._ishta_phala(jd=h_obj.julian_day,
                                                      place=h_obj.Place)  # Assuming it takes rasi_chart as input
        # Output: list of 7 (Sun-Sat)
        print(f"    Raw Ishta Phala from PyJHora: {ishta_phala_raw}")

        # Kashta Phala (if available and desired)
        # kashta_phala_raw = jhora_strength._kashta_phala(jd=h_obj.julian_day, place=h_obj.Place)
        # print(f"    Raw Kashta Phala from PyJHora: {kashta_phala_raw}")

        raw_strength_data = {"shadbala_components_raw": shadbala_raw,
                             "ishta_phala_raw": ishta_phala_raw}  # , "kashta_phala_raw": kashta_phala_raw}
        save_raw_text_to_dataset(raw_strength_data, person_dir_name_safe, "PlanetaryStrengths", dataset_folder_path)

        planets = PLANET_FULL_NAMES_LIST[:7]  # Sun to Saturn

        shadbala_components_processed = {
            "SthanaBala": {planets[i]: shadbala_raw[0][i] for i in range(7)},
            "KalaBala": {planets[i]: shadbala_raw[1][i] for i in range(7)},
            "DigBala": {planets[i]: shadbala_raw[2][i] for i in range(7)},
            "ChestaBala": {planets[i]: shadbala_raw[3][i] for i in range(7)},
            "NaisargikaBala": {planets[i]: shadbala_raw[4][i] for i in range(7)},
            "DrikBala": {planets[i]: shadbala_raw[5][i] for i in range(7)},
        }
        shadbala_total_processed = {planets[i]: shadbala_raw[6][i] for i in range(7)}
        shadbala_rupa_processed = {planets[i]: shadbala_raw[7][i] for i in range(7)}
        shadbala_strength_processed = {planets[i]: shadbala_raw[8][i] for i in range(7)}
        ishta_phala_processed = {planets[i]: ishta_phala_raw[i] for i in range(len(ishta_phala_raw))}
        # kashta_phala_processed      = {planets[i]: kashta_phala_raw[i] for i in range(len(kashta_phala_raw))}

        json_output = {
            "Shadbala_Components": shadbala_components_processed,
            "Shadbala_Total": shadbala_total_processed,
            "Shadbala_Rupa": shadbala_rupa_processed,
            "Shadbala_Strength_Ratio": shadbala_strength_processed,
            "IshtaPhala": ishta_phala_processed,
            # "KashtaPhala": kashta_phala_processed
        }
        save_json_to_dataset(json_output, person_dir_name_safe, "PlanetaryStrengths", dataset_folder_path,
                             birth_params_for_json)
    except Exception as e:
        print(f"    ERROR extracting Planetary Strengths: {e}")
        traceback.print_exc()


def extract_and_save_yogas(h_obj: Horoscope, birth_params_for_json: Dict,
                           dataset_folder_path: Path, person_dir_name_safe: str):
    print(f"  EXTRACTING Yogas for {h_obj.name}...")
    try:
        # get_yoga_details returns: yoga_results_dict, num_found, num_possible
        yoga_results_raw, _, _ = jhora_yoga.get_yoga_details(
            jd=h_obj.julian_day,
            place=h_obj.Place,
            divisional_chart_factor=1,  # For D1 based yogas
            language='en'
        )
        print(f"    Raw Yoga results from PyJHora: {len(yoga_results_raw)} yogas identified.")
        save_raw_text_to_dataset(yoga_results_raw, person_dir_name_safe, "Yogas_Detected", dataset_folder_path)

        processed_yogas = []
        if yoga_results_raw:  # If the dictionary is not empty
            for yoga_func_name, details in yoga_results_raw.items():
                # details = [chart_ID_str, yoga_display_name, yoga_description, yoga_benefits]
                processed_yogas.append({
                    "name": details[1],
                    "description": details[2],
                    "benefits": details[3]
                    # "function_name": yoga_func_name # Optional: for debugging which func triggered it
                })

        json_output = {"Detected_Yogas": processed_yogas}
        save_json_to_dataset(json_output, person_dir_name_safe, "Yogas_Detected", dataset_folder_path,
                             birth_params_for_json)
    except Exception as e:
        print(f"    ERROR extracting Yogas: {e}")
        traceback.print_exc()


def extract_and_save_tajika_details(h_obj: Horoscope, birth_data: BirthData, birth_params_for_json: Dict,
                                    dataset_folder_path: Path, person_dir_name_safe: str):
    print(f"  EXTRACTING Tajika (Annual Chart) details for {h_obj.name}...")
    try:
        current_year = datetime.date.today().year
        # years_from_birth for Tajaka calculation is age completed.
        # If birth is Jan 1990, for year 2024, age completed is 34.
        # So Varshaphal for 35th year starts in 2024.
        # PyJHora's tajaka.annual_chart takes 'years' as completed age.
        # So if you want varshaphal for 2024-2025, years = current_year - birth_year
        years_completed = current_year - birth_data.date_of_birth.year

        # Check if birthday for current_year has passed. If not, varshaphal is for (current_year-1) to current_year
        today = datetime.date.today()
        this_year_birthday = datetime.date(current_year, birth_data.date_of_birth.month, birth_data.date_of_birth.day)

        if today < this_year_birthday:
            years_completed -= 1  # Varshaphal is for the year that started on last year's birthday

        varshaphal_year_commencing = birth_data.date_of_birth.year + years_completed

        print(f"    Calculating Tajika for {varshaphal_year_commencing} (age completed: {years_completed})")

        # jd_at_dob for tajaka.annual_chart is the natal birth JD
        tajika_chart_raw, tajika_commencement_raw = jhora_tajaka.annual_chart(
            jd_at_dob=h_obj.julian_day,
            place=h_obj.Place,
            divisional_chart_factor=1,  # D1 of annual chart
            years=years_completed
        )
        # tajika_commencement_raw is [(year, month, day), time_str_dms]
        print(f"    Raw Tajika Chart from PyJHora: {tajika_chart_raw}")
        print(f"    Raw Tajika Commencement: {tajika_commencement_raw}")

        raw_tajika_output = {"chart_positions": tajika_chart_raw, "commencement_details": tajika_commencement_raw}
        save_raw_text_to_dataset(raw_tajika_output, person_dir_name_safe,
                                 f"Tajika_Varshaphal{varshaphal_year_commencing}", dataset_folder_path)

        comm_date_tuple, comm_time_str = tajika_commencement_raw
        comm_date_str = f"{comm_date_tuple[0]:04d}-{comm_date_tuple[1]:02d}-{comm_date_tuple[2]:02d}"

        processed_positions = []
        for planet_id, (rasi_idx, long_in_rasi) in tajika_chart_raw:
            processed_positions.append({
                "point": get_planet_name_from_id(planet_id),
                "rasi_index": rasi_idx,
                "rasi_name": get_rasi_name_from_index(rasi_idx),
                "longitude_in_rasi": round(long_in_rasi, 4),
                "longitude_dms": _format_longitude_dms(long_in_rasi)
            })

        json_output = {
            "varshaphal_year_commencing": varshaphal_year_commencing,
            "age_completed_at_varshaphal_start": years_completed,
            "commencement_date": comm_date_str,
            "commencement_time_dms": comm_time_str,  # This is already in DMS string format
            "chart_positions": processed_positions,
        }
        save_json_to_dataset(json_output, person_dir_name_safe, f"Tajika_Varshaphal{varshaphal_year_commencing}",
                             dataset_folder_path, birth_params_for_json)

    except Exception as e:
        print(f"    ERROR extracting Tajika details: {e}")
        traceback.print_exc()


# --- Main Execution Logic --- (Slightly modified from previous to call new functions)
def main():
    """Main orchestrator for the Dasha extraction pipeline."""
    _initialize_global_constants()
    print("--- PyJHora Astrological Data Extraction Pipeline ---")

    if not JATAK_FILE_PATH.is_file():
        print(f"CRITICAL ERROR: Input file Jatak.txt not found: '{JATAK_FILE_PATH}'. Exiting.");
        return

    raw_jatak_entries = parse_jatak_txt(JATAK_FILE_PATH)
    if not raw_jatak_entries: print("No records in Jatak.txt or parsing failed. Exiting."); return

    all_birth_data_objects = process_raw_entries_to_birthdata(raw_jatak_entries)
    if not all_birth_data_objects: print("No birth data objects created. Exiting."); return

    print(f"\n--- STARTING EXTRACTION FOR {len(all_birth_data_objects)} INDIVIDUALS ---")
    for current_birth_data in all_birth_data_objects:
        print(f"\n\nPROCESSING: {current_birth_data.name}")
        print(
            f"  Details - DOB: {current_birth_data.dob_str}, TOB: {current_birth_data.tob_str}, Place: {current_birth_data.raw_place_string}")

        h_obj: Optional[Horoscope] = None
        birth_params_for_json = asdict(current_birth_data)
        birth_params_for_json['date_of_birth'] = current_birth_data.dob_str  # Ensure string format
        birth_params_for_json['time_of_birth'] = current_birth_data.tob_str  # Ensure string format
        birth_params_for_json['ayanamsa_mode_to_be_used'] = DEFAULT_AYANAMSA_MODE

        try:
            print(f"  Instantiating Horoscope for {current_birth_data.name}...")
            drik_dob = drik.Date(current_birth_data.date_of_birth.year, current_birth_data.date_of_birth.month,
                                 current_birth_data.date_of_birth.day)
            h_obj = Horoscope(
                    date_in=drik_dob,
                    birth_time=current_birth_data.tob_str,
                    latitude=current_birth_data.latitude,
                    longitude=current_birth_data.longitude,
                    timezone_offset=current_birth_data.timezone_offset,
                    ayanamsa_mode=DEFAULT_AYANAMSA_MODE
            )
            # Manually assign the name to the h_obj if needed for other functions,
            # or rely on current_birth_data.name.
            # PyJHora's Horoscope object itself might not store the name internally.
            # For our Dasha text generators that use h_obj.name, we'll need to pass current_birth_data.name explicitly.
            # I will adjust the Dasha generator calls if they were relying on h_obj.name.
            birth_params_for_json["actual_ayanamsa_mode_used"] = h_obj.ayanamsa_mode
            print(f"    Horoscope object OK. Ayanamsa: {h_obj.ayanamsa_mode}, JD: {h_obj.julian_day:.4f}")
        except Exception as e_horo:
            print(f"    CRITICAL ERROR creating Horoscope for {current_birth_data.name}: {e_horo}");
            traceback.print_exc();
            continue

        person_dir_safe = re.sub(r'[^\w_.)( -]', '', current_birth_data.name.replace(" ", "_"))
        time_suffix_folder = current_birth_data.time_of_birth.strftime("%H%M")
        person_folder_name = f"{person_dir_safe}_{time_suffix_folder}"
        person_output_path = OUTPUT_BASE_PATH / person_folder_name
        dataset_path = person_output_path / "DataSet"
        try:
            dataset_path.mkdir(parents=True, exist_ok=True);
            print(f"  Output directory OK: {dataset_path}")
        except OSError as oe:
            print(f"    ERROR creating dir {dataset_path}: {oe}. Skipping."); continue

        geo_info_path = person_output_path / f"{person_dir_safe}_GeoTimeZone_Info.txt"
        try:
            with open(geo_info_path, 'w', encoding='utf-8') as f_geo:
                f_geo.write(f"Geo/Timezone Info for: {current_birth_data.name}\n" + "".join(
                    [f"  {k}: {v}\n" for k, v in birth_params_for_json.items() if k not in ['name']]))  # Basic dump
            print(f"    Saved Geo/Timezone diagnostic: {geo_info_path.name}")
        except Exception as e_geo_save:
            print(f"    ERROR saving Geo/TZ diagnostic: {e_geo_save}")

        # --- Call Data Extraction Functions ---
        d1_positions = extract_and_save_d1_chart(h_obj, birth_params_for_json, dataset_path, person_dir_safe)
        if d1_positions:
            extract_and_save_d9_chart(h_obj, d1_positions, birth_params_for_json, dataset_path, person_dir_safe)
            extract_and_save_chara_karakas(d1_positions, birth_params_for_json, dataset_path, person_dir_safe)
            extract_and_save_ashtakavarga(h_obj, d1_positions, birth_params_for_json, dataset_path, person_dir_safe)

        extract_and_save_planetary_strengths(h_obj, birth_params_for_json, dataset_path, person_dir_safe)
        extract_and_save_yogas(h_obj, birth_params_for_json, dataset_path, person_dir_safe)
        extract_and_save_tajika_details(h_obj, current_birth_data, birth_params_for_json, dataset_path, person_dir_safe)

        # TODO: Add calls for Arudhas, Sphutas, Doshas, Longevity when implemented
        # extract_and_save_arudha_padas(h_obj, d1_positions, birth_params_for_json, dataset_path, person_dir_safe)
        # extract_and_save_sphutas(h_obj, current_birth_data, birth_params_for_json, dataset_path, person_dir_safe)
        # extract_and_save_doshas(h_obj, birth_params_for_json, dataset_path, person_dir_safe)
        # extract_and_save_longevity_indicators(h_obj, birth_params_for_json, dataset_path, person_dir_safe)

        # Master Nested Vimsottari Dasha
        print(f"  Generating Vimsottari Dasha for {current_birth_data.name}...")
        vimsottari_text = generate_vimsottari_text_for_universal_parser(h_obj)
        save_raw_text_to_dataset(vimsottari_text, person_dir_safe, "VimsottariDasa_PyJHoraText", dataset_path)
        if "Error" not in vimsottari_text:
            vimsottari_json = parse_dasha_text_content(vimsottari_text, current_birth_data.name,
                                                       f"Vimsottari Master ({current_birth_data.name})",
                                                       birth_params_for_json)
            save_json_to_dataset(vimsottari_json, person_dir_safe, "VimsottariDasa-Master_Nested", dataset_path,
                                 add_birth_params_to_payload=False)
        else:
            print(f"    Skipping Vimsottari JSON for {current_birth_data.name} due to text error.")

        # Master Nested K.N. Rao Chara Dasha
        if d1_positions:
            print(f"  Generating K.N. Rao Chara Dasha for {current_birth_data.name}...")
            knrao_text = generate_knrao_chara_text_for_universal_parser(h_obj, d1_positions, KNRAO_CHARA_TOTAL_YEARS)
            save_raw_text_to_dataset(knrao_text, person_dir_safe, "KNRaoCharaDasa_PyJHoraText", dataset_path)
            if "Error" not in knrao_text:
                knrao_json = parse_dasha_text_content(knrao_text, current_birth_data.name,
                                                      f"KNRaoChara Master ({current_birth_data.name})",
                                                      birth_params_for_json)
                save_json_to_dataset(knrao_json, person_dir_safe, "KNRaoCharaDasa-Master_Nested", dataset_path,
                                     add_birth_params_to_payload=False)
            else:
                print(f"    Skipping KNRaoChara JSON for {current_birth_data.name} due to text error.")
        else:
            print(f"    Skipping KNRaoChara Dasha for {current_birth_data.name} (D1 missing).")

        print(f"  --- FINISHED PROCESSING: {current_birth_data.name} ---")
    print("\n\n--- ALL INDIVIDUALS PROCESSED. PIPELINE COMPLETE. ---")


if __name__ == "__main__":
    print("Starting PyJHora Data Extraction Pipeline script...")
    script_start_time = time.time()
    main()
    script_end_time = time.time()
    print(f"Total execution time: {script_end_time - script_start_time:.2f} seconds.")