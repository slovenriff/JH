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
    print("ERROR: Required libraries not found. Please install them: pip install geopy timezonefinder pytz")
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
    print(f"FATAL ERROR: PyJHora import failed: {e}. Ensure PyJHora is correctly installed and accessible.")
    exit()

# --- Configuration ---
DEFAULT_AYANAMSA_MODE = "LAHIRI"
OUTPUT_BASE_PATH = Path("./Kundali")
JATAK_FILE_PATH = Path("./Jatak.txt")
GEOCODER_USER_AGENT = "PyjhoraDashaExtractor/1.2"  # Incremented version

# Dasha Calculation Spans
VIMSOTTARI_FULL_CYCLE_YEARS = 120  # For text generation, the Vimsottari function calculates all MDs
KNRAO_CHARA_TOTAL_YEARS = 96  # Calculate for 96 years (e.g., 8 cycles of 12 Rasis if all Rasis had 1 year MD)

ZODIAC_MAP_UNIVERSAL = {
    "Ar": "Aries", "Ta": "Taurus", "Ge": "Gemini", "Cn": "Cancer",
    "Le": "Leo", "Vi": "Virgo", "Li": "Libra", "Sc": "Scorpio",
    "Sg": "Sagittarius", "Cp": "Capricorn", "Aq": "Aquarius", "Pi": "Pisces",
    "Sun": "Sun", "Moon": "Moon", "Mars": "Mars", "Merc": "Mercury", "Mer": "Mercury",
    "Jup": "Jupiter", "Ven": "Venus", "Sat": "Saturn",
    "Rah": "Rahu", "Ket": "Ketu"
}
PLANET_FULL_NAMES_LIST, PLANET_SHORT_NAMES_LIST = None, None

# Dynamically populate ZODIAC_MAP_UNIVERSAL with PyJHora planet names
# Attempt to get planet names from jhora.utils first, then jhora.const
if hasattr(jhora_utils, 'PLANET_NAMES'):
    PLANET_FULL_NAMES_LIST = jhora_utils.PLANET_NAMES
elif hasattr(const, 'PLANET_NAMES'):
    PLANET_FULL_NAMES_LIST = const.PLANET_NAMES
elif hasattr(const, 'planet_names'):  # some versions might use lowercase
    PLANET_FULL_NAMES_LIST = const.planet_names

if hasattr(jhora_utils, 'PLANET_SHORT_NAMES'):
    PLANET_SHORT_NAMES_LIST = jhora_utils.PLANET_SHORT_NAMES
elif hasattr(const, 'PLANET_SHORT_NAMES'):
    PLANET_SHORT_NAMES_LIST = const.PLANET_SHORT_NAMES
elif hasattr(const, 'planet_short_names'):  # some versions might use lowercase
    PLANET_SHORT_NAMES_LIST = const.planet_short_names

if not (PLANET_FULL_NAMES_LIST and PLANET_SHORT_NAMES_LIST and
        isinstance(PLANET_FULL_NAMES_LIST, list) and len(PLANET_FULL_NAMES_LIST) >= 9 and
        isinstance(PLANET_SHORT_NAMES_LIST, list) and len(PLANET_SHORT_NAMES_LIST) >= 9):
    print("WARNING: PyJHora planet name lists not found or incomplete. Using fallback for ZODIAC_MAP_UNIVERSAL.")
    PLANET_FULL_NAMES_LIST = ['Sun', 'Moon', 'Mars', 'Mercury', 'Jupiter', 'Venus', 'Saturn', 'Rahu', 'Ketu']
    PLANET_SHORT_NAMES_LIST = ["Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa", "Ra", "Ke"]

print("INFO: Populating ZODIAC_MAP_UNIVERSAL with planet names.")
# Ensure list type for safety, though the fallback guarantees it
if PLANET_FULL_NAMES_LIST and PLANET_SHORT_NAMES_LIST:
    common_len_names = min(len(PLANET_FULL_NAMES_LIST), len(PLANET_SHORT_NAMES_LIST))
    common_len_names = min(common_len_names, 9)  # Max 9 grahas for standard use
    for i in range(common_len_names):
        short_name = PLANET_SHORT_NAMES_LIST[i]
        full_name = PLANET_FULL_NAMES_LIST[i]
        if isinstance(full_name, str):
            full_name = full_name.capitalize()
        if short_name not in ZODIAC_MAP_UNIVERSAL:
            ZODIAC_MAP_UNIVERSAL[short_name] = full_name

# Rasi names from PyJHora const
if hasattr(const, 'RASHI_NAMES') and hasattr(const, 'RASHI_SHORT_NAMES'):
    if len(const.RASHI_NAMES) == 12 and len(const.RASHI_SHORT_NAMES) == 12:
        for i in range(12):
            short_name = const.RASHI_SHORT_NAMES[i]
            full_name = const.RASHI_NAMES[i]
            if short_name not in ZODIAC_MAP_UNIVERSAL:  # ZODIAC_MAP_UNIVERSAL already has them hardcoded, but this is safer
                ZODIAC_MAP_UNIVERSAL[short_name] = full_name
    else:
        print(
            "WARNING: PyJHora Rashi name lists are not of expected length (12). Rasi name expansion might be affected.")
else:
    print(
        "WARNING: PyJHora Rashi name lists (RASHI_NAMES, RASHI_SHORT_NAMES) not found in const module. Using hardcoded map.")


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
    iana_timezone_name: Optional[str] = None

    @property
    def tob_str(self) -> str: return self.time_of_birth.strftime("%H:%M:%S")

    @property
    def dob_str(self) -> str: return self.date_of_birth.strftime("%Y-%m-%d")


# --- Helper functions ---
def _format_datetime_from_jd(jd_val: float) -> str:
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
    if second >= 60: second = 0; minute += 1;  # Cascade seconds
    if minute >= 60: minute = 0; hour += 1;  # Cascade minutes
    if hour >= 24: hour = 0;  # Reset hour, assuming JD refers to start of Gregorian day.
    # PyJHora seems to handle day increments internally with JD.
    return f"{year:04d}-{month:02d}-{day:02d} {hour:02d}:{minute:02d}:{second:02d}"


def _parse_datetime_universal(date_str_with_time: str) -> str:
    try:
        dt = datetime.datetime.strptime(date_str_with_time, "%Y-%m-%d %H:%M:%S");
        return dt.isoformat()
    except ValueError:
        try:
            dt = datetime.datetime.strptime(date_str_with_time, "%Y-%m-%d");
            return dt.isoformat()
        except ValueError:
            print(f"Warning: Could not parse datetime string '{date_str_with_time}' to ISO format.")
            return date_str_with_time


def _expand_name_universal(name_short: str, dasha_system_name: str) -> str:
    return ZODIAC_MAP_UNIVERSAL.get(name_short.strip(), name_short.strip())


# --- Jatak.txt Parsing and Geocoding ---
def parse_jatak_txt(file_path: Path) -> List[Dict[str, str]]:
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
    if not place_str: return None, None, None, None, None, None
    geolocator = Nominatim(user_agent=GEOCODER_USER_AGENT, timeout=10)
    tf = TimezoneFinder()
    lat, lon, tz_offset, city, country, iana_tz_name = None, None, None, None, None, None
    try:
        print(f"      Geocoding '{place_str}'...")
        location = geolocator.geocode(place_str, language='en', addressdetails=True)
        time.sleep(1.1)  # Respect Nominatim usage policy
        if location and location.latitude is not None and location.longitude is not None:
            lat, lon = location.latitude, location.longitude
            raw_address = location.raw.get('address', {})
            city = raw_address.get('city', raw_address.get('town', raw_address.get('village', raw_address.get('county',
                                                                                                              place_str.split(
                                                                                                                  ',')[
                                                                                                                  0].strip()))))
            country = raw_address.get('country_code', '').upper()  # Use country code for more reliable India check
            if not country: country = raw_address.get('country', "Unknown")  # Fallback to full country name

            iana_tz_name = tf.timezone_at(lng=lon, lat=lat)
            if iana_tz_name:
                try:
                    timezone_obj = pytz.timezone(iana_tz_name)
                    birth_dt_naive = datetime.datetime.combine(dob, tob)
                    birth_dt_aware = timezone_obj.localize(birth_dt_naive,
                                                           is_dst=None)  # is_dst=None for historical ambiguity
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
        print(f"    ERROR: Geocoding service unavailable for '{place_str}'.")
    except GeocoderServiceError as e:
        print(f"    ERROR: Geocoding service error for '{place_str}': {e}")
    except Exception as e:
        print(f"    ERROR geocoding '{place_str}': {e}"); traceback.print_exc()

    if not city and place_str: city = place_str.split(',')[0].strip()
    # Ensure country name is full if only code was found previously
    if country and len(country) == 2:  # If it's a country code like 'IN'
        try:
            country_full_name = pytz.country_names[country.lower()]
            country = country_full_name
        except KeyError:
            print(f"    INFO: Could not expand country code '{country}' to full name.")
            # Keep the code or use a fallback from raw_address if available and more descriptive
            country = raw_address.get('country', country) if raw_address.get('country') else country

    return lat, lon, tz_offset, city, country, iana_tz_name


def process_raw_entries_to_birthdata(raw_entries: List[Dict[str, str]]) -> List[BirthData]:
    birth_data_list = []
    for i, entry in enumerate(raw_entries):
        print(f"\nProcessing Jatak Record {i + 1}/{len(raw_entries)}: {entry.get('Name', 'Unknown Name')}")
        name = entry.get("Name")
        date_str = entry.get("Date")
        time_str = entry.get("Time")
        place_str = entry.get("Place")
        gender = entry.get("Gender", "neutral")  # Allow Gender from Jatak.txt

        if not (name and date_str and time_str and place_str):
            print(f"    WARNING: Skipping record for '{name or 'Unknown'}' due to missing Name, Date, Time, or Place.");
            continue
        try:
            dob = datetime.datetime.strptime(date_str, "%B %d, %Y").date()
            tob = datetime.datetime.strptime(time_str, "%H:%M:%S").time()
        except ValueError as e:
            print(
                f"    ERROR: Could not parse date/time for {name} ('{date_str}','{time_str}'): {e}. Skipping record.");
            continue

        lat, lon, tz_offset, city, country, iana_tz_name = geocode_and_enrich_place(place_str, dob, tob)

        geocoding_successful_flag = False
        if lat is not None and lon is not None and tz_offset is not None:
            geocoding_successful_flag = True
        else:  # Fallback for India if TZ lookup failed but geocoding gave Indian location
            if country and ("india" in country.lower() or country == "IN") and tz_offset is None:
                print(
                    "    INFO: Geocoding indicated India, but TZ lookup failed. Using default TZ +5.5 for India as fallback.")
                tz_offset = 5.5
                if not iana_tz_name: iana_tz_name = "Asia/Kolkata (Assumed)"
                # Latitude/Longitude might still be missing or partially available. User should be aware.
                # If lat/lon are None, Horoscope object might fail. This is a critical point.
                if lat is None or lon is None:
                    print(
                        f"    CRITICAL: Lat/Lon still missing for {name} at '{place_str}' despite India fallback for TZ. Skipping record.")
                    continue  # Cannot proceed without Lat/Lon
                geocoding_successful_flag = True  # Considered successful for TZ
            else:
                print(
                    f"    CRITICAL: Geocoding/TZ information incomplete for {name} at '{place_str}'. Skipping record.")
                continue

        bd = BirthData(name=name, date_of_birth=dob, time_of_birth=tob, latitude=lat, longitude=lon,
                       timezone_offset=tz_offset, city_name=city, country_name=country, gender=gender,
                       raw_place_string=place_str, geocoding_success=geocoding_successful_flag,
                       iana_timezone_name=iana_tz_name)
        birth_data_list.append(bd)
        print(
            f"    Enriched: {name}, Lat:{lat:.4f}, Lon:{lon:.4f}, TZ Offset:{tz_offset}, City:'{city}', Country:'{country}', IANA TZ:'{iana_tz_name}', Gender:'{gender}'")
    return birth_data_list


# --- K.N. Rao Chara Dasha: Master Nested Text and JSON Generation ---
def generate_knrao_chara_text_for_universal_parser(h_obj: Horoscope, d1_chart_positions: list,
                                                   total_years_to_calculate: int) -> str:
    text_lines = []
    dasha_system_name = "K.N. Rao Chara Dasa"
    text_lines.append(f"{dasha_system_name}:")
    text_lines.append("Maha Dasas:")

    md_summary_lines = []
    md_detailed_blocks = []

    # Ensure RASHI_NAMES and RASHI_SHORT_NAMES are available
    if not (hasattr(const, 'RASHI_NAMES') and hasattr(const, 'RASHI_SHORT_NAMES') and
            len(const.RASHI_NAMES) == 12 and len(const.RASHI_SHORT_NAMES) == 12):
        print("ERROR (KNRAO): Rashi name constants not available or invalid. Cannot generate text.")
        return "Error during K.N. Rao Chara Dasa generation: Missing Rashi constants."

    try:
        md_progression_rasis = jhora_chara_dhasa._dhasa_progression_knrao_method(d1_chart_positions)
    except Exception as e:
        print(f"ERROR (KNRAO): Failed to get Dasha progression: {e}")
        return f"Error during K.N. Rao Chara Dasa generation: {e}"

    elapsed_total_years_for_mds = 0.0
    current_jd_for_mds = h_obj.julian_day
    one_year_in_days = const.SIDEREAL_YEAR

    max_md_cycles = (total_years_to_calculate // 1) + 3  # Generous cycle count, min MD duration is 1 year typically

    for cycle_num in range(max_md_cycles):
        if elapsed_total_years_for_mds >= total_years_to_calculate: break
        for md_rasi_index_current_cycle in md_progression_rasis:
            if elapsed_total_years_for_mds >= total_years_to_calculate: break

            md_start_jd_current_md = current_jd_for_mds
            try:
                md_total_duration_years_full = jhora_chara_dhasa._dhasa_duration_knrao_method(d1_chart_positions,
                                                                                              md_rasi_index_current_cycle)
            except Exception as e:
                print(f"ERROR (KNRAO): Failed to get MD duration for Rasi Index {md_rasi_index_current_cycle}: {e}")
                continue  # Skip this MD if duration calculation fails

            if md_total_duration_years_full <= 0: md_total_duration_years_full = 1.0  # Fallback for 0 duration

            remaining_years_for_target = total_years_to_calculate - elapsed_total_years_for_mds
            actual_md_run_duration_this_iteration = min(md_total_duration_years_full, remaining_years_for_target)

            if actual_md_run_duration_this_iteration <= 0 and total_years_to_calculate > elapsed_total_years_for_mds:
                # If this MD could run but we've hit the year limit precisely with previous MDs,
                # and this is a new MD, we might still want to calculate it if its theoretical duration fits.
                # However, the min(md_total_duration_years_full, remaining_years_for_target) should handle this.
                # This case is more for "if remaining_years_for_target is 0, but this is the first MD beyond that"
                # Let's be strict: if remaining_years_for_target is <=0, we don't run more MDs.
                pass  # The initial condition `elapsed_total_years_for_mds >= total_years_to_calculate` handles this.

            if actual_md_run_duration_this_iteration <= 0: continue

            md_end_jd_current_md = md_start_jd_current_md + (actual_md_run_duration_this_iteration * one_year_in_days)

            md_rasi_name_full = const.RASHI_NAMES[md_rasi_index_current_cycle]
            md_rasi_name_short = const.RASHI_SHORT_NAMES[md_rasi_index_current_cycle]
            md_start_str = _format_datetime_from_jd(md_start_jd_current_md)
            md_end_str = _format_datetime_from_jd(md_end_jd_current_md)

            md_summary_lines.append(f"  {md_rasi_name_full}: {md_start_str} - {md_end_str}")

            current_md_block = []
            current_md_block.append(f"{md_rasi_name_short} MD: {md_start_str} - {md_end_str}")
            current_md_block.append(f"Antardasas in this MD:")

            # ADs
            ad_proportional_duration_years = md_total_duration_years_full / 12.0
            if ad_proportional_duration_years > 0:
                current_ad_start_jd = md_start_jd_current_md
                try:
                    ad_start_progression_index = md_progression_rasis.index(md_rasi_index_current_cycle)
                except ValueError:  # Should not happen
                    print(f"ERROR (KNRAO): MD Rasi {md_rasi_name_short} not in progression. Skipping ADs.")
                    elapsed_total_years_for_mds += actual_md_run_duration_this_iteration
                    current_jd_for_mds = md_end_jd_current_md
                    continue

                for i in range(12):  # 12 ADs
                    if current_ad_start_jd >= md_end_jd_current_md: break  # AD cannot extend beyond MD

                    ad_rasi_index = md_progression_rasis[(ad_start_progression_index + i) % 12]
                    ad_rasi_name_short = const.RASHI_SHORT_NAMES[ad_rasi_index]
                    ad_start_jd_this_ad = current_ad_start_jd
                    ad_end_jd_this_ad = min(ad_start_jd_this_ad + (ad_proportional_duration_years * one_year_in_days),
                                            md_end_jd_current_md)

                    if ad_end_jd_this_ad <= ad_start_jd_this_ad:  # If no valid duration
                        current_ad_start_jd = ad_end_jd_this_ad  # effectively skips if ad_end = ad_start
                        continue

                    ad_start_str = _format_datetime_from_jd(ad_start_jd_this_ad)
                    ad_end_str = _format_datetime_from_jd(ad_end_jd_this_ad)
                    current_md_block.append(f"    {ad_rasi_name_short} AD: {ad_start_str} - {ad_end_str}")
                    current_md_block.append(f"    Pratyantardasas in this AD:")

                    # PDs
                    pd_proportional_duration_years = ad_proportional_duration_years / 12.0
                    if pd_proportional_duration_years > 0:
                        current_pd_start_jd = ad_start_jd_this_ad
                        try:
                            pd_start_progression_index = md_progression_rasis.index(ad_rasi_index)
                        except ValueError:
                            print(f"ERROR (KNRAO): AD Rasi {ad_rasi_name_short} not in progression. Skipping PDs.")
                            current_ad_start_jd = ad_end_jd_this_ad
                            continue

                        for j in range(12):  # 12 PDs
                            if current_pd_start_jd >= ad_end_jd_this_ad: break

                            pd_rasi_index = md_progression_rasis[(pd_start_progression_index + j) % 12]
                            pd_rasi_name_short = const.RASHI_SHORT_NAMES[pd_rasi_index]
                            pd_start_jd_this_pd = current_pd_start_jd
                            pd_end_jd_this_pd = min(
                                pd_start_jd_this_pd + (pd_proportional_duration_years * one_year_in_days),
                                ad_end_jd_this_ad)

                            if pd_end_jd_this_pd <= pd_start_jd_this_pd:
                                current_pd_start_jd = pd_end_jd_this_pd
                                continue

                            pd_start_str = _format_datetime_from_jd(pd_start_jd_this_pd)
                            pd_end_str = _format_datetime_from_jd(pd_end_jd_this_pd)
                            current_md_block.append(f"        {pd_rasi_name_short} PD: {pd_start_str} - {pd_end_str}")
                            current_md_block.append(f"        Sookshma-antardasas in this PD:")

                            # SDs
                            sd_proportional_duration_years = pd_proportional_duration_years / 12.0
                            if sd_proportional_duration_years > 0:
                                current_sd_start_jd = pd_start_jd_this_pd
                                try:
                                    sd_start_progression_index = md_progression_rasis.index(pd_rasi_index)
                                except ValueError:
                                    print(
                                        f"ERROR (KNRAO): PD Rasi {pd_rasi_name_short} not in progression. Skipping SDs.")
                                    current_pd_start_jd = pd_end_jd_this_pd
                                    continue

                                for k in range(12):  # 12 SDs
                                    if current_sd_start_jd >= pd_end_jd_this_pd: break

                                    sd_rasi_index = md_progression_rasis[(sd_start_progression_index + k) % 12]
                                    sd_rasi_name_short = const.RASHI_SHORT_NAMES[sd_rasi_index]
                                    sd_start_jd_this_sd = current_sd_start_jd
                                    sd_end_jd_this_sd = min(
                                        sd_start_jd_this_sd + (sd_proportional_duration_years * one_year_in_days),
                                        pd_end_jd_this_pd)

                                    if sd_end_jd_this_sd <= sd_start_jd_this_sd:
                                        current_sd_start_jd = sd_end_jd_this_sd
                                        continue

                                    sd_start_str = _format_datetime_from_jd(sd_start_jd_this_sd)
                                    sd_end_str = _format_datetime_from_jd(sd_end_jd_this_sd)
                                    current_md_block.append(
                                        f"            {sd_rasi_name_short} SD: {sd_start_str} - {sd_end_str}")
                                    current_sd_start_jd = sd_end_jd_this_sd
                                current_md_block.append("")  # After all SDs in a PD
                            current_pd_start_jd = pd_end_jd_this_pd
                        current_md_block.append("")  # After all PDs in an AD
                    current_ad_start_jd = ad_end_jd_this_ad
                current_md_block.append("")  # After all ADs in an MD

            md_detailed_blocks.extend(current_md_block)
            md_detailed_blocks.append("")  # Blank line between MD blocks

            elapsed_total_years_for_mds += actual_md_run_duration_this_iteration
            current_jd_for_mds = md_end_jd_current_md  # Start of next MD is end of current

    text_lines.extend(md_summary_lines)
    text_lines.append("")
    text_lines.extend(md_detailed_blocks)
    return "\n".join(text_lines)


# --- Vimsottari Dasha Text Generation (for Nested JSON) ---
def generate_vimsottari_text_for_universal_parser(h_obj: Horoscope) -> str:
    text_lines = [];
    dasha_system_name = "Vimsottari Dasa";
    text_lines.append(f"{dasha_system_name}:");
    text_lines.append("Maha Dasas:")

    # Ensure PLANET_FULL_NAMES_LIST and PLANET_SHORT_NAMES_LIST are valid
    if not (PLANET_FULL_NAMES_LIST and PLANET_SHORT_NAMES_LIST and
            len(PLANET_FULL_NAMES_LIST) >= 9 and len(PLANET_SHORT_NAMES_LIST) >= 9):
        print("ERROR (Vimsottari): Planet name lists not available or invalid. Cannot generate text.")
        return "Error during Vimsottari Dasa generation: Missing planet name constants."

    jd_dob = h_obj.julian_day
    try:
        mahadashas_dict = jhora_vimsottari_std.vimsottari_mahadasa(jd=jd_dob, place=h_obj.Place,
                                                                   dhasa_starting_planet=1)  # Default start from Moon's nakshatra lord
    except Exception as e:
        print(f"ERROR (Vimsottari): Failed to get Mahadashas: {e}")
        return f"Error during Vimsottari Dasa generation: {e}"

    md_summary_lines = [];
    md_detailed_blocks = []
    sorted_md_lords = sorted(mahadashas_dict.keys(), key=lambda lord: mahadashas_dict[lord])

    for md_idx_loop, md_lord_idx in enumerate(sorted_md_lords):
        md_start_jd_val = mahadashas_dict[md_lord_idx]
        md_lord_name_full = PLANET_FULL_NAMES_LIST[md_lord_idx].capitalize()
        md_lord_name_short = PLANET_SHORT_NAMES_LIST[md_lord_idx]
        md_dur_years = jhora_vimsottari_std.vimsottari_dict[md_lord_idx]
        md_end_jd_val = md_start_jd_val + (md_dur_years * const.SIDEREAL_YEAR)

        md_start_str = _format_datetime_from_jd(md_start_jd_val);
        md_end_str = _format_datetime_from_jd(md_end_jd_val)
        md_summary_lines.append(f"  {md_lord_name_full}: {md_start_str} - {md_end_str}")

        current_md_block = [];
        current_md_block.append(f"{md_lord_name_short} MD: {md_start_str} - {md_end_str}");
        current_md_block.append(f"Antardasas in this MD:")

        try:
            antardashas_dict = jhora_vimsottari_std._vimsottari_bhukti(md_lord_idx, md_start_jd_val)
        except Exception as e:
            print(f"ERROR (Vimsottari): Failed to get Bhuktis for MD {md_lord_name_short}: {e}")
            continue  # Skip ADs for this MD if error

        sorted_ad_lords = sorted(antardashas_dict.keys(), key=lambda lord: antardashas_dict[lord])
        for ad_lord_idx in sorted_ad_lords:
            ad_start_jd_val = antardashas_dict[ad_lord_idx];
            ad_lord_name_short = PLANET_SHORT_NAMES_LIST[ad_lord_idx]
            ad_dur_prop_md = jhora_vimsottari_std.vimsottari_dict[ad_lord_idx]
            ad_dur_years = (
                                       ad_dur_prop_md * md_dur_years) / const.HUMAN_LIFE_SPAN_FOR_VIMSOTTARI_DHASA  # PyJHora uses this const
            ad_end_jd_val_calculated = ad_start_jd_val + (ad_dur_years * const.SIDEREAL_YEAR)

            # Cap AD end by the start of the next MD or the end of the current MD
            ad_end_jd_val = ad_end_jd_val_calculated
            if md_idx_loop + 1 < len(sorted_md_lords):
                next_md_start_jd = mahadashas_dict[sorted_md_lords[md_idx_loop + 1]]
                ad_end_jd_val = min(ad_end_jd_val, next_md_start_jd)
            ad_end_jd_val = min(ad_end_jd_val, md_end_jd_val)  # Ensure AD does not exceed its MD

            if ad_start_jd_val >= ad_end_jd_val: continue  # Skip if no duration

            ad_start_str = _format_datetime_from_jd(ad_start_jd_val);
            ad_end_str = _format_datetime_from_jd(ad_end_jd_val)
            current_md_block.append(f"    {ad_lord_name_short} AD: {ad_start_str} - {ad_end_str}");
            current_md_block.append(f"    Pratyantardasas in this AD:")

            try:
                pratyantardashas_dict = jhora_vimsottari_std._vimsottari_antara(md_lord_idx, ad_lord_idx,
                                                                                ad_start_jd_val)
            except Exception as e:
                print(f"ERROR (Vimsottari): Failed to get Antaras for AD {ad_lord_name_short}: {e}")
                continue

            sorted_pd_lords = sorted(pratyantardashas_dict.keys(), key=lambda lord: pratyantardashas_dict[lord])
            for pd_lord_idx in sorted_pd_lords:
                pd_start_jd_val = pratyantardashas_dict[pd_lord_idx];
                pd_lord_name_short = PLANET_SHORT_NAMES_LIST[pd_lord_idx]
                pd_dur_prop_ad = jhora_vimsottari_std.vimsottari_dict[pd_lord_idx]
                pd_dur_years = (pd_dur_prop_ad * ad_dur_years) / const.HUMAN_LIFE_SPAN_FOR_VIMSOTTARI_DHASA
                pd_end_jd_val_calculated = pd_start_jd_val + (pd_dur_years * const.SIDEREAL_YEAR);
                pd_end_jd_val = min(pd_end_jd_val_calculated, ad_end_jd_val)  # Cap by AD end

                if pd_start_jd_val >= pd_end_jd_val: continue

                pd_start_str = _format_datetime_from_jd(pd_start_jd_val);
                pd_end_str = _format_datetime_from_jd(pd_end_jd_val)
                current_md_block.append(f"        {pd_lord_name_short} PD: {pd_start_str} - {pd_end_str}");
                current_md_block.append(f"        Sookshma-antardasas in this PD:")

                # Sookshma Dasa calculation (proportional within PD)
                sookshmadashas_dict = {};
                current_sd_start_jd_val = pd_start_jd_val;
                sd_lord_iter_start_idx = pd_lord_idx  # Sookshma starts from PD lord

                # Generate SD sequence starting from pd_lord_idx
                sd_lord_iter_idx = sd_lord_iter_start_idx
                for _sd_loop_idx in range(9):  # Iterate 9 times for all Sookshma lords in sequence
                    sookshmadashas_dict[sd_lord_iter_idx] = current_sd_start_jd_val  # Store start JD

                    sd_dur_prop_pd = jhora_vimsottari_std.vimsottari_dict[sd_lord_iter_idx]
                    sd_dur_years_iter = (sd_dur_prop_pd * pd_dur_years) / const.HUMAN_LIFE_SPAN_FOR_VIMSOTTARI_DHASA
                    current_sd_start_jd_val += (
                                sd_dur_years_iter * const.SIDEREAL_YEAR)  # End of this SD is start of next

                    sd_lord_iter_idx = jhora_vimsottari_std.vimsottari_next_adhipati(
                        sd_lord_iter_idx)  # Get next lord in Vimsottari sequence

                # Sort by start date just in case, though direct calculation should be ordered
                sorted_sd_lords = sorted(sookshmadashas_dict.keys(), key=lambda lord: sookshmadashas_dict[lord])

                for sd_lord_idx_val in sorted_sd_lords:
                    sd_start_jd_val_iter = sookshmadashas_dict[sd_lord_idx_val];
                    sd_lord_name_short_iter = PLANET_SHORT_NAMES_LIST[sd_lord_idx_val]
                    sd_dur_prop_pd_iter = jhora_vimsottari_std.vimsottari_dict[sd_lord_idx_val]
                    sd_dur_years_final = (
                                                     sd_dur_prop_pd_iter * pd_dur_years) / const.HUMAN_LIFE_SPAN_FOR_VIMSOTTARI_DHASA
                    sd_end_jd_val_iter_calculated = sd_start_jd_val_iter + (sd_dur_years_final * const.SIDEREAL_YEAR);
                    sd_end_jd_val_iter = min(sd_end_jd_val_iter_calculated, pd_end_jd_val)  # Cap by PD end

                    if sd_start_jd_val_iter >= sd_end_jd_val_iter: continue

                    sd_start_str_iter = _format_datetime_from_jd(sd_start_jd_val_iter);
                    sd_end_str_iter = _format_datetime_from_jd(sd_end_jd_val_iter)
                    current_md_block.append(
                        f"            {sd_lord_name_short_iter} SD: {sd_start_str_iter} - {sd_end_str_iter}")
                current_md_block.append("")  # After all SDs in a PD
            current_md_block.append("")  # After all PDs in an AD
        md_detailed_blocks.extend(current_md_block);
        md_detailed_blocks.append("")  # After all ADs in an MD

    text_lines.extend(md_summary_lines);
    text_lines.append("");
    text_lines.extend(md_detailed_blocks)
    return "\n".join(text_lines)


# --- Universal Dasha Parser Logic ---
def parse_dasha_text_content(text_content: str, person_name: str,
                             dasha_system_source_id: str,
                             birth_params: Optional[Dict] = None) -> dict:
    lines = [line for line in text_content.splitlines()]  # Keep original spacing for regex
    parsed_data = {"person_name": person_name,
                   "birth_parameters_used": birth_params or {},
                   "dasha_system_name": "Unknown Dasha System",
                   "source_file": dasha_system_source_id, "dasas": []}

    dasha_system_header_pattern = re.compile(r"^\s*([A-Za-z0-9\s\(\)\-\._':]+? Dasa(?: \([^)]+\))?):")
    # Regex to capture optional type (MD, AD, PD, SD) and ensure name is non-greedy
    period_line_regex = re.compile(
        r"^(?P<indent>\s*)(?P<name>[A-Za-z0-9\s]+?)\s*(?P<type>MD|AD|PD|SD)?:\s*(?P<start_date>\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2})\s*-\s*(?P<end_date>\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2})")
    # Summary only has name and dates, no explicit MD/AD/PD/SD type marker in the line itself usually
    summary_period_line_regex = re.compile(
        r"^\s*(?P<name>[A-Za-z0-9\s]+?):\s*(?P<start_date>\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2})\s*-\s*(?P<end_date>\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2})")

    context_stack = [];
    current_dasha_system_name = "Unknown Dasa";
    first_dasha_system_header_found = False

    for line_num, line_content in enumerate(lines):  # First pass for Dasha System Name
        stripped_line = line_content.strip()
        if not first_dasha_system_header_found:
            match_ds_header = dasha_system_header_pattern.match(stripped_line)
            if match_ds_header:
                current_dasha_system_name = match_ds_header.group(1).strip()
                parsed_data["dasha_system_name"] = current_dasha_system_name
                first_dasha_system_header_found = True
                break  # Found it, stop this loop

    if not first_dasha_system_header_found:  # Fallback if header pattern not found
        if "Vimsottari" in dasha_system_source_id:
            parsed_data["dasha_system_name"] = "Vimsottari Dasa"
        elif "K.N. Rao Chara Dasa" in dasha_system_source_id:
            parsed_data["dasha_system_name"] = "K.N. Rao Chara Dasa"
        print(
            f"Warning: Dasha system name not found via regex in text from '{dasha_system_source_id}'. Using fallback: '{parsed_data['dasha_system_name']}'")

    is_in_summary_block = False
    # section_header_to_level maps a descriptive header to the *level of the sub-periods it introduces*
    # The keys are the headers that *precede* the list of periods of a certain type
    # e.g., "Antardasas in this MD:" precedes a list of Level 2 periods.
    section_header_to_level = {
        "Maha Dasas:": 1,  # This indicates the following lines are Mahadashas (Level 1) in summary format
        "Antardasas in this MD:": 2,
        "Pratyantardasas in this AD:": 3,
        "Sookshma-antardasas in this PD:": 4
    }
    # period_type_by_level is used when the period line itself (e.g. "Su MD:") indicates the level
    period_type_by_level = {1: "Mahadasha", 2: "Antardasha", 3: "Pratyantardasha", 4: "Sookshma-antardasha"}

    for line_num, line_content in enumerate(lines):
        stripped_line = line_content.strip()
        if not stripped_line: continue

        # Skip the main Dasha system header line if it's encountered again
        if dasha_system_header_pattern.match(stripped_line): continue

        # Check for section headers that define the context for subsequent lines
        is_section_header = False
        for header, _ in section_header_to_level.items():
            if stripped_line == header:
                is_in_summary_block = (
                            header == "Maha Dasas:")  # Only "Maha Dasas:" implies summary format for subsequent lines
                is_section_header = True
                break
        if is_section_header:
            continue  # Move to the next line, this line was just a header

        # Try matching detailed period line first (e.g., "Su MD: ...")
        match = period_line_regex.match(line_content)  # Use line_content to get indent for detailed

        level = 0
        period_type_str = ""
        data = None

        if match:
            data = match.groupdict()
            period_type_shorthand = data['type']  # MD, AD, PD, SD
            if period_type_shorthand == "MD":
                level = 1
            elif period_type_shorthand == "AD":
                level = 2
            elif period_type_shorthand == "PD":
                level = 3
            elif period_type_shorthand == "SD":
                level = 4

            if level > 0:
                period_type_str = period_type_by_level[level]
            is_in_summary_block = False  # A detailed line means we are out of summary block

        elif is_in_summary_block:  # If in summary block, try summary regex (e.g. "Sun: ...")
            match_summary = summary_period_line_regex.match(stripped_line)
            if match_summary:
                data = match_summary.groupdict()
                level = 1  # Summary lines are assumed to be Mahadashas
                period_type_str = period_type_by_level[level]

        if data and level > 0:
            name_short = data['name'].strip()
            period_obj = {"level": level, "period_type": period_type_str,
                          "name": _expand_name_universal(name_short, current_dasha_system_name),
                          "start_datetime": _parse_datetime_universal(data['start_date']),
                          "end_datetime": _parse_datetime_universal(data['end_date']), "sub_periods": []}

            # Manage context stack: pop levels until current level fits
            while context_stack and level <= context_stack[-1]['level']:
                context_stack.pop()

            if not context_stack:  # If stack is empty
                if level == 1:  # Only level 1 can be at the root
                    parsed_data["dasas"].append(period_obj)
                    context_stack.append(period_obj)
                # else: Error or unexpected line, ignore for now
            else:  # Stack is not empty, means we are adding a sub-period
                parent_period = context_stack[-1]
                if level == parent_period['level'] + 1:  # Valid sub-period
                    parent_period["sub_periods"].append(period_obj)
                    context_stack.append(period_obj)
                # else: Error like trying to add L3 under L1, ignore for now

            # If this was a Level 1 period (MD), and it was parsed from a detailed line (not summary),
            # then subsequent non-indented lines are not part of its summary.
            if level == 1 and match:  # 'match' implies detailed line like "Su MD: ..."
                is_in_summary_block = False
    return parsed_data


# --- Main Execution Logic ---
def main():
    print("--- PyJHora Data Extractor (Multi-Jatak & Master Nested Dasha Focus) ---")
    if not JATAK_FILE_PATH.is_file():
        print(f"ERROR: Input file Jatak.txt not found at {JATAK_FILE_PATH}. Exiting.")
        return

    raw_jatak_entries = parse_jatak_txt(JATAK_FILE_PATH)
    if not raw_jatak_entries: print("No records found in Jatak.txt. Exiting."); return

    all_birth_data = process_raw_entries_to_birthdata(raw_jatak_entries)
    if not all_birth_data: print("No birth data successfully processed after geocoding. Exiting."); return

    for current_birth_data in all_birth_data:
        print(f"\n\n--- Processing Dasha for: {current_birth_data.name} ---")
        h: Optional[Horoscope] = None

        birth_params_for_json = {
            "name": current_birth_data.name,  # Added for completeness in birth_params
            "date_of_birth": current_birth_data.dob_str,
            "time_of_birth": current_birth_data.tob_str,
            "latitude": current_birth_data.latitude,
            "longitude": current_birth_data.longitude,
            "timezone_offset": current_birth_data.timezone_offset,
            "city_name": current_birth_data.city_name,
            "country_name": current_birth_data.country_name,
            "raw_place_string": current_birth_data.raw_place_string,
            "iana_timezone_name": current_birth_data.iana_timezone_name,
            "geocoding_success": current_birth_data.geocoding_success,
            "ayanamsa_mode": DEFAULT_AYANAMSA_MODE  # Initial, will be updated if Horoscope obj created
        }
        try:
            drik_birth_date_obj = drik.Date(year=current_birth_data.date_of_birth.year,
                                            month=current_birth_data.date_of_birth.month,
                                            day=current_birth_data.date_of_birth.day)
            h = Horoscope(date_in=drik_birth_date_obj, birth_time=current_birth_data.tob_str,
                          latitude=current_birth_data.latitude, longitude=current_birth_data.longitude,
                          timezone_offset=current_birth_data.timezone_offset, ayanamsa_mode=DEFAULT_AYANAMSA_MODE)
            birth_params_for_json["ayanamsa_mode"] = h.ayanamsa_mode  # Update with actual Ayanamsa used by Horoscope
        except Exception as e:
            print(f"    ERROR Horoscope setup for {current_birth_data.name}: {e}");
            traceback.print_exc();
            continue
        if not h: continue

        person_dir_name_safe = re.sub(r'[^\w_.)( -]', '', current_birth_data.name.replace(" ", "_"))  # Sanitize name
        time_suffix_folder = current_birth_data.time_of_birth.strftime("%H%M")
        person_folder_name = f"{person_dir_name_safe}_{time_suffix_folder}"

        person_output_base_path = OUTPUT_BASE_PATH / person_folder_name
        dataset_folder_path = person_output_base_path / "DataSet"  # DataSet subfolder
        try:
            dataset_folder_path.mkdir(parents=True, exist_ok=True)  # Create DataSet folder
        except OSError as oe:
            print(f"    ERROR creating output directory {dataset_folder_path}: {oe}");
            continue

        geo_info_path = person_output_base_path / f"{person_dir_name_safe}_GeoTimeZone_Info.txt"
        try:
            with open(geo_info_path, 'w', encoding='utf-8') as f_geo:
                f_geo.write(f"Geo and Timezone Information for: {current_birth_data.name}\n" + \
                            f"Raw Place String: {current_birth_data.raw_place_string}\n" + \
                            f"Determined City: {current_birth_data.city_name}\n" + \
                            f"Determined Country: {current_birth_data.country_name}\n" + \
                            f"Determined Latitude: {current_birth_data.latitude:.6f}\n" + \
                            f"Determined Longitude: {current_birth_data.longitude:.6f}\n" + \
                            f"Determined IANA Timezone: {current_birth_data.iana_timezone_name}\n" + \
                            f"Determined Timezone Offset (hours from UTC): {current_birth_data.timezone_offset}\n" + \
                            f"Geocoding Success: {current_birth_data.geocoding_success}\n" + \
                            f"Gender: {current_birth_data.gender}\n")
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
            knrao_text_generated = generate_knrao_chara_text_for_universal_parser(h, d1_positions,
                                                                                  KNRAO_CHARA_TOTAL_YEARS)

            raw_text_knrao_filepath = dataset_folder_path / f"{person_dir_name_safe}_KNRaoCharaDasa_PyJHora_RawText.txt"
            try:
                with open(raw_text_knrao_filepath, 'w', encoding='utf-8') as f_text:
                    f_text.write(knrao_text_generated)
                print(f"    Saved K.N. Rao Chara Dasha Raw Text to: {raw_text_knrao_filepath}")
            except Exception as e:
                print(f"    ERROR saving K.N. Rao Chara Dasha Raw Text: {e}")

            if "Error during K.N. Rao Chara Dasa generation" not in knrao_text_generated:
                master_knrao_nested_data = parse_dasha_text_content(
                    knrao_text_generated, current_birth_data.name,
                    f"K.N. Rao Chara Dasa Master (PyJHora - {current_birth_data.name})",
                    birth_params=birth_params_for_json
                )
                master_knrao_filepath = dataset_folder_path / f"{person_dir_name_safe}-KNRaoCharaDasa-Master_Nested.json"
                try:
                    with open(master_knrao_filepath, 'w', encoding='utf-8') as f_json:
                        json.dump(master_knrao_nested_data, f_json, indent=2, ensure_ascii=False)
                    print(f"    Saved Master Nested K.N. Rao Chara Dasha to: {master_knrao_filepath}")
                except Exception as e:
                    print(f"    ERROR saving Master KNRao JSON for {current_birth_data.name}: {e}")
            else:
                print(
                    f"    Skipping Master Nested K.N. Rao Chara Dasha JSON for {current_birth_data.name} due to generation error.")
        else:
            print(
                f"    Skipping K.N. Rao Chara Dasha for {current_birth_data.name} (D1 chart error or other critical issue).")

        # --- Master Nested Vimsottari Dasha ---
        print(f"    Generating Master Nested Vimsottari Dasha for {current_birth_data.name}...")
        vimsottari_text_generated = generate_vimsottari_text_for_universal_parser(h)

        raw_text_vimsottari_filepath = dataset_folder_path / f"{person_dir_name_safe}_VimsottariDasa_PyJHora_RawText.txt"
        try:
            with open(raw_text_vimsottari_filepath, 'w', encoding='utf-8') as f_text:
                f_text.write(vimsottari_text_generated)
            print(f"    Saved Vimsottari Dasha Raw Text to: {raw_text_vimsottari_filepath}")
        except Exception as e:
            print(f"    ERROR saving Vimsottari Dasha Raw Text: {e}")

        if "Error during Vimsottari Dasa generation" not in vimsottari_text_generated:
            master_vimsottari_nested_data = parse_dasha_text_content(
                vimsottari_text_generated, current_birth_data.name,
                f"Vimsottari Dasa Master (PyJHora - {current_birth_data.name})",
                birth_params=birth_params_for_json
            )
            master_vimsottari_filepath = dataset_folder_path / f"{person_dir_name_safe}-VimsottariDasa-Master_Nested.json"
            try:
                with open(master_vimsottari_filepath, 'w', encoding='utf-8') as f_json:
                    json.dump(master_vimsottari_nested_data, f_json, indent=2, ensure_ascii=False)
                print(f"    Saved Master Nested Vimsottari Dasha to: {master_vimsottari_filepath}")
            except Exception as e:
                print(f"    ERROR saving Master Vimsottari JSON for {current_birth_data.name}: {e}")
        else:
            print(f"    Skipping Master Nested Vimsottari for {current_birth_data.name} due to generation error.")

    print("\n\n--- All Processing Complete ---")


if __name__ == "__main__":
    main()