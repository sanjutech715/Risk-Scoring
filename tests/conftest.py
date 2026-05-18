import sys
from pathlib import Path

# Ensure both the project root and src directory are on sys.path for test imports.
ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
for path in (str(ROOT), str(SRC)):
    if path not in sys.path:
        sys.path.insert(0, path)
