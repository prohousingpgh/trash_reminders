#!/usr/bin/env python3
"""Initialize the SQLite database."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.db import get_connection, init_db


def main() -> None:
    conn = get_connection()
    init_db(conn)
    conn.close()
    print("Database initialized.")


if __name__ == "__main__":
    main()
