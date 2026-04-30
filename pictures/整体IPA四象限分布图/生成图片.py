from pathlib import Path
import sys

PICTURES_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PICTURES_ROOT))

from build_all import build_single


if __name__ == "__main__":
    build_single(Path(__file__).resolve().parent.name)
