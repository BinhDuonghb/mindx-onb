from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = BASE_DIR / "data"

TICKETS_FILE = DATA_DIR / "tickets.json"
TEST_TICKETS_FILE = DATA_DIR / "test_tickets.json"  


def ensure_storage():
    DATA_DIR.mkdir(exist_ok=True)

    if not TICKETS_FILE.exists():
        TICKETS_FILE.write_text(
            "[]",
            encoding="utf-8"
        )

    if not TEST_TICKETS_FILE.exists():
        TEST_TICKETS_FILE.write_text(
            "[]",
            encoding="utf-8"
        )