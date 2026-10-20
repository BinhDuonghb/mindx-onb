#!/usr/bin/env python3
"""
Run pytest and capture output to timestamped evidence log.
Usage: python run_tests.py [pytest_args]
Example: python run_tests.py .\tests\integrations\KB\ -v --tb=short
"""
import subprocess
import sys
from datetime import datetime
from pathlib import Path

def main():
    # Create logs directory if it doesn't exist
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    # Generate timestamped log filename
    timestamp = datetime.now().strftime("%Y%m%d")
    log_file = logs_dir / f"pytest_{timestamp}.log"

    # Build pytest command using the current Python interpreter (respects venv)
    pytest_args = sys.argv[1:] if len(sys.argv) > 1 else ["tests/"]
    cmd = [sys.executable, "-m", "pytest"] + pytest_args

    print(f"Running: {' '.join(cmd)}")
    print(f"Logging to: {log_file}\n")

    # Run pytest and capture output
    result = subprocess.run(cmd, capture_output=True, text=True)

    # Write to log file (append mode to preserve multiple runs same day)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"\n{'='*70}\n")
        f.write(f"Test run: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Command: {' '.join(cmd)}\n")
        f.write(f"{'='*70}\n\n")
        f.write(result.stdout)
        if result.stderr:
            f.write("\n--- STDERR ---\n")
            f.write(result.stderr)

    # Print to console as well
    print(result.stdout)
    if result.stderr:
        print("--- STDERR ---", file=sys.stderr)
        print(result.stderr, file=sys.stderr)

    return result.returncode

if __name__ == "__main__":
    sys.exit(main())
