from pathlib import Path
import sys


STAGING_DIR = Path(__file__).resolve().parents[1]
if str(STAGING_DIR) not in sys.path:
    sys.path.insert(0, str(STAGING_DIR))
