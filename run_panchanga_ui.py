# run_panchanga_ui.py

from jhora.ui.panchangam import Panchanga
# from jhora import utils # utils is used internally by Panchanga, not directly here
import sys
# from _datetime import datetime # This import might be from an older context or specific need
                              # Panchanga class will handle its own datetime needs.
                              # Let's try without it first, standard datetime is usually available.
import datetime # Standard Python datetime

from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QLineEdit, QLabel, QComboBox
from PyQt6.QtCore import QDate
from jhora.panchanga import drik # For drik.Date and drik.Place if needed

# --- Define a simple input widget for the Panchanga UI ---
# The Panchanga class in PyJHora is a QWidget, but it doesn't seem to have
# input fields directly. It expects to be given data or compute it based on
# attributes set before calling compute_horoscope().
# We need to simulate how it would get its data.
# For simplicity, we'll hardcode the data for now when calling compute_horoscope.

class PanchangaLauncher(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PyJHora Panchanga Launcher")
        self.layout = QVBoxLayout(self)

        # --- Minimal Inputs often needed by Horoscope objects ---
        # We will set these directly on the Panchanga object

        self.panchanga_widget = Panchanga() # Create the Panchanga widget

        # Hardcode Abhijeet's details for this test
        # These attributes need to be set on the panchanga_widget instance
        # before calling compute_horoscope.
        # The Panchanga class inherits from Horoscope_Chart_Tab, which inherits from Horo_Chart_Tabs_UI,
        # which in turn has attributes like self.date_of_birth, self.birth_time, self.Place etc.

        name = "Abhijeet Singh Chauhan"
        dob_pvr = drik.Date(1976, 9, 6)  # drik.Date takes (year, month, day)
        tob_str = "11:20:00"
        place_obj = drik.Place(Place="New Delhi, IN", latitude=28.621111, longitude=77.080278, timezone=5.5)
        ayanamsa_mode = "LAHIRI"

        # Set these values on the panchanga_widget instance
        # The Panchanga widget seems to expect these to be set on itself as it acts like a mini-horoscope container.
        # It inherits methods that would use these.
        self.panchanga_widget.date_of_birth = dob_pvr
        self.panchanga_widget.birth_date = datetime.date(1976,9,6) # It might also use this
        self.panchanga_widget.birth_time = tob_str
        self.panchanga_widget.Place = place_obj
        self.panchanga_widget.ayanamsa_mode = ayanamsa_mode
        self.panchanga_widget.language("en") # Set language, e.g., English

        # It seems compute_horoscope is the method to trigger calculations.
        # It might not need arguments if attributes are pre-set.
        self.panchanga_widget.compute_horoscope() # This should populate its internal data

        self.layout.addWidget(self.panchanga_widget)
        self.panchanga_widget.show() # Show the panchanga widget itself

def except_hook(cls, exception, traceback_obj): # Renamed traceback to traceback_obj
    print('Exception caught by custom hook:')
    # This will print the standard traceback information
    sys_excepthook_orig = getattr(sys, '__excepthook__', sys.excepthook) # Get original if it exists
    sys_excepthook_orig(cls, exception, traceback_obj)

sys.excepthook = except_hook # Set our custom exception hook

App = QApplication(sys.argv)
launcher = PanchangaLauncher()
# launcher.show() # The launcher itself doesn't need to be shown if Panchanga is shown directly
sys.exit(App.exec())