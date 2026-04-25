# tests/conftest.py — pytest configuration
import sys
from pathlib import Path

# Make project root importable
sys.path.insert(0, str(Path(__file__).parents[1]))
