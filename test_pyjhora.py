# test_pyjhora.py
# Focused data extraction based on jhora.horoscope.main.Horoscope structure

from jhora.horoscope.main import Horoscope
from jhora.panchanga import drik  # For drik.Date object
from jhora import const, utils  # For access to constants and utility functions if needed
from datetime import datetime
import sys
import json  # For pretty printing

print(f"Script started at: {datetime.now()}")

# --- Define Birth Details (inputs to Horoscope class) ---
person_name_for_reference = "PVR Narasimha Rao (Test)"  # Store descriptive info separately
birth_details = {
    "latitude": 16.1833,
    "longitude": 81.1333,
    "timezone_offset": 5.5,
    "date_in": drik.Date(1969, 8, 15),
    "birth_time": f"{9:02d}:{15:02d}:{0:02d}",  # "HH:MM:SS"
    "ayanamsa_mode": "LAHIRI",  # As per const.available_ayanamsa_modes
    "language": 'en'
    # Other parameters like 'calculation_type', 'years', 'bhava_madhya_method' can be added if needed,
    # otherwise they will use defaults from Horoscope.__init__
}

# This dictionary will hold all extracted data
extracted_data = {
    "person_for_reference": person_name_for_reference,
    "input_birth_details": {
        "latitude": birth_details["latitude"],
        "longitude": birth_details["longitude"],
        "timezone_offset": birth_details["timezone_offset"],
        "date_str": f"{birth_details['date_in'].year}-{birth_details['date_in'].month}-{birth_details['date_in'].day}",
        "time_str": birth_details["birth_time"],
        "ayanamsa_mode": birth_details["ayanamsa_mode"],
        "language": birth_details["language"],
    },
    "horoscope_object_attributes": {},
    "calendar_information": {},
    "bhava_chart_information": [],
    "d1_rasi_chart_details": {},
    "d1_rasi_chart_placements_raw": [],  # Raw planet strings per house
    "d1_rasi_ascendant_house_idx": -1,
    "all_divisional_chart_details": {},  # Will store aggregated D-chart data
    "dasha_systems": {},  # To be populated later
    "yogas": {},  # To be populated later
    "other_calculations": {}  # For Arudhas, Ashtakavarga etc.
}

try:
    print(f"\n1. Creating Horoscope object with parameters:")
    for k, v in birth_details.items():
        if isinstance(v, drik.Date):
            print(f"   {k}: drik.Date({v.year},{v.month},{v.day})")
        else:
            print(f"   {k}: {v}")

    h = Horoscope(**birth_details)  # Pass dictionary as keyword arguments
    print("   Horoscope object 'h' created successfully.")

    # Store some direct attributes from 'h' if they are simple values
    extracted_data["horoscope_object_attributes"]["julian_day"] = h.julian_day
    extracted_data["horoscope_object_attributes"]["ayanamsa_value"] = h.ayanamsa_value
    extracted_data["horoscope_object_attributes"]["place_name_resolved"] = h.place_name
    # ... any other simple attributes directly on h ...

    # Extract data populated by __init__
    if hasattr(h, 'calendar_info'):
        extracted_data["calendar_information"] = h.calendar_info
        print("   Extracted calendar_information.")
    if hasattr(h, 'bhava_chart_info'):
        extracted_data["bhava_chart_information"] = h.bhava_chart_info  # List of tuples
        print("   Extracted bhava_chart_information.")

    # Call get_horoscope_information_for_chart for D1 (Rasi)
    print("\n2. Calling h.get_horoscope_information_for_chart() for D1 (Rasi Chart)...")
    d1_details, d1_placements, d1_asc = h.get_horoscope_information_for_chart(chart_index=0)
    extracted_data["d1_rasi_chart_details"] = d1_details
    extracted_data["d1_rasi_chart_placements_raw"] = d1_placements
    extracted_data["d1_rasi_ascendant_house_idx"] = d1_asc
    print("   D1 Rasi Chart data extracted.")

    # Optional: Call get_horoscope_information() for all standard D-charts
    # This can be time-consuming as it calculates many charts.
    # You can enable this later if needed.
    # print("\n3. Calling h.get_horoscope_information() for all standard D-charts (can be slow)...")
    # all_d_chart_details, _, _ = h.get_horoscope_information()
    # extracted_data["all_divisional_chart_details"] = all_d_chart_details
    # print("   All standard D-chart data extracted.")

    # NEXT: Based on the structure of 'd1_chart_details' and how other modules work,
    # we would add calls to functions from:
    # - jhora.horoscope.chart.yoga (needs Rasi planet positions, often as a simple list per house)
    # - jhora.horoscope.chart.dhasa... (needs various inputs, DOB, TOB, Place, Moon long etc.)
    # - jhora.horoscope.chart.arudhas (needs Rasi planet positions)
    # - etc.

    # For example, to get the Rasi planet positions in a format usable by other modules:
    # We need to parse d1_chart_details or see if h object exposes planet_positions directly now
    # Let's assume `d1_details` has keys like "Rasi-Sun", "Rasi-Moon", etc.
    # This is a placeholder, actual parsing logic depends on d1_details format.

    # To get planet_positions list like [[planet_id, (house_idx, longitude_in_house)], ...],
    # which is a common input for many functions in jhora.horoscope.chart:
    # The `Horoscope.get_horoscope_information_for_chart` method itself calls
    # `charts.divisional_chart` which returns this structure.
    # We need to see if this list is easily accessible or reconstructable.
    # For now, `d1_details` dictionary holds the info in string format.

    # Let's obtain Rasi planet positions in the structured list format:
    print("\n4. Obtaining structured Rasi planet positions (D1)...")
    # The rasi_chart function from charts.py is what get_horoscope_information_for_chart uses internally for D1.
    # jd_at_dob for the Horoscope object is self.julian_day
    # place_as_tuple is self.Place
    # ayanamsa_mode is self.ayanamsa_mode
    # We need the `charts` module.
    from jhora.horoscope.chart import charts as jhc_charts

    structured_d1_planet_positions = jhc_charts.rasi_chart(
        jd_at_dob=h.julian_day,
        place_as_tuple=h.Place,
        ayanamsa_mode=h.ayanamsa_mode
        # Assuming other params like years, months, pravesha_type use defaults for natal chart
    )
    extracted_data["other_calculations"]["d1_structured_planet_positions"] = structured_d1_planet_positions
    print(f"   Structured D1 Planet Positions (first 3): {structured_d1_planet_positions[:3]}")

    # Now we can use `structured_d1_planet_positions` for other calculations.
    # Example: Arudhas
    from jhora.horoscope.chart import arudhas as jhc_arudhas

    print("\n5. Calculating Bhava Arudhas for D1...")
    bhava_arudhas_d1 = jhc_arudhas.bhava_arudhas_from_planet_positions(structured_d1_planet_positions)
    extracted_data["other_calculations"]["d1_bhava_arudhas"] = bhava_arudhas_d1
    print(f"   Bhava Arudhas for D1 (A1 to A12 Rasi Indices): {bhava_arudhas_d1}")

    # Example: Yogas (many yoga functions take 'planet_positions' or a 'house_to_planet_list')
    # To convert structured_d1_planet_positions to house_to_planet_list (list of strings per house):
    # `jhc_utils` refers to `jhora.utils`
    h_to_p_list_d1 = utils.get_house_planet_list_from_planet_positions(structured_d1_planet_positions)
    extracted_data["other_calculations"]["d1_house_to_planet_list"] = h_to_p_list_d1
    print(f"\n6. D1 House to Planet List (for yoga checks etc.): {h_to_p_list_d1[:4]}...")  # Print first 4 houses

    from jhora.horoscope.chart import yoga as jhc_yoga

    print("\n7. Checking for some Yogas in D1...")
    vesi_present = jhc_yoga.vesi_yoga_from_planet_positions(
        structured_d1_planet_positions)  # Many yoga funcs take planet_positions
    extracted_data["yogas"]["d1_vesi_yoga"] = vesi_present
    print(f"   Vesi Yoga present in D1: {vesi_present}")

    # Example for a yoga that might need house_to_planet_list if originally written that way
    # kemadruma_present = jhc_yoga.kemadruma_yoga_from_planet_positions(structured_d1_planet_positions)
    # print(f"   Kemadruma Yoga present in D1: {kemadruma_present}")

    print("\nExtraction process completed.")

except Exception as e:
    print(f"\nAN ERROR OCCURRED:")
    print(f"  Type: {type(e).__name__}")
    print(f"  Details: {e}")
    import traceback

    traceback.print_exc()

finally:
    print("\n\n--- FINAL EXTRACTED DATA (JSON Summary) ---")


    # We need a custom handler for drik.Date and other non-serializable objects if any
    def custom_serializer(obj):
        if isinstance(obj, drik.Date):
            return f"drik.Date({obj.year},{obj.month},{obj.day})"
        if isinstance(obj, tuple) and hasattr(obj, '_fields'):  # namedtuple
            return dict(obj._asdict())
        try:
            return str(obj)  # Fallback for other unhandled types
        except:
            return f"<Object of type {type(obj).__name__} not serializable>"


    # Pretty print the main extracted_data dictionary
    # Be cautious if any sub-dictionaries are massive
    try:
        # Let's limit what we try to JSON serialize initially to avoid overly complex objects
        summary_data = {
            "person_for_reference": extracted_data["person_for_reference"],
            "input_birth_details": extracted_data["input_birth_details"],
            "horoscope_object_attributes": extracted_data["horoscope_object_attributes"],
            # "calendar_information": extracted_data["calendar_information"], # Can be large
            # "bhava_chart_information": extracted_data["bhava_chart_information"], # List of tuples
            "d1_rasi_ascendant_house_idx": extracted_data["d1_rasi_ascendant_house_idx"],
            "other_calculations_summary": {
                "d1_bhava_arudhas_count": len(extracted_data["other_calculations"].get("d1_bhava_arudhas", [])),
                "d1_h_to_p_first_4": extracted_data["other_calculations"].get("d1_house_to_planet_list", [])[:4]
            },
            "yogas_summary": extracted_data["yogas"]
        }
        print(json.dumps(summary_data, indent=2, default=custom_serializer, ensure_ascii=False))
    except Exception as json_e:
        print(f"Error during JSON serialization for summary: {json_e}")
        print("Printing keys of extracted_data instead:")
        for k in extracted_data.keys():
            print(f"- {k}")

    # To save ALL extracted data to a file (d1_chart_details can be very large):
    # with open("extracted_horoscope_data.json", "w", encoding="utf-8") as f:
    #    json.dump(extracted_data, f, indent=2, default=custom_serializer, ensure_ascii=False)
    # print("\nFull extracted data saved to extracted_horoscope_data.json (if uncommented)")

print(f"\nScript finished at: {datetime.now()}")