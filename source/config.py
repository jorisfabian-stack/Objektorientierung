"""Central configuration for data paths used across the app.

Put shared constants here so modules import paths from a single place.
"""
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_ROOT = PROJECT_ROOT / "data"
PICTURE_ROOT = DATA_ROOT / "pictures"
EKG_ROOT = DATA_ROOT / "ekg_data"
ACTIVITY_FILE = DATA_ROOT / "activity.csv"
