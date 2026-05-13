#!/usr/bin/env python3
import os
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

os.environ.setdefault("MINIMEAL_STORAGE_MODE", "dynamodb")
os.environ.setdefault("MINIMEAL_USERS_TABLE", "minimeal-users")
os.environ.setdefault("MINIMEAL_MEALS_TABLE", "minimeal-meals")

from app.services.storage import get_storage  # noqa: E402


def main():
    storage = get_storage()
    storage.initialize()

    print("minimeal AWS setup complete")
    print(f"backend: {storage.active_backend}")
    print(f"users_table: {storage.users_table_name}")
    print(f"meals_table: {storage.meals_table_name}")
    print("seeded_accounts:")
    for account in storage.list_seeded_accounts():
        print(
            f"  - {account['display_name']}: "
            f"{account['username']} / {account['password']}"
        )


if __name__ == "__main__":
    main()
