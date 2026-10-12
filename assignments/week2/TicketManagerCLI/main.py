from ticket_manager.cli import run_cli
from ticket_manager.config import ensure_storage


if __name__ == "__main__":
    ensure_storage()
    raise SystemExit(run_cli())