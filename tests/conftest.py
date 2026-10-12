import os
import sys

# The project is a flat set of scripts at the repository root (utils.py,
# fdroid_data_exporter.py...), so make them importable from the tests.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
