"""Add a teacher account without storing a plaintext password."""

import getpass
import json
import os
import tempfile
from pathlib import Path

from auth import TEACHERS_FILE, make_password_record


def main() -> None:
    username = input("Teacher username: ").strip()
    if not username:
        raise SystemExit("Username cannot be empty")

    password = getpass.getpass("Teacher password: ")
    confirmation = getpass.getpass("Confirm password: ")
    if not password:
        raise SystemExit("Password cannot be empty")
    if password != confirmation:
        raise SystemExit("Passwords do not match")

    credentials_path = Path(
        os.environ.get("TEACHERS_FILE", str(TEACHERS_FILE))
    )
    try:
        records = json.loads(credentials_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        records = []

    if not isinstance(records, list):
        raise SystemExit("Teacher credentials file must contain a JSON list")
    if any(record.get("username") == username for record in records if isinstance(record, dict)):
        raise SystemExit("That username already exists")

    records.append(make_password_record(username, password))
    credentials_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=credentials_path.parent,
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            json.dump(records, temporary_file, indent=2)
            temporary_file.write("\n")
        temporary_path.replace(credentials_path)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)

    print(f"Teacher account created: {username}")


if __name__ == "__main__":
    main()