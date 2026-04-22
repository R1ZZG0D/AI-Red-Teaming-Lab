from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lab.shared.config import Settings
from lab.shared.database import initialize_lab_state, reset_database


def main() -> None:
    parser = argparse.ArgumentParser(description="Initialize or reset the shared lab database.")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete the SQLite database before recreating it.",
    )
    args = parser.parse_args()

    settings = Settings.from_env()
    if args.reset:
        reset_database(settings.db_path)
    initialize_lab_state(settings)
    print(f"Initialized lab database at {settings.db_path}")


if __name__ == "__main__":
    main()
